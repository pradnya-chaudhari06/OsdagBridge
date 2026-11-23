"""Drive the real OsdagBridge desktop window off-screen and generate a report.

This reproduces the manual workflow

    open OsdagBridge -> fill the Input Dock -> Design -> Generate Report -> save PDF

without a visible display (Qt ``offscreen`` platform).  It uses the real
``CustomWindow``, the real design worker code path (``backend.set_input`` +
``backend.design``), the real Output Dock figure capture
(``OutputDock._on_report_clicked``) and the real ``ReportOptionsDialog
.build_request`` -- only the two *modal* steps (the options dialog's ``exec``
and the "Save PDF" file picker) are replaced by programmatic equivalents, and
message boxes are logged instead of blocking.

Usage (inside the ``osdagbridge-env`` conda environment):

    python scripts/report_harness/generate_report_offscreen.py CASE.json OUT.pdf

``CASE.json`` holds only the values a user types into the Input Dock (see
``sample_case.json``); every other input keeps the application's own defaults.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback

# HARNESS_PLATFORM=windows uses a real (but off-screen positioned) window so
# that the OpenCASCADE 3D view can create an OpenGL context and the 3D CAD
# figures are captured as well.  The default "offscreen" platform needs no
# display at all but cannot render the OpenGL 3D views.
os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("HARNESS_PLATFORM", "offscreen"))


def _log(msg: str) -> None:
    print(f"[harness] {msg}", flush=True)


def main(case_path: str, out_pdf: str) -> int:
    case = json.load(open(case_path, encoding="utf-8"))

    # Importing the desktop entry module runs the same start-up steps as the
    # application (DLL paths, section databases).
    import osdagbridge.desktop.__main__ as app_main  # noqa: F401
    from PySide6.QtWidgets import QApplication, QLineEdit

    import osdagbridge
    _log(f"osdagbridge package path: {list(osdagbridge.__path__)}")

    from osdagbridge.desktop.ui.dialogs import custom_messagebox
    from osdagbridge.desktop.ui.template_page import CustomWindow
    from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge
    from osdagbridge.core.utils.common import (
        KEY_CARRIAGEWAY_WIDTH, KEY_PROJECT_LOCATION, KEY_SKEW_ANGLE, KEY_SPAN,
    )

    # --- message boxes would block forever off-screen: log them instead ------
    def _mb_exec(self):
        try:
            _log(f"MessageBox: {self.windowTitle()} :: {getattr(self, 'text', lambda: '')()}")
        except Exception:
            _log("MessageBox shown")
        return "Continue"
    custom_messagebox.CustomMessageBox.exec = _mb_exec

    app = QApplication.instance() or QApplication(sys.argv)
    stylesheet = app_main.load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)
    win = CustomWindow("OsdagBridge", PlateGirderBridge)
    win.resize(1600, 1000)
    if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
        win.move(-4000, -4000)          # keep the real window out of sight
    win.show()
    app.processEvents()

    # --- Input Dock: type the required values ----------------------------------
    def _type(key, value):
        w = win.input_dock.findChild(QLineEdit, key)
        if w is None:
            raise RuntimeError(f"Input field {key!r} not found")
        w.setText(str(value))
        w.editingFinished.emit()
        app.processEvents()
        _log(f"input {key} = {value!r}")

    _type(KEY_SPAN, case["span_m"])
    _type(KEY_CARRIAGEWAY_WIDTH, case["carriageway_width_m"])
    _type(KEY_SKEW_ANGLE, case["skew_angle_deg"])

    # --- Project location: same lookup as ProjectLocationDialog ------------------
    from osdagbridge.core.bridge_types.plate_girder.ui_fields_project_location import (
        get_weather,
    )
    from osdagbridge.core.data.project_location.zone_lookup import get_zones_for_coordinates

    state, district = case["location"]["state"], case["location"]["district"]


    weather = get_weather(state, district)   # db injected by decorator
    if weather and (not weather.get("zone") or not weather.get("wind_speed")):
        lat, lon = weather.get("latitude"), weather.get("longitude")
        if lat is not None and lon is not None:
            zd = get_zones_for_coordinates(float(lat), float(lon))
            if not weather.get("zone") and zd.get("seismic_zone"):
                weather["zone"] = zd.get("seismic_zone")
                if zd.get("zone_factor"):
                    weather["z_value"] = zd.get("zone_factor")
            if not weather.get("wind_speed") and zd.get("wind_Vb"):
                weather["wind_speed"] = zd.get("wind_Vb")
    loc = {
        "method": "location_name",
        "data": {"state": state, "district": district},
        "weather_data": weather,
        "display_text": f"{district}, {state}",
        "show_display": True,
    }
    win.input_dock._update_input_dict(KEY_PROJECT_LOCATION, loc)
    _log(f"location = {district}, {state}; weather = {weather}")

    for key, value in (case.get("extra_inputs") or {}).items():
        win.input_dict[key] = value
        _log(f"extra input {key} = {value!r}")

    # --- Design (same worker thread as the Design button) ----------------------
    t0 = time.time()
    win.common_design_func("Design")
    while getattr(win, "_design_running", False):
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()
    _log(f"design finished in {time.time() - t0:.1f} s")
    if not getattr(win.backend, "output_dict", None) or not dict(win.backend.output_dict):
        _log("design produced no output_dict -- aborting")
        return 2

    # --- Generate Report ----------------------------------------------------------
    from osdagbridge.desktop.ui.dialogs.report_options import ReportOptionsDialog
    result_box = {}

    def _open_report_dialog(self, cad_generator=None):
        dlg = ReportOptionsDialog(parent=self)
        meta = case.get("report_metadata", {})
        for attr in ("project_name", "designer", "reviewer", "client", "group_name",
                     "report_version", "job_number"):
            if attr in meta and hasattr(dlg, attr):
                getattr(dlg, attr).setText(meta[attr])
        if "comments" in meta:
            dlg.comments.setPlainText(meta["comments"])
        request = dlg.build_request(os.path.abspath(out_pdf))
        _log(f"report sections = {request.options.sections}; "
             f"include_figures = {request.options.include_figures}")
        figs = (cad_generator or {}).get("figure_data", {})
        _log(f"captured figures: {sorted(k for k, v in figs.items() if v)}")
        dump = os.environ.get("HARNESS_DUMP")
        if dump:
            # Save the exact (payload, request) handed to generate_report so the
            # report can be rebuilt later without re-running the design
            # (scripts/report_harness/rebuild_report.py).
            import pickle
            from osdagbridge.core.reports import report_generator as rg
            real_generate = rg.generate_report

            def _dump_then_generate(payload, req):
                import copy
                snap = copy.copy(payload)
                snap.figure_data = dict(payload.figure_data)
                with open(dump, "wb") as fh:
                    pickle.dump({"payload": snap, "request": req}, fh)
                _log(f"payload dumped to {dump}")
                return real_generate(payload, req)
            rg.generate_report = _dump_then_generate
        result_box["result"] = self.backend.generate_design_report(request, cad_generator)

    CustomWindow.open_report_dialog = _open_report_dialog
    win.output_dock._on_report_clicked()
    res = result_box.get("result")
    _log(f"report result: {res}")
    ok = res is not None and getattr(res, "pdf_path", None)
    sys.stdout.flush()
    sys.stderr.flush()
    # Skip Qt/OpenCASCADE teardown (it can abort natively after the work is
    # done); the PDF has already been written.
    os._exit(0 if ok else 3)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    except Exception:
        traceback.print_exc()
        sys.exit(1)

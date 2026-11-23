# =============================================================================
# Chapter 3: Loads and Load Combinations
# Extracted from report_generator.py — DO NOT add business logic here.
# =============================================================================

from osdagbridge.core.utils.common import (
    KEY_CB_LOAD,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_PL_SELF_WEIGHT_FACTOR,
    KEY_RL_LOAD_VALUE,
    KEY_SL_DAMPING,
    KEY_SL_DEAD_LOAD_MODE,
    KEY_SL_DEAD_LOAD_VALUE,
    KEY_SL_HORIZONTAL_COEFF,
    KEY_SL_IMPORTANCE_FACTOR,
    KEY_SL_LIVE_LOAD_MODE,
    KEY_SL_LIVE_LOAD_VALUE,
    KEY_SL_SEISMIC_ZONE,
    KEY_SL_SOIL_TYPE,
    KEY_SL_SPECTRAL_COEFF,
    KEY_SL_TIME_PERIOD,
    KEY_SL_VERTICAL_COEFF,
    KEY_SL_ZONE_FACTOR,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_WC_MATERIAL,
    KEY_WC_THICKNESS,
    KEY_WL_AVG_EXPOSED_HEIGHT,
    KEY_WL_BASIC_WIND_SPEED,
    KEY_WL_HOURLY_MEAN_WIND,
    KEY_WL_HOURLY_WIND_PRESSURE,
    KEY_WL_LONGITUDINAL_WIND_FORCE,
    KEY_WL_TERRAIN_TYPE,
    KEY_WL_TRANSVERSE_WIND_FORCE,
    KEY_WL_VERTICAL_WIND_FORCE
)

from osdagbridge.core.reports.report_utils import _tex, _render_value
from osdagbridge.core.reports.latex_tables import build_longtable, fit_colspec, format_row, parse_colspec
from osdagbridge.core.reports import styles
from osdagbridge.core.reports.report_data import (
    braking_info,
    footway_info,
    selected_vehicles,
)

# -----------------------------------------------------------------------------
# Live load tables (Requirement: vehicle live load and footway live load are
# reported in two separate tables).  The data comes from report_data, which
# reads the vehicles actually ticked in Additional Inputs -> Loading -> Live
# Load; nothing is hard-coded here.
# -----------------------------------------------------------------------------
# Shown instead of an empty cell when a value is not in the design data.
_NA = r"\textit{Not available}"


def _or_na(text):
    """Rendered value, or 'Not available' when the source value is missing."""
    return text if str(text).strip() else _NA


def _num(v, nd=2, unit=""):
    if v is None:
        return "---"
    return f"{v:.{nd}f}" + (f" {unit}" if unit else "")


_VEHICLE_SPEC = r"|L{4.6cm}|C{2.6cm}|C{4.2cm}|C{3.4cm}|"


# The design pipeline has no IRC 6 Cl. 212 centrifugal-force calculation
# (IRC6_2017 only mentions it in load-combination comments).  The row states
# whether the force applies (straight bridge: not applicable) and never
# computes or estimates a value -- see report_data.centrifugal_text.
from osdagbridge.core.reports.report_data import (  # noqa: E402
    CENTRIFUGAL_NOT_APPLICABLE, CENTRIFUGAL_NOT_COMPUTED, centrifugal_text,
)


def vehicle_live_load_table(input_dict):
    """Table: Vehicle Live Load (one row per selected vehicle class)."""
    vehicles = selected_vehicles(input_dict)
    brk = braking_info(input_dict)

    rows = []
    if not vehicles:
        rows.append(r"\multicolumn{4}{|l|}{\textit{No vehicle class selected in "
                    r"Additional Inputs $\rightarrow$ Loading $\rightarrow$ Live Load.}} \\[6pt]"
                    "\n" r"\hline")
    for v in vehicles:
        if v.braking_considered is None:
            braking = "As per IRC 6 Cl. 211.2"
        else:
            braking = "Yes" if v.braking_considered else "No"
        total = _num(v.total_load_kN, 1)
        if v.total_load_kN is None:
            total = r"---\textsuperscript{\dag}"
        imf = (f"{v.impact_factor:.3f} ({_tex(v.impact_clause)})"
               if v.impact_factor is not None else "---")
        rows.append(format_row([_tex(v.name), total, imf, _tex(braking)]))

    lane_txt = ""
    if brk.lanes is not None:
        lane_txt = f"{brk.lanes} design lane(s)" + (f" [{brk.lanes_source}]" if brk.lanes_source else "")
    if brk.force_kN is not None:
        bforce = f"{brk.force_kN:.2f} kN ({brk.force_t:.2f} t) for {lane_txt}"
    else:
        # Never a raw Python error: the reason is plain text from report_data.
        bforce = "Not available --- " + (brk.unavailable_reason or "the braking force was not computed") + "."
    ecc = _num(brk.eccentricity_m, 2, "m above top of deck")

    # Value cells span columns 2-4; give them exactly that width (after the
    # width fit) so the spanning cell never widens the table.
    spec = fit_colspec(_VEHICLE_SPEC)
    w = parse_colspec(spec)["widths_cm"]
    sep_cm = styles.TABLE["tabcolsep_pt"] / styles.PT_PER_CM
    rule_cm = styles.TABLE["arrayrulewidth_pt"] / styles.PT_PER_CM
    # floor + small margin: a spanning cell even 0.01 cm wider than the
    # spanned columns widens the last column and misaligns the header shading
    span_w = int((sum(w[1:]) + 4 * sep_cm + 2 * rule_cm) * 100) / 100.0 - 0.02
    for label, value in ((r"Braking load (IRC 6 Cl. 211.2)", bforce),
                         (r"Braking load eccentricity (IRC 6 Cl. 211.3)", ecc),
                         (r"Centrifugal force (IRC 6 Cl. 212)", centrifugal_text(input_dict))):
        rows.append(r"\textbf{" + label + r"} & \multicolumn{3}{p{" + f"{span_w:.2f}"
                    + r"cm}|}{" + _tex(value) + r"} \\[6pt]" "\n" r"\hline")

    table = build_longtable(
        _VEHICLE_SPEC,
        ["Vehicle Class", "Total Load (kN)", "Impact Factor (1+IM)", "Braking Load Considered?"],
        "\n".join(rows),
        caption=r"\textbf{Vehicle Live Load (LL)}",
    )
    notes = [r"\noindent\textit{Note: Only the vehicle classes selected by the user are listed. "
             r"Total load = sum of the axle / track loads of the IRC 6 Cl. 204 vehicle definition.}"]
    if any(v.total_load_kN is None for v in vehicles):
        notes.append(r"\par\noindent\textit{\textsuperscript{\dag} Vehicle not defined in the OsdagBridge "
                     r"IRC 6 vehicle library --- total load not available.}")
    return table + "\n" + "\n".join(notes) + "\n"


def footway_live_load_table(input_dict):
    """Table: Footway (footpath) Live Load."""
    fw = footway_info(input_dict)
    na = r"\textit{Not applicable (no footpath provided)}"
    rows = [format_row([r"\textnormal{Footpath Provided}", _tex(fw.provision)])]
    if fw.applicable:
        rows.append(format_row([r"\textnormal{Number of Footpaths}",
                                str(fw.n_footpaths) if fw.n_footpaths is not None else "---"]))
        rows.append(format_row([r"\textnormal{Footpath Width}", _num(fw.width_m, 3, "m")]))
        rows.append(format_row([r"\textnormal{Footway Load Definition}", _tex(fw.pressure_mode)]))
        if fw.pressure_kN_m2 is not None:
            p = (f"{fw.pressure_kN_m2:.3f} kN/m" + r"\textsuperscript{2}"
                 + f" ({_tex(fw.pressure_source)})")
        else:
            p = "---"
        rows.append(format_row([r"\textnormal{Footway Live Load Intensity}", p]))
    else:
        rows.append(format_row([r"\textnormal{Footway Live Load Intensity}", na]))
    return build_longtable(
        r"|L{5.5cm}|p{10.0cm}|",
        ["Parameter", "Value"],
        "\n".join(rows),
        caption=r"\textbf{Footway Live Load (FPLL)}",
    )


def ch3_loads(input_dict):
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017

    # Vz / Pz — prefer stored computed values; fall back to IRC6 Table 12
    vz_val = input_dict.get(KEY_WL_HOURLY_MEAN_WIND)
    pz_val = input_dict.get(KEY_WL_HOURLY_WIND_PRESSURE)
    if not vz_val or not pz_val:
        try:
            _vb  = input_dict.get(KEY_WL_BASIC_WIND_SPEED) or input_dict.get('wind_speed')
            _h   = input_dict.get(KEY_WL_AVG_EXPOSED_HEIGHT)
            _ter = {
                "Plain Terrain": "plain",
                "Terrain with Obstructions": "obstructed",
            }.get(str(input_dict.get(KEY_WL_TERRAIN_TYPE, "")).strip(), "plain")
            _res = IRC6_2017.table_12(float(_h), _ter, float(_vb))
            if not vz_val:
                vz_val = _res.get("Vz")
            if not pz_val:
                pz_val = _res.get("Pz")
        except Exception:
            pass
    vz_str = f"{float(vz_val):.2f} m/s" if vz_val not in (None, "") else "N/A"
    pz_str = f"{float(pz_val):.2f} N/m²" if pz_val not in (None, "") else "N/A"

    # Table 3.5 — Seismic: prefer stored computed values; fall back to IRC6 cl_218_5_1
    sl_zone_factor = input_dict.get(KEY_SL_ZONE_FACTOR)
    sl_spectral    = input_dict.get(KEY_SL_SPECTRAL_COEFF)
    sl_ah          = input_dict.get(KEY_SL_HORIZONTAL_COEFF)
    sl_av          = input_dict.get(KEY_SL_VERTICAL_COEFF)
    if not sl_ah or not sl_zone_factor:
        try:
            _zone = input_dict.get(KEY_SL_SEISMIC_ZONE) or input_dict.get('seismic_zone')
            _zmap = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V"}
            _z    = str(_zone).strip().upper()
            if _z.isdigit():
                _z = _zmap.get(_z)
            _smap = {"Type I – Rocky or Hard": 1, "Type II – Medium Soil": 2, "Type III – Soft Soil": 3}
            _st   = _smap.get(str(input_dict.get(KEY_SL_SOIL_TYPE, "")), 1)
            _tp   = input_dict.get(KEY_SL_TIME_PERIOD)
            _damp = input_dict.get(KEY_SL_DAMPING) or "5"
            _dl_v = input_dict.get(KEY_SL_DEAD_LOAD_VALUE)
            _ll_v = input_dict.get(KEY_SL_LIVE_LOAD_VALUE)
            _dead = float(_dl_v) if str(input_dict.get(KEY_SL_DEAD_LOAD_MODE, "")) == "Custom" and _dl_v else 0.0
            _live = float(_ll_v) if str(input_dict.get(KEY_SL_LIVE_LOAD_MODE, "")) == "Custom" and _ll_v else 0.0
            _res  = IRC6_2017.cl_218_5_1(zone=f"Zone {_z}", soil_type=_st, dead_load_kN=_dead,
                        live_load_kN=_live, period_T=float(_tp) if _tp else None,
                        damping_percent=float(_damp))
            if not sl_zone_factor:
                sl_zone_factor = _res.get("Z")
            if not sl_spectral:
                sl_spectral    = _res.get("Sa_g_adjusted")
            if not sl_ah:
                sl_ah          = _res.get("Ah")
            if not sl_av:
                sl_av          = round(_res.get("Ah", 0) * 2 / 3, 4)
        except Exception:
            pass

    def _sl(v, unit=""):
        return f"{float(v):.4f}{unit}" if v not in (None, "") else "N/A"

    # Table 3.6 — Temperature: compute effective bridge temp range from shade temps
    tl_temp_min = tl_temp_max = tl_rise = tl_fall = "N/A"
    try:
        _tmax = input_dict.get(KEY_TL_HIGHEST_MAX_TEMP) or input_dict.get('shade_temp_max')
        _tmin = input_dict.get(KEY_TL_LOWEST_MIN_TEMP)  or input_dict.get('shade_temp_min')
        if _tmax and _tmin:
            _res    = IRC6_2017.cl_215_2_effective_bridge_temperature(
                          float(_tmax), float(_tmin), 'metallic', False)
            _bt_min = _res.get('T_min', 0)
            _bt_max = _res.get('T_max', 0)
            _mean   = (_bt_max + _bt_min) / 2.0
            tl_temp_min = f"{_bt_min:.2f}"
            tl_temp_max = f"{_bt_max:.2f}"
            tl_rise     = f"{_bt_max - _mean:.2f}"
            tl_fall     = f"{_mean - _bt_min:.2f}"
    except Exception:
        pass

    # --- Table 3.7: Load Combinations (dynamically generated from IRC 6) ---
    _LOAD_LABEL_MAP = {
        'dead_load':         'DL',
        'surfacing':         'SIDL',
        'live_load':         'LL',
        'wind_load':         'WL',
        'thermal_load':      'TL',
        'vehicle_collision': 'VC',
        'barge_impact':      'BI',
        'floating_bodies':   'FB',
        'seismic':           'EQ',
    }

    def _fmt_factors(factors):
        """Format a factors dict into a compact load-case string for the table."""
        parts = []
        for load, val in factors.items():
            label = _LOAD_LABEL_MAP.get(load, load.upper())
            if isinstance(val, dict):  # permanent load with adding/relieving
                add = val.get('adding')
                rel = val.get('relieving')
                add_s = f"{add:.2f}" if add is not None else '--'
                rel_s = f"{rel:.2f}" if rel is not None else '--'
                parts.append(f"{label}({add_s}/{rel_s})")
            else:
                if val is None:
                    continue  # skip N/A factors
                parts.append(f"{label}({val:.2f})")
        return ' + '.join(parts)

    uls_combos = IRC6_2017.uls_load_combinations()
    sls_combos = IRC6_2017.sls_load_combinations()
    lc_rows = []
    for i, combo in enumerate(uls_combos, start=1):
        cases = _fmt_factors(combo['factors'])
        lc_rows.append(
            f"ULS-{i:02d}" + r" & " + cases + r" \\[6pt]" + "\n"
            + r"\hline"
        )
    for i, combo in enumerate(sls_combos, start=1):
        cases = _fmt_factors(combo['factors'])
        lc_rows.append(
            f"SLS-{i:02d}" + r" & " + cases + r" \\[6pt]" + "\n"
            + r"\hline"
        )

    lc_rows_str = "\n".join(lc_rows)

    return r"""
\chapter{Loads and Load Combinations}

This section summarizes all loads applied to the bridge and the load combinations considered for analysis and design.

\vspace{1em}
""" + build_longtable(
    r"|L{5.5cm}|p{10.0cm}|",
    r"\textbf{parameter} & \textbf{value}",
    r"""\textnormal{Steel Self-Weight Applied} & """ + (_render_value(input_dict, KEY_MATERIAL_GIRDER_DENSITY, ' kN/m\\textsuperscript{3}')) + r""" \\[6pt]
\hline
\textnormal{Concrete Deck Weight} & """ + (_render_value(input_dict, KEY_MATERIAL_DECK_DENSITY, ' kN/m\\textsuperscript{3}')) + r""" \\[6pt]
\hline
\textnormal{Self-Weight Factor} & """ + (_render_value(input_dict, KEY_PL_SELF_WEIGHT_FACTOR)) + r""" \\[6pt]
\hline
""",
    caption=r"\textbf{Dead Load -- Self Weight}",
) + r"""

\vspace{1em}
""" + build_longtable(
    r"|L{5.5cm}|p{10.0cm}|",
    r"\textbf{parameter} & \textbf{value}",
    r"""\textnormal{Wearing Course Load} & """ + (_render_value(input_dict, KEY_WC_MATERIAL)) + r""" x """ + (_render_value(input_dict, KEY_WC_THICKNESS)) + r""" \\[6pt]
\hline
\textnormal{Additional SIDL (Crash Barrier)} & """ + (_render_value(input_dict, KEY_CB_LOAD)) + r""" kN/m per barrier \\[6pt]
\hline
\textnormal{Railing Load} & """ + (_render_value(input_dict, KEY_RL_LOAD_VALUE)) + r""" kN/m\sdstar{} \\[6pt]
\hline
""",
    caption=r"\textbf{Dead Load for Surfacing (DW)}",
) + r"""

\vspace{1em}
""" + vehicle_live_load_table(input_dict) + r"""

\vspace{1em}
""" + footway_live_load_table(input_dict) + r"""

\vspace{1em}
""" + build_longtable(
    r"|L{5.5cm}|p{10.0cm}|",
    r"\textbf{parameter} & \textbf{value}",
    r"""\textnormal{Basic Wind Speed, Vb} & """ + (_render_value(input_dict,'wind_speed', ' m/s')) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Terrain Type} & """ + (_render_value(input_dict, KEY_WL_TERRAIN_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Average Exposed Height, H (m)} & """ + (_render_value(input_dict, KEY_WL_AVG_EXPOSED_HEIGHT, ' m')) + r""" \\[6pt]
\hline
\textnormal{Hourly Mean Wind Speed, Vz} & """ + (_tex(vz_str) if vz_str != "N/A" else _NA) + r""" \\[6pt]
\hline
\textnormal{Hourly Wind Pressure, Pz} & """ + (_tex(pz_str) if pz_str != "N/A" else _NA) + r""" \\[6pt]
\hline
\textnormal{Transverse Wind Force} & """ + _or_na(_render_value(input_dict, KEY_WL_TRANSVERSE_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\textnormal{Longitudinal Wind Force} & """ + _or_na(_render_value(input_dict, KEY_WL_LONGITUDINAL_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\textnormal{Vertical Wind Force} & """ + _or_na(_render_value(input_dict, KEY_WL_VERTICAL_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
""",
    caption=r"\textbf{Wind Load (WL) --- per IRC 6}",
) + r"""

\vspace{1em}
""" + build_longtable(
    r"|L{5.5cm}|p{10.0cm}|",
    r"\textbf{parameter} & \textbf{value}",
    r"""\textnormal{Seismic Zone} & """ + (_render_value(input_dict,'seismic_zone')) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Zone Factor, Z} & """ + (_render_value(input_dict, KEY_SL_ZONE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Importance Factor, I} & """ + (_render_value(input_dict, KEY_SL_IMPORTANCE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Type of Soil} & """ + (_render_value(input_dict, KEY_SL_SOIL_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Sa/g} & """ + (_render_value(input_dict, KEY_SL_SPECTRAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Coefficient, Ah} & """ + (_render_value(input_dict, KEY_SL_HORIZONTAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Vertical Seismic Coefficient, Av} & """ + (_render_value(input_dict, KEY_SL_VERTICAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Force (longitudinal)} & """ + _NA + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Force (transverse)} & """ + _NA + r""" \\[6pt]
\hline
""",
    caption=r"\textbf{Earthquake Load (EL) --- per IRC 6}",
) + r"""

\vspace{1em}
""" + build_longtable(
    r"|L{5.5cm}|p{10.0cm}|",
    r"\textbf{parameter} & \textbf{value}",
    r"""\textnormal{Maximum Shade Temperature} & """ + (_render_value(input_dict,'shade_temp_max')) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Minimum Shade Temperature} & """ + (_render_value(input_dict,'shade_temp_min')) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Effective Bridge Temp. Range} & """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MIN)) + r""" to """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MAX)) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Temperature Rise / Fall for Design} & +""" + (_render_value(input_dict, KEY_TL_TEMP_RISE)) + r""" $^\circ$C / \textminus{}""" + (_render_value(input_dict, KEY_TL_TEMP_FALL)) + r""" $^\circ$C \\[6pt]
\hline
""",
    caption=r"\textbf{Temperature Load (TL) --- per IRC 6}",
) + r"""

\vspace{1em}
""" + build_longtable(
    r"|C{4.0cm}|p{11.5cm}|",
    r"\textbf{Combination ID} & \textbf{Load Cases}",
    r"""""" + lc_rows_str + r"""
""",
    caption=r"\textbf{Load Combinations}",
) + r"""

\noindent\textit{Note: All IRC 6 load combinations are auto-generated by OsdagBridge. User-defined custom combinations, if any, are appended.}
"""



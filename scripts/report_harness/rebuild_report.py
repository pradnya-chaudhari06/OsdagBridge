"""Rebuild a report PDF from a payload saved by generate_report_offscreen.py.

    python scripts/report_harness/rebuild_report.py PAYLOAD.pkl OUT.pdf

The payload contains the design ``input_dict`` / ``output_dict`` and the
captured figure bytes exactly as they were handed to ``generate_report`` by the
application, so the report can be regenerated with the current report code
without re-running the (slow) structural design.  Only load pickle files that
you created yourself.
"""
from __future__ import annotations

import os
import pickle
import sys


def main(pkl_path: str, out_pdf: str) -> int:
    from osdagbridge.core.reports.report_generator import generate_report

    with open(pkl_path, "rb") as fh:
        data = pickle.load(fh)
    payload, request = data["payload"], data["request"]
    out_pdf = os.path.abspath(out_pdf)
    request.output_dir = os.path.dirname(out_pdf)
    request.file_stem = os.path.splitext(os.path.basename(out_pdf))[0]
    result = generate_report(payload, request)
    print(f"[rebuild] {result}")
    return 0 if result.pdf_path else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

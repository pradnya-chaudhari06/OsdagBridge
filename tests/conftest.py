"""Shared pytest configuration.

On Windows, a conda environment that is *not activated* (e.g. pytest started
with the full path to the environment's python.exe) does not have
``<prefix>/Library/bin`` on the DLL search path; numpy / matplotlib then abort
natively (0xc06d007f) on first use.  The desktop entry point solves this in
``osdagbridge.desktop.__main__``; the same registration is done here so the
test suite behaves identically whether or not the environment is activated.
"""
import os
import sys


def _register_conda_dll_directories():
    if os.name != "nt":
        return
    for sub in ("Library/bin", "Library/mingw-w64/bin", "Library/usr/bin", "DLLs", ""):
        path = os.path.join(sys.prefix, sub)
        if os.path.isdir(path):
            try:
                os.add_dll_directory(path)
            except (OSError, AttributeError):
                pass
            if path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")


_register_conda_dll_directories()

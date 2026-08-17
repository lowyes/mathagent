#!/usr/bin/env python3
"""Report visualization-library availability in the active Python environment."""

from __future__ import annotations

import importlib
import json
import platform
import shutil
import sys
from pathlib import Path


PACKAGES = ("numpy", "pandas", "matplotlib", "seaborn", "plotly", "networkx", "geopandas")


def find_matlab() -> str | None:
    """Find MATLAB on PATH or in common Windows installation locations."""
    on_path = shutil.which("matlab")
    if on_path:
        return on_path
    if platform.system() != "Windows":
        return None
    candidates: list[Path] = []
    for root in (Path("C:/Program Files/MATLAB"), Path("D:/Program Files/MATLAB"), Path("D:/MATLAB")):
        if root.is_dir():
            candidates.extend(root.glob("R*/bin/matlab.exe"))
    return str(sorted(candidates, reverse=True)[0]) if candidates else None


def package_status(name: str) -> dict[str, object]:
    try:
        module = importlib.import_module(name)
    except Exception as exc:  # import failures are part of the diagnostic result
        return {"available": False, "version": None, "error": f"{type(exc).__name__}: {exc}"}
    return {"available": True, "version": getattr(module, "__version__", "unknown"), "error": None}


def main() -> None:
    report = {
        "python": {"executable": sys.executable, "version": platform.python_version()},
        "packages": {name: package_status(name) for name in PACKAGES},
        "executables": {
            "matlab": find_matlab(),
            "pdftoppm": shutil.which("pdftoppm"),
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compile the graduate modeling LaTeX paper twice and write a QA report."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


WARNING_MARKERS = (
    "Overfull \\hbox",
    "Underfull \\hbox",
    "LaTeX Warning: Reference",
    "LaTeX Warning: Citation",
    "There were undefined references",
    "Missing character:",
)


def compile_paper(paper_dir: Path, source: str, engine: str) -> dict[str, object]:
    root = paper_dir.resolve()
    source_path = root / source
    executable = shutil.which(engine)
    if not source_path.is_file():
        return {"ok": False, "error": f"缺少 LaTeX 主文件：{source_path}"}
    if executable is None:
        return {"ok": False, "error": f"找不到编译器：{engine}"}

    command = [
        executable,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        source_path.name,
    ]
    passes: list[dict[str, object]] = []
    combined_output: list[str] = []
    for pass_no in (1, 2):
        process = subprocess.run(
            command,
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=180,
            check=False,
        )
        output = process.stdout + "\n" + process.stderr
        combined_output.append(f"===== PASS {pass_no} =====\n{output}")
        passes.append({"pass": pass_no, "returncode": process.returncode})
        if process.returncode != 0:
            break

    log_text = "\n".join(combined_output)
    (root / "编译过程.log").write_text(log_text, encoding="utf-8")
    tex_log_path = root / (source_path.stem + ".log")
    tex_log = tex_log_path.read_text(encoding="utf-8", errors="replace") if tex_log_path.is_file() else ""
    warnings = [line.strip() for line in tex_log.splitlines() if any(marker in line for marker in WARNING_MARKERS)]
    pdf_path = root / (source_path.stem + ".pdf")
    ok = len(passes) == 2 and all(item["returncode"] == 0 for item in passes) and pdf_path.is_file()
    return {
        "ok": ok,
        "engine": executable,
        "source": source_path.name,
        "pdf": pdf_path.name if pdf_path.is_file() else None,
        "passes": passes,
        "warnings": warnings,
        "visual_review_required": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper_dir", type=Path)
    parser.add_argument("--source", default="main.tex")
    parser.add_argument("--engine", default="xelatex")
    args = parser.parse_args()
    report = compile_paper(args.paper_dir, args.source, args.engine)
    report_path = args.paper_dir / "编译报告.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report.get("ok") else 1)


if __name__ == "__main__":
    main()

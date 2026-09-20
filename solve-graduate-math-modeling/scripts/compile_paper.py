#!/usr/bin/env python3
"""Compile the graduate modeling LaTeX paper twice and write a QA report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


WARNING_MARKERS = (
    "Overfull \\hbox",
    "Underfull \\hbox",
    "LaTeX Warning: Reference",
    "LaTeX Warning: Citation",
    "There were undefined references",
    "Missing character:",
)

PROJECT_INPUT_SUFFIXES = {
    ".tex", ".cls", ".sty", ".bib", ".bst",
    ".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps", ".tif", ".tiff",
}

TEXLIVE_SEARCH_ROOTS = (
    Path("D:/texlive-min"),
    Path("D:/texlive"),
    Path("C:/texlive-min"),
    Path("C:/texlive"),
)


def resolve_xelatex(explicit: Path | None = None) -> tuple[str | None, str]:
    """Resolve XeLaTeX without requiring the current process PATH to be refreshed."""
    if explicit is not None:
        candidate = explicit.expanduser().resolve()
        if candidate.is_file():
            return str(candidate), "explicit"
        return None, "explicit-missing"

    on_path = shutil.which("xelatex") or shutil.which("xelatex.exe")
    if on_path:
        return on_path, "path"

    environment_candidates: list[Path] = []
    for variable in ("TEXLIVE_BIN", "TEXLIVE_ROOT"):
        value = os.environ.get(variable, "").strip()
        if not value:
            continue
        base = Path(value).expanduser()
        environment_candidates.extend((base / "xelatex.exe", base / "bin" / "windows" / "xelatex.exe"))
    for candidate in environment_candidates:
        if candidate.is_file():
            return str(candidate.resolve()), "environment"

    discovered: list[Path] = []
    for root in TEXLIVE_SEARCH_ROOTS:
        if root.is_dir():
            discovered.extend(root.glob("*/bin/windows/xelatex.exe"))
    discovered.sort(key=lambda path: path.parent.parent.parent.name, reverse=True)
    for candidate in discovered:
        if candidate.is_file():
            return str(candidate.resolve()), "texlive-auto-discovery"

    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    program_files = os.environ.get("ProgramFiles", "").strip()
    miktex_candidates = []
    if local_app_data:
        miktex_candidates.append(Path(local_app_data) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64" / "xelatex.exe")
    if program_files:
        miktex_candidates.append(Path(program_files) / "MiKTeX" / "miktex" / "bin" / "x64" / "xelatex.exe")
    for candidate in miktex_candidates:
        if candidate.is_file():
            return str(candidate.resolve()), "miktex-auto-discovery"
    return None, "not-found"


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def pdf_structure_ok(path: Path) -> bool:
    """Perform a dependency-free structural smoke check for a generated PDF."""
    if not path.is_file():
        return False
    data = path.read_bytes()
    tail = data[-8192:]
    return (
        data.startswith(b"%PDF-")
        and b"/Root" in data
        and b"xref" in data
        and b"startxref" in tail
        and b"%%EOF" in tail
    )


def collect_project_inputs(
    paper_root: Path,
    project_root: Path,
    source_path: Path,
    pdf_path: Path,
) -> tuple[list[dict[str, str]], bool]:
    """Hash project-owned inputs recorded by XeLaTeX's ``.fls`` file."""
    fls_path = paper_root / f"{source_path.stem}.fls"
    candidates: set[Path] = {source_path.resolve()}
    recorder_ok = fls_path.is_file()
    if recorder_ok:
        for line in fls_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("INPUT "):
                continue
            raw = line[6:].strip()
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = paper_root / candidate
            try:
                candidate = candidate.resolve()
            except OSError:
                continue
            if (
                candidate.is_file()
                and candidate != pdf_path.resolve()
                and (candidate == project_root or project_root in candidate.parents)
                and candidate.suffix.lower() in PROJECT_INPUT_SUFFIXES
            ):
                candidates.add(candidate)

    records = [
        {
            "path": path.relative_to(project_root).as_posix(),
            "sha256": sha256(path),
        }
        for path in sorted(candidates)
    ]
    return records, recorder_ok


def compile_paper(
    paper_dir: Path,
    source: str,
    engine: str,
    compiler: Path | None = None,
) -> dict[str, object]:
    root = paper_dir.resolve()
    source_path = (root / source).resolve()
    if source_path != root and root not in source_path.parents:
        return {"ok": False, "error": f"LaTeX 主文件越出论文目录：{source}"}
    if source_path.suffix.lower() != ".tex":
        return {"ok": False, "error": f"LaTeX 主文件必须使用 .tex 扩展名：{source_path}"}
    executable, engine_resolution = resolve_xelatex(compiler)
    if not source_path.is_file():
        return {"ok": False, "error": f"缺少 LaTeX 主文件：{source_path}"}
    if executable is None:
        location_hint = f"（显式路径：{compiler}）" if compiler is not None else ""
        return {
            "ok": False,
            "error": (
                f"找不到编译器：{engine}{location_hint}。请将 XeLaTeX 加入 PATH，"
                "或使用 --compiler 指定 xelatex.exe；脚本也会自动检查 C:/D: 下常见 TeX Live 目录。"
            ),
            "engine_resolution": engine_resolution,
        }

    source_relative = source_path.relative_to(root).as_posix()
    command = [
        executable,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-recorder",
        source_relative,
    ]
    # Recorder 是编译证据的一部分。先删除旧 .fls，确保后续输入清单来自
    # 本次运行，而不是上一次成功编译遗留的辅助文件。
    fls_path = root / f"{source_path.stem}.fls"
    fls_path.unlink(missing_ok=True)
    passes: list[dict[str, object]] = []
    combined_output: list[str] = []
    for pass_no in (1, 2):
        try:
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
        except subprocess.TimeoutExpired as exc:
            output = "".join(
                part.decode("utf-8", "replace") if isinstance(part, bytes) else (part or "")
                for part in (exc.stdout, exc.stderr)
            )
            combined_output.append(f"===== PASS {pass_no} TIMEOUT =====\n{output}")
            passes.append({"pass": pass_no, "returncode": None, "status": "timeout"})
            break
        output = process.stdout + "\n" + process.stderr
        combined_output.append(f"===== PASS {pass_no} =====\n{output}")
        passes.append({"pass": pass_no, "returncode": process.returncode, "status": "completed"})
        if process.returncode != 0:
            break

    log_text = "\n".join(combined_output)
    (root / "编译过程.log").write_text(log_text, encoding="utf-8")
    tex_log_path = root / (source_path.stem + ".log")
    tex_log = tex_log_path.read_text(encoding="utf-8", errors="replace") if tex_log_path.is_file() else ""
    warnings = [line.strip() for line in tex_log.splitlines() if any(marker in line for marker in WARNING_MARKERS)]
    pdf_path = root / (source_path.stem + ".pdf")
    project_root = root.parent
    inputs, recorder_ok = collect_project_inputs(root, project_root, source_path, pdf_path)
    pdf_ok = pdf_structure_ok(pdf_path)
    ok = (
        len(passes) == 2
        and all(item["returncode"] == 0 for item in passes)
        and recorder_ok
        and bool(inputs)
        and pdf_ok
    )
    return {
        "schema_version": 1,
        "ok": ok,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "engine": Path(executable).name,
        "engine_path": executable,
        "engine_resolution": engine_resolution,
        "source": source_relative,
        "pdf": pdf_path.name if pdf_path.is_file() else None,
        "passes": passes,
        "warnings": warnings,
        "input_manifest_source": "xelatex-recorder" if recorder_ok else "missing-recorder",
        "inputs": inputs,
        "pdf_sha256": sha256(pdf_path) if pdf_path.is_file() else None,
        "pdf_size": pdf_path.stat().st_size if pdf_path.is_file() else None,
        "pdf_structure_ok": pdf_ok,
        "visual_review_required": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper_dir", type=Path)
    parser.add_argument("--source", default="main.tex")
    # graduate-modeling.cls 依赖 xeCJK 的字体选择与回退，只支持 XeLaTeX。
    # 这里限定取值，避免 --engine 让人以为 pdflatex/lualatex 也能出正确排版。
    parser.add_argument(
        "--engine",
        default="xelatex",
        choices=["xelatex"],
        help="仅支持 xelatex；模板在其他引擎下会直接报错退出。",
    )
    parser.add_argument(
        "--compiler",
        type=Path,
        help="可选：显式指定 xelatex.exe；未指定时依次检查 PATH、环境变量和 C:/D: 常见安装目录。",
    )
    args = parser.parse_args()
    report = compile_paper(args.paper_dir, args.source, args.engine, args.compiler)
    report_path = args.paper_dir / "编译报告.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report.get("ok") else 1)


if __name__ == "__main__":
    main()

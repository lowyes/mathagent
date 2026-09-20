#!/usr/bin/env python3
"""Resolve the active LaTeX source chain starting from ``main.tex``."""

from __future__ import annotations

import re
from pathlib import Path


INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")


def strip_comments(text: str) -> str:
    """Remove unescaped TeX comments before scanning input directives."""
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in text.splitlines())


def _resolve_reference(paper_root: Path, reference: str) -> Path:
    candidate = Path(reference.strip())
    if candidate.suffix.lower() != ".tex":
        candidate = candidate.with_suffix(".tex")
    return (paper_root / candidate).resolve()


def collect_active_tex(main_path: Path) -> tuple[list[Path], list[str]]:
    r"""Return active TeX files in first-use order and any source-chain errors.

    TeX resolves ``\input`` and ``\include`` paths from the main compilation
    directory.  Only files reachable from ``main.tex`` are returned; abandoned
    drafts and backups elsewhere in the paper directory are intentionally ignored.
    """
    main = main_path.resolve()
    paper_root = main.parent
    ordered: list[Path] = []
    visited: set[Path] = set()
    visiting: set[Path] = set()
    errors: list[str] = []

    def visit(path: Path) -> None:
        resolved = path.resolve()
        if resolved in visiting:
            errors.append(f"LaTeX source include cycle: {resolved}")
            return
        if resolved in visited:
            return
        if resolved != paper_root and paper_root not in resolved.parents:
            errors.append(f"LaTeX source escapes paper directory: {resolved}")
            return
        if not resolved.is_file():
            errors.append(f"Referenced LaTeX source is missing: {resolved}")
            return

        visiting.add(resolved)
        visited.add(resolved)
        ordered.append(resolved)
        text = strip_comments(resolved.read_text(encoding="utf-8", errors="replace"))
        for reference in INPUT_RE.findall(text):
            visit(_resolve_reference(paper_root, reference))
        visiting.remove(resolved)

    visit(main)
    return ordered, errors

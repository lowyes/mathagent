#!/usr/bin/env python3
"""Locate likely verbose or encyclopedic prose in modeling-paper TeX/Markdown files."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


SOURCE_SUFFIXES = {".tex", ".md"}
GENERIC_PATTERNS = {
    "model_history": re.compile(r"(?:由.{0,24}(?:提出|发明)|于(?:19|20)\d{2}年提出)"),
    "dictionary_definition": re.compile(r"是一种.{0,45}(?:方法|模型|算法|技术).{0,25}(?:用于|应用于)"),
    "generic_significance": re.compile(r"(?:具有重要(?:的)?(?:意义|价值)|有助于.{0,30}(?:理解|提高|改善)|得到广泛应用)"),
    "generic_development": re.compile(r"(?:近年来|随着.{0,30}(?:发展|进步))"),
    "vague_performance": re.compile(r"(?:效果较好|性能较好|取得了良好效果|验证了模型的可行性)"),
}
TRANSITIONS = ("首先", "其次", "再次", "然后", "最后", "综上所述", "结果表明")


def strip_tex_controls(text: str) -> str:
    text = re.sub(r"(?m)^\s*%.*$", "", text)
    text = re.sub(r"\\(?:label|ref|eqref|cite)\{[^}]*\}", "", text)
    text = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?", "", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    return text


def iter_sources(path: Path):
    if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES:
        yield path
        return
    if path.is_dir():
        for candidate in sorted(path.rglob("*")):
            if candidate.is_file() and candidate.suffix.lower() in SOURCE_SUFFIXES:
                yield candidate


def analyze_file(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    findings = []
    transition_counts = Counter()
    for index, paragraph in enumerate(paragraphs, start=1):
        plain = re.sub(r"\s+", " ", strip_tex_controls(paragraph)).strip()
        if not plain:
            continue
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", plain))
        if cjk_count >= 420:
            findings.append({
                "kind": "long_paragraph", "paragraph": index,
                "cjk_chars": cjk_count, "sample": plain[:120],
            })
        for sentence in re.split(r"[。！？；]", plain):
            sentence_cjk = len(re.findall(r"[\u4e00-\u9fff]", sentence))
            if sentence_cjk >= 105:
                findings.append({
                    "kind": "long_sentence", "paragraph": index,
                    "cjk_chars": sentence_cjk, "sample": sentence[:120],
                })
        for name, pattern in GENERIC_PATTERNS.items():
            if pattern.search(plain):
                findings.append({"kind": name, "paragraph": index, "sample": plain[:160]})
        for word in TRANSITIONS:
            transition_counts[word] += plain.count(word)
    total_cjk = len(re.findall(r"[\u4e00-\u9fff]", strip_tex_controls(raw)))
    dense_transitions = {
        word: count for word, count in transition_counts.items()
        if count >= max(4, round(total_cjk / 1500))
    }
    return {
        "file": str(path), "cjk_chars": total_cjk, "paragraphs": len(paragraphs),
        "dense_transitions": dense_transitions, "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Paper directory or a .tex/.md file")
    parser.add_argument("--json", action="store_true", help="Emit full JSON report")
    args = parser.parse_args()
    path = args.path.resolve()
    files = list(iter_sources(path))
    if not files:
        parser.error("no .tex or .md source files found")
    reports = [analyze_file(file) for file in files]
    summary = Counter(f["kind"] for report in reports for f in report["findings"])
    output = {
        "path": str(path), "files_checked": len(files), "summary": dict(summary),
        "note": "Warnings require contextual review; they are not automatic deletion rules.",
        "files": reports,
    }
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"Checked {len(files)} source file(s).")
        print("Warning counts:")
        for name, count in sorted(summary.items()):
            print(f"  {name}: {count}")
        for report in reports:
            if report["findings"] or report["dense_transitions"]:
                print(f"\n{report['file']}")
                if report["dense_transitions"]:
                    print(f"  dense_transitions: {report['dense_transitions']}")
                for item in report["findings"][:12]:
                    print(f"  P{item['paragraph']} {item['kind']}: {item['sample']}")
                remaining = len(report["findings"]) - 12
                if remaining > 0:
                    print(f"  ... {remaining} more finding(s); use --json for all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

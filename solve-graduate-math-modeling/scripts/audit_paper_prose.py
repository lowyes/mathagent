#!/usr/bin/env python3
"""Locate likely verbose or encyclopedic prose in modeling-paper TeX/Markdown files."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from paper_sources import collect_active_tex


SOURCE_SUFFIXES = {".tex", ".md"}
GENERIC_PATTERNS = {
    "model_history": re.compile(r"(?:由.{0,24}(?:提出|发明)|于(?:19|20)\d{2}年提出)"),
    "dictionary_definition": re.compile(r"是一种.{0,45}(?:方法|模型|算法|技术).{0,25}(?:用于|应用于)"),
    "generic_significance": re.compile(r"(?:具有重要(?:的)?(?:意义|价值)|有助于.{0,30}(?:理解|提高|改善)|得到广泛应用)"),
    "generic_development": re.compile(r"(?:近年来|随着.{0,30}(?:发展|进步))"),
    "vague_performance": re.compile(r"(?:效果较好|性能较好|取得了良好效果|验证了模型的可行性)"),
    "internal_engineering_jargon": re.compile(
        r"(?:数据审计|结果锁定|锁定模型|读取上游|回读结果|下游消费者|"
        r"项目清单|小问清单|流水线门禁|质量门禁|manifest\b|pipeline\b)",
        re.IGNORECASE,
    ),
    "local_path_leak": re.compile(r"(?:[A-Za-z]:\\|/home/[^\s]+|/Users/[^\s]+)"),
    "causal_overreach": re.compile(
        r"(?:(?:相关|SHAP|特征重要性|回归系数|敏感性).{0,35}(?:证明|表明|说明).{0,35}"
        r"(?:导致|驱动|引起|决定)|(?:证明|证实).{0,45}(?:导致|驱动|引起))"
    ),
}
TRANSITIONS = ("首先", "其次", "再次", "然后", "最后", "综上所述", "结果表明")
QUANTITATIVE_RESULT = re.compile(
    r"(?:\d+(?:\.\d+)?\s*%|"
    r"(?:RMSE|MAE|MAPE|R\s*\^?2|准确率|召回率|可行率|置信区间|"
    r"误差(?:下降|降低|增加|为)|目标值(?:为|达到))"
    r"[^。！？；]{0,24}\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
INTERPRETATION_OR_DECISION = re.compile(
    r"(?:说明|表明|意味着|据此|因此|由此|故选择|最终采用|优于|劣于|"
    r"相比|相较|下降|降低|提高|改善|适用于|适用边界|仍需|仅能|"
    r"只能|只反映|不包含|不能|但|然而|局限|风险|未表现出)"
)
ADJACENT_TABLE_FIGURE = re.compile(
    r"\\end\{(?P<first>table\*?|figure\*?)\}"
    r"(?P<gap>(?:\s|%[^\n]*(?:\n|$))*)"
    r"\\begin\{(?P<second>table\*?|figure\*?)\}",
    re.DOTALL,
)
EVIDENCE_BLOCK_BEFORE_HEADING = re.compile(
    r"\\end\{(?P<env>table\*?|figure\*?)\}"
    r"(?:\s|%[^\n]*(?:\n|$))*"
    r"(?=\\(?:section|subsection|subsubsection)\*?\{)",
    re.DOTALL,
)


def strip_tex_controls(text: str) -> str:
    text = re.sub(r"(?m)^\s*%.*$", "", text)
    text = re.sub(r"\\(?:label|ref|eqref|cite)\{[^}]*\}", "", text)
    text = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?", "", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    return text


def iter_sources(path: Path):
    if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES:
        if path.suffix.lower() == ".tex" and path.name.lower() == "main.tex":
            active_sources, errors = collect_active_tex(path)
            if errors:
                raise ValueError("；".join(errors))
            yield from active_sources
            return
        yield path
        return
    if path.is_dir():
        main_path = path / "main.tex"
        if main_path.is_file():
            active_sources, errors = collect_active_tex(main_path)
            if errors:
                raise ValueError("；".join(errors))
            yield from active_sources
            return
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
        structural_block = any(
            marker in paragraph
            for marker in (
                "\\begin{table", "\\begin{longtable", "\\begin{tabular",
                "\\begin{figure", "\\begin{equation", "\\begin{align",
                "\\begin{algorithm", "\\[",
            )
        )
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", plain))
        if not structural_block and cjk_count >= 420:
            findings.append({
                "kind": "long_paragraph", "paragraph": index,
                "cjk_chars": cjk_count, "sample": plain[:120],
            })
        if not structural_block:
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
        if (
            not structural_block
            and cjk_count >= 35
            and QUANTITATIVE_RESULT.search(plain)
            and not INTERPRETATION_OR_DECISION.search(plain)
        ):
            findings.append({
                "kind": "result_without_interpretation",
                "paragraph": index,
                "sample": plain[:160],
            })
        for word in TRANSITIONS:
            transition_counts[word] += plain.count(word)
    for match in ADJACENT_TABLE_FIGURE.finditer(raw):
        first = match.group("first").rstrip("*")
        second = match.group("second").rstrip("*")
        if {first, second} == {"table", "figure"}:
            findings.append({
                "kind": "adjacent_table_figure_without_bridge",
                "paragraph": raw[:match.start()].count("\n\n") + 1,
                "sample": (
                    f"{first} 后直接接 {second}；若前文未说明两者的证据分工，"
                    "应增加承接句或删去重复载体"
                ),
            })
    for match in EVIDENCE_BLOCK_BEFORE_HEADING.finditer(raw):
        findings.append({
            "kind": "evidence_block_without_followup",
            "paragraph": raw[:match.start()].count("\n\n") + 1,
            "sample": (
                f"{match.group('env').rstrip('*')} 后直接进入新标题；"
                "复核图表结论是否已在此前或此后明确解释"
            ),
        })
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
    try:
        files = list(iter_sources(path))
    except ValueError as exc:
        parser.error(str(exc))
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

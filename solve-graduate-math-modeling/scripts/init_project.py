#!/usr/bin/env python3
"""Initialize a graduate mathematical modeling project with per-subquestion ownership."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from problem_spec import load_problem_spec


TASK_TYPE_LABELS = {
    "deterministic_rule": "确定性规则判定",
    "prediction": "预测",
    "classification": "分类",
    "fitting": "拟合",
    "clustering": "聚类",
    "optimization": "优化",
    "evaluation": "评价",
    "simulation": "仿真",
    "association_decision": "关联分析与决策",
}


def chinese_number(number: int) -> str:
    digits = "零一二三四五六七八九"
    if 0 <= number < 10:
        return digits[number]
    if number < 20:
        return "十" + (digits[number % 10] if number % 10 else "")
    if number < 100:
        return digits[number // 10] + "十" + (digits[number % 10] if number % 10 else "")
    return str(number)


def parse_map(value: str) -> list[tuple[int, int]]:
    mapping: dict[int, int] = {}
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            question_text, count_text = item.split(":", 1)
            question, count = int(question_text), int(count_text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"无效映射 {item!r}，应使用 1:3,2:2 形式"
            ) from exc
        if question < 1 or count < 1:
            raise argparse.ArgumentTypeError("问题编号和小问数量必须为正整数")
        if question in mapping:
            raise argparse.ArgumentTypeError(f"问题 {question} 重复")
        mapping[question] = count
    if not mapping:
        raise argparse.ArgumentTypeError("至少指定一个问题")
    return sorted(mapping.items())


def parse_titles(value: str) -> dict[int, str]:
    """Parse ``1=标题,2=标题`` into per-question paper titles."""
    titles: dict[int, str] = {}
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            number_text, title = item.split("=", 1)
            number = int(number_text.strip())
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"无效问题标题 {item!r}，应使用 1=预测模型,2=优化方案 形式"
            ) from exc
        title = title.strip()
        if number < 1 or not title:
            raise argparse.ArgumentTypeError("问题编号必须为正整数且标题不得为空")
        if number in titles:
            raise argparse.ArgumentTypeError(f"问题 {number} 的标题重复")
        titles[number] = title
    return titles


def parse_analysis_modes(value: str) -> dict[int, str]:
    """Parse ``1=top-level,2=per-subquestion`` into per-question choices."""
    aliases = {
        "top-level": "top_level",
        "top_level": "top_level",
        "per-subquestion": "per_subquestion",
        "per_subquestion": "per_subquestion",
        "hybrid": "hybrid",
    }
    modes: dict[int, str] = {}
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            number_text, raw_mode = item.split("=", 1)
            number = int(number_text.strip())
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"无效问题分析模式 {item!r}，应使用 1=top-level,2=per-subquestion 形式"
            ) from exc
        mode = aliases.get(raw_mode.strip())
        if number < 1 or mode is None:
            raise argparse.ArgumentTypeError(
                "问题编号必须为正整数，模式必须为 top-level、per-subquestion 或 hybrid"
            )
        if number in modes:
            raise argparse.ArgumentTypeError(f"问题 {number} 的分析模式重复")
        modes[number] = mode
    return modes


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def subquestion_label(sub_no: int) -> str:
    if 1 <= sub_no <= 26:
        return chr(ord("a") + sub_no - 1)
    return str(sub_no)


def subquestion_section(
    question_no: int,
    sub_no: int,
    include_problem_analysis: bool = False,
    label: str | None = None,
    title: str | None = None,
    explicit: bool = True,
) -> str:
    label = label or subquestion_label(sub_no)
    title = (title or "").strip()
    if explicit:
        # 旧版 --map 初始化没有语义标题，继续保留“小问 a”写法；新版
        # problem-spec 提供标题后才升级为“问题 a：语义标题”。
        heading = f"问题 {label}：{title}" if title else f"小问 {label}"
    else:
        heading = title or "模型建立与求解"
    analysis = (
        "\\subsubsection{问题分析}\n\n"
        "围绕本小问的任务、数据特征、关键困难和处理策略展开；只在本小问与同题其他小问的任务性质明显不同时保留。\n\n"
        if include_problem_analysis
        else ""
    )
    return f"""\\subsection{{{heading}}}

{analysis}
% 完整性要求不等于固定标题要求。请根据本问复杂度自然组织正文，并覆盖：
% 任务边界、数据与约束、方法选择、数学表达与参数来源、真实求解、
% 结果、验证、直接回答和适用边界。简单小问可全部写在本节内；只有
% 内容确实较长时才增加“模型建立与求解”“结果与分析”等少量小标题。
% 流程图表达整体结构，伪代码表达精确执行，二者不固定先后且不得重复。

\\label{{sec:q{question_no}-s{sub_no}-solution}}

% 核心结果、验证证据与直接回答应相邻呈现，并引用本小问“结果”目录中的真实文件。
% 图片示例：
% \\includegraphics[width=0.82\\textwidth]{{../求解/问题{chinese_number(question_no)}/小问{sub_no}/图/示例图.pdf}}
"""


def initialize(
    output: Path,
    mapping: list[tuple[int, int]],
    competition: str,
    with_shared_data_section: bool = False,
    question_titles: dict[int, str] | None = None,
    structure_profile: str = "mixed",
    assumptions_symbols_mode: str = "combined",
    include_model_evaluation: bool = True,
    question_analysis_modes: dict[int, str] | None = None,
    question_specs: dict[int, list[dict[str, object]]] | None = None,
    structure_rationale: str | None = None,
    model_evaluation_rationale: str | None = None,
    question_heading_style: str = "concise",
    style_transfer: dict[str, object] | None = None,
    blueprint_schema_version: int | None = None,
) -> None:
    if structure_profile not in {"shared_data", "problem_local", "mixed"}:
        raise SystemExit(f"未知论文结构 Profile：{structure_profile}")
    if assumptions_symbols_mode not in {"combined", "separate"}:
        raise SystemExit(f"未知假设与符号组织方式：{assumptions_symbols_mode}")
    if question_heading_style not in {"concise", "solution"}:
        raise SystemExit(f"未知问题标题样式：{question_heading_style}")
    if structure_profile == "shared_data":
        with_shared_data_section = True
    elif structure_profile == "problem_local" and with_shared_data_section:
        raise SystemExit("problem_local Profile 不得启用公共数据章节")
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"目标目录非空，拒绝覆盖：{output}")
    output.mkdir(parents=True, exist_ok=True)

    skill_dir = Path(__file__).resolve().parent.parent
    template = skill_dir / "assets" / "graduate-latex-template"
    if not template.is_dir():
        raise SystemExit(f"缺少论文模板：{template}")

    (output / "题目").mkdir()
    (output / "数据").mkdir()
    (output / "求解" / "公共" / "代码").mkdir(parents=True)
    (output / "交付").mkdir()
    shutil.copytree(template, output / "论文")

    manifest: dict[str, object] = {
        "competition": competition,
        "official_rules_checked": False,
        "paper_profile": {
            "schema_version": 3 if blueprint_schema_version else 2,
            "mode": "default",
            "structure_profile": structure_profile,
            "structure_rationale": structure_rationale or {
                "shared_data": "多问共享同一数据口径与公共预处理，先集中说明后再逐问建模",
                "problem_local": "各问数据对象或处理方式差异明显，预处理留在对应问题附近",
                "mixed": "公共事实集中说明，特征构造与模型专属处理仍保留在对应问题附近",
            }[structure_profile],
            "layout": "",
            "override_reason": "",
            "override_reference": "",
            "assumptions_symbols_mode": assumptions_symbols_mode,
            "shared_data_section": with_shared_data_section,
            "model_evaluation_section": include_model_evaluation,
            "model_evaluation_rationale": model_evaluation_rationale or (
                "需要统一汇总多问模型的优势、局限、适用边界与推广条件"
                if include_model_evaluation
                else "各问已就地完成评价，且末问承担总结或决策功能，不另设重复章节"
            ),
            "question_heading_style": question_heading_style,
            "source_order": [],
            "sources": {
                "abstract": "sections/abstract.tex",
                "restatement": "sections/restatement.tex",
                "assumptions_symbols": (
                    "sections/assumptions-symbols.tex" if assumptions_symbols_mode == "combined" else ""
                ),
                "assumptions": "sections/assumptions.tex" if assumptions_symbols_mode == "separate" else "",
                "symbols": "sections/symbols.tex" if assumptions_symbols_mode == "separate" else "",
                "shared_data": "sections/data-preprocessing.tex" if with_shared_data_section else "",
                "questions": [],
                "model_evaluation": (
                    "sections/model-evaluation.tex" if include_model_evaluation else ""
                ),
                "references": "sections/references.tex",
                "appendix": "sections/appendix.tex",
            },
        },
        "paper_workflow": {
            "schema_version": 3,
            "results_locked": False,
            "abstract_status": "placeholder",
            "abstract_evidence_check": "pending",
            "abstract_questions": [],
            "abstract_scope_reason": "",
            "abstract_evidence": [],
            "abstract_plan": [],
            "model_review": {
                "status": "pending",
                "strengths": [],
                "strengths_not_applicable_reason": "",
                "limitations": [],
                "improvements": [],
                "extension_applicability": "pending",
                "extension_reason": "",
                "extensions": [],
            },
            "citation_review": {
                "status": "pending",
                "applicability": "pending",
                "reason": "",
            },
            "citation_ledger": [],
            "pdf_visual_review": {
                "status": "pending",
                "pdf_sha256": "",
                "checks": [],
            },
        },
        "questions": [],
        "handoffs": [],
        "style_transfer": {
            "enabled": False,
            "sources": [],
            "style_card": "",
            "status": "not_requested",
        },
    }
    question_inputs: list[str] = []

    question_titles = question_titles or {}
    question_analysis_modes = question_analysis_modes or {}
    question_specs = question_specs or {}

    for question_no, sub_count in mapping:
        q_cn = chinese_number(question_no)
        question_title = question_titles.get(question_no, "请根据题意概括本问任务")
        analysis_mode = question_analysis_modes.get(question_no, "top_level")
        if analysis_mode not in {"top_level", "per_subquestion", "hybrid"}:
            raise SystemExit(f"问题 {question_no} 的分析模式无效：{analysis_mode}")
        q_dir = output / "求解" / f"问题{q_cn}"
        q_dir.mkdir(parents=True)
        section_inputs: list[str] = []
        question_entry = {
            "question": question_no,
            "title": question_title,
            "analysis_mode": analysis_mode,
            "folder": f"求解/问题{q_cn}",
            "subquestions": [],
        }

        configured_subquestions = question_specs.get(question_no, [])
        if configured_subquestions and len(configured_subquestions) != sub_count:
            raise SystemExit(f"问题 {question_no} 的 problem-spec 小问数量与映射不一致")
        for sub_no in range(1, sub_count + 1):
            sub_spec = configured_subquestions[sub_no - 1] if configured_subquestions else {}
            label = str(sub_spec.get("label", subquestion_label(sub_no))).strip()
            subtitle = str(sub_spec.get("title", "")).strip()
            explicit = sub_spec.get("explicit", True) is True
            task_profile = sub_spec.get("task_profile", {})
            declared_outputs = task_profile.get("outputs", []) if isinstance(task_profile, dict) else []
            structured_outputs = [item for item in declared_outputs if isinstance(item, dict)]
            target_output = "；".join(
                str(item.get("name", "")).strip() for item in structured_outputs
                if str(item.get("name", "")).strip()
            )
            units = "；".join(dict.fromkeys(
                str(item.get("unit", "")).strip() for item in structured_outputs
                if str(item.get("unit", "")).strip()
            ))
            acceptance_criteria = [
                str(item.get("acceptance", "")).strip() for item in structured_outputs
                if str(item.get("acceptance", "")).strip()
            ]
            sq_dir = q_dir / f"小问{sub_no}"
            for child in ("代码", "图", "结果"):
                (sq_dir / child).mkdir(parents=True)
            sq_manifest = {
                "schema_version": (
                    3 if sub_spec and (blueprint_schema_version or 1) >= 2
                    else 2 if sub_spec
                    else 1
                ),
                "question": question_no,
                "subquestion": sub_no,
                "label": label,
                "explicit": explicit,
                "title": subtitle,
                "task_profile": task_profile,
                "argument_plan": sub_spec.get("argument_plan", {}),
                "target_output": target_output,
                "units": units,
                "inputs": [],
                "dependencies": [],
                "contract": {
                    "objective": "",
                    "non_goals": [],
                    "acceptance_criteria": acceptance_criteria,
                    "dependencies": [],
                },
                "literature_review": sub_spec.get(
                    "literature_review", {"applicability": "pending", "reason": ""}
                ),
                "literature_candidates": [],
                "model_comparison": {
                    "applicability": "pending",
                    "reason": "",
                    "primary_metric": "",
                    "candidates": [],
                    "ensemble": {},
                    "ensemble_reason": "",
                    "result_file": "",
                    "decision": "",
                },
                "methods": sub_spec.get("methods", []),
                "algorithms": [],
                "experiments": [],
                "revision_workflow": {
                    "schema_version": 1,
                    "status": "pending",
                    "no_revision_reason": "",
                    "cycles": [],
                },
                "validation_methods": [],
                "findings": [],
                "claims": [],
                "stage_gates": {
                    "problem_analysis": {"status": "pending", "checks": []},
                    "modeling": {"status": "pending", "checks": []},
                    "computation": {"status": "pending", "checks": []},
                    "paper": {"status": "pending", "checks": []},
                },
                "code_files": [],
                "figure_files": [],
                "result_files": [],
                "headline_metrics": {},
                "random_seeds": [],
                "solver_or_training_status": "",
                "status": "pending",
                "validation": {"status": "pending", "checks": []},
                "direct_answer": "",
            }
            write_json(sq_dir / "小问清单.json", sq_manifest)
            question_entry["subquestions"].append(
                {
                    "subquestion": sub_no,
                    "label": label,
                    "explicit": explicit,
                    "title": subtitle,
                    "task_profile": task_profile,
                    "folder": f"求解/问题{q_cn}/小问{sub_no}",
                }
            )

            filename = f"question-{question_no}-sub-{sub_no}.tex"
            (output / "论文" / "sections" / filename).write_text(
                subquestion_section(
                    question_no,
                    sub_no,
                    include_problem_analysis=analysis_mode in {"per_subquestion", "hybrid"},
                    label=label,
                    title=subtitle,
                    explicit=explicit,
                ),
                encoding="utf-8",
            )
            section_inputs.append(f"\\input{{sections/{filename}}}")

        question_entry["subquestion_count"] = sub_count
        manifest["questions"].append(question_entry)
        question_filename = f"question-{question_no}.tex"
        top_analysis = (
            "\\subsection{问题分析}\n\n"
            "围绕本问题的任务、数据特征、关键困难、处理策略及上下游依赖展开；"
            "不重复问题重述，不以算法名称或通用原理作为起点。\n\n"
            if analysis_mode in {"top_level", "hybrid"}
            else ""
        )
        question_heading = (
            f"问题{q_cn}的求解：{question_title}"
            if question_heading_style == "solution"
            else f"问题{q_cn}：{question_title}"
        )
        question_text = (
            f"\\section{{{question_heading}}}\n\n"
            + top_analysis
            + "\n".join(section_inputs)
            + "\n"
        )
        (output / "论文" / "sections" / question_filename).write_text(question_text, encoding="utf-8")
        question_inputs.append(f"\\input{{sections/{question_filename}}}")
        manifest["paper_profile"]["sources"]["questions"].append(f"sections/{question_filename}")

    main_path = output / "论文" / "main.tex"
    main_text = main_path.read_text(encoding="utf-8")
    begin = "% BEGIN AUTO QUESTION INPUTS"
    end = "% END AUTO QUESTION INPUTS"
    before, remainder = main_text.split(begin, 1)
    _, after = remainder.split(end, 1)
    main_text = before + begin + "\n" + "\n".join(question_inputs) + "\n" + end + after

    data_begin = "% BEGIN OPTIONAL SHARED DATA INPUT"
    data_end = "% END OPTIONAL SHARED DATA INPUT"
    before, remainder = main_text.split(data_begin, 1)
    _, after = remainder.split(data_end, 1)
    data_input = "\\input{sections/data-preprocessing.tex}" if with_shared_data_section else ""
    main_text = before + data_begin + "\n" + data_input + "\n" + data_end + after

    assumptions_begin = "% BEGIN AUTO ASSUMPTIONS SYMBOLS INPUT"
    assumptions_end = "% END AUTO ASSUMPTIONS SYMBOLS INPUT"
    before, remainder = main_text.split(assumptions_begin, 1)
    _, after = remainder.split(assumptions_end, 1)
    assumption_inputs = (
        "\\input{sections/assumptions-symbols.tex}"
        if assumptions_symbols_mode == "combined"
        else "\\input{sections/assumptions.tex}\n\\input{sections/symbols.tex}"
    )
    main_text = before + assumptions_begin + "\n" + assumption_inputs + "\n" + assumptions_end + after

    evaluation_begin = "% BEGIN OPTIONAL MODEL EVALUATION INPUT"
    evaluation_end = "% END OPTIONAL MODEL EVALUATION INPUT"
    before, remainder = main_text.split(evaluation_begin, 1)
    _, after = remainder.split(evaluation_end, 1)
    evaluation_input = "\\input{sections/model-evaluation.tex}" if include_model_evaluation else ""
    main_text = before + evaluation_begin + "\n" + evaluation_input + "\n" + evaluation_end + after

    main_path.write_text(main_text, encoding="utf-8")

    profile_sources = manifest["paper_profile"]["sources"]
    source_order = [profile_sources["abstract"], profile_sources["restatement"]]
    if assumptions_symbols_mode == "combined":
        source_order.append(profile_sources["assumptions_symbols"])
        assumptions_layout = "assumptions-symbols-combined"
    else:
        source_order.extend([profile_sources["assumptions"], profile_sources["symbols"]])
        assumptions_layout = "assumptions-symbols-separate"
    if with_shared_data_section:
        source_order.append(profile_sources["shared_data"])
    source_order.extend(profile_sources["questions"])
    if include_model_evaluation:
        source_order.append(profile_sources["model_evaluation"])
    source_order.extend([profile_sources["references"], profile_sources["appendix"]])
    manifest["paper_profile"]["source_order"] = source_order
    manifest["paper_profile"]["layout"] = (
        f"abstract-contents-restatement-{assumptions_layout}-"
        f"{'shared-data-' if with_shared_data_section else ''}questions-"
        f"{'evaluation-' if include_model_evaluation else ''}references-appendix"
    )

    if style_transfer and style_transfer.get("enabled") is True:
        card = style_transfer.get("card", {})
        style_schema_version = 2 if (blueprint_schema_version or 1) >= 2 else 1
        raw_sources = style_transfer.get("sources", [])
        sources = list(raw_sources) if isinstance(raw_sources, list) else []

        def card_line(item: object, include_reason: bool = False) -> str:
            if not isinstance(item, dict):
                return f"- {str(item).strip()}"
            statement = str(item.get("statement", "")).strip()
            if include_reason:
                reason = str(item.get("reason", "")).strip()
                return f"- {statement}（当前赛题依据：{reason}）"
            supported_by = "、".join(str(value).strip() for value in item.get("supported_by", []))
            return f"- {statement}（范文证据：{supported_by}）"

        def source_line(item: object) -> str:
            if not isinstance(item, dict):
                return f"- {str(item).strip()}"
            source_id = str(item.get("id", "")).strip()
            title = str(item.get("title", "")).strip()
            locator = str(item.get("locator", "")).strip()
            path_or_citation = str(item.get("path_or_citation", "")).strip()
            return f"- [{source_id}] {title}；定位：{locator}；来源：{path_or_citation}"

        lines = [
            "# Style Card",
            "",
            "参考边界：仅学习结构、证据节奏和标题粒度，不迁移模型、数值、假设、结论或原句。",
            "",
            "## 范文共同特征",
            "",
        ]
        lines.extend(card_line(item) for item in card.get("common_features", []))
        lines.extend(["", "## 可选择变体", ""])
        lines.extend(card_line(item) for item in card.get("variants", []))
        lines.extend(["", "## 当前赛题采用", ""])
        lines.extend(card_line(item, include_reason=True) for item in card.get("current_choices", []))
        lines.extend(["", "## 参考来源", ""])
        lines.extend(source_line(item) for item in sources)
        (output / "论文" / "style-card.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        review_file = ""
        review_status = "checked"
        if style_schema_version >= 2:
            review_file = "论文/style-review.md"
            review_status = "card_ready"
            (output / review_file).write_text(
                "# 优秀范文写后对照复核\n\n"
                "> REVIEW_STATUS: pending。本文完成并编译后填写；范文只提供结构与证据节奏参照。\n\n"
                "| 维度 | 范文定位与观察 | 本文位置 | 差距判断 | 已采取处理 |\n"
                "|---|---|---|---|---|\n"
                "| 摘要逐问覆盖与关键数字 | 待填写 | 待填写 | 待填写 | 待填写 |\n"
                "| 题面映射与标题粒度 | 待填写 | 待填写 | 待填写 | 待填写 |\n"
                "| 模型引入与参数来源 | 待填写 | 待填写 | 待填写 | 待填写 |\n"
                "| 结果、验证与模型取舍 | 待填写 | 待填写 | 待填写 | 待填写 |\n"
                "| 段落、图表与跨小问递进及解释边界 | 待填写 | 待填写 | 待填写 | 待填写 |\n"
                "| 图表密度与最终 PDF 版面 | 待填写 | 待填写 | 待填写 | 待填写 |\n\n"
                "复核完成后，把项目清单 `style_transfer.status` 改为 `checked`，"
                "并在 `checks` 中登记各维度的本文位置、发现和处理；不得只写“与范文一致”。\n",
                encoding="utf-8",
            )
        manifest["style_transfer"] = {
            "schema_version": style_schema_version,
            "enabled": True,
            "sources": sources,
            "style_card": "论文/style-card.md",
            "review_file": review_file,
            "checks": [],
            "status": review_status,
        }

    write_json(output / "项目清单.json", manifest)
    plan_lines = [
        "# 求解计划",
        "",
        "按问题与小问填写目标、输入、模型、输出、依赖、验证方案和文件归属。任何方法选择都应有数据规模、约束结构或评价指标依据。",
    ]
    if (blueprint_schema_version or 1) >= 2 and question_specs:
        plan_lines.extend([
            "",
            "> 下列内容由 problem-spec schema v2 自动生成。它是内部论证骨架，不要求照搬为论文固定标题。",
        ])
        for question_no, _ in mapping:
            plan_lines.extend(["", f"## 问题{chinese_number(question_no)}：{question_titles.get(question_no, '')}"])
            for sub_no, sub_spec in enumerate(question_specs.get(question_no, []), start=1):
                task_profile = sub_spec.get("task_profile", {})
                argument_plan = sub_spec.get("argument_plan", {})
                outputs = task_profile.get("outputs", []) if isinstance(task_profile, dict) else []
                output_text = "；".join(
                    f"{item.get('name', '')}（单位：{item.get('unit', '')}；粒度：{item.get('granularity', '')}；验收：{item.get('acceptance', '')}）"
                    for item in outputs
                    if isinstance(item, dict)
                )
                primary_type = str(task_profile.get("primary", ""))
                plan_lines.extend([
                    "",
                    f"### {sub_spec.get('label', subquestion_label(sub_no))} {sub_spec.get('title', '')}".rstrip(),
                    f"- 任务类型：{TASK_TYPE_LABELS.get(primary_type, primary_type)}",
                    f"- 类型判据：{task_profile.get('primary_reason', '')}",
                    f"- 最终要回答：{argument_plan.get('decision_question', '')}",
                    f"- 所需证据：{'；'.join(argument_plan.get('evidence_required', []))}",
                    f"- 解释边界：{argument_plan.get('interpretation_boundary', '')}",
                    f"- 交付物：{output_text}",
                ])
    (output / "求解计划.md").write_text("\n".join(plan_lines) + "\n", encoding="utf-8")
    print(f"已创建研究生数学建模项目：{output.resolve()}")
    print("问题映射：" + ", ".join(f"{q}:{count}" for q, count in mapping))


def initialize_from_spec(output: Path, spec_path: Path, competition_fallback: str) -> None:
    try:
        spec = load_problem_spec(spec_path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    profile = spec.get("paper_profile", {})
    questions = spec.get("questions", [])
    mapping = [(int(question["number"]), len(question["subquestions"])) for question in questions]
    titles = {int(question["number"]): str(question["title"]) for question in questions}
    analysis_modes = {
        int(question["number"]): str(
            question.get("analysis_mode", profile.get("analysis_default", "top_level"))
        )
        for question in questions
    }
    question_specs = {
        int(question["number"]): list(question["subquestions"])
        for question in questions
    }
    structure_profile = str(profile.get("structure_profile", "mixed"))
    shared_data = profile.get("shared_data_section", structure_profile == "shared_data") is True
    include_evaluation = profile.get("model_evaluation_section", True) is True
    initialize(
        output,
        mapping,
        str(spec.get("competition", competition_fallback)),
        with_shared_data_section=shared_data,
        question_titles=titles,
        structure_profile=structure_profile,
        assumptions_symbols_mode=str(profile.get("assumptions_symbols_mode", "combined")),
        include_model_evaluation=include_evaluation,
        question_analysis_modes=analysis_modes,
        question_specs=question_specs,
        structure_rationale=str(profile.get("structure_rationale", "")),
        model_evaluation_rationale=str(profile.get("model_evaluation_rationale", "")),
        question_heading_style=str(profile.get("question_heading_style", "concise")),
        style_transfer=spec.get("style_transfer", {"enabled": False}),
        blueprint_schema_version=int(spec.get("schema_version", 1)),
    )
    write_json(output / "problem-spec.json", spec)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="新项目目录（必须为空或不存在）")
    parser.add_argument(
        "--spec",
        type=Path,
        help="题目阅读后形成的 problem-spec.json；提供时优先于旧版结构参数",
    )
    parser.add_argument(
        "--map",
        dest="question_map",
        type=parse_map,
        default=parse_map("1:1,2:1,3:1"),
        help='问题与小问数量，例如 "1:3,2:2,3:1"',
    )
    parser.add_argument(
        "--competition",
        default="中国研究生数学建模竞赛（以当届官方通知为准）",
        help="写入项目清单的比赛名称",
    )
    parser.add_argument(
        "--titles",
        type=parse_titles,
        default={},
        help='各顶层问题的正文标题，例如 "1=水质预测,2=动态响应分析"',
    )
    parser.add_argument(
        "--with-shared-data-section",
        action="store_true",
        help="mixed Profile 下，仅当多问确实共享同一数据审计与预处理时加入公共数据章节",
    )
    parser.add_argument(
        "--structure-profile",
        choices=["mixed", "shared-data", "problem-local"],
        default="mixed",
        help="按赛题数据组织选择混合型、公共数据型或问题独立型结构",
    )
    parser.add_argument(
        "--assumptions-symbols",
        choices=["combined", "separate"],
        default="combined",
        help="将模型假设与符号说明合并为一章或拆成两个一级章节",
    )
    parser.add_argument(
        "--analysis-modes",
        type=parse_analysis_modes,
        default={},
        help='逐题指定问题分析位置，例如 "1=top-level,2=per-subquestion,3=hybrid"',
    )
    parser.add_argument(
        "--omit-model-evaluation",
        action="store_true",
        help="各问已就地评价或末问已承担总结功能时，不生成独立模型评价章",
    )
    args = parser.parse_args()
    if args.spec:
        initialize_from_spec(args.output, args.spec, args.competition)
        return
    unknown_titles = sorted(set(args.titles) - {number for number, _ in args.question_map})
    if unknown_titles:
        parser.error(f"--titles 含有 --map 中不存在的问题编号：{unknown_titles}")
    unknown_analysis = sorted(set(args.analysis_modes) - {number for number, _ in args.question_map})
    if unknown_analysis:
        parser.error(f"--analysis-modes 含有 --map 中不存在的问题编号：{unknown_analysis}")
    structure_profile = args.structure_profile.replace("-", "_")
    if structure_profile == "problem_local" and args.with_shared_data_section:
        parser.error("problem-local Profile 不能与 --with-shared-data-section 同时使用")
    initialize(
        args.output,
        args.question_map,
        args.competition,
        args.with_shared_data_section,
        args.titles,
        structure_profile,
        args.assumptions_symbols,
        not args.omit_model_evaluation,
        args.analysis_modes,
    )


if __name__ == "__main__":
    main()

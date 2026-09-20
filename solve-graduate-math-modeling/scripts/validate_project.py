#!/usr/bin/env python3
"""Validate per-subquestion code, figure, result, and manifest ownership."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from paper_sources import collect_active_tex
from problem_spec import (
    LITERATURE_APPLICABILITY,
    METHOD_REPRESENTATIONS,
    METHOD_TYPES,
    TASK_TYPES,
    TASKS_REQUIRING_EXPERIMENTS,
    TASKS_REQUIRING_MODEL_COMPARISON,
    validate_problem_spec,
)


CODE_EXTENSIONS = {
    ".py", ".ipynb", ".m", ".jl", ".r", ".sql", ".c", ".cc", ".cpp",
    ".dot", ".gv", ".mmd", ".tex",
}
FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps", ".tif", ".tiff"}
FLOWCHART_EXTENSIONS = {".pdf", ".svg"}
RESULT_EXTENSIONS = {
    ".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet", ".txt",
    ".npz", ".npy", ".pkl", ".mat",
}
ALGORITHM_SOURCE_TYPES = {"problem", "upstream", "data", "literature", "calibration", "scenario"}
EXPERIMENT_STATUSES = {"passed", "failed", "inconclusive"}
FINDING_TYPES = {"research", "engineering", "decision"}
CLAIM_STATUSES = {"verified", "qualified", "rejected"}
LITERATURE_STATUSES = {"adopted", "benchmarked", "rejected", "data_blocked"}
LITERATURE_DIRECTNESS = {"direct", "adjacent", "method"}
MODEL_COMPARISON_APPLICABILITY = {"required", "not_applicable"}
MODEL_ROLES = {"baseline", "standalone", "ensemble"}
VALIDATION_METHOD_TYPES = {
    "out_of_sample", "cross_validation", "classification_metrics",
    "error_analysis", "residual_analysis", "sensitivity", "robustness",
    "uncertainty", "feasibility", "convergence", "optimality", "ablation",
    "benchmark", "statistical_test", "simulation_check", "physical_boundary",
    "other",
}
STAGE_GATE_KEYS = ("problem_analysis", "modeling", "computation", "paper")
STYLE_REVIEW_DIMENSIONS = {
    "摘要逐问覆盖与关键数字",
    "题面映射与标题粒度",
    "模型引入与参数来源",
    "结果、验证与模型取舍",
    "段落、图表与跨小问递进及解释边界",
    "图表密度与最终PDF版面",
}
STYLE_REVIEW_DIMENSION_ALIASES = {
    "跨小问承接与解释边界": "段落、图表与跨小问递进及解释边界",
}
ABSTRACT_HIGHLIGHT_STATUSES = {"qualified", "not_applicable"}
ABSTRACT_HIGHLIGHT_TYPES = {
    "decision_variable_design",
    "constraint_handling",
    "model_combination",
    "staged_or_dynamic_modeling",
    "objective_redesign",
    "problem_structure_alignment",
    "validated_model_improvement",
}
REVISION_COMPONENTS = {
    "problem_scope", "assumption", "data", "preprocessing", "feature",
    "model", "parameter", "solver", "validation_protocol", "claim_boundary",
}
MODEL_IMPROVEMENT_STATUSES = {"implemented", "future"}
CITATION_APPLICABILITY = {"required", "not_required"}
CITATION_SOURCE_TYPES = {
    "official_rule", "standard", "dataset", "primary_research",
    "application_research", "book", "technical_document", "web_resource",
    "software",
}
CITATION_AUTHORITIES = {
    "primary", "peer_reviewed", "authoritative_secondary", "discovery_only",
}


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def listed_paths(entries: object) -> set[str]:
    if not isinstance(entries, list):
        return set()
    return {str(item).replace("\\", "/") for item in entries if isinstance(item, str)}


def strip_tex_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in text.splitlines())


def nonempty_string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def validate_abstract_plan(
    root: Path,
    paper_workflow: dict[str, object],
    all_question_numbers: list[int],
    abstract_question_numbers: list[int],
) -> list[str]:
    """Validate the decision-bearing abstract plan for schema-v2 projects.

    The plan records what the writer must decide before drafting. It deliberately
    does not police sentence templates or require every problem to claim an
    innovation.
    """
    schema_version = paper_workflow.get("schema_version", 1)
    if not isinstance(schema_version, int):
        return ["paper_workflow.schema_version 必须是整数"]
    if schema_version < 2:
        return []

    errors: list[str] = []
    plan = paper_workflow.get("abstract_plan", [])
    if not isinstance(plan, list):
        return ["paper_workflow.abstract_plan 必须是数组"]

    entries: dict[int, dict[str, object]] = {}
    for index, entry in enumerate(plan, start=1):
        prefix = f"摘要规划第{index}项"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}必须是对象")
            continue
        question = entry.get("question")
        if not isinstance(question, int):
            errors.append(f"{prefix}的 question 必须是整数")
            continue
        if question in entries:
            errors.append(f"摘要规划不得重复登记问题{chinese_number(question)}")
            continue
        entries[question] = entry

    expected = set(abstract_question_numbers)
    extra = sorted(set(entries) - expected)
    if extra:
        errors.append(f"摘要规划包含摘要范围外的问题：{extra}")

    for question in abstract_question_numbers:
        entry = entries.get(question)
        if entry is None:
            errors.append(f"摘要缺少问题{chinese_number(question)}的写作规划")
            continue

        for field, label in (
            ("task", "直接任务"),
            ("core_method", "核心方法或规则"),
            ("key_result", "关键结果"),
            ("direct_answer", "直接答案"),
        ):
            if not str(entry.get(field, "")).strip():
                errors.append(f"摘要问题{chinese_number(question)}缺少{label}：{field}")

        inherited = entry.get("inherits_from", [])
        if not isinstance(inherited, list) or not all(isinstance(item, int) for item in inherited):
            errors.append(f"摘要问题{chinese_number(question)}的 inherits_from 必须是整数数组")
            inherited = []
        else:
            if len(inherited) != len(set(inherited)):
                errors.append(f"摘要问题{chinese_number(question)}的 inherits_from 不得重复")
            invalid_upstream = sorted(
                item for item in set(inherited)
                if item not in all_question_numbers or item >= question
            )
            if invalid_upstream:
                errors.append(
                    f"摘要问题{chinese_number(question)}只能继承编号更小且真实存在的问题："
                    f"{invalid_upstream}"
                )
        if inherited:
            if not nonempty_string_list(entry.get("retained")):
                errors.append(f"摘要问题{chinese_number(question)}继承上游时必须说明 retained")
            if not nonempty_string_list(entry.get("modifications")):
                errors.append(f"摘要问题{chinese_number(question)}继承上游时必须说明 modifications")
            if not str(entry.get("new_difficulty", "")).strip():
                errors.append(f"摘要问题{chinese_number(question)}继承上游时必须说明 new_difficulty")

        highlight = entry.get("model_highlight", {})
        if not isinstance(highlight, dict):
            errors.append(f"摘要问题{chinese_number(question)}的 model_highlight 必须是对象")
            continue
        status = highlight.get("status")
        if status not in ABSTRACT_HIGHLIGHT_STATUSES:
            errors.append(
                f"摘要问题{chinese_number(question)}的模型亮点状态必须为 "
                "qualified 或 not_applicable"
            )
        elif status == "not_applicable":
            if not str(highlight.get("reason", "")).strip():
                errors.append(f"摘要问题{chinese_number(question)}不提炼模型亮点时必须说明原因")
        else:
            highlight_type = highlight.get("type")
            if highlight_type not in ABSTRACT_HIGHLIGHT_TYPES:
                errors.append(
                    f"摘要问题{chinese_number(question)}的模型亮点 type 不合法：{highlight_type}"
                )
            if not str(highlight.get("statement", "")).strip():
                errors.append(f"摘要问题{chinese_number(question)}的模型亮点缺少具体设计陈述")
            if not str(highlight.get("problem_link", "")).strip():
                errors.append(f"摘要问题{chinese_number(question)}的模型亮点缺少题目结构对应关系")
            evidence = highlight.get("evidence", {})
            if not isinstance(evidence, dict):
                errors.append(f"摘要问题{chinese_number(question)}的模型亮点 evidence 必须是对象")
                continue
            files = evidence.get("files", [])
            if not nonempty_string_list(files):
                errors.append(f"摘要问题{chinese_number(question)}的模型亮点缺少证据文件")
            else:
                for evidence_file in files:
                    if not (root / evidence_file).is_file():
                        errors.append(f"摘要模型亮点证据文件不存在：{evidence_file}")
            if not str(evidence.get("locator", "")).strip():
                errors.append(f"摘要问题{chinese_number(question)}的模型亮点缺少证据定位")

    return errors


def validate_revision_workflow(root: Path, sq_dir: Path, manifest: dict[str, object]) -> list[str]:
    """Validate an explicit diagnose-revise-rerun loop when a manifest opts in."""
    workflow = manifest.get("revision_workflow")
    if workflow is None:
        return []
    prefix = relative(sq_dir, root)
    if not isinstance(workflow, dict):
        return [f"{prefix} 的 revision_workflow 必须是对象"]

    errors: list[str] = []
    status = workflow.get("status")
    if status not in {"pending", "passed"}:
        errors.append(f"{prefix} 的 revision_workflow.status 必须为 pending 或 passed")
    cycles = workflow.get("cycles", [])
    if not isinstance(cycles, list):
        return errors + [f"{prefix} 的 revision_workflow.cycles 必须是数组"]

    experiments = {
        str(item.get("id", "")).strip(): item
        for item in manifest.get("experiments", [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    validations = {
        str(item.get("id", "")).strip(): item
        for item in manifest.get("validation_methods", [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    cycle_ids: set[str] = set()
    for index, cycle in enumerate(cycles, start=1):
        cycle_prefix = f"{prefix} 的第{index}次模型修订"
        if not isinstance(cycle, dict):
            errors.append(f"{cycle_prefix}不是对象")
            continue
        for field in ("id", "diagnosis", "outcome", "decision"):
            if not str(cycle.get(field, "")).strip():
                errors.append(f"{cycle_prefix}缺少 {field}")
        cycle_id = str(cycle.get("id", "")).strip()
        if cycle_id in cycle_ids:
            errors.append(f"{cycle_prefix}的 id 重复：{cycle_id}")
        if cycle_id:
            cycle_ids.add(cycle_id)

        changed = cycle.get("changed_components", [])
        if not isinstance(changed, list) or not changed:
            errors.append(f"{cycle_prefix}缺少 changed_components")
        else:
            invalid = sorted({str(item) for item in changed} - REVISION_COMPONENTS)
            if invalid:
                errors.append(f"{cycle_prefix}包含无效修改类型：{invalid}")

        previous_id = str(cycle.get("previous_experiment", "")).strip()
        revised_id = str(cycle.get("revised_experiment", "")).strip()
        if previous_id not in experiments:
            errors.append(f"{cycle_prefix}的 previous_experiment 不存在：{previous_id or '(空)'}")
        if revised_id not in experiments:
            errors.append(f"{cycle_prefix}的 revised_experiment 不存在：{revised_id or '(空)'}")
        elif experiments[revised_id].get("status") != "passed":
            errors.append(f"{cycle_prefix}的 revised_experiment 必须是可用的 passed 运行")
        if previous_id and previous_id == revised_id:
            errors.append(f"{cycle_prefix}的新旧实验不得相同")

        trigger = cycle.get("trigger", {})
        if not isinstance(trigger, dict):
            errors.append(f"{cycle_prefix}的 trigger 必须是对象")
            continue
        trigger_type = str(trigger.get("type", "")).strip()
        trigger_id = str(trigger.get("id", "")).strip()
        if trigger_type == "experiment":
            if trigger_id not in experiments:
                errors.append(f"{cycle_prefix}触发实验不存在：{trigger_id or '(空)'}")
        elif trigger_type == "validation":
            if trigger_id not in validations:
                errors.append(f"{cycle_prefix}触发验证不存在：{trigger_id or '(空)'}")
        else:
            errors.append(f"{cycle_prefix}的 trigger.type 必须为 experiment 或 validation")
        evidence_file = str(trigger.get("evidence_file", "")).strip().replace("\\", "/")
        if not evidence_file:
            errors.append(f"{cycle_prefix}缺少触发证据文件")
        elif not (root / evidence_file).is_file():
            errors.append(f"{cycle_prefix}的触发证据文件不存在：{evidence_file}")
        if not str(trigger.get("locator", "")).strip():
            errors.append(f"{cycle_prefix}缺少触发证据定位")

    if manifest.get("status") == "complete" and status != "passed":
        errors.append(f"{prefix} 完成前必须通过模型修订复核")
    if status == "passed" and not cycles and not str(
        workflow.get("no_revision_reason", "")
    ).strip():
        errors.append(f"{prefix} 未发生模型修订时必须填写 no_revision_reason")
    return errors


def validate_model_review(root: Path, paper_workflow: dict[str, object]) -> list[str]:
    """Validate evidence-backed strengths, limitations, remedies, and extensions."""
    schema_version = paper_workflow.get("schema_version", 1)
    if not isinstance(schema_version, int):
        return ["paper_workflow.schema_version 必须是整数"]
    if schema_version < 3:
        return []
    review = paper_workflow.get("model_review", {})
    if not isinstance(review, dict):
        return ["paper_workflow.model_review 必须是对象"]
    errors: list[str] = []
    if review.get("status") != "passed":
        errors.append("最终交付前必须完成 paper_workflow.model_review")

    def evidence_items(field: str, require_nonempty: bool) -> tuple[list[dict[str, object]], set[str]]:
        raw = review.get(field, [])
        if not isinstance(raw, list):
            errors.append(f"model_review.{field} 必须是数组")
            return [], set()
        if require_nonempty and not raw:
            errors.append(f"model_review.{field} 至少登记一项")
        items: list[dict[str, object]] = []
        ids: set[str] = set()
        for index, item in enumerate(raw, start=1):
            prefix = f"model_review.{field}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix}必须是对象")
                continue
            for key in ("id", "statement", "evidence_file", "locator"):
                if not str(item.get(key, "")).strip():
                    errors.append(f"{prefix}缺少 {key}")
            item_id = str(item.get("id", "")).strip()
            if item_id in ids:
                errors.append(f"{prefix}的 id 重复：{item_id}")
            if item_id:
                ids.add(item_id)
            evidence_file = str(item.get("evidence_file", "")).strip().replace("\\", "/")
            if evidence_file and not (root / evidence_file).is_file():
                errors.append(f"{prefix}的证据文件不存在：{evidence_file}")
            if field == "limitations" and not str(item.get("impact", "")).strip():
                errors.append(f"{prefix}缺少 impact")
            items.append(item)
        return items, ids

    strengths, _ = evidence_items("strengths", False)
    if not strengths and not str(review.get("strengths_not_applicable_reason", "")).strip():
        errors.append("model_review 未登记优势时必须说明 strengths_not_applicable_reason")
    _, limitation_ids = evidence_items("limitations", True)

    improvements = review.get("improvements", [])
    covered_limitations: set[str] = set()
    if not isinstance(improvements, list) or not improvements:
        errors.append("model_review.improvements 至少登记一项")
        improvements = []
    for index, item in enumerate(improvements, start=1):
        prefix = f"model_review.improvements[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}必须是对象")
            continue
        for field in ("id", "proposal", "requirements"):
            if not str(item.get(field, "")).strip():
                errors.append(f"{prefix}缺少 {field}")
        improvement_status = item.get("status")
        if improvement_status not in MODEL_IMPROVEMENT_STATUSES:
            errors.append(f"{prefix}.status 必须为 implemented 或 future")
        linked = item.get("limitation_ids", [])
        if not nonempty_string_list(linked):
            errors.append(f"{prefix}缺少 limitation_ids")
            linked = []
        unknown = set(linked) - limitation_ids
        if unknown:
            errors.append(f"{prefix}关联了不存在的局限：{sorted(unknown)}")
        covered_limitations.update(set(linked) & limitation_ids)
        if improvement_status == "implemented":
            evidence_file = str(item.get("evidence_file", "")).strip().replace("\\", "/")
            if not evidence_file or not str(item.get("locator", "")).strip():
                errors.append(f"{prefix}已实现但缺少证据文件或定位")
            elif not (root / evidence_file).is_file():
                errors.append(f"{prefix}的证据文件不存在：{evidence_file}")
    uncovered = limitation_ids - covered_limitations
    if uncovered:
        errors.append(f"以下模型局限尚未对应改进方向：{sorted(uncovered)}")

    applicability = review.get("extension_applicability")
    extensions = review.get("extensions", [])
    if applicability not in {"applicable", "not_applicable"}:
        errors.append("model_review.extension_applicability 必须为 applicable 或 not_applicable")
    elif applicability == "not_applicable":
        if not str(review.get("extension_reason", "")).strip():
            errors.append("不讨论推广时必须填写 model_review.extension_reason")
    elif not isinstance(extensions, list) or not extensions:
        errors.append("声明可推广时 model_review.extensions 至少登记一项")
    if isinstance(extensions, list):
        for index, item in enumerate(extensions, start=1):
            prefix = f"model_review.extensions[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix}必须是对象")
                continue
            for field in ("scenario", "shared_structure", "changed_assumptions", "validation_required"):
                if not str(item.get(field, "")).strip():
                    errors.append(f"{prefix}缺少 {field}")
    return errors


def citation_keys_from_paper(paper_root: Path, paper_text: str) -> tuple[set[str], set[str]]:
    cited: set[str] = set()
    for group in re.findall(
        r"\\(?:[A-Za-z]*cite[A-Za-z]*)\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}",
        paper_text,
    ):
        cited.update(key.strip() for key in group.split(",") if key.strip())
    defined = set(re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", paper_text))
    bib_references = re.findall(r"\\bibliography\{([^}]+)\}", paper_text)
    bib_references += re.findall(r"\\addbibresource(?:\[[^\]]*\])?\{([^}]+)\}", paper_text)
    for group in bib_references:
        for item in group.split(","):
            name = item.strip()
            if not name:
                continue
            bib_path = paper_root / (name if name.lower().endswith(".bib") else name + ".bib")
            if bib_path.is_file():
                bib_text = bib_path.read_text(encoding="utf-8", errors="replace")
                defined.update(re.findall(r"@\w+\s*\{\s*([^,\s]+)", bib_text))
    return cited, defined


def validate_citation_ledger(
    paper_workflow: dict[str, object],
    cited_keys: set[str],
    defined_keys: set[str],
) -> list[str]:
    """Validate source authority and citation/ledger/reference bidirectionality."""
    schema_version = paper_workflow.get("schema_version", 1)
    if not isinstance(schema_version, int):
        return ["paper_workflow.schema_version 必须是整数"]
    if schema_version < 3:
        return []
    review = paper_workflow.get("citation_review", {})
    ledger = paper_workflow.get("citation_ledger", [])
    if not isinstance(review, dict):
        return ["paper_workflow.citation_review 必须是对象"]
    errors: list[str] = []
    if review.get("status") != "passed":
        errors.append("最终交付前必须完成 citation_review")
    applicability = review.get("applicability")
    if applicability not in CITATION_APPLICABILITY:
        errors.append("citation_review.applicability 必须为 required 或 not_required")
    if not str(review.get("reason", "")).strip():
        errors.append("citation_review.reason 不得为空")
    if not isinstance(ledger, list):
        return errors + ["paper_workflow.citation_ledger 必须是数组"]
    if applicability == "required" and not ledger:
        errors.append("引用适用时 citation_ledger 至少登记一项")
    if applicability == "not_required" and (ledger or cited_keys or defined_keys):
        errors.append("citation_review 标记 not_required，但论文或台账仍包含引用")

    ids: set[str] = set()
    ledger_keys: set[str] = set()
    for index, item in enumerate(ledger, start=1):
        prefix = f"citation_ledger[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}必须是对象")
            continue
        for field in ("id", "claim", "citation_key", "verification_source"):
            if not str(item.get(field, "")).strip():
                errors.append(f"{prefix}缺少 {field}")
        source_id = str(item.get("id", "")).strip()
        citation_key = str(item.get("citation_key", "")).strip()
        if source_id in ids:
            errors.append(f"{prefix}的 id 重复：{source_id}")
        if citation_key in ledger_keys:
            errors.append(f"{prefix}的 citation_key 重复：{citation_key}")
        if source_id:
            ids.add(source_id)
        if citation_key:
            ledger_keys.add(citation_key)
        if item.get("source_type") not in CITATION_SOURCE_TYPES:
            errors.append(f"{prefix}.source_type 无效：{item.get('source_type')}")
        authority = item.get("authority")
        if authority not in CITATION_AUTHORITIES:
            errors.append(f"{prefix}.authority 无效：{authority}")
        role = item.get("claim_role")
        if role not in {"core", "supporting"}:
            errors.append(f"{prefix}.claim_role 必须为 core 或 supporting")
        if role == "core" and authority == "discovery_only":
            errors.append(f"{prefix}的核心主张不能由 discovery_only 来源支撑")
        if not nonempty_string_list(item.get("used_in")):
            errors.append(f"{prefix}.used_in 至少登记一个正文位置")
        if item.get("verified") is not True:
            errors.append(f"{prefix}尚未完成来源核验")

    if applicability == "required":
        missing_ledger = cited_keys - ledger_keys
        missing_citation = ledger_keys - cited_keys
        missing_definition = cited_keys - defined_keys
        unused_definition = defined_keys - cited_keys
        if missing_ledger:
            errors.append(f"正文引用缺少 citation_ledger 登记：{sorted(missing_ledger)}")
        if missing_citation:
            errors.append(f"citation_ledger 条目未在正文引用：{sorted(missing_citation)}")
        if missing_definition:
            errors.append(f"正文引用缺少参考文献定义：{sorted(missing_definition)}")
        if unused_definition:
            errors.append(f"参考文献表存在正文未引用条目：{sorted(unused_definition)}")
    return errors


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def pdf_structure_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    size = path.stat().st_size
    if size == 0:
        return False
    with path.open("rb") as stream:
        head = stream.read(4096)
        stream.seek(max(0, size - 8192))
        tail = stream.read()
    return (
        head.startswith(b"%PDF-")
        and b"/Root" in tail
        and b"xref" in tail
        and b"startxref" in tail
        and b"%%EOF" in tail
    )


def figure_structure_ok(path: Path) -> bool:
    """Dependency-free signature checks for accepted static figure formats."""
    if not path.is_file() or path.stat().st_size == 0:
        return False
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return pdf_structure_ok(path)
    size = path.stat().st_size
    with path.open("rb") as stream:
        head = stream.read(4096)
        stream.seek(max(0, size - 4096))
        tail = stream.read()
    if suffix == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n") and tail.endswith(b"IEND\xaeB`\x82")
    if suffix in {".jpg", ".jpeg"}:
        return head.startswith(b"\xff\xd8") and tail.rstrip().endswith(b"\xff\xd9")
    if suffix == ".svg":
        head_text = head.decode("utf-8-sig", errors="replace").lower()
        tail_text = tail.decode("utf-8", errors="replace").lower()
        return "<svg" in head_text and "</svg>" in tail_text
    if suffix == ".eps":
        return head.startswith(b"%!PS-Adobe")
    if suffix in {".tif", ".tiff"}:
        return head.startswith((b"II*\x00", b"MM\x00*"))
    return False


def chinese_number(value: int) -> str:
    digits = "零一二三四五六七八九"
    if value < 10:
        return digits[value]
    if value == 10:
        return "十"
    if value < 20:
        return "十" + digits[value % 10]
    if value < 100:
        return digits[value // 10] + "十" + (digits[value % 10] if value % 10 else "")
    return str(value)


def validate(project: Path, final: bool = False) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []
    root = project.resolve()
    project_manifest_path = root / "项目清单.json"
    if not project_manifest_path.is_file():
        return {"ok": False, "errors": ["缺少 项目清单.json"], "warnings": [], "checked": []}

    try:
        project_manifest = json.loads(project_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "errors": [f"项目清单无法读取：{exc}"], "warnings": [], "checked": []}

    manifest_paths: set[Path] = set()
    figure_hashes: dict[str, str] = {}
    subquestion_index: dict[str, dict[str, object]] = {}
    core_algorithm_count = 0
    pseudocode_anchors: set[str] = set()
    paper_root = root / "论文"
    paper_text = ""
    active_paper_sources: list[Path] = []
    main_tex = paper_root / "main.tex"
    if main_tex.is_file():
        active_paper_sources, source_errors = collect_active_tex(main_tex)
        errors.extend(source_errors)
        paper_text = "\n".join(
            strip_tex_comments(path.read_text(encoding="utf-8"))
            for path in active_paper_sources
        )
    elif paper_root.is_dir():
        errors.append("论文目录缺少 main.tex，无法确定正式论文源文件链")
    algorithm_blocks = re.findall(
        r"\\begin\{algorithm\}(.*?)\\end\{algorithm\}",
        paper_text,
        flags=re.DOTALL,
    )
    questions = project_manifest.get("questions", [])
    if not isinstance(questions, list) or not questions:
        errors.append("项目清单未定义任何问题")
        questions = []

    for question in questions:
        if not isinstance(question, dict):
            errors.append("项目清单中的问题条目不是对象")
            continue
        for subquestion in question.get("subquestions", []):
            if not isinstance(subquestion, dict) or "folder" not in subquestion:
                errors.append("小问条目缺少 folder")
                continue
            sq_dir = root / str(subquestion["folder"])
            manifest_path = sq_dir / "小问清单.json"
            manifest_paths.add(manifest_path.resolve())
            for child in ("代码", "图", "结果"):
                if not (sq_dir / child).is_dir():
                    errors.append(f"缺少目录：{relative(sq_dir / child, root)}")
            if not manifest_path.is_file():
                errors.append(f"缺少清单：{relative(manifest_path, root)}")
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"清单无法读取 {relative(manifest_path, root)}：{exc}")
                continue
            subquestion_index[relative(sq_dir, root)] = manifest

            try:
                manifest_schema_version = int(manifest.get("schema_version", 1))
            except (TypeError, ValueError):
                manifest_schema_version = 0
                errors.append(f"schema_version 必须为正整数：{relative(manifest_path, root)}")

            status = manifest.get("status", "pending")
            if status not in {"pending", "in_progress", "complete", "blocked"}:
                errors.append(f"状态无效 {relative(manifest_path, root)}：{status}")
            if final and status != "complete":
                errors.append(f"最终交付仍有未完成小问：{relative(sq_dir, root)}（{status}）")
            errors.extend(validate_revision_workflow(root, sq_dir, manifest))

            task_profile = manifest.get("task_profile", {})
            adaptive_task = isinstance(task_profile, dict) and bool(task_profile)
            task_type = str(task_profile.get("primary", "")).strip() if adaptive_task else ""
            secondary_traits = task_profile.get("secondary", []) if adaptive_task else []
            if adaptive_task:
                if task_type not in TASK_TYPES:
                    errors.append(
                        f"task_profile.primary 无效 {relative(sq_dir, root)}：{task_type or '(空)'}"
                    )
                if not isinstance(secondary_traits, list) or not all(
                    str(value).strip() for value in secondary_traits
                ):
                    errors.append(f"task_profile.secondary 必须为字符串数组：{relative(sq_dir, root)}")
                if manifest_schema_version >= 3 and not str(
                    task_profile.get("primary_reason", "")
                ).strip():
                    errors.append(
                        f"task_profile.primary_reason 必须说明题型判定依据：{relative(sq_dir, root)}"
                    )
                outputs = task_profile.get("outputs", [])
                if not isinstance(outputs, list) or not outputs:
                    errors.append(f"task_profile.outputs 至少登记一个输出：{relative(sq_dir, root)}")
                elif manifest_schema_version >= 3:
                    for output_index, output in enumerate(outputs, start=1):
                        if not isinstance(output, dict):
                            errors.append(
                                f"schema v3 的 task_profile.outputs[{output_index}] 必须是对象："
                                f"{relative(sq_dir, root)}"
                            )
                            continue
                        for field in ("name", "unit", "granularity", "acceptance"):
                            if not str(output.get(field, "")).strip():
                                errors.append(
                                    f"task_profile.outputs[{output_index}].{field} 不得为空："
                                    f"{relative(sq_dir, root)}"
                                )
                    argument_plan = manifest.get("argument_plan", {})
                    if not isinstance(argument_plan, dict):
                        errors.append(f"argument_plan 必须是对象：{relative(sq_dir, root)}")
                    else:
                        if not str(argument_plan.get("decision_question", "")).strip():
                            errors.append(
                                f"argument_plan.decision_question 不得为空：{relative(sq_dir, root)}"
                            )
                        evidence_required = argument_plan.get("evidence_required", [])
                        if not isinstance(evidence_required, list) or not any(
                            str(value).strip() for value in evidence_required
                        ):
                            errors.append(
                                f"argument_plan.evidence_required 至少登记一项：{relative(sq_dir, root)}"
                            )
                        if not str(argument_plan.get("interpretation_boundary", "")).strip():
                            errors.append(
                                f"argument_plan.interpretation_boundary 不得为空："
                                f"{relative(sq_dir, root)}"
                            )

            actual_code = sorted(
                p
                for p in (sq_dir / "代码").rglob("*")
                if p.is_file()
                and p.suffix.lower() in CODE_EXTENSIONS
                and "__pycache__" not in p.parts
            )
            actual_figures = sorted(p for p in (sq_dir / "图").rglob("*") if p.is_file())
            actual_results = sorted(p for p in (sq_dir / "结果").rglob("*") if p.is_file())
            for figure in actual_figures:
                if figure.suffix.lower() not in FIGURE_EXTENSIONS:
                    errors.append(f"图文件类型不受支持：{relative(figure, root)}")
                elif not figure_structure_ok(figure):
                    errors.append(f"图文件为空或结构无效：{relative(figure, root)}")
            declared_groups = {
                "code_files": (actual_code, listed_paths(manifest.get("code_files"))),
                "figure_files": (actual_figures, listed_paths(manifest.get("figure_files"))),
                "result_files": (actual_results, listed_paths(manifest.get("result_files"))),
            }
            for field, (actual, declared) in declared_groups.items():
                actual_rel = {relative(path, root) for path in actual}
                missing = declared - actual_rel
                unlisted = actual_rel - declared
                for item in sorted(missing):
                    errors.append(f"清单声明但文件不存在 [{field}]：{item}")
                for item in sorted(unlisted):
                    warnings.append(f"文件尚未登记 [{field}]：{item}")

            if status == "complete":
                if not actual_code:
                    errors.append(f"已完成小问缺少代码：{relative(sq_dir, root)}")
                if not actual_results:
                    errors.append(f"已完成小问缺少结果：{relative(sq_dir, root)}")
                validation = manifest.get("validation", {})
                if not isinstance(validation, dict) or validation.get("status") != "passed":
                    errors.append(
                        f"已完成小问尚未通过验证：{relative(sq_dir, root)}"
                        "；小问清单的 validation.status 必须为 passed"
                        "（初始化写入的 pending 需在验证完成后改写）"
                    )
                if not str(manifest.get("direct_answer", "")).strip():
                    errors.append(f"已完成小问缺少直接回答：{relative(sq_dir, root)}")

                accepted_algorithms: set[str] = set()
                algorithms = manifest.get("methods", []) if adaptive_task else manifest.get("algorithms", [])
                entity_name = "方法" if adaptive_task else "算法"
                if not isinstance(algorithms, list) or not algorithms:
                    errors.append(f"已完成小问缺少{entity_name}定义与证据血缘：{relative(sq_dir, root)}")
                else:
                    for algorithm_index, algorithm in enumerate(algorithms, start=1):
                        prefix = f"{relative(sq_dir, root)} 的第{algorithm_index}个{entity_name}"
                        if not isinstance(algorithm, dict):
                            errors.append(f"{prefix}不是对象")
                            continue
                        required_fields = ("id", "name", "purpose", "method_type") if adaptive_task else (
                            "name", "purpose", "formula_reference"
                        )
                        for field in required_fields:
                            if not str(algorithm.get(field, "")).strip():
                                errors.append(f"{prefix}缺少 {field}")
                        method_type = str(algorithm.get("method_type", "")).strip()
                        representations = algorithm.get("representations", [])
                        representation_set = (
                            {str(value).strip() for value in representations if str(value).strip()}
                            if isinstance(representations, list)
                            else set()
                        )
                        if adaptive_task:
                            if method_type not in METHOD_TYPES:
                                errors.append(f"{prefix}的 method_type 无效：{method_type or '(空)'}")
                            if not representation_set:
                                errors.append(f"{prefix}缺少 representations")
                            unknown_representations = representation_set - METHOD_REPRESENTATIONS
                            if unknown_representations:
                                errors.append(
                                    f"{prefix}含未知表达载体：{sorted(unknown_representations)}"
                                )
                            if not str(algorithm.get("formula_reference", "")).strip() and not str(
                                algorithm.get("definition_reference", "")
                            ).strip():
                                errors.append(f"{prefix}必须登记 formula_reference 或 definition_reference")
                        is_core = algorithm.get("is_core")
                        if not isinstance(is_core, bool):
                            errors.append(f"{prefix}缺少布尔字段 is_core")
                        if not str(algorithm.get("core_reason", "")).strip():
                            errors.append(f"{prefix}缺少 core_reason")
                        if is_core is True:
                            core_algorithm_count += 1
                        requires_pseudocode = (
                            is_core is True if not adaptive_task else "pseudocode" in representation_set
                        )
                        requires_flowchart = (
                            is_core is True if not adaptive_task else "flowchart" in representation_set
                        )
                        if adaptive_task and is_core is True and method_type == "iterative_algorithm":
                            for required_representation in ("pseudocode", "flowchart"):
                                if required_representation not in representation_set:
                                    errors.append(
                                        f"{prefix}为核心迭代算法，缺少 {required_representation} 表达"
                                    )
                        if requires_pseudocode:
                            for field in ("pseudocode_anchor", "pseudocode_reference"):
                                if not str(algorithm.get(field, "")).strip():
                                    errors.append(f"{prefix}声明伪代码表达却缺少 {field}")
                            pseudocode_anchor = str(algorithm.get("pseudocode_anchor", "")).strip()
                            if pseudocode_anchor in pseudocode_anchors:
                                errors.append(f"{prefix}的伪代码标签重复：{pseudocode_anchor}")
                            if pseudocode_anchor:
                                pseudocode_anchors.add(pseudocode_anchor)
                                label_token = f"\\label{{{pseudocode_anchor}}}"
                                matching_blocks = [
                                    block for block in algorithm_blocks if label_token in block
                                ]
                                if not matching_blocks:
                                    errors.append(
                                        f"{prefix}的伪代码未出现在 algorithm 环境中：{pseudocode_anchor}"
                                    )
                                elif len(matching_blocks) > 1:
                                    errors.append(
                                        f"{prefix}的伪代码标签对应多个 algorithm 环境：{pseudocode_anchor}"
                                    )
                                else:
                                    block = matching_blocks[0]
                                    for command in ("\\caption", "\\KwIn", "\\KwOut"):
                                        if command not in block:
                                            errors.append(
                                                f"{prefix}的伪代码缺少 {command}：{pseudocode_anchor}"
                                            )
                        if requires_flowchart:
                            for field in ("flowchart_source", "flowchart_file", "flowchart_reference"):
                                if not str(algorithm.get(field, "")).strip():
                                    errors.append(f"{prefix}声明流程图表达却缺少 {field}")
                            flowchart_source = str(algorithm.get("flowchart_source", "")).strip().replace("\\", "/")
                            if flowchart_source:
                                source_path = root / flowchart_source
                                if not source_path.is_file():
                                    errors.append(f"{prefix}的流程图源文件不存在：{flowchart_source}")
                                if Path(flowchart_source).suffix.lower() not in CODE_EXTENSIONS:
                                    errors.append(f"{prefix}的流程图源文件类型不受支持：{flowchart_source}")
                                expected_code_root = (sq_dir / "代码").resolve()
                                try:
                                    source_path.resolve().relative_to(expected_code_root)
                                except ValueError:
                                    errors.append(f"{prefix}的流程图源文件不在所属小问代码目录：{flowchart_source}")
                                if flowchart_source not in listed_paths(manifest.get("code_files")):
                                    errors.append(f"{prefix}的流程图源文件未登记到 code_files：{flowchart_source}")
                            flowchart_file = str(algorithm.get("flowchart_file", "")).strip().replace("\\", "/")
                            if flowchart_file:
                                flowchart_path = root / flowchart_file
                                if not flowchart_path.is_file():
                                    errors.append(f"{prefix}的流程图文件不存在：{flowchart_file}")
                                if Path(flowchart_file).suffix.lower() not in FLOWCHART_EXTENSIONS:
                                    errors.append(f"{prefix}的流程图必须为可编辑/可缩放的 PDF 或 SVG：{flowchart_file}")
                                expected_figure_root = (sq_dir / "图").resolve()
                                try:
                                    flowchart_path.resolve().relative_to(expected_figure_root)
                                except ValueError:
                                    errors.append(f"{prefix}的流程图不在所属小问图目录：{flowchart_file}")
                                if flowchart_file not in listed_paths(manifest.get("figure_files")):
                                    errors.append(f"{prefix}的流程图未登记到 figure_files：{flowchart_file}")
                        algorithm_name = str(algorithm.get("name", "")).strip()
                        if algorithm_name:
                            accepted_algorithms.add(algorithm_name)
                        parameters = algorithm.get("parameters", [])
                        parameter_applicability = str(
                            algorithm.get("parameter_applicability", "required" if not adaptive_task else "")
                        ).strip()
                        if adaptive_task and parameter_applicability not in {"required", "not_required"}:
                            errors.append(f"{prefix}的 parameter_applicability 必须为 required 或 not_required")
                        if parameter_applicability == "not_required":
                            if not str(algorithm.get("parameter_reason", "")).strip():
                                errors.append(f"{prefix}不需要参数血缘时必须填写 parameter_reason")
                            if parameters not in (None, []):
                                errors.append(f"{prefix}声明参数不适用，但 parameters 非空")
                            continue
                        if not isinstance(parameters, list) or not parameters:
                            errors.append(f"{prefix}缺少参数来源")
                            continue
                        for parameter_index, parameter in enumerate(parameters, start=1):
                            parameter_prefix = f"{prefix}的第{parameter_index}个参数"
                            if not isinstance(parameter, dict):
                                errors.append(f"{parameter_prefix}不是对象")
                                continue
                            for field in ("symbol", "value_or_rule", "unit", "source_type", "source", "downstream_use"):
                                if not str(parameter.get(field, "")).strip():
                                    errors.append(f"{parameter_prefix}缺少 {field}")
                            source_type = str(parameter.get("source_type", "")).strip()
                            if source_type and source_type not in ALGORITHM_SOURCE_TYPES:
                                errors.append(
                                    f"{parameter_prefix}的 source_type 无效：{source_type}；"
                                    f"应为 {sorted(ALGORITHM_SOURCE_TYPES)} 之一"
                                )

                literature_required = True
                literature_applicability = "required"
                if adaptive_task:
                    literature_review = manifest.get("literature_review", {})
                    if not isinstance(literature_review, dict):
                        errors.append(f"已完成小问缺少 literature_review：{relative(sq_dir, root)}")
                        literature_review = {}
                    literature_applicability = str(
                        literature_review.get("applicability", "")
                    ).strip()
                    if literature_applicability not in LITERATURE_APPLICABILITY - {"pending"}:
                        errors.append(
                            f"文献审计 applicability 无效 {relative(sq_dir, root)}："
                            f"{literature_applicability or '(空)'}"
                        )
                    if not str(literature_review.get("reason", "")).strip():
                        errors.append(f"文献审计缺少适用性理由：{relative(sq_dir, root)}")
                    literature_required = literature_applicability == "required"
                literature_candidates = manifest.get("literature_candidates", [])
                if not isinstance(literature_candidates, list):
                    errors.append(f"literature_candidates 必须是数组：{relative(sq_dir, root)}")
                    literature_candidates = []
                if literature_required and not literature_candidates:
                    errors.append(f"已完成小问缺少真实文献方法筛选：{relative(sq_dir, root)}")
                if literature_applicability == "not_required" and literature_candidates:
                    warnings.append(
                        f"文献审计声明不适用但仍登记候选；请复核口径：{relative(sq_dir, root)}"
                    )
                if literature_candidates:
                    has_direct_candidate = False
                    for literature_index, candidate in enumerate(literature_candidates, start=1):
                        prefix = f"{relative(sq_dir, root)} 的第{literature_index}条文献候选"
                        if not isinstance(candidate, dict):
                            errors.append(f"{prefix}不是对象")
                            continue
                        for field in (
                            "id", "title", "venue", "doi_or_url", "verification_url",
                            "problem_match", "formula_or_method", "required_data",
                            "available_fields", "transfer_decision",
                        ):
                            if not str(candidate.get(field, "")).strip():
                                errors.append(f"{prefix}缺少 {field}")
                        if not str(candidate.get("method", candidate.get("algorithm", ""))).strip():
                            errors.append(f"{prefix}缺少 method（兼容旧字段 algorithm）")
                        year = candidate.get("year")
                        if not isinstance(year, int) or year < 1900 or year > 2100:
                            errors.append(f"{prefix}的 year 无效：{year}")
                        verification_url = str(candidate.get("verification_url", "")).strip()
                        if verification_url and not verification_url.startswith(("https://", "http://")):
                            errors.append(f"{prefix}的 verification_url 不是有效网络地址")
                        directness = str(candidate.get("directness", "")).strip()
                        if directness not in LITERATURE_DIRECTNESS:
                            errors.append(f"{prefix}的 directness 无效：{directness}")
                        if directness == "direct":
                            has_direct_candidate = True
                        literature_status = str(candidate.get("status", "")).strip()
                        if literature_status not in LITERATURE_STATUSES:
                            errors.append(f"{prefix}的 status 无效：{literature_status}")
                        used_by_field = "used_by_methods" if adaptive_task else "used_by_algorithms"
                        used_by = candidate.get(
                            used_by_field,
                            candidate.get("used_by_algorithms", []) if adaptive_task else [],
                        )
                        if not isinstance(used_by, list):
                            errors.append(f"{prefix}的 {used_by_field} 必须是数组")
                            used_by = []
                        linked_algorithms = {str(name).strip() for name in used_by if str(name).strip()}
                        if literature_status in {"adopted", "benchmarked"} and not linked_algorithms:
                            errors.append(f"{prefix}采用或测试后却未关联项目算法")
                        unknown_algorithms = linked_algorithms - accepted_algorithms
                        if unknown_algorithms:
                            errors.append(
                                f"{prefix}关联了不存在的项目算法：" + "、".join(sorted(unknown_algorithms))
                            )
                    if not has_direct_candidate and literature_applicability == "required":
                        warnings.append(f"文献筛选尚无直接场景研究：{relative(sq_dir, root)}")
                elif adaptive_task and literature_applicability == "conditional":
                    warnings.append(
                        f"条件适用的文献审计未登记候选；确认该问可由题面或标准直接定义："
                        f"{relative(sq_dir, root)}"
                    )

                contract = manifest.get("contract", {})
                if not isinstance(contract, dict):
                    errors.append(f"已完成小问缺少建模契约：{relative(sq_dir, root)}")
                else:
                    if not str(contract.get("objective", "")).strip():
                        errors.append(f"建模契约缺少 objective：{relative(sq_dir, root)}")
                    for field in ("non_goals", "acceptance_criteria"):
                        values = contract.get(field, [])
                        if not isinstance(values, list) or not any(str(value).strip() for value in values):
                            errors.append(f"建模契约缺少 {field}：{relative(sq_dir, root)}")
                    if not isinstance(contract.get("dependencies", []), list):
                        errors.append(f"建模契约 dependencies 必须是数组：{relative(sq_dir, root)}")

                passed_algorithms: set[str] = set()
                experiment_ids: set[str] = set()
                experiments_required = (
                    task_type in TASKS_REQUIRING_EXPERIMENTS if adaptive_task else True
                )
                experiments = manifest.get("experiments", [])
                if not isinstance(experiments, list):
                    errors.append(f"experiments 必须是数组：{relative(sq_dir, root)}")
                    experiments = []
                if experiments_required and not experiments:
                    errors.append(f"已完成小问缺少实验记录：{relative(sq_dir, root)}")
                if experiments:
                    for experiment_index, experiment in enumerate(experiments, start=1):
                        prefix = f"{relative(sq_dir, root)} 的第{experiment_index}条实验"
                        if not isinstance(experiment, dict):
                            errors.append(f"{prefix}不是对象")
                            continue
                        for field in ("id", "name", "purpose", "command_or_entry", "config", "verdict"):
                            if not str(experiment.get(field, "")).strip():
                                errors.append(f"{prefix}缺少 {field}")
                        experiment_id = str(experiment.get("id", "")).strip()
                        if experiment_id:
                            experiment_ids.add(experiment_id)
                        experiment_status = str(experiment.get("status", "")).strip()
                        if experiment_status not in EXPERIMENT_STATUSES:
                            errors.append(f"{prefix}的 status 无效：{experiment_status}")
                        names_field = "method_names" if adaptive_task else "algorithm_names"
                        names = experiment.get(
                            names_field,
                            experiment.get("algorithm_names", []) if adaptive_task else [],
                        )
                        if not isinstance(names, list) or not any(str(name).strip() for name in names):
                            errors.append(f"{prefix}缺少 {names_field}")
                            names = []
                        unknown_names = {
                            str(name).strip() for name in names if str(name).strip()
                        } - accepted_algorithms
                        if unknown_names:
                            errors.append(
                                f"{prefix}关联了不存在的{entity_name}："
                                + "、".join(sorted(unknown_names))
                            )
                        if experiment_status == "passed":
                            passed_algorithms.update(str(name).strip() for name in names if str(name).strip())
                        result_files = experiment.get("result_files", [])
                        if not isinstance(result_files, list) or not result_files:
                            errors.append(f"{prefix}缺少 result_files")
                        else:
                            for result_file in result_files:
                                result_path = root / str(result_file)
                                if not result_path.is_file():
                                    errors.append(f"{prefix}的结果文件不存在：{result_file}")
                uncovered_algorithms = accepted_algorithms - passed_algorithms
                if experiments_required and uncovered_algorithms:
                    errors.append(
                        f"最终{entity_name}缺少通过的实验记录 {relative(sq_dir, root)}："
                        + "、".join(sorted(uncovered_algorithms))
                    )

                validation_methods = manifest.get("validation_methods", [])
                if not isinstance(validation_methods, list) or not validation_methods:
                    errors.append(f"已完成小问缺少与正文结合的验证评估记录：{relative(sq_dir, root)}")
                else:
                    validation_ids: set[str] = set()
                    for method_index, method in enumerate(validation_methods, start=1):
                        prefix = f"{relative(sq_dir, root)} 的第{method_index}种验证评估方法"
                        if not isinstance(method, dict):
                            errors.append(f"{prefix}不是对象")
                            continue
                        required_validation_fields = [
                            "id", "name", "target", "purpose", "applicability_reason",
                            "procedure_reference", "data_protocol", "evidence_file",
                            "evidence_locator", "result_summary", "interpretation",
                            "decision_impact", "paper_location", "paper_anchor",
                        ]
                        if experiments_required:
                            required_validation_fields.append("experiment_id")
                        for field in required_validation_fields:
                            if not str(method.get(field, "")).strip():
                                errors.append(f"{prefix}缺少 {field}")
                        method_id = str(method.get("id", "")).strip()
                        if method_id in validation_ids:
                            errors.append(f"{prefix}的 id 重复：{method_id}")
                        if method_id:
                            validation_ids.add(method_id)
                        method_type = str(method.get("type", "")).strip()
                        if method_type not in VALIDATION_METHOD_TYPES:
                            errors.append(f"{prefix}的 type 无效：{method_type}")
                        experiment_id = str(method.get("experiment_id", "")).strip()
                        if experiment_id and experiment_id not in experiment_ids:
                            errors.append(f"{prefix}关联的实验不存在：{experiment_id}")
                        criteria = method.get("criteria", [])
                        if not isinstance(criteria, list) or not criteria:
                            errors.append(f"{prefix}缺少指标或判据 criteria")
                        else:
                            for criterion_index, criterion in enumerate(criteria, start=1):
                                criterion_prefix = f"{prefix}的第{criterion_index}个指标或判据"
                                if not isinstance(criterion, dict):
                                    errors.append(f"{criterion_prefix}不是对象")
                                    continue
                                for field in ("name", "definition_reference", "acceptance_rule"):
                                    if not str(criterion.get(field, "")).strip():
                                        errors.append(f"{criterion_prefix}缺少 {field}")
                        evidence_file = str(method.get("evidence_file", "")).strip().replace("\\", "/")
                        if evidence_file:
                            if not (root / evidence_file).is_file():
                                errors.append(f"{prefix}的证据文件不存在：{evidence_file}")
                            if evidence_file not in listed_paths(manifest.get("result_files")):
                                errors.append(f"{prefix}的证据文件未登记到 result_files：{evidence_file}")
                            expected_result_root = (sq_dir / "结果").resolve()
                            try:
                                (root / evidence_file).resolve().relative_to(expected_result_root)
                            except ValueError:
                                errors.append(f"{prefix}的证据文件不在所属小问结果目录：{evidence_file}")
                        paper_anchor = str(method.get("paper_anchor", "")).strip()
                        if paper_anchor and f"\\label{{{paper_anchor}}}" not in paper_text:
                            errors.append(f"{prefix}的正文标签不存在：{paper_anchor}")

                comparison = manifest.get("model_comparison", {})
                if not isinstance(comparison, dict):
                    errors.append(f"已完成小问缺少多模型比较声明：{relative(sq_dir, root)}")
                else:
                    applicability = str(comparison.get("applicability", "")).strip()
                    reason = str(comparison.get("reason", "")).strip()
                    if applicability not in MODEL_COMPARISON_APPLICABILITY:
                        errors.append(
                            f"模型比较 applicability 无效 {relative(sq_dir, root)}：{applicability or '(空)'}"
                            f"；合法取值为 {'/'.join(sorted(MODEL_COMPARISON_APPLICABILITY))}"
                            "（初始化写入的 pending 必须在小问完成前改成其中之一）"
                        )
                    comparison_required_by_task = (
                        task_type in TASKS_REQUIRING_MODEL_COMPARISON if adaptive_task else False
                    )
                    if comparison_required_by_task and applicability != "required":
                        errors.append(
                            f"预测/分类任务必须执行可靠基线与主要候选比较：{relative(sq_dir, root)}"
                        )
                    if not reason:
                        errors.append(f"模型比较缺少适用性理由：{relative(sq_dir, root)}")
                    if applicability == "required":
                        for field in ("primary_metric", "result_file", "decision"):
                            if not str(comparison.get(field, "")).strip():
                                errors.append(f"模型比较缺少 {field}：{relative(sq_dir, root)}")
                        comparison_file = str(comparison.get("result_file", "")).strip()
                        if comparison_file and not (root / comparison_file).is_file():
                            errors.append(f"模型比较结果文件不存在：{comparison_file}")
                        candidates = comparison.get("candidates", [])
                        candidate_names: set[str] = set()
                        non_ensemble_names: set[str] = set()
                        ensemble_names: set[str] = set()
                        has_baseline = False
                        if not isinstance(candidates, list) or len(candidates) < 2:
                            errors.append(f"模型比较至少需要一个可靠基线和一个主要候选：{relative(sq_dir, root)}")
                            candidates = []
                        for candidate_index, candidate in enumerate(candidates, start=1):
                            prefix = f"{relative(sq_dir, root)} 的第{candidate_index}个比较模型"
                            if not isinstance(candidate, dict):
                                errors.append(f"{prefix}不是对象")
                                continue
                            for field in ("name", "family", "role", "experiment_id"):
                                if not str(candidate.get(field, "")).strip():
                                    errors.append(f"{prefix}缺少 {field}")
                            name = str(candidate.get("name", "")).strip()
                            role = str(candidate.get("role", "")).strip()
                            exp_id = str(candidate.get("experiment_id", "")).strip()
                            if role not in MODEL_ROLES:
                                errors.append(
                                    f"{prefix}的 role 无效：{role or '(空)'}"
                                    f"；合法取值为 {'/'.join(sorted(MODEL_ROLES))}"
                                )
                            if name in candidate_names:
                                errors.append(f"{prefix}的模型名重复：{name}")
                            if name:
                                candidate_names.add(name)
                                if name not in accepted_algorithms:
                                    errors.append(
                                        f"{prefix}未登记{entity_name}定义与参数血缘：{name}"
                                        f"；参与比较的基线与被放弃的候选也要写进本小问{entity_name}清单，"
                                        "名称必须与 candidates 完全一致"
                                    )
                            if role == "ensemble":
                                ensemble_names.add(name)
                            elif role in {"baseline", "standalone"}:
                                non_ensemble_names.add(name)
                            if role == "baseline":
                                has_baseline = True
                            if exp_id and exp_id not in experiment_ids:
                                errors.append(f"{prefix}关联的实验不存在：{exp_id}")
                        if len(non_ensemble_names) < 2 or not has_baseline:
                            errors.append(f"模型比较缺少可靠基线或主要候选：{relative(sq_dir, root)}")
                        ensemble = comparison.get("ensemble", {})
                        if ensemble_names:
                            if not isinstance(ensemble, dict):
                                errors.append(f"模型比较 ensemble 不是对象：{relative(sq_dir, root)}")
                            else:
                                for field in (
                                    "method", "weight_source", "leakage_control", "formula_reference",
                                    "qualification_evidence", "complementarity_evidence", "oof_evidence",
                                ):
                                    if not str(ensemble.get(field, "")).strip():
                                        errors.append(f"模型融合缺少 {field}：{relative(sq_dir, root)}")
                                members = ensemble.get("members", [])
                                if not isinstance(members, list) or len(
                                    {str(x).strip() for x in members if str(x).strip()}
                                ) < 2:
                                    errors.append(f"模型融合至少需要两个成员：{relative(sq_dir, root)}")
                                else:
                                    unknown_members = {
                                        str(x).strip() for x in members if str(x).strip()
                                    } - non_ensemble_names
                                    if unknown_members:
                                        errors.append(
                                            "模型融合成员不在非融合候选中：" + "、".join(sorted(unknown_members))
                                        )
                        elif not str(comparison.get("ensemble_reason", "")).strip():
                            errors.append(
                                f"未测试融合模型时必须填写 ensemble_reason：{relative(sq_dir, root)}"
                            )

                findings = manifest.get("findings", [])
                if not isinstance(findings, list) or not findings:
                    errors.append(f"已完成小问缺少发现与决策记录：{relative(sq_dir, root)}")
                else:
                    for finding_index, finding in enumerate(findings, start=1):
                        prefix = f"{relative(sq_dir, root)} 的第{finding_index}条发现"
                        if not isinstance(finding, dict):
                            errors.append(f"{prefix}不是对象")
                            continue
                        finding_type = str(finding.get("type", "")).strip()
                        if finding_type not in FINDING_TYPES:
                            errors.append(f"{prefix}的 type 无效：{finding_type}")
                        for field in ("statement", "evidence", "implication"):
                            if not str(finding.get(field, "")).strip():
                                errors.append(f"{prefix}缺少 {field}")

                claims = manifest.get("claims", [])
                if not isinstance(claims, list) or not claims:
                    errors.append(f"已完成小问缺少结论—证据矩阵：{relative(sq_dir, root)}")
                else:
                    for claim_index, claim in enumerate(claims, start=1):
                        prefix = f"{relative(sq_dir, root)} 的第{claim_index}条结论"
                        if not isinstance(claim, dict):
                            errors.append(f"{prefix}不是对象")
                            continue
                        for field in ("id", "statement", "paper_location"):
                            if not str(claim.get(field, "")).strip():
                                errors.append(f"{prefix}缺少 {field}")
                        claim_status = str(claim.get("status", "")).strip()
                        if claim_status not in CLAIM_STATUSES:
                            errors.append(f"{prefix}的 status 无效：{claim_status}")
                        evidence_items = claim.get("evidence", [])
                        if not isinstance(evidence_items, list) or not evidence_items:
                            errors.append(f"{prefix}缺少 evidence")
                            continue
                        for evidence_index, evidence in enumerate(evidence_items, start=1):
                            evidence_prefix = f"{prefix}的第{evidence_index}条证据"
                            if not isinstance(evidence, dict):
                                errors.append(f"{evidence_prefix}不是对象")
                                continue
                            for field in ("file", "locator", "relation"):
                                if not str(evidence.get(field, "")).strip():
                                    errors.append(f"{evidence_prefix}缺少 {field}")
                            evidence_file = str(evidence.get("file", "")).strip()
                            if evidence_file and not (root / evidence_file).is_file():
                                errors.append(f"{evidence_prefix}文件不存在：{evidence_file}")

                stage_gates = manifest.get("stage_gates", {})
                if not isinstance(stage_gates, dict):
                    errors.append(f"已完成小问缺少四阶段质量门：{relative(sq_dir, root)}")
                else:
                    for gate_name in STAGE_GATE_KEYS:
                        gate = stage_gates.get(gate_name, {})
                        prefix = f"{relative(sq_dir, root)} 的 {gate_name} 质量门"
                        if not isinstance(gate, dict):
                            errors.append(f"{prefix}不是对象")
                            continue
                        gate_status = str(gate.get("status", "")).strip()
                        checks = gate.get("checks", [])
                        if not isinstance(checks, list) or not any(str(check).strip() for check in checks):
                            errors.append(f"{prefix}缺少 checks")
                        must_pass = gate_name != "paper" or final
                        if must_pass and gate_status != "passed":
                            errors.append(f"{prefix}尚未通过：{gate_status or 'missing'}")
                        elif gate_name == "paper" and gate_status not in {"pending", "passed"}:
                            errors.append(f"{prefix}状态无效：{gate_status}")
                        elif gate_name == "paper" and gate_status == "pending":
                            warnings.append(f"论文质量门尚未通过；最终交付请使用 --final：{relative(sq_dir, root)}")

            for figure in actual_figures:
                key = digest(figure)
                current = relative(figure, root)
                previous = figure_hashes.get(key)
                if previous and previous != current:
                    errors.append(f"相同图文件重复归属两个小问：{previous}；{current}")
                else:
                    figure_hashes[key] = current
            checked.append(relative(sq_dir, root))

    solve_root = root / "求解"
    if solve_root.is_dir():
        for path in solve_root.rglob("*"):
            if not path.is_file() or path.resolve() in manifest_paths:
                continue
            parts = set(path.relative_to(solve_root).parts)
            suffix = path.suffix.lower()
            rel = relative(path, root)
            if suffix in CODE_EXTENSIONS and "代码" not in parts and "__pycache__" not in parts:
                errors.append(f"代码文件不在代码目录：{rel}")
            if suffix.lower() in FIGURE_EXTENSIONS and "图" not in parts:
                errors.append(f"图文件不在小问图目录：{rel}")
            if suffix.lower() in RESULT_EXTENSIONS and "结果" not in parts and "代码" not in parts:
                errors.append(f"结果文件不在小问结果目录：{rel}")

    # 跨小问交接：SKILL.md 与交付检查都要求字段、单位、粒度、质量标记和 fallback，
    # 因此这里对 handoffs 做结构校验，而不是让它停留在只写不校验的清单字段。
    handoffs = project_manifest.get("handoffs", [])
    handoff_edges: set[tuple[str, str]] = set()
    if not isinstance(handoffs, list):
        errors.append("项目清单的 handoffs 必须是数组")
        handoffs = []
    for handoff_index, handoff in enumerate(handoffs, start=1):
        prefix = f"项目清单的第{handoff_index}条跨小问交接"
        if not isinstance(handoff, dict):
            errors.append(f"{prefix}不是对象")
            continue
        endpoints: dict[str, str] = {}
        for field in ("from", "to"):
            value = str(handoff.get(field, "")).strip().replace("\\", "/")
            if not value:
                errors.append(f"{prefix}缺少 {field}")
                continue
            if value not in subquestion_index:
                errors.append(f"{prefix}的 {field} 不是已登记的小问目录：{value}")
                continue
            endpoints[field] = value
        if endpoints.get("from") and endpoints.get("from") == endpoints.get("to"):
            errors.append(f"{prefix}的 from 与 to 相同：{endpoints['from']}")
        for field in ("quality_flags", "fallback"):
            if not str(handoff.get(field, "")).strip():
                errors.append(f"{prefix}缺少 {field}")
        fields = handoff.get("fields", [])
        if not isinstance(fields, list) or not fields:
            errors.append(f"{prefix}缺少 fields")
        else:
            for field_index, field_entry in enumerate(fields, start=1):
                field_prefix = f"{prefix}的第{field_index}个字段"
                if not isinstance(field_entry, dict):
                    errors.append(f"{field_prefix}不是对象")
                    continue
                for key in ("name", "unit", "granularity"):
                    if not str(field_entry.get(key, "")).strip():
                        errors.append(f"{field_prefix}缺少 {key}")
        if "from" in endpoints and "to" in endpoints:
            handoff_edges.add((endpoints["from"], endpoints["to"]))

    if final:
        if project_manifest.get("official_rules_checked") is not True:
            errors.append("尚未核对当届官方通知：official_rules_checked 必须为 true")
        paper_profile = project_manifest.get("paper_profile", {})
        if not isinstance(paper_profile, dict):
            errors.append("项目清单缺少 paper_profile")
            paper_profile = {}
        profile_mode = str(paper_profile.get("mode", "default")).strip()
        if profile_mode not in {"default", "official_override", "user_override"}:
            errors.append(
                "paper_profile.mode 必须为 default、official_override 或 user_override"
            )
            profile_mode = "default"
        structure_profile = str(paper_profile.get("structure_profile", "mixed")).strip()
        try:
            profile_schema_version = int(paper_profile.get("schema_version", 1))
        except (TypeError, ValueError):
            profile_schema_version = 0
            errors.append("paper_profile.schema_version 必须为正整数")
        assumptions_symbols_mode = str(
            paper_profile.get("assumptions_symbols_mode", "combined")
        ).strip()
        shared_data_enabled = paper_profile.get("shared_data_section") is True
        model_evaluation_enabled = paper_profile.get("model_evaluation_section", True) is True
        question_heading_style = str(
            paper_profile.get("question_heading_style", "concise")
        ).strip()
        if profile_mode == "default":
            if profile_schema_version >= 2 and not isinstance(
                paper_profile.get("shared_data_section"), bool
            ):
                errors.append("paper_profile.shared_data_section 必须为布尔值")
            if profile_schema_version >= 2 and not isinstance(
                paper_profile.get("model_evaluation_section"), bool
            ):
                errors.append("paper_profile.model_evaluation_section 必须为布尔值")
            if structure_profile not in {"shared_data", "problem_local", "mixed"}:
                errors.append(
                    "paper_profile.structure_profile 必须为 shared_data、problem_local 或 mixed"
                )
                structure_profile = "mixed"
            if profile_schema_version >= 2 and not str(
                paper_profile.get("structure_rationale", "")
            ).strip():
                errors.append("默认结构必须填写 paper_profile.structure_rationale")
            if structure_profile == "shared_data" and not shared_data_enabled:
                errors.append("shared_data Profile 必须启用公共数据章节")
            if structure_profile == "problem_local" and shared_data_enabled:
                errors.append("problem_local Profile 不得启用公共数据章节")
            if assumptions_symbols_mode not in {"combined", "separate"}:
                errors.append(
                    "paper_profile.assumptions_symbols_mode 必须为 combined 或 separate"
                )
                assumptions_symbols_mode = "combined"
            if profile_schema_version >= 3 and question_heading_style not in {"concise", "solution"}:
                errors.append("paper_profile.question_heading_style 必须为 concise 或 solution")
                question_heading_style = "concise"
            if profile_schema_version >= 2 and not str(
                paper_profile.get("model_evaluation_rationale", "")
            ).strip():
                errors.append("必须说明是否设置独立模型评价章的依据")
            assumptions_layout = (
                "assumptions-symbols-combined"
                if assumptions_symbols_mode == "combined"
                else "assumptions-symbols-separate"
            )
            expected_layout = (
                f"abstract-contents-restatement-{assumptions_layout}-"
                f"{'shared-data-' if shared_data_enabled else ''}questions-"
                f"{'evaluation-' if model_evaluation_enabled else ''}references-appendix"
            )
            legacy_layout = (
                "abstract-contents-restatement-assumptions-symbols-optional-data-"
                "questions-evaluation-references-appendix"
            )
            accepted_layout = expected_layout if profile_schema_version >= 2 else legacy_layout
            if paper_profile.get("layout") != accepted_layout:
                errors.append(f"paper_profile.layout 必须与结构决策一致：{accepted_layout}")
        if profile_mode != "default":
            if not str(paper_profile.get("layout", "")).strip():
                errors.append("覆盖默认结构时 paper_profile.layout 不得为空")
            if not str(paper_profile.get("override_reason", "")).strip():
                errors.append("覆盖默认结构时必须填写 paper_profile.override_reason")
            if not str(paper_profile.get("override_reference", "")).strip():
                errors.append("覆盖默认结构时必须填写 paper_profile.override_reference")
        if profile_schema_version >= 3:
            problem_spec_path = root / "problem-spec.json"
            if not problem_spec_path.is_file():
                errors.append("任务驱动项目缺少根目录 problem-spec.json")
            else:
                try:
                    problem_spec = json.loads(problem_spec_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    errors.append(f"problem-spec.json 无法读取：{exc}")
                else:
                    errors.extend(
                        f"problem-spec.json：{message}"
                        for message in validate_problem_spec(problem_spec)
                    )
        style_transfer = project_manifest.get("style_transfer", {"enabled": False})
        if not isinstance(style_transfer, dict):
            errors.append("style_transfer 必须是对象")
        elif style_transfer.get("enabled") is True:
            try:
                style_schema_version = int(style_transfer.get("schema_version", 1))
            except (TypeError, ValueError):
                style_schema_version = 1
                errors.append("style_transfer.schema_version 必须为正整数")
            sources = style_transfer.get("sources", [])
            if not isinstance(sources, list) or not sources:
                errors.append("启用风格迁移时必须登记参考来源")
            style_card = str(style_transfer.get("style_card", "")).strip().replace("\\", "/")
            if not style_card or not (root / style_card).is_file():
                errors.append("启用风格迁移时必须提供可追溯的 Style Card 文件")
            if style_schema_version >= 2:
                for source_index, source in enumerate(sources, start=1):
                    if not isinstance(source, dict):
                        errors.append(f"style_transfer.sources[{source_index}] 必须是对象")
                        continue
                    for field in ("id", "title", "locator", "path_or_citation"):
                        if not str(source.get(field, "")).strip():
                            errors.append(
                                f"style_transfer.sources[{source_index}].{field} 不得为空"
                            )
                review_file = str(style_transfer.get("review_file", "")).strip().replace("\\", "/")
                review_path = root / review_file if review_file else None
                if not review_file or review_path is None or not review_path.is_file():
                    errors.append("schema v2 风格迁移缺少写后范文对照复核文件")
                status = str(style_transfer.get("status", "")).strip()
                if status not in {"card_ready", "checked"}:
                    errors.append("style_transfer.status 必须为 card_ready 或 checked")
                checks = style_transfer.get("checks", [])
                if status == "checked":
                    if review_path is not None and review_path.is_file():
                        review_text = review_path.read_text(encoding="utf-8", errors="replace")
                        if "REVIEW_STATUS: checked" not in review_text:
                            errors.append("范文对照复核文件尚未标记 REVIEW_STATUS: checked")
                    covered_dimensions: set[str] = set()
                    if not isinstance(checks, list):
                        errors.append("style_transfer.checks 必须是数组")
                    else:
                        for check_index, check in enumerate(checks, start=1):
                            prefix = f"style_transfer.checks[{check_index}]"
                            if not isinstance(check, dict):
                                errors.append(f"{prefix} 必须是对象")
                                continue
                            for field in ("dimension", "paper_location", "finding", "action"):
                                if not str(check.get(field, "")).strip():
                                    errors.append(f"{prefix}.{field} 不得为空")
                            dimension = str(check.get("dimension", "")).strip()
                            dimension = STYLE_REVIEW_DIMENSION_ALIASES.get(dimension, dimension)
                            if dimension:
                                covered_dimensions.add(dimension)
                    missing_dimensions = sorted(STYLE_REVIEW_DIMENSIONS - covered_dimensions)
                    if missing_dimensions:
                        errors.append(f"范文写后复核缺少维度：{missing_dimensions}")
                if final and status != "checked":
                    errors.append("最终交付前必须完成范文写后对照复核：status=checked")
            elif style_transfer.get("status") != "checked":
                errors.append("Style Card 尚未完成人工边界复核：status 必须为 checked")
        profile_sources = paper_profile.get("sources", {})
        if not isinstance(profile_sources, dict):
            errors.append("paper_profile.sources 必须是对象")
            profile_sources = {}
        active_rel = [path.relative_to(paper_root).as_posix() for path in active_paper_sources]
        question_sources = profile_sources.get("questions", [])
        if not isinstance(question_sources, list) or len(question_sources) != len(questions):
            errors.append("paper_profile.sources.questions 必须逐题登记正式章节")
            question_sources = []
        for index, value in enumerate(question_sources, start=1):
            source = str(value).strip().replace("\\", "/")
            if not source:
                errors.append(f"paper_profile.sources.questions 第{index}项为空")
                continue
            if source not in active_rel:
                errors.append(f"问题章节未进入 main.tex：{source}")
            path = paper_root / source
            question_entry = questions[index - 1] if index <= len(questions) else {}
            question_no = int(question_entry.get("question", index)) if isinstance(question_entry, dict) else index
            question_title = str(question_entry.get("title", "")).strip() if isinstance(question_entry, dict) else ""
            if not question_title or "请根据题意概括" in question_title:
                errors.append(f"问题{chinese_number(question_no)}尚未填写正式章节标题")
            if path.is_file() and profile_mode == "default":
                question_text = strip_tex_comments(path.read_text(encoding="utf-8"))
                has_top_analysis = bool(
                    re.search(r"\\subsection\s*\{[^}]*问题分析[^}]*\}", question_text)
                )
                if question_title and "请根据题意概括" not in question_title:
                    heading_text = (
                        f"问题{chinese_number(question_no)}的求解：{question_title}"
                        if question_heading_style == "solution"
                        else f"问题{chinese_number(question_no)}：{question_title}"
                    )
                    expected_heading = f"\\section{{{heading_text}}}"
                    if expected_heading not in question_text:
                        errors.append(
                            f"顶层问题章节标题与项目清单不一致：应为 {expected_heading}"
                        )
                subquestions = question_entry.get("subquestions", []) if isinstance(question_entry, dict) else []
                sub_analysis_flags: list[bool] = []
                for sub_index, sub_entry in enumerate(subquestions, start=1):
                    sub_source = f"sections/question-{question_no}-sub-{sub_index}.tex"
                    sub_path = paper_root / sub_source
                    default_label = chr(ord("a") + sub_index - 1) if sub_index <= 26 else str(sub_index)
                    expected_label = (
                        str(sub_entry.get("label", default_label)).strip()
                        if isinstance(sub_entry, dict)
                        else default_label
                    )
                    if sub_source not in active_rel or not sub_path.is_file():
                        errors.append(f"问题{chinese_number(question_no)}缺少正式小问源文件：{sub_source}")
                        continue
                    sub_text = strip_tex_comments(sub_path.read_text(encoding="utf-8"))
                    sub_analysis_flags.append(
                        bool(re.search(r"\\subsubsection\s*\{[^}]*问题分析[^}]*\}", sub_text))
                    )
                    subtitle = (
                        str(sub_entry.get("title", "")).strip()
                        if isinstance(sub_entry, dict)
                        else ""
                    )
                    explicit = sub_entry.get("explicit", True) is True if isinstance(sub_entry, dict) else True
                    expected_subheading = (
                        f"问题 {expected_label}：{subtitle}"
                        if explicit and subtitle
                        else f"小问 {expected_label}"
                        if explicit
                        else subtitle or "模型建立与求解"
                    )
                    if f"\\subsection{{{expected_subheading}}}" not in sub_text:
                        errors.append(
                            f"{sub_source} 的标题应与题面顺序对应为“{expected_subheading}”"
                        )
                analysis_mode = str(question_entry.get("analysis_mode", "top_level")).strip()
                if analysis_mode not in {"top_level", "per_subquestion", "hybrid"}:
                    errors.append(
                        f"问题{chinese_number(question_no)}的 analysis_mode 必须为 "
                        "top_level、per_subquestion 或 hybrid"
                    )
                elif analysis_mode == "top_level" and not has_top_analysis:
                    errors.append(f"顶层统一分析模式缺少“问题分析”小节：{source}")
                elif analysis_mode == "per_subquestion":
                    if has_top_analysis:
                        errors.append(f"逐小问分析模式不应保留重复的顶层“问题分析”：{source}")
                    if sub_analysis_flags and not all(sub_analysis_flags):
                        errors.append(
                            f"逐小问分析模式要求每个小问均含“问题分析”：问题{chinese_number(question_no)}"
                        )
                elif analysis_mode == "hybrid":
                    if not has_top_analysis or not any(sub_analysis_flags):
                        errors.append(
                            f"混合分析模式要求同时存在顶层概览和至少一个小问内部分析："
                            f"问题{chinese_number(question_no)}"
                        )

        if profile_mode == "default":
            ordered_roles: list[tuple[str, str]] = []
            for role in ("abstract", "restatement"):
                value = str(profile_sources.get(role, "")).strip().replace("\\", "/")
                if not value:
                    errors.append(f"paper_profile.sources 缺少 {role}")
                else:
                    ordered_roles.append((role, value))
            if assumptions_symbols_mode == "combined":
                value = str(profile_sources.get("assumptions_symbols", "")).strip().replace("\\", "/")
                if not value:
                    errors.append("合并假设与符号时 paper_profile.sources.assumptions_symbols 不能为空")
                else:
                    ordered_roles.append(("assumptions_symbols", value))
                if any(str(profile_sources.get(role, "")).strip() for role in ("assumptions", "symbols")):
                    errors.append("合并假设与符号时 assumptions 与 symbols 源应为空")
            else:
                if str(profile_sources.get("assumptions_symbols", "")).strip():
                    errors.append("拆分假设与符号时 assumptions_symbols 源应为空")
                for role in ("assumptions", "symbols"):
                    value = str(profile_sources.get(role, "")).strip().replace("\\", "/")
                    if not value:
                        errors.append(f"拆分假设与符号时 paper_profile.sources.{role} 不能为空")
                    else:
                        ordered_roles.append((role, value))
            shared_data = str(profile_sources.get("shared_data", "")).strip().replace("\\", "/")
            if shared_data_enabled:
                if not shared_data:
                    errors.append("启用公共数据章节但 paper_profile.sources.shared_data 为空")
                else:
                    ordered_roles.append(("shared_data", shared_data))
            elif shared_data:
                errors.append("未启用公共数据章节时 paper_profile.sources.shared_data 应为空")
            elif re.search(r"\\section\s*\{数据说明与预处理\}", paper_text):
                errors.append("未启用公共数据章节，但正式论文源文件链中仍存在“数据说明与预处理”")
            ordered_roles.extend(
                (f"question_{index}", str(value).strip().replace("\\", "/"))
                for index, value in enumerate(question_sources, start=1)
                if str(value).strip()
            )
            model_evaluation = str(
                profile_sources.get("model_evaluation", "")
            ).strip().replace("\\", "/")
            if model_evaluation_enabled:
                if not model_evaluation:
                    errors.append("启用模型评价章但 paper_profile.sources.model_evaluation 为空")
                else:
                    ordered_roles.append(("model_evaluation", model_evaluation))
            elif model_evaluation:
                errors.append("未启用模型评价章时 paper_profile.sources.model_evaluation 应为空")
            elif re.search(r"\\section\s*\{模型评价(?:与推广)?\}", paper_text):
                errors.append("未启用模型评价章，但正式论文源文件链中仍存在该章节")
            for role in ("references", "appendix"):
                value = str(profile_sources.get(role, "")).strip().replace("\\", "/")
                if not value:
                    errors.append(f"paper_profile.sources 缺少 {role}")
                else:
                    ordered_roles.append((role, value))
            declared_source_order = paper_profile.get("source_order", [])
            expected_source_order = [source for _, source in ordered_roles]
            normalized_source_order = (
                [str(value).strip().replace("\\", "/") for value in declared_source_order]
                if isinstance(declared_source_order, list)
                else []
            )
            if normalized_source_order != expected_source_order:
                errors.append("paper_profile.source_order 与默认章节角色和启用状态不一致")
            positions: list[int] = []
            for role, source in ordered_roles:
                if source not in active_rel:
                    errors.append(f"paper_profile 登记的正式章节未进入 main.tex：{role}={source}")
                else:
                    positions.append(active_rel.index(source))
            if positions != sorted(positions) or len(positions) != len(set(positions)):
                errors.append("main.tex 的正式章节顺序与 paper_profile.layout 不一致")
        else:
            source_order = paper_profile.get("source_order", [])
            if not isinstance(source_order, list) or not source_order:
                errors.append("覆盖默认结构时必须在 paper_profile.source_order 登记正式章节顺序")
                source_order = []
            normalized_order = [str(value).strip().replace("\\", "/") for value in source_order]
            if any(not value for value in normalized_order):
                errors.append("paper_profile.source_order 不得包含空路径")
            if len(normalized_order) != len(set(normalized_order)):
                errors.append("paper_profile.source_order 不得包含重复路径")
            override_positions: list[int] = []
            for source in normalized_order:
                if source not in active_rel:
                    errors.append(f"覆盖结构登记的正式章节未进入 main.tex：{source}")
                else:
                    override_positions.append(active_rel.index(source))
            if override_positions != sorted(override_positions):
                errors.append("main.tex 的正式章节顺序与 paper_profile.source_order 不一致")
            abstract_source = str(profile_sources.get("abstract", "")).strip().replace("\\", "/")
            required_override_sources = [abstract_source] + [
                str(value).strip().replace("\\", "/") for value in question_sources
            ]
            for source in required_override_sources:
                if not source or source not in normalized_order:
                    errors.append(f"覆盖结构的 source_order 缺少摘要或问题章节：{source or '(空)'}")
        if main_tex.is_file():
            main_without_comments = strip_tex_comments(main_tex.read_text(encoding="utf-8"))
            if profile_mode == "default":
                abstract_source = str(profile_sources.get("abstract", "")).strip().replace("\\", "/")
                restatement_source = str(profile_sources.get("restatement", "")).strip().replace("\\", "/")
                abstract_token = f"\\input{{{abstract_source}}}"
                restatement_token = f"\\input{{{restatement_source}}}"
                contents_token = "\\tableofcontents"
                front_positions = [
                    main_without_comments.find(abstract_token),
                    main_without_comments.find(contents_token),
                    main_without_comments.find(restatement_token),
                ]
                if any(position < 0 for position in front_positions) or front_positions != sorted(front_positions):
                    errors.append("main.tex 必须按“摘要—目录—问题重述”顺序组织前置内容")
            title_match = re.search(r"\\papertitle\s*\{([^{}]+)\}", main_without_comments)
            if not title_match or any(
                marker in title_match.group(1)
                for marker in ("论文标题", "请填写", "用一句话概括")
            ):
                errors.append("最终论文尚未填写正式题目：请替换 main.tex 中的 \\papertitle 占位文本")

        structural_tokens = {
            "restatement": (
                "问题重述",
                ["\\section{问题重述}", "\\subsection{问题背景}", "\\subsection{问题提出}"],
            ),
            "references": (
                "参考文献",
                ["\\begin{thebibliography}"],
            ),
            "appendix": (
                "附录",
                ["\\appendix", "\\section{"],
            ),
        }
        if profile_mode == "default" and assumptions_symbols_mode == "combined":
            structural_tokens["assumptions_symbols"] = (
                "基本假设与符号说明",
                [
                    "\\section{基本假设与符号说明}",
                    "\\subsection{基本假设}",
                    "\\subsection{符号说明}",
                ],
            )
        elif profile_mode == "default":
            structural_tokens["assumptions"] = ("模型假设", ["\\section{模型假设}"])
            structural_tokens["symbols"] = ("符号说明", ["\\section{符号说明}"])
        if profile_mode == "default" and model_evaluation_enabled:
            structural_tokens["model_evaluation"] = (
                "模型评价与推广",
                ["\\section{模型评价与推广}"],
            )
        if profile_mode == "default" and shared_data_enabled:
            structural_tokens["shared_data"] = (
                "数据说明与预处理",
                ["\\section{数据说明与预处理}"],
            )
        if profile_mode == "default":
            for role, (label, tokens) in structural_tokens.items():
                source = str(profile_sources.get(role, "")).strip().replace("\\", "/")
                source_path = paper_root / source
                if not source or not source_path.is_file():
                    continue
                source_text = strip_tex_comments(source_path.read_text(encoding="utf-8"))
                token_positions = [source_text.find(token) for token in tokens]
                if any(position < 0 for position in token_positions) or token_positions != sorted(token_positions):
                    errors.append(f"{label}章节的标题层级或顺序不符合默认模板：{source}")
        # 只对能机械解析到小问目录的依赖做反查，散文式依赖描述不误报。
        for sq_rel, sq_manifest in sorted(subquestion_index.items()):
            declared = sq_manifest.get("dependencies", [])
            if not isinstance(declared, list):
                errors.append(f"{sq_rel} 的 dependencies 必须是数组")
                continue
            for dependency in declared:
                upstream = str(dependency).strip().replace("\\", "/")
                if upstream not in subquestion_index:
                    continue
                if (upstream, sq_rel) not in handoff_edges:
                    errors.append(
                        f"{sq_rel} 依赖 {upstream} 但项目清单缺少对应 handoffs 记录"
                        "（需含字段、单位、粒度、质量标记与 fallback）"
                    )
        if core_algorithm_count == 0:
            errors.append("最终论文未识别任何核心方法；至少登记一种承担核心推理或求解责任的方法")
        paper_workflow = project_manifest.get("paper_workflow", {})
        if not isinstance(paper_workflow, dict):
            errors.append("项目清单缺少 paper_workflow")
            paper_workflow = {}
        if paper_workflow.get("results_locked") is not True:
            errors.append("正式摘要前尚未锁定全部结果：paper_workflow.results_locked 必须为 true")
        if paper_workflow.get("abstract_status") != "final":
            errors.append("摘要尚未标记为 final")
        if paper_workflow.get("abstract_evidence_check") != "passed":
            errors.append("摘要关键结果尚未完成逐问证据复核")
        all_question_numbers = [
            int(question.get("question", 0))
            for question in questions
            if isinstance(question, dict)
        ]
        configured_abstract_questions = paper_workflow.get("abstract_questions", [])
        if configured_abstract_questions in (None, []):
            abstract_question_numbers = all_question_numbers
        elif not isinstance(configured_abstract_questions, list) or not all(
            isinstance(number, int) for number in configured_abstract_questions
        ):
            errors.append("paper_workflow.abstract_questions 必须是整数数组；空数组表示全部问题")
            abstract_question_numbers = all_question_numbers
        else:
            invalid_numbers = sorted(set(configured_abstract_questions) - set(all_question_numbers))
            if invalid_numbers:
                errors.append(f"摘要范围包含不存在的问题：{invalid_numbers}")
            if len(configured_abstract_questions) != len(set(configured_abstract_questions)):
                errors.append("paper_workflow.abstract_questions 不得包含重复问题")
            abstract_question_numbers = [
                number for number in all_question_numbers if number in configured_abstract_questions
            ]
            if set(abstract_question_numbers) != set(all_question_numbers) and not str(
                paper_workflow.get("abstract_scope_reason", "")
            ).strip():
                errors.append("摘要未覆盖全部问题时必须填写 paper_workflow.abstract_scope_reason")
        scoped_questions = [
            question
            for question in questions
            if isinstance(question, dict)
            and int(question.get("question", 0)) in abstract_question_numbers
        ]
        errors.extend(validate_abstract_plan(
            root,
            paper_workflow,
            all_question_numbers,
            abstract_question_numbers,
        ))
        abstract_evidence = paper_workflow.get("abstract_evidence", [])
        if not isinstance(abstract_evidence, list):
            errors.append("paper_workflow.abstract_evidence 必须是数组")
            abstract_evidence = []
        evidence_by_question: dict[int, dict[str, object]] = {}
        for entry in abstract_evidence:
            if isinstance(entry, dict) and isinstance(entry.get("question"), int):
                evidence_by_question[int(entry["question"])] = entry
        for question in scoped_questions:
            if not isinstance(question, dict):
                continue
            question_no = int(question.get("question", 0))
            entry = evidence_by_question.get(question_no)
            if not entry:
                errors.append(f"摘要缺少问题{chinese_number(question_no)}的证据登记")
                continue
            if entry.get("checked") is not True:
                errors.append(f"摘要问题{chinese_number(question_no)}的证据尚未复核")
            files = entry.get("files", [])
            if not isinstance(files, list) or not files:
                errors.append(f"摘要问题{chinese_number(question_no)}缺少证据文件")
            else:
                for evidence_file in files:
                    if not (root / str(evidence_file)).is_file():
                        errors.append(f"摘要证据文件不存在：{evidence_file}")
            if not str(entry.get("locator", "")).strip():
                errors.append(f"摘要问题{chinese_number(question_no)}缺少字段/键/行定位")
        errors.extend(validate_model_review(root, paper_workflow))
        cited_keys, defined_keys = citation_keys_from_paper(paper_root, paper_text)
        errors.extend(validate_citation_ledger(paper_workflow, cited_keys, defined_keys))
        abstract_files = [
            path
            for path in active_paper_sources
            if "% ABSTRACT_STATUS:" in path.read_text(encoding="utf-8", errors="replace")
        ]
        if not abstract_files:
            errors.append("最终交付缺少可校验的摘要 TeX 文件")
        else:
            abstract_text = "\n".join(path.read_text(encoding="utf-8") for path in abstract_files)
            if "% ABSTRACT_STATUS: final" not in abstract_text:
                errors.append("摘要文件仍是 placeholder，或缺少 % ABSTRACT_STATUS: final 标记")
            positions: list[int] = []
            for question in scoped_questions:
                if not isinstance(question, dict):
                    continue
                question_no = int(question.get("question", 0))
                label = f"问题{chinese_number(question_no)}"
                pattern = rf"\\textbf\{{(?:针对)?{re.escape(label)}[：:]\}}"
                match = re.search(pattern, abstract_text)
                if not match:
                    errors.append(f"摘要缺少独立粗体段落标签：{label}：或针对{label}：")
                else:
                    positions.append(match.start())
            if positions != sorted(positions):
                errors.append("摘要中的问题段落未按题面顺序排列")

        # 只接受论文根目录下由 compile_paper.py 生成的当前报告。递归搜索或“任一历史报告
        # 成功即可”会让旧产物掩盖当前编译失败。输入哈希用于发现编译后又修改正文或图表。
        compile_report_path = paper_root / "编译报告.json"
        verified_pdf: Path | None = None
        verified_pdf_hash = ""
        if not compile_report_path.is_file():
            errors.append(
                "最终交付缺少论文编译报告：请先运行 python scripts/compile_paper.py <项目目录>/论文"
            )
        else:
            try:
                compile_report = json.loads(compile_report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"编译报告无法读取 {relative(compile_report_path, root)}：{exc}")
                compile_report = {}
            if not isinstance(compile_report, dict):
                errors.append(f"编译报告格式错误：{relative(compile_report_path, root)}")
                compile_report = {}
            if compile_report.get("schema_version") != 1:
                errors.append("编译报告版本过旧或无效；请用当前 compile_paper.py 重新编译")
            if compile_report.get("ok") is not True:
                errors.append("论文最近一次编译未成功；请修复编译错误后重新编译")
            engine_name = Path(str(compile_report.get("engine", ""))).name.lower()
            if engine_name not in {"xelatex", "xelatex.exe"}:
                errors.append("编译报告的 engine 不是 xelatex")
            if not str(compile_report.get("compiled_at", "")).strip():
                errors.append("编译报告缺少 compiled_at")
            passes = compile_report.get("passes", [])
            if not isinstance(passes, list) or len(passes) != 2:
                errors.append("编译报告必须包含两遍 XeLaTeX 记录")
            elif [item.get("pass") for item in passes if isinstance(item, dict)] != [1, 2] or any(
                not isinstance(item, dict)
                or item.get("returncode") != 0
                or item.get("status") != "completed"
                for item in passes
            ):
                errors.append("两遍 XeLaTeX 编译记录不完整或存在失败")
            if compile_report.get("input_manifest_source") != "xelatex-recorder":
                errors.append("编译报告缺少 XeLaTeX recorder 输入清单")
            inputs = compile_report.get("inputs", [])
            if not isinstance(inputs, list) or not inputs:
                errors.append("编译报告缺少当前论文输入文件哈希")
                inputs = []
            source_name = str(compile_report.get("source", "")).strip()
            source_seen = False
            recorded_input_paths: set[Path] = set()
            for index, entry in enumerate(inputs, start=1):
                if not isinstance(entry, dict):
                    errors.append(f"编译报告第{index}条输入记录不是对象")
                    continue
                rel_path = str(entry.get("path", "")).strip().replace("\\", "/")
                expected_hash = str(entry.get("sha256", "")).strip().lower()
                candidate = (root / rel_path).resolve()
                if not rel_path or (candidate != root and root not in candidate.parents):
                    errors.append(f"编译报告输入路径越出项目目录：{rel_path or '(空)'}")
                    continue
                if not candidate.is_file():
                    errors.append(f"编译后输入文件已不存在：{rel_path}")
                    continue
                recorded_input_paths.add(candidate)
                actual_hash = digest(candidate).lower()
                if expected_hash != actual_hash:
                    errors.append(f"论文输入在编译后发生变化，请重新编译：{rel_path}")
                if candidate == (paper_root / source_name).resolve():
                    source_seen = True
            if not source_name or not (paper_root / source_name).is_file():
                errors.append("编译报告记录的主 TeX 文件不存在")
            elif not source_seen:
                errors.append("主 TeX 文件未进入编译输入哈希清单")
            required_compile_inputs = set(active_paper_sources)
            local_class = paper_root / "graduate-modeling.cls"
            if local_class.is_file():
                required_compile_inputs.add(local_class.resolve())
            missing_recorded_inputs = required_compile_inputs - recorded_input_paths
            for missing_input in sorted(missing_recorded_inputs):
                errors.append(
                    f"正式论文源文件未进入编译输入哈希清单：{relative(missing_input, root)}"
                )
            pdf_name = str(compile_report.get("pdf", "")).strip()
            pdf_path = (paper_root / pdf_name).resolve() if pdf_name else paper_root / "__missing__.pdf"
            if not pdf_name or (pdf_path != paper_root and paper_root not in pdf_path.parents):
                errors.append("编译报告的 PDF 路径为空或越出论文目录")
            elif not pdf_path.is_file():
                errors.append(f"编译报告记录的 PDF 不存在：{relative(pdf_path, root)}")
            else:
                actual_pdf_hash = digest(pdf_path)
                actual_pdf_size = pdf_path.stat().st_size
                if str(compile_report.get("pdf_sha256", "")).lower() != actual_pdf_hash.lower():
                    errors.append("PDF 哈希与编译报告不一致")
                if compile_report.get("pdf_size") != actual_pdf_size:
                    errors.append("PDF 大小与编译报告不一致")
                if compile_report.get("pdf_structure_ok") is not True or not pdf_structure_ok(pdf_path):
                    errors.append("PDF 未通过基本结构检查")
                else:
                    verified_pdf = pdf_path
                    verified_pdf_hash = actual_pdf_hash
                    checked.append(f"论文已完成两遍编译并绑定当前输入：{relative(pdf_path, root)}")
            if compile_report.get("visual_review_required") is not True:
                errors.append("编译报告未声明必须进行 PDF 视觉检查")

        visual_review = paper_workflow.get("pdf_visual_review", {})
        if not isinstance(visual_review, dict) or visual_review.get("status") != "passed":
            errors.append("最终交付前必须完成人工 PDF 视觉检查并登记 pdf_visual_review")
        else:
            review_hash = str(visual_review.get("pdf_sha256", "")).strip().lower()
            review_checks = visual_review.get("checks", [])
            if verified_pdf is not None and review_hash != verified_pdf_hash.lower():
                errors.append("PDF 视觉检查记录对应的不是当前编译版本")
            if not isinstance(review_checks, list) or not any(str(item).strip() for item in review_checks):
                errors.append("pdf_visual_review.checks 至少记录一项实际检查内容")

    return {"ok": not errors, "final_mode": final, "errors": errors, "warnings": warnings, "checked": checked}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--report", type=Path, help="报告路径，默认写入项目根目录")
    parser.add_argument("--final", action="store_true", help="最终交付校验，同时要求论文质量门通过")
    args = parser.parse_args()
    report = validate(args.project, final=args.final)
    output = args.report or (args.project / "结构校验报告.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()

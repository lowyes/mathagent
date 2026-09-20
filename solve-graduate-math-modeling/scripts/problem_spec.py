#!/usr/bin/env python3
"""Load and validate a task-driven mathematical-modeling problem blueprint."""

from __future__ import annotations

import json
from pathlib import Path


TASK_TYPES = {
    "deterministic_rule",
    "prediction",
    "classification",
    "fitting",
    "clustering",
    "optimization",
    "evaluation",
    "simulation",
    "association_decision",
}

METHOD_TYPES = {
    "deterministic_rule",
    "statistical_test",
    "association_analysis",
    "feature_pipeline",
    "predictive_model",
    "predictive_pipeline",
    "fitting_model",
    "clustering_model",
    "optimization_model",
    "simulation_model",
    "evaluation_model",
    "mechanistic_model",
    "iterative_algorithm",
}

METHOD_REPRESENTATIONS = {
    "definition",
    "formula",
    "flowchart",
    "pseudocode",
    "result_table",
    "experiment_table",
    "ablation_table",
    "case_table",
    "result_figure",
    "comparison_figure",
    "diagnostic_figure",
    "correlation_figure",
    "trajectory_figure",
    "confusion_matrix",
    "recommendation_text",
}

LITERATURE_APPLICABILITY = {"pending", "required", "conditional", "not_required"}
ANALYSIS_MODES = {"top_level", "per_subquestion", "hybrid"}
STRUCTURE_PROFILES = {"shared_data", "problem_local", "mixed"}
ASSUMPTION_SYMBOL_MODES = {"combined", "separate"}
HEADING_STYLES = {"concise", "solution"}
SUPPORTED_SCHEMA_VERSIONS = {1, 2}

TASKS_REQUIRING_EXPERIMENTS = {
    "prediction",
    "classification",
    "fitting",
    "clustering",
    "optimization",
    "evaluation",
    "simulation",
}
TASKS_REQUIRING_MODEL_COMPARISON = {"prediction", "classification"}


def _nonempty_text(value: object) -> bool:
    return bool(str(value).strip())


def _validate_task_profile(
    profile: object,
    prefix: str,
    errors: list[str],
    schema_version: int,
) -> None:
    if not isinstance(profile, dict):
        errors.append(f"{prefix}.task_profile 必须是对象")
        return
    primary = str(profile.get("primary", "")).strip()
    if primary not in TASK_TYPES:
        errors.append(f"{prefix}.task_profile.primary 无效：{primary or '(空)'}")
    if schema_version >= 2 and not _nonempty_text(profile.get("primary_reason", "")):
        errors.append(f"{prefix}.task_profile.primary_reason 必须说明主任务类型的判定依据")
    secondary = profile.get("secondary", [])
    if not isinstance(secondary, list) or not all(_nonempty_text(item) for item in secondary):
        errors.append(f"{prefix}.task_profile.secondary 必须是非空字符串数组或空数组")
    outputs = profile.get("outputs", [])
    if not isinstance(outputs, list) or not outputs:
        errors.append(f"{prefix}.task_profile.outputs 至少登记一个题目要求的输出")
    elif schema_version >= 2:
        for index, output in enumerate(outputs, start=1):
            output_prefix = f"{prefix}.task_profile.outputs[{index}]"
            if not isinstance(output, dict):
                errors.append(f"{output_prefix} 在 schema v2 中必须是对象")
                continue
            for field in ("name", "unit", "granularity", "acceptance"):
                if not _nonempty_text(output.get(field, "")):
                    errors.append(f"{output_prefix}.{field} 不得为空")
    elif not any(
        _nonempty_text(item.get("name", "")) if isinstance(item, dict) else _nonempty_text(item)
        for item in outputs
    ):
        errors.append(f"{prefix}.task_profile.outputs 至少登记一个有效输出")


def _validate_argument_plan(plan: object, prefix: str, errors: list[str]) -> None:
    if not isinstance(plan, dict):
        errors.append(f"{prefix}.argument_plan 在 schema v2 中必须是对象")
        return
    if not _nonempty_text(plan.get("decision_question", "")):
        errors.append(f"{prefix}.argument_plan.decision_question 不得为空")
    evidence = plan.get("evidence_required", [])
    if not isinstance(evidence, list) or not any(_nonempty_text(item) for item in evidence):
        errors.append(f"{prefix}.argument_plan.evidence_required 至少登记一项证据需求")
    if not _nonempty_text(plan.get("interpretation_boundary", "")):
        errors.append(f"{prefix}.argument_plan.interpretation_boundary 不得为空")


def _validate_literature(review: object, prefix: str, errors: list[str]) -> None:
    if not isinstance(review, dict):
        errors.append(f"{prefix}.literature_review 必须是对象")
        return
    applicability = str(review.get("applicability", "")).strip()
    if applicability not in LITERATURE_APPLICABILITY:
        errors.append(f"{prefix}.literature_review.applicability 无效：{applicability or '(空)'}")
    if applicability != "pending" and not _nonempty_text(review.get("reason", "")):
        errors.append(f"{prefix}.literature_review.reason 不得为空")


def _validate_methods(methods: object, prefix: str, errors: list[str], ids: set[str]) -> None:
    if methods is None:
        return
    if not isinstance(methods, list):
        errors.append(f"{prefix}.methods 必须是数组")
        return
    for index, method in enumerate(methods, start=1):
        method_prefix = f"{prefix}.methods[{index}]"
        if not isinstance(method, dict):
            errors.append(f"{method_prefix} 必须是对象")
            continue
        method_id = str(method.get("id", "")).strip()
        if not method_id:
            errors.append(f"{method_prefix}.id 不得为空")
        elif method_id in ids:
            errors.append(f"{method_prefix}.id 重复：{method_id}")
        else:
            ids.add(method_id)
        if not _nonempty_text(method.get("name", "")):
            errors.append(f"{method_prefix}.name 不得为空")
        method_type = str(method.get("method_type", "")).strip()
        if method_type not in METHOD_TYPES:
            errors.append(f"{method_prefix}.method_type 无效：{method_type or '(空)'}")
        representations = method.get("representations", [])
        if not isinstance(representations, list) or not representations:
            errors.append(f"{method_prefix}.representations 至少登记一种表达载体")
        else:
            unknown = {str(item).strip() for item in representations} - METHOD_REPRESENTATIONS
            if unknown:
                errors.append(f"{method_prefix}.representations 含未知值：{sorted(unknown)}")
        if method_type == "iterative_algorithm" and method.get("is_core") is True:
            reps = {str(item).strip() for item in representations} if isinstance(representations, list) else set()
            for required in ("pseudocode", "flowchart"):
                if required not in reps:
                    errors.append(f"{method_prefix} 为核心迭代算法，缺少 {required} 表达")


def _validate_style_transfer_v2(style: dict[str, object], errors: list[str]) -> None:
    sources = style.get("sources", [])
    if not isinstance(sources, list) or not sources:
        errors.append("启用风格迁移时 style_transfer.sources 不得为空")
        return
    source_ids: set[str] = set()
    for index, source in enumerate(sources, start=1):
        prefix = f"style_transfer.sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} 在 schema v2 中必须是对象")
            continue
        source_id = str(source.get("id", "")).strip()
        if not source_id:
            errors.append(f"{prefix}.id 不得为空")
        elif source_id in source_ids:
            errors.append(f"{prefix}.id 重复：{source_id}")
        else:
            source_ids.add(source_id)
        for field in ("title", "locator", "path_or_citation"):
            if not _nonempty_text(source.get(field, "")):
                errors.append(f"{prefix}.{field} 不得为空")

    card = style.get("card", {})
    if not isinstance(card, dict):
        errors.append("启用风格迁移时 style_transfer.card 必须是对象")
        return
    for field, minimum_support in (("common_features", 2), ("variants", 1)):
        values = card.get(field, [])
        if not isinstance(values, list):
            errors.append(f"style_transfer.card.{field} 必须是数组")
            continue
        for index, item in enumerate(values, start=1):
            prefix = f"style_transfer.card.{field}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} 在 schema v2 中必须是对象")
                continue
            if not _nonempty_text(item.get("statement", "")):
                errors.append(f"{prefix}.statement 不得为空")
            supported_by = item.get("supported_by", [])
            if not isinstance(supported_by, list):
                errors.append(f"{prefix}.supported_by 必须是来源 id 数组")
                continue
            normalized = [str(value).strip() for value in supported_by if str(value).strip()]
            if len(set(normalized)) < minimum_support:
                errors.append(
                    f"{prefix}.supported_by 至少需要 {minimum_support} 个独立来源"
                )
            unknown = sorted(set(normalized) - source_ids)
            if unknown:
                errors.append(f"{prefix}.supported_by 含未知来源：{unknown}")

    choices = card.get("current_choices", [])
    if not isinstance(choices, list) or not choices:
        errors.append("启用风格迁移时 style_transfer.card.current_choices 不得为空")
    else:
        for index, item in enumerate(choices, start=1):
            prefix = f"style_transfer.card.current_choices[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} 在 schema v2 中必须是对象")
                continue
            for field in ("statement", "reason"):
                if not _nonempty_text(item.get(field, "")):
                    errors.append(f"{prefix}.{field} 不得为空")


def validate_problem_spec(spec: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(spec, dict):
        return ["problem-spec 根节点必须是对象"]
    schema_version = spec.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(
            "problem-spec.schema_version 必须为受支持版本："
            + ", ".join(str(value) for value in sorted(SUPPORTED_SCHEMA_VERSIONS))
        )
        schema_version = 1

    profile = spec.get("paper_profile", {})
    if not isinstance(profile, dict):
        errors.append("paper_profile 必须是对象")
        profile = {}
    structure = str(profile.get("structure_profile", "mixed")).strip()
    if structure not in STRUCTURE_PROFILES:
        errors.append(f"paper_profile.structure_profile 无效：{structure}")
    assumptions = str(profile.get("assumptions_symbols_mode", "combined")).strip()
    if assumptions not in ASSUMPTION_SYMBOL_MODES:
        errors.append(f"paper_profile.assumptions_symbols_mode 无效：{assumptions}")
    heading = str(profile.get("question_heading_style", "concise")).strip()
    if heading not in HEADING_STYLES:
        errors.append(f"paper_profile.question_heading_style 无效：{heading}")
    if not _nonempty_text(profile.get("structure_rationale", "")):
        errors.append("paper_profile.structure_rationale 必须说明当前赛题的真实结构依据")
    if not _nonempty_text(profile.get("model_evaluation_rationale", "")):
        errors.append("paper_profile.model_evaluation_rationale 必须说明是否设置独立模型评价章")
    for field in ("shared_data_section", "model_evaluation_section"):
        if field in profile and not isinstance(profile.get(field), bool):
            errors.append(f"paper_profile.{field} 必须为布尔值")
    shared_data = profile.get("shared_data_section", structure == "shared_data") is True
    if structure == "shared_data" and not shared_data:
        errors.append("shared_data Profile 必须启用 shared_data_section")
    if structure == "problem_local" and shared_data:
        errors.append("problem_local Profile 不得启用 shared_data_section")

    questions = spec.get("questions", [])
    if not isinstance(questions, list) or not questions:
        errors.append("questions 至少包含一个问题")
        return errors
    question_numbers: set[int] = set()
    method_ids: set[str] = set()
    for q_index, question in enumerate(questions, start=1):
        prefix = f"questions[{q_index}]"
        if not isinstance(question, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        number = question.get("number")
        if not isinstance(number, int) or number < 1:
            errors.append(f"{prefix}.number 必须为正整数")
        elif number in question_numbers:
            errors.append(f"{prefix}.number 重复：{number}")
        else:
            question_numbers.add(number)
        if not _nonempty_text(question.get("title", "")):
            errors.append(f"{prefix}.title 不得为空")
        analysis_mode = str(question.get("analysis_mode", profile.get("analysis_default", "top_level"))).strip()
        if analysis_mode not in ANALYSIS_MODES:
            errors.append(f"{prefix}.analysis_mode 无效：{analysis_mode}")
        subquestions = question.get("subquestions", [])
        if not isinstance(subquestions, list) or not subquestions:
            errors.append(f"{prefix}.subquestions 至少包含一个求解单元")
            continue
        labels: set[str] = set()
        for s_index, subquestion in enumerate(subquestions, start=1):
            sub_prefix = f"{prefix}.subquestions[{s_index}]"
            if not isinstance(subquestion, dict):
                errors.append(f"{sub_prefix} 必须是对象")
                continue
            label = str(subquestion.get("label", "")).strip()
            if not label:
                errors.append(f"{sub_prefix}.label 不得为空")
            elif label in labels:
                errors.append(f"{sub_prefix}.label 重复：{label}")
            else:
                labels.add(label)
            if not isinstance(subquestion.get("explicit"), bool):
                errors.append(f"{sub_prefix}.explicit 必须为布尔值")
            if not _nonempty_text(subquestion.get("title", "")):
                errors.append(f"{sub_prefix}.title 不得为空")
            _validate_task_profile(
                subquestion.get("task_profile"), sub_prefix, errors, int(schema_version)
            )
            _validate_literature(subquestion.get("literature_review"), sub_prefix, errors)
            _validate_methods(subquestion.get("methods"), sub_prefix, errors, method_ids)
            if int(schema_version) >= 2:
                _validate_argument_plan(subquestion.get("argument_plan"), sub_prefix, errors)

    style = spec.get("style_transfer", {"enabled": False})
    if not isinstance(style, dict) or not isinstance(style.get("enabled", False), bool):
        errors.append("style_transfer.enabled 必须为布尔值")
    elif style.get("enabled") is True:
        if int(schema_version) >= 2:
            _validate_style_transfer_v2(style, errors)
            return errors
        sources = style.get("sources", [])
        card = style.get("card", {})
        if not isinstance(sources, list) or not any(_nonempty_text(item) for item in sources):
            errors.append("启用风格迁移时 style_transfer.sources 不得为空")
        if not isinstance(card, dict):
            errors.append("启用风格迁移时 style_transfer.card 必须是对象")
        else:
            for field in ("common_features", "variants", "current_choices"):
                values = card.get(field, [])
                if not isinstance(values, list) or not any(_nonempty_text(item) for item in values):
                    errors.append(f"启用风格迁移时 style_transfer.card.{field} 不得为空")
    return errors


def load_problem_spec(path: Path) -> dict[str, object]:
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"problem-spec 无法读取：{exc}") from exc
    errors = validate_problem_spec(spec)
    if errors:
        raise ValueError("problem-spec 校验失败：\n- " + "\n- ".join(errors))
    return spec

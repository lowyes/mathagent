#!/usr/bin/env python3
"""Validate per-subquestion code, figure, result, and manifest ownership."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


CODE_EXTENSIONS = {".py", ".ipynb", ".m", ".jl", ".r", ".sql", ".c", ".cc", ".cpp"}
FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps"}
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
STAGE_GATE_KEYS = ("problem_analysis", "modeling", "computation", "paper")


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def listed_paths(entries: object) -> set[str]:
    if not isinstance(entries, list):
        return set()
    return {str(item).replace("\\", "/") for item in entries if isinstance(item, str)}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


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

            status = manifest.get("status", "pending")
            if status not in {"pending", "in_progress", "complete", "blocked"}:
                errors.append(f"状态无效 {relative(manifest_path, root)}：{status}")
            if final and status != "complete":
                errors.append(f"最终交付仍有未完成小问：{relative(sq_dir, root)}（{status}）")

            actual_code = sorted(
                p
                for p in (sq_dir / "代码").rglob("*")
                if p.is_file()
                and p.suffix.lower() in CODE_EXTENSIONS
                and "__pycache__" not in p.parts
            )
            actual_figures = sorted(p for p in (sq_dir / "图").rglob("*") if p.is_file())
            actual_results = sorted(p for p in (sq_dir / "结果").rglob("*") if p.is_file())
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
                    errors.append(f"已完成小问尚未通过验证：{relative(sq_dir, root)}")
                if not str(manifest.get("direct_answer", "")).strip():
                    errors.append(f"已完成小问缺少直接回答：{relative(sq_dir, root)}")

                accepted_algorithms: set[str] = set()
                algorithms = manifest.get("algorithms", [])
                if not isinstance(algorithms, list) or not algorithms:
                    errors.append(f"已完成小问缺少算法公式与参数血缘：{relative(sq_dir, root)}")
                else:
                    for algorithm_index, algorithm in enumerate(algorithms, start=1):
                        prefix = f"{relative(sq_dir, root)} 的第{algorithm_index}个算法"
                        if not isinstance(algorithm, dict):
                            errors.append(f"{prefix}不是对象")
                            continue
                        for field in ("name", "purpose", "formula_reference"):
                            if not str(algorithm.get(field, "")).strip():
                                errors.append(f"{prefix}缺少 {field}")
                        algorithm_name = str(algorithm.get("name", "")).strip()
                        if algorithm_name:
                            accepted_algorithms.add(algorithm_name)
                        parameters = algorithm.get("parameters", [])
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

                literature_candidates = manifest.get("literature_candidates", [])
                if not isinstance(literature_candidates, list) or not literature_candidates:
                    errors.append(f"已完成小问缺少真实文献算法筛选：{relative(sq_dir, root)}")
                else:
                    has_direct_candidate = False
                    for literature_index, candidate in enumerate(literature_candidates, start=1):
                        prefix = f"{relative(sq_dir, root)} 的第{literature_index}条文献候选"
                        if not isinstance(candidate, dict):
                            errors.append(f"{prefix}不是对象")
                            continue
                        for field in (
                            "id", "title", "venue", "doi_or_url", "verification_url",
                            "problem_match", "algorithm", "formula_or_method", "required_data",
                            "available_fields", "transfer_decision",
                        ):
                            if not str(candidate.get(field, "")).strip():
                                errors.append(f"{prefix}缺少 {field}")
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
                        used_by = candidate.get("used_by_algorithms", [])
                        if not isinstance(used_by, list):
                            errors.append(f"{prefix}的 used_by_algorithms 必须是数组")
                            used_by = []
                        linked_algorithms = {str(name).strip() for name in used_by if str(name).strip()}
                        if literature_status in {"adopted", "benchmarked"} and not linked_algorithms:
                            errors.append(f"{prefix}采用或测试后却未关联项目算法")
                        unknown_algorithms = linked_algorithms - accepted_algorithms
                        if unknown_algorithms:
                            errors.append(
                                f"{prefix}关联了不存在的项目算法：" + "、".join(sorted(unknown_algorithms))
                            )
                    if not has_direct_candidate:
                        warnings.append(f"文献筛选尚无直接场景研究：{relative(sq_dir, root)}")

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
                experiments = manifest.get("experiments", [])
                if not isinstance(experiments, list) or not experiments:
                    errors.append(f"已完成小问缺少实验记录：{relative(sq_dir, root)}")
                else:
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
                        names = experiment.get("algorithm_names", [])
                        if not isinstance(names, list) or not any(str(name).strip() for name in names):
                            errors.append(f"{prefix}缺少 algorithm_names")
                            names = []
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
                if uncovered_algorithms:
                    errors.append(
                        f"最终算法缺少通过的实验记录 {relative(sq_dir, root)}："
                        + "、".join(sorted(uncovered_algorithms))
                    )

                comparison = manifest.get("model_comparison", {})
                if not isinstance(comparison, dict):
                    errors.append(f"已完成小问缺少多模型比较声明：{relative(sq_dir, root)}")
                else:
                    applicability = str(comparison.get("applicability", "")).strip()
                    reason = str(comparison.get("reason", "")).strip()
                    if applicability not in MODEL_COMPARISON_APPLICABILITY:
                        errors.append(f"模型比较 applicability 无效 {relative(sq_dir, root)}：{applicability}")
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
                        if not isinstance(candidates, list) or len(candidates) < 4:
                            errors.append(f"预测/分类小问至少需要三个非融合候选和一个融合模型：{relative(sq_dir, root)}")
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
                                errors.append(f"{prefix}的 role 无效：{role}")
                            if name in candidate_names:
                                errors.append(f"{prefix}的模型名重复：{name}")
                            if name:
                                candidate_names.add(name)
                                if name not in accepted_algorithms:
                                    errors.append(f"{prefix}未登记算法公式与参数血缘：{name}")
                            if role == "ensemble":
                                ensemble_names.add(name)
                            elif role in {"baseline", "standalone"}:
                                non_ensemble_names.add(name)
                            if role == "baseline":
                                has_baseline = True
                            if exp_id and exp_id not in experiment_ids:
                                errors.append(f"{prefix}关联的实验不存在：{exp_id}")
                        if len(non_ensemble_names) < 3 or not has_baseline or not ensemble_names:
                            errors.append(f"模型比较缺少三个非融合候选、基线或融合模型：{relative(sq_dir, root)}")
                        ensemble = comparison.get("ensemble", {})
                        if not isinstance(ensemble, dict):
                            errors.append(f"模型比较 ensemble 不是对象：{relative(sq_dir, root)}")
                        else:
                            for field in ("method", "weight_source", "leakage_control", "formula_reference"):
                                if not str(ensemble.get(field, "")).strip():
                                    errors.append(f"模型融合缺少 {field}：{relative(sq_dir, root)}")
                            members = ensemble.get("members", [])
                            if not isinstance(members, list) or len({str(x).strip() for x in members if str(x).strip()}) < 2:
                                errors.append(f"模型融合至少需要两个成员：{relative(sq_dir, root)}")
                            else:
                                unknown_members = {str(x).strip() for x in members if str(x).strip()} - non_ensemble_names
                                if unknown_members:
                                    errors.append(f"模型融合成员不在非融合候选中：" + "、".join(sorted(unknown_members)))

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

    if final:
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
        abstract_evidence = paper_workflow.get("abstract_evidence", [])
        if not isinstance(abstract_evidence, list):
            errors.append("paper_workflow.abstract_evidence 必须是数组")
            abstract_evidence = []
        evidence_by_question: dict[int, dict[str, object]] = {}
        for entry in abstract_evidence:
            if isinstance(entry, dict) and isinstance(entry.get("question"), int):
                evidence_by_question[int(entry["question"])] = entry
        for question in questions:
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
        abstract_files = sorted((root / "论文").rglob("*摘要*.tex")) if (root / "论文").is_dir() else []
        if not abstract_files:
            errors.append("最终交付缺少可校验的摘要 TeX 文件")
        else:
            abstract_text = "\n".join(path.read_text(encoding="utf-8") for path in abstract_files)
            if "% ABSTRACT_STATUS: final" not in abstract_text:
                errors.append("摘要文件仍是 placeholder，或缺少 % ABSTRACT_STATUS: final 标记")
            positions: list[int] = []
            for question in questions:
                if not isinstance(question, dict):
                    continue
                question_no = int(question.get("question", 0))
                label = f"问题{chinese_number(question_no)}"
                pattern = rf"\\textbf\{{针对{re.escape(label)}[：:]\}}"
                match = re.search(pattern, abstract_text)
                if not match:
                    errors.append(f"摘要缺少独立粗体段落标签：针对{label}：")
                else:
                    positions.append(match.start())
            if positions != sorted(positions):
                errors.append("摘要中的问题段落未按题面顺序排列")

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

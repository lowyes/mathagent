from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compile_paper  # noqa: E402
import audit_paper_prose  # noqa: E402
import init_project  # noqa: E402
import paper_sources  # noqa: E402
import problem_spec  # noqa: E402
import validate_project  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def minimal_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Root 1 0 R >>\nendobj\n"
        b"xref\n0 2\n0000000000 65535 f \ntrailer\n<< /Root 1 0 R >>\n"
        b"startxref\n64\n%%EOF\n"
    )


def minimal_png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )


def parameter(symbol: str) -> dict[str, str]:
    return {
        "symbol": symbol,
        "value_or_rule": "由训练期滚动验证确定",
        "unit": "无量纲",
        "source_type": "calibration",
        "source": "训练期内层验证 RMSE 最小",
        "downstream_use": "最终模型训练",
    }


def award_paper_problem_spec() -> dict[str, object]:
    """Nine-unit blueprint reconstructed from the inspected award paper."""
    task_rows = {
        1: [
            ("a", "孕周分组与达标判定", "deterministic_rule", []),
            ("b", "达标时间预测", "prediction", []),
        ],
        2: [
            ("a", "测量误差分布拟合", "fitting", ["prediction"]),
            ("b", "孕妇分群与分层拟合", "clustering", ["fitting"]),
            ("c", "异常风险关联判定", "association_decision", []),
            ("d", "检测方案关联分析", "association_decision", ["evaluation"]),
        ],
        3: [
            ("a", "连续指标预测", "prediction", []),
            ("b", "异常样本预测", "prediction", []),
            ("c", "临床因素关联与建议", "association_decision", ["evaluation"]),
        ],
    }
    titles = {1: "孕周达标规律分析", 2: "检测误差与异常风险分析", 3: "检测结果预测与决策"}
    questions = []
    for number, rows in task_rows.items():
        subquestions = []
        for label, title, primary, secondary in rows:
            subquestions.append({
                "label": label,
                "explicit": True,
                "title": title,
                "task_profile": {
                    "primary": primary,
                    "secondary": secondary,
                    "outputs": [f"{title}的可核验结果"],
                },
                "literature_review": {
                    "applicability": "required" if primary in {"prediction", "fitting", "clustering"} else "conditional",
                    "reason": "预测或统计建模需核验方法依据" if primary in {"prediction", "fitting", "clustering"} else "题面规则优先，必要时补充标准依据",
                },
                "methods": [],
            })
        questions.append({
            "number": number,
            "title": titles[number],
            "analysis_mode": "top_level",
            "subquestions": subquestions,
        })
    return {
        "schema_version": 1,
        "competition": "研究生数学建模结构试验",
        "paper_profile": {
            "structure_profile": "shared_data",
            "shared_data_section": True,
            "assumptions_symbols_mode": "combined",
            "model_evaluation_section": True,
            "model_evaluation_rationale": "三问评价口径不同，末章集中总结适用边界与推广性",
            "question_heading_style": "concise",
            "structure_rationale": "九个求解单元共享同一数据清洗口径，故设置公共数据章",
        },
        "questions": questions,
        "style_transfer": {
            "enabled": True,
            "sources": ["一等奖论文：重点E23100650012"],
            "card": {
                "common_features": ["问题分析先交代任务困难，再引入方法"],
                "variants": ["显式小问按题面编号组织"],
                "current_choices": ["结论与证据表相邻呈现"],
            },
        },
    }


def schema_v2_style_transfer_spec() -> dict[str, object]:
    spec = json.loads(
        (SKILL_ROOT / "assets" / "problem-spec.example.json").read_text(encoding="utf-8")
    )
    spec["style_transfer"] = {
        "enabled": True,
        "sources": [
            {
                "id": "A",
                "title": "一等奖论文甲",
                "locator": "摘要第1页、目录第3页",
                "path_or_citation": "D:/references/award-a.pdf",
            },
            {
                "id": "B",
                "title": "一等奖论文乙",
                "locator": "摘要第1至2页、问题一第8至12页",
                "path_or_citation": "D:/references/award-b.pdf",
            },
        ],
        "card": {
            "common_features": [
                {
                    "statement": "摘要按问题顺序给出方法、数字与结论",
                    "supported_by": ["A", "B"],
                }
            ],
            "variants": [
                {
                    "statement": "模型评价章是否独立取决于正文是否已就地收束",
                    "supported_by": ["A"],
                }
            ],
            "current_choices": [
                {
                    "statement": "各问结果与验证相邻呈现",
                    "reason": "当前问题的小问依赖较强，分离会削弱证据承接",
                }
            ],
        },
    }
    return spec


def build_complete_project(root: Path, **initialize_kwargs: object) -> None:
    init_project.initialize(
        root,
        [(1, 1)],
        "回归测试",
        question_titles={1: "样本外预测"},
        **initialize_kwargs,
    )
    sq = root / "求解" / "问题一" / "小问1"
    code = sq / "代码" / "main.py"
    flow_source = sq / "代码" / "flow.py"
    flow = sq / "图" / "flow.pdf"
    result = sq / "结果" / "metrics.csv"
    compare = sq / "结果" / "comparison.csv"
    code.write_text("print('ok')\n", encoding="utf-8")
    flow_source.write_text("print('flow')\n", encoding="utf-8")
    flow.write_bytes(minimal_pdf_bytes())
    result.write_text("split,rmse\nholdout,0.18\n", encoding="utf-8")
    compare.write_text("model,rmse\nPersistence,0.31\nRidge,0.18\n", encoding="utf-8")

    rel_result = "求解/问题一/小问1/结果/metrics.csv"
    rel_compare = "求解/问题一/小问1/结果/comparison.csv"
    manifest = {
        "question": 1,
        "subquestion": 1,
        "target_output": "预测值",
        "units": "NTU",
        "inputs": ["数据/监测.csv"],
        "dependencies": [],
        "contract": {
            "objective": "给出严格样本外预测",
            "non_goals": ["不进行因果推断"],
            "acceptance_criteria": ["RMSE 低于可靠基线"],
            "dependencies": [],
        },
        "literature_candidates": [{
            "id": "L01",
            "title": "Rolling validation for forecasting",
            "year": 2024,
            "venue": "Journal of Forecasting Tests",
            "doi_or_url": "https://example.org/paper",
            "verification_url": "https://example.org/paper",
            "problem_match": "同类时间序列预测",
            "directness": "direct",
            "algorithm": "Ridge",
            "formula_or_method": "滚动验证与正则估计",
            "required_data": "等间隔序列",
            "available_fields": "本题具备等间隔序列",
            "transfer_decision": "采用其验证协议",
            "status": "adopted",
            "used_by_algorithms": ["Ridge"],
        }],
        "model_comparison": {
            "applicability": "required",
            "reason": "预测任务需要与可靠基线进行样本外比较",
            "primary_metric": "RMSE",
            "candidates": [
                {"name": "Persistence", "family": "naive", "role": "baseline", "experiment_id": "E1"},
                {"name": "Ridge", "family": "linear", "role": "standalone", "experiment_id": "E1"},
            ],
            "ensemble": {},
            "ensemble_reason": "候选残差高度相关，缺少稳定互补性，故不测试融合",
            "result_file": rel_compare,
            "decision": "Ridge 的样本外 RMSE 最低",
        },
        "algorithms": [
            {
                "name": "Persistence",
                "purpose": "可靠基线",
                "formula_reference": "式(1)",
                "is_core": False,
                "core_reason": "仅作为最低能力基线",
                "parameters": [parameter("h")],
            },
            {
                "name": "Ridge",
                "purpose": "给出最终预测",
                "formula_reference": "式(2)",
                "is_core": True,
                "core_reason": "承担最终预测与主要结论",
                "pseudocode_anchor": "alg:q1-core",
                "pseudocode_reference": "算法1",
                "flowchart_source": "求解/问题一/小问1/代码/flow.py",
                "flowchart_file": "求解/问题一/小问1/图/flow.pdf",
                "flowchart_reference": "图2",
                "parameters": [parameter("lambda")],
            },
        ],
        "experiments": [{
            "id": "E1",
            "name": "滚动验证",
            "purpose": "比较样本外误差",
            "command_or_entry": "python 求解/问题一/小问1/代码/main.py",
            "config": "seed=42",
            "verdict": "Ridge 优于基线",
            "status": "passed",
            "algorithm_names": ["Persistence", "Ridge"],
            "result_files": [rel_compare],
        }],
        "revision_workflow": {
            "schema_version": 1,
            "status": "passed",
            "no_revision_reason": "样本外指标满足验收标准，无需回滚重建",
            "cycles": [],
        },
        "validation_methods": [{
            "id": "V1",
            "name": "时间留出验证",
            "type": "out_of_sample",
            "target": "最终模型",
            "purpose": "检验未来泛化",
            "applicability_reason": "时间序列不能随机打乱",
            "procedure_reference": "正文4.3节",
            "data_protocol": "训练期在前、验证期在后",
            "experiment_id": "E1",
            "evidence_file": rel_result,
            "evidence_locator": "holdout 行 rmse 列",
            "result_summary": "RMSE=0.18",
            "interpretation": "低于基线0.31",
            "decision_impact": "采用Ridge",
            "paper_location": "正文表1",
            "paper_anchor": "tab:q1-validation",
            "criteria": [{
                "name": "RMSE",
                "definition_reference": "式(3)",
                "acceptance_rule": "低于Persistence",
            }],
        }],
        "findings": [{
            "type": "decision",
            "statement": "Ridge优于基线",
            "evidence": rel_compare,
            "implication": "采用Ridge作为最终模型",
        }],
        "claims": [{
            "id": "C1",
            "statement": "验证RMSE为0.18",
            "status": "verified",
            "paper_location": "正文表1",
            "evidence": [{"file": rel_result, "locator": "holdout行", "relation": "直接支撑"}],
        }],
        "stage_gates": {
            name: {"status": "passed", "checks": ["已核验"]}
            for name in ("problem_analysis", "modeling", "computation", "paper")
        },
        "code_files": [
            "求解/问题一/小问1/代码/main.py",
            "求解/问题一/小问1/代码/flow.py",
        ],
        "figure_files": ["求解/问题一/小问1/图/flow.pdf"],
        "result_files": [rel_result, rel_compare],
        "headline_metrics": {"rmse": 0.18},
        "random_seeds": [42],
        "solver_or_training_status": "训练收敛",
        "status": "complete",
        "validation": {"status": "passed", "checks": ["时间留出验证通过"]},
        "direct_answer": "最终模型验证RMSE为0.18，优于基线。",
    }
    write_json(sq / "小问清单.json", manifest)

    paper = root / "论文"
    main_path = paper / "main.tex"
    main_path.write_text(
        main_path.read_text(encoding="utf-8").replace(
            "论文标题：用一句话概括对象、方法与目标",
            "面向样本外预测的正则化建模",
        ),
        encoding="utf-8",
    )
    (paper / "sections" / "abstract.tex").write_text(
        "% ABSTRACT_STATUS: final\n"
        "\\begin{abstract}\n"
        "\\textbf{针对问题一：}本文比较可靠基线与岭回归，验证RMSE为0.18。\n"
        "\\end{abstract}\n",
        encoding="utf-8",
    )
    analysis_modes = initialize_kwargs.get("question_analysis_modes", {})
    analysis_mode = analysis_modes.get(1, "top_level") if isinstance(analysis_modes, dict) else "top_level"
    sub_analysis = (
        "\\subsubsection{问题分析}\n本小问单独分析预测任务与数据困难。\n"
        if analysis_mode in {"per_subquestion", "hybrid"}
        else ""
    )
    (paper / "sections" / "question-1-sub-1.tex").write_text(
        "\\subsection{小问 a}\n"
        + sub_analysis
        + "\\begin{algorithm}[H]\n"
        "\\caption{岭回归求解}\\label{alg:q1-core}\n"
        "\\KwIn{训练序列}\\KwOut{样本外预测}\n"
        "滚动训练并返回最优模型\\;\n"
        "\\end{algorithm}\n"
        "\\begin{table}[H]\\caption{验证结果}\\label{tab:q1-validation}\n"
        "\\begin{tabular}{ll}模型&RMSE\\\\ Ridge&0.18\\end{tabular}\\end{table}\n",
        encoding="utf-8",
    )

    project = json.loads((root / "项目清单.json").read_text(encoding="utf-8"))
    project["official_rules_checked"] = True
    project["paper_workflow"].update({
        "results_locked": True,
        "abstract_status": "final",
        "abstract_evidence_check": "passed",
        "abstract_plan": [{
            "question": 1,
            "task": "比较候选方法并形成样本外预测",
            "inherits_from": [],
            "retained": [],
            "modifications": [],
            "new_difficulty": "",
            "core_method": "时间滚动验证下的岭回归",
            "model_highlight": {
                "status": "not_applicable",
                "reason": "本问采用常规模型比较，不将算法名称包装为创新",
            },
            "key_result": "验证RMSE为0.18，低于基线0.31",
            "direct_answer": "采用Ridge作为最终预测模型",
            "validation_or_boundary": "结论限于当前时间留出协议",
        }],
        "abstract_evidence": [{
            "question": 1,
            "checked": True,
            "files": [rel_result],
            "locator": "holdout行rmse列",
        }],
        "model_review": {
            "status": "passed",
            "strengths": [{
                "id": "S1",
                "statement": "时间留出RMSE低于持续性基线",
                "evidence_file": rel_compare,
                "locator": "Persistence与Ridge两行的rmse列",
            }],
            "strengths_not_applicable_reason": "",
            "limitations": [{
                "id": "L1",
                "statement": "结论仅覆盖当前时间留出窗口",
                "evidence_file": rel_result,
                "locator": "holdout行",
                "impact": "不能直接外推到结构突变时期",
            }],
            "improvements": [{
                "id": "I1",
                "limitation_ids": ["L1"],
                "proposal": "增加跨工况和结构突变窗口验证",
                "status": "future",
                "requirements": "需要新增跨工况观测数据",
            }],
            "extension_applicability": "not_applicable",
            "extension_reason": "当前回归夹具不声明跨场景推广",
            "extensions": [],
        },
        "citation_review": {
            "status": "passed",
            "applicability": "not_required",
            "reason": "夹具仅使用题面设定与自产生结果，不含外部主张",
        },
        "citation_ledger": [],
    })
    write_json(root / "项目清单.json", project)


def add_valid_compile_proof(root: Path) -> None:
    paper = root / "论文"
    pdf = paper / "main.pdf"
    # The structural smoke test is deliberately dependency-free. This fixture is
    # not evidence of a real typesetting run; it only exercises report integrity.
    pdf.write_bytes(minimal_pdf_bytes())
    active, errors = paper_sources.collect_active_tex(paper / "main.tex")
    if errors:
        raise AssertionError(errors)
    inputs = []
    for path in active + [paper / "graduate-modeling.cls"]:
        inputs.append({"path": path.relative_to(root).as_posix(), "sha256": file_hash(path)})
    report = {
        "schema_version": 1,
        "ok": True,
        "compiled_at": "2026-09-09T00:00:00+00:00",
        "engine": "xelatex",
        "engine_path": "xelatex",
        "source": "main.tex",
        "pdf": "main.pdf",
        "passes": [
            {"pass": 1, "returncode": 0, "status": "completed"},
            {"pass": 2, "returncode": 0, "status": "completed"},
        ],
        "warnings": [],
        "input_manifest_source": "xelatex-recorder",
        "inputs": inputs,
        "pdf_sha256": file_hash(pdf),
        "pdf_size": pdf.stat().st_size,
        "pdf_structure_ok": True,
        "visual_review_required": True,
    }
    write_json(paper / "编译报告.json", report)
    project = json.loads((root / "项目清单.json").read_text(encoding="utf-8"))
    project["paper_workflow"]["pdf_visual_review"] = {
        "status": "passed",
        "pdf_sha256": file_hash(pdf),
        "checks": ["逐页检查标题、公式、图表、页码与溢出"],
    }
    write_json(root / "项目清单.json", project)


class SkillRegressionTests(unittest.TestCase):
    def test_schema_v2_style_transfer_requires_independent_support(self) -> None:
        spec = schema_v2_style_transfer_spec()
        spec["style_transfer"]["card"]["common_features"][0]["supported_by"] = ["A"]
        errors = problem_spec.validate_problem_spec(spec)
        self.assertTrue(any("至少需要 2 个独立来源" in error for error in errors), errors)

    def test_schema_v2_style_transfer_has_postwriting_review_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            spec_path = Path(tmp) / "problem-spec.json"
            write_json(spec_path, schema_v2_style_transfer_spec())
            init_project.initialize_from_spec(root, spec_path, "fallback")

            project = json.loads((root / "项目清单.json").read_text(encoding="utf-8"))
            style = project["style_transfer"]
            self.assertEqual(style["schema_version"], 2)
            self.assertEqual(style["status"], "card_ready")
            self.assertTrue((root / style["review_file"]).is_file())
            initial_report = validate_project.validate(root)
            self.assertTrue(initial_report["ok"], initial_report["errors"])

            review_path = root / style["review_file"]
            review_path.write_text(
                review_path.read_text(encoding="utf-8").replace(
                    "REVIEW_STATUS: pending", "REVIEW_STATUS: checked"
                ),
                encoding="utf-8",
            )
            style["status"] = "checked"
            style["checks"] = [
                {
                    "dimension": dimension,
                    "paper_location": "正文对应章节或最终PDF页码",
                    "finding": "已逐项核对证据节奏与当前题面需求",
                    "action": "保留当前结构并记录差异边界",
                }
                for dimension in sorted(validate_project.STYLE_REVIEW_DIMENSIONS)
            ]
            write_json(root / "项目清单.json", project)
            checked_report = validate_project.validate(root)
            self.assertTrue(checked_report["ok"], checked_report["errors"])

            for check in style["checks"]:
                if check["dimension"] == "段落、图表与跨小问递进及解释边界":
                    check["dimension"] = "跨小问承接与解释边界"
            write_json(root / "项目清单.json", project)
            legacy_dimension_report = validate_project.validate(root)
            self.assertTrue(legacy_dimension_report["ok"], legacy_dimension_report["errors"])

    def test_final_rejects_unfinished_style_review_and_accepts_completed_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            add_valid_compile_proof(root)
            project_path = root / "项目清单.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            sources = schema_v2_style_transfer_spec()["style_transfer"]["sources"]
            review_file = root / "论文" / "style-review.md"
            review_file.write_text("# 优秀范文写后对照复核\n\n> REVIEW_STATUS: pending\n", encoding="utf-8")
            (root / "论文" / "style-card.md").write_text(
                "# Style Card\n\n参考边界：只迁移结构与证据节奏。\n", encoding="utf-8"
            )
            project["style_transfer"] = {
                "schema_version": 2,
                "enabled": True,
                "sources": sources,
                "style_card": "论文/style-card.md",
                "review_file": "论文/style-review.md",
                "checks": [],
                "status": "card_ready",
            }
            write_json(project_path, project)
            unfinished = validate_project.validate(root, final=True)
            self.assertTrue(
                any("必须完成范文写后对照复核" in error for error in unfinished["errors"]),
                unfinished["errors"],
            )

            review_file.write_text(
                "# 优秀范文写后对照复核\n\n> REVIEW_STATUS: checked\n", encoding="utf-8"
            )
            project["style_transfer"]["status"] = "checked"
            project["style_transfer"]["checks"] = [
                {
                    "dimension": dimension,
                    "paper_location": "正文与最终PDF",
                    "finding": "已定位范文和本文的对应证据",
                    "action": "保留有效差异并修正证据断层",
                }
                for dimension in sorted(validate_project.STYLE_REVIEW_DIMENSIONS)
            ]
            write_json(project_path, project)
            completed = validate_project.validate(root, final=True)
            self.assertTrue(completed["ok"], completed["errors"])

    def test_schema_v2_blueprint_populates_argument_and_output_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            spec_path = SKILL_ROOT / "assets" / "problem-spec.example.json"
            spec = problem_spec.load_problem_spec(spec_path)
            self.assertEqual(spec["schema_version"], 2)
            init_project.initialize_from_spec(root, spec_path, "fallback")
            manifest = json.loads(
                (root / "求解" / "问题一" / "小问1" / "小问清单.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["schema_version"], 3)
            self.assertIn("逐对象状态标签", manifest["target_output"])
            self.assertIn("类别", manifest["units"])
            self.assertTrue(manifest["contract"]["acceptance_criteria"])
            self.assertIn("decision_question", manifest["argument_plan"])
            plan_text = (root / "求解计划.md").read_text(encoding="utf-8")
            self.assertIn("任务类型：确定性规则判定", plan_text)
            self.assertIn("最终要回答：", plan_text)
            self.assertIn("解释边界：", plan_text)
            report = validate_project.validate(root)
            self.assertTrue(report["ok"], report["errors"])

    def test_schema_v2_rejects_unjustified_task_type_and_vague_output(self) -> None:
        spec = json.loads(
            (SKILL_ROOT / "assets" / "problem-spec.example.json").read_text(encoding="utf-8")
        )
        unit = spec["questions"][0]["subquestions"][0]
        unit["task_profile"].pop("primary_reason")
        unit["task_profile"]["outputs"][0]["acceptance"] = ""
        unit["argument_plan"]["interpretation_boundary"] = ""
        errors = problem_spec.validate_problem_spec(spec)
        self.assertTrue(any("primary_reason" in error for error in errors), errors)
        self.assertTrue(any("acceptance" in error for error in errors), errors)
        self.assertTrue(any("interpretation_boundary" in error for error in errors), errors)

    def test_problem_spec_initializes_nine_semantic_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec_path = base / "award-problem-spec.json"
            root = base / "project"
            write_json(spec_path, award_paper_problem_spec())
            init_project.initialize_from_spec(root, spec_path, "fallback")

            project = json.loads((root / "项目清单.json").read_text(encoding="utf-8"))
            self.assertEqual(project["paper_profile"]["schema_version"], 3)
            self.assertEqual(sum(q["subquestion_count"] for q in project["questions"]), 9)
            self.assertTrue((root / "problem-spec.json").is_file())
            self.assertTrue((root / "论文" / "style-card.md").is_file())
            q2b = (root / "论文" / "sections" / "question-2-sub-2.tex").read_text(encoding="utf-8")
            self.assertIn("\\subsection{问题 b：孕妇分群与分层拟合}", q2b)
            report = validate_project.validate(root)
            self.assertTrue(report["ok"], report["errors"])

    def test_adaptive_deterministic_rule_does_not_force_experiment_or_literature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            sq_manifest_path = root / "求解" / "问题一" / "小问1" / "小问清单.json"
            manifest = json.loads(sq_manifest_path.read_text(encoding="utf-8"))
            manifest.update({
                "schema_version": 2,
                "task_profile": {
                    "primary": "deterministic_rule",
                    "secondary": [],
                    "outputs": ["按题面阈值给出的确定性判定"],
                },
                "literature_review": {
                    "applicability": "not_required",
                    "reason": "阈值由题面完整给定，不需要外部方法迁移",
                },
                "literature_candidates": [],
                "methods": [{
                    "id": "M1",
                    "name": "题面阈值判定",
                    "purpose": "按给定规则形成类别结果",
                    "method_type": "deterministic_rule",
                    "definition_reference": "正文4.2节判定定义",
                    "representations": ["definition", "result_table"],
                    "is_core": True,
                    "core_reason": "直接产生本问结论",
                    "parameter_applicability": "not_required",
                    "parameter_reason": "阈值来自题面常量，不存在待估参数",
                    "parameters": [],
                }],
                "algorithms": [],
                "experiments": [],
                "model_comparison": {
                    "applicability": "not_applicable",
                    "reason": "确定性规则不存在候选预测模型选择",
                    "primary_metric": "",
                    "candidates": [],
                    "ensemble": {},
                    "ensemble_reason": "",
                    "result_file": "",
                    "decision": "",
                },
            })
            manifest["validation_methods"][0]["experiment_id"] = ""
            write_json(sq_manifest_path, manifest)
            report = validate_project.validate(root)
            self.assertTrue(report["ok"], report["errors"])

    def test_adaptive_prediction_must_compare_against_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            sq_manifest_path = root / "求解" / "问题一" / "小问1" / "小问清单.json"
            manifest = json.loads(sq_manifest_path.read_text(encoding="utf-8"))
            manifest["schema_version"] = 2
            manifest["task_profile"] = {
                "primary": "prediction",
                "secondary": [],
                "outputs": ["样本外预测"],
            }
            manifest["literature_review"] = {
                "applicability": "required",
                "reason": "预测任务需要核验模型与验证协议",
            }
            manifest["methods"] = []
            for index, algorithm in enumerate(manifest["algorithms"], start=1):
                method = dict(algorithm)
                method.update({
                    "id": f"M{index}",
                    "method_type": "predictive_model",
                    "representations": ["formula"] + (
                        ["pseudocode", "flowchart"] if algorithm["is_core"] else []
                    ),
                    "parameter_applicability": "required",
                })
                manifest["methods"].append(method)
            manifest["model_comparison"]["applicability"] = "not_applicable"
            manifest["model_comparison"]["reason"] = "错误地跳过比较"
            write_json(sq_manifest_path, manifest)
            report = validate_project.validate(root)
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("预测/分类任务必须执行可靠基线" in error for error in report["errors"]),
                report["errors"],
            )

    def test_final_abstract_accepts_plain_problem_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            abstract = root / "论文" / "sections" / "abstract.tex"
            abstract.write_text(
                abstract.read_text(encoding="utf-8").replace("针对问题一：", "问题一："),
                encoding="utf-8",
            )
            add_valid_compile_proof(root)
            report = validate_project.validate(root, final=True)
            self.assertTrue(report["ok"], report["errors"])

    def test_final_requires_schema_v2_abstract_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            add_valid_compile_proof(root)
            project_path = root / "项目清单.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            project["paper_workflow"]["abstract_plan"] = []
            write_json(project_path, project)
            report = validate_project.validate(root, final=True)
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("缺少问题一的写作规划" in error for error in report["errors"]),
                report["errors"],
            )

    def test_qualified_abstract_highlight_requires_problem_link_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            add_valid_compile_proof(root)
            project_path = root / "项目清单.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            plan = project["paper_workflow"]["abstract_plan"][0]
            plan["model_highlight"] = {
                "status": "qualified",
                "type": "validated_model_improvement",
                "statement": "对基础模型增加正则化约束",
                "problem_link": "",
                "evidence": {"files": [], "locator": ""},
            }
            write_json(project_path, project)
            rejected = validate_project.validate(root, final=True)
            self.assertTrue(
                any("缺少题目结构对应关系" in error for error in rejected["errors"]),
                rejected["errors"],
            )
            self.assertTrue(
                any("模型亮点缺少证据文件" in error for error in rejected["errors"]),
                rejected["errors"],
            )

            plan["model_highlight"].update({
                "problem_link": "对应高维共线输入下的稳定估计要求",
                "evidence": {
                    "files": ["求解/问题一/小问1/结果/comparison.csv"],
                    "locator": "Persistence与Ridge两行的rmse列",
                },
            })
            write_json(project_path, project)
            accepted = validate_project.validate(root, final=True)
            self.assertTrue(accepted["ok"], accepted["errors"])

    def test_abstract_plan_enforces_incremental_inheritance(self) -> None:
        base_entry = {
            "question": 1,
            "task": "建立基础预测模型",
            "inherits_from": [],
            "retained": [],
            "modifications": [],
            "new_difficulty": "",
            "core_method": "基础回归模型",
            "model_highlight": {
                "status": "not_applicable",
                "reason": "本问建立基础模型，不单列亮点",
            },
            "key_result": "得到基础预测结果",
            "direct_answer": "给出问题一预测值",
            "validation_or_boundary": "",
        }
        inherited_entry = {
            "question": 2,
            "task": "在新增约束下更新预测",
            "inherits_from": [1],
            "retained": [],
            "modifications": [],
            "new_difficulty": "",
            "core_method": "约束扩展模型",
            "model_highlight": {
                "status": "not_applicable",
                "reason": "仅对基础模型作必要扩展",
            },
            "key_result": "得到约束情景结果",
            "direct_answer": "给出问题二方案",
            "validation_or_boundary": "",
        }
        workflow = {
            "schema_version": 2,
            "abstract_plan": [base_entry, inherited_entry],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rejected = validate_project.validate_abstract_plan(root, workflow, [1, 2], [1, 2])
            self.assertTrue(any("必须说明 retained" in error for error in rejected), rejected)
            self.assertTrue(any("必须说明 modifications" in error for error in rejected), rejected)
            self.assertTrue(any("必须说明 new_difficulty" in error for error in rejected), rejected)

            inherited_entry.update({
                "retained": ["沿用问题一的数据口径与基础状态"],
                "modifications": ["加入新增约束并扩展状态变量"],
                "new_difficulty": "新增状态与原决策发生耦合",
            })
            accepted = validate_project.validate_abstract_plan(root, workflow, [1, 2], [1, 2])
            self.assertEqual(accepted, [])

    def test_revision_workflow_requires_real_rerun_and_trigger_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            manifest_path = root / "求解" / "问题一" / "小问1" / "小问清单.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["revision_workflow"] = {
                "schema_version": 1,
                "status": "passed",
                "no_revision_reason": "",
                "cycles": [{
                    "id": "R1",
                    "trigger": {
                        "type": "validation",
                        "id": "V1",
                        "evidence_file": "求解/问题一/小问1/结果/metrics.csv",
                        "locator": "holdout行rmse列",
                    },
                    "diagnosis": "边界窗口误差偏高",
                    "changed_components": ["claim_boundary"],
                    "previous_experiment": "E1",
                    "revised_experiment": "E2",
                    "outcome": "限定结论后通过复核",
                    "decision": "采用限定后的结论",
                }],
            }
            write_json(manifest_path, manifest)
            rejected = validate_project.validate(root)
            self.assertTrue(
                any("revised_experiment 不存在" in error for error in rejected["errors"]),
                rejected["errors"],
            )

            revised = dict(manifest["experiments"][0])
            revised.update({"id": "E2", "name": "边界修订后复核"})
            manifest["experiments"].append(revised)
            write_json(manifest_path, manifest)
            accepted = validate_project.validate(root)
            self.assertTrue(accepted["ok"], accepted["errors"])

    def test_model_review_links_every_limitation_to_an_improvement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            add_valid_compile_proof(root)
            project_path = root / "项目清单.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            project["paper_workflow"]["model_review"]["improvements"][0]["limitation_ids"] = ["L9"]
            write_json(project_path, project)
            report = validate_project.validate(root, final=True)
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("不存在的局限" in error for error in report["errors"]),
                report["errors"],
            )
            self.assertTrue(
                any("尚未对应改进方向" in error for error in report["errors"]),
                report["errors"],
            )

    def test_citation_ledger_matches_text_and_reference_definition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            paper = root / "论文"
            question = paper / "sections" / "question-1-sub-1.tex"
            question.write_text(
                question.read_text(encoding="utf-8") + "\n相关方法定义参见文献\\cite{source1}。\n",
                encoding="utf-8",
            )
            references = paper / "sections" / "references.tex"
            references.write_text(
                references.read_text(encoding="utf-8").replace(
                    "\\end{thebibliography}",
                    "\\bibitem{source1} 作者. 题名[J]. 期刊, 2025.\n\\end{thebibliography}",
                ),
                encoding="utf-8",
            )
            project_path = root / "项目清单.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            project["paper_workflow"]["citation_review"] = {
                "status": "passed",
                "applicability": "required",
                "reason": "正文采用了一项外部方法定义",
            }
            project["paper_workflow"]["citation_ledger"] = [{
                "id": "S1",
                "claim": "外部方法定义",
                "claim_role": "supporting",
                "source_type": "primary_research",
                "authority": "peer_reviewed",
                "citation_key": "source1",
                "verification_source": "正式期刊页面",
                "used_in": ["问题一模型建立"],
                "verified": True,
            }]
            write_json(project_path, project)
            add_valid_compile_proof(root)
            accepted = validate_project.validate(root, final=True)
            self.assertTrue(accepted["ok"], accepted["errors"])

            project["paper_workflow"]["citation_ledger"] = []
            write_json(project_path, project)
            rejected = validate_project.validate(root, final=True)
            self.assertTrue(
                any("正文引用缺少 citation_ledger" in error for error in rejected["errors"]),
                rejected["errors"],
            )

    def test_initializer_uses_ascii_template_and_flexible_subquestion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            init_project.initialize(
                root,
                [(1, 1), (2, 1)],
                "回归测试",
                question_titles={1: "预测建模", 2: "优化决策"},
            )
            paper_files = [p.relative_to(root / "论文").as_posix() for p in (root / "论文").rglob("*") if p.is_file()]
            self.assertTrue(any(name.startswith("sections/question-1") for name in paper_files))
            self.assertFalse(any("章节/" in name or "#U" in name for name in paper_files))
            self.assertFalse(any(name.endswith(".zip") for name in paper_files))
            self.assertFalse((root / "论文" / "章节").exists())
            sub_text = (root / "论文" / "sections" / "question-1-sub-1.tex").read_text(encoding="utf-8")
            self.assertIn("\\subsection{小问 a}", sub_text)
            self.assertNotIn("\\subsubsection{模型建立与求解}", sub_text)
            self.assertEqual(sub_text.count("\\subsection{"), 1)
            profile = json.loads((root / "项目清单.json").read_text(encoding="utf-8"))["paper_profile"]
            workflow = json.loads((root / "项目清单.json").read_text(encoding="utf-8"))["paper_workflow"]
            self.assertEqual(workflow["schema_version"], 3)
            self.assertEqual(workflow["abstract_plan"], [])
            self.assertEqual(workflow["model_review"]["status"], "pending")
            self.assertEqual(workflow["citation_review"]["status"], "pending")
            self.assertEqual(workflow["citation_ledger"], [])
            initialized_manifest = json.loads(
                (root / "求解" / "问题一" / "小问1" / "小问清单.json").read_text(encoding="utf-8")
            )
            self.assertEqual(initialized_manifest["revision_workflow"]["status"], "pending")
            self.assertEqual(
                profile["layout"],
                "abstract-contents-restatement-assumptions-symbols-combined-questions-evaluation-references-appendix",
            )
            self.assertEqual(profile["mode"], "default")
            self.assertEqual(
                profile["source_order"],
                [
                    "sections/abstract.tex",
                    "sections/restatement.tex",
                    "sections/assumptions-symbols.tex",
                    "sections/question-1.tex",
                    "sections/question-2.tex",
                    "sections/model-evaluation.tex",
                    "sections/references.tex",
                    "sections/appendix.tex",
                ],
            )
            question_text = (root / "论文" / "sections" / "question-1.tex").read_text(encoding="utf-8")
            self.assertIn("\\section{问题一：预测建模}", question_text)
            main_text = (root / "论文" / "main.tex").read_text(encoding="utf-8")
            self.assertNotIn("\\input{sections/data-preprocessing.tex}", main_text)

            shared_root = Path(tmp) / "project-with-shared-data"
            init_project.initialize(
                shared_root,
                [(1, 1)],
                "回归测试",
                with_shared_data_section=True,
                question_titles={1: "预测建模"},
            )
            shared_main = (shared_root / "论文" / "main.tex").read_text(encoding="utf-8")
            self.assertIn("\\input{sections/data-preprocessing.tex}", shared_main)

    def test_only_active_tex_chain_is_collected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp)
            (paper / "sections").mkdir()
            (paper / "main.tex").write_text("\\input{sections/live}\n% \\input{sections/old}\n", encoding="utf-8")
            (paper / "sections" / "live.tex").write_text("live\n", encoding="utf-8")
            (paper / "sections" / "old.tex").write_text("stale duplicate label\n", encoding="utf-8")
            sources, errors = paper_sources.collect_active_tex(paper / "main.tex")
            self.assertEqual(errors, [])
            self.assertEqual([p.name for p in sources], ["main.tex", "live.tex"])

            (paper / "main.tex").write_text("\\input{../outside}\n", encoding="utf-8")
            (paper.parent / "outside.tex").write_text("outside\n", encoding="utf-8")
            _, errors = paper_sources.collect_active_tex(paper / "main.tex")
            self.assertTrue(any("escapes paper directory" in error for error in errors))

    def test_problem_local_profile_can_split_frontmatter_and_omit_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(
                root,
                structure_profile="problem_local",
                assumptions_symbols_mode="separate",
                include_model_evaluation=False,
                question_analysis_modes={1: "per_subquestion"},
            )
            profile = json.loads((root / "项目清单.json").read_text(encoding="utf-8"))["paper_profile"]
            self.assertEqual(profile["structure_profile"], "problem_local")
            self.assertEqual(profile["assumptions_symbols_mode"], "separate")
            self.assertFalse(profile["shared_data_section"])
            self.assertFalse(profile["model_evaluation_section"])
            self.assertEqual(
                profile["source_order"],
                [
                    "sections/abstract.tex",
                    "sections/restatement.tex",
                    "sections/assumptions.tex",
                    "sections/symbols.tex",
                    "sections/question-1.tex",
                    "sections/references.tex",
                    "sections/appendix.tex",
                ],
            )
            question_text = (root / "论文" / "sections" / "question-1.tex").read_text(encoding="utf-8")
            sub_text = (root / "论文" / "sections" / "question-1-sub-1.tex").read_text(encoding="utf-8")
            self.assertNotIn("\\subsection{问题分析}", question_text)
            self.assertIn("\\subsubsection{问题分析}", sub_text)
            add_valid_compile_proof(root)
            report = validate_project.validate(root, final=True)
            self.assertTrue(report["ok"], report["errors"])

    def test_shared_data_profile_and_hybrid_analysis_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(
                root,
                structure_profile="shared_data",
                question_analysis_modes={1: "hybrid"},
            )
            main_text = (root / "论文" / "main.tex").read_text(encoding="utf-8")
            self.assertIn("\\input{sections/data-preprocessing.tex}", main_text)
            add_valid_compile_proof(root)
            report = validate_project.validate(root, final=True)
            self.assertTrue(report["ok"], report["errors"])

    def test_legacy_paper_profile_remains_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            project_path = root / "项目清单.json"
            project = json.loads(project_path.read_text(encoding="utf-8"))
            profile = project["paper_profile"]
            for field in (
                "schema_version",
                "structure_profile",
                "structure_rationale",
                "assumptions_symbols_mode",
                "model_evaluation_section",
                "model_evaluation_rationale",
            ):
                profile.pop(field, None)
            project["paper_workflow"].pop("schema_version", None)
            project["paper_workflow"].pop("abstract_plan", None)
            project["paper_workflow"].pop("model_review", None)
            project["paper_workflow"].pop("citation_review", None)
            project["paper_workflow"].pop("citation_ledger", None)
            profile["layout"] = (
                "abstract-contents-restatement-assumptions-symbols-optional-data-"
                "questions-evaluation-references-appendix"
            )
            write_json(project_path, project)
            add_valid_compile_proof(root)
            report = validate_project.validate(root, final=True)
            self.assertTrue(report["ok"], report["errors"])

    def test_adaptive_structure_decisions_are_enforced(self) -> None:
        cases = {
            "shared profile without shared chapter": (
                lambda project: project["paper_profile"].update({"structure_profile": "shared_data"}),
                "shared_data Profile 必须启用公共数据章节",
            ),
            "per-subquestion mode with only top analysis": (
                lambda project: project["questions"][0].update({"analysis_mode": "per_subquestion"}),
                "逐小问分析模式不应保留重复的顶层",
            ),
            "evaluation disabled but source retained": (
                lambda project: project["paper_profile"].update({"model_evaluation_section": False}),
                "model_evaluation 应为空",
            ),
        }
        for name, (mutate, expected) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "project"
                build_complete_project(root)
                project_path = root / "项目清单.json"
                project = json.loads(project_path.read_text(encoding="utf-8"))
                mutate(project)
                write_json(project_path, project)
                add_valid_compile_proof(root)
                report = validate_project.validate(root, final=True)
                self.assertFalse(report["ok"])
                self.assertTrue(any(expected in error for error in report["errors"]), report["errors"])

    def test_prose_audit_follows_main_tex_when_file_is_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp)
            (paper / "sections").mkdir()
            main = paper / "main.tex"
            main.write_text("\\input{sections/live}\n", encoding="utf-8")
            (paper / "sections" / "live.tex").write_text("正式正文。\n", encoding="utf-8")
            (paper / "sections" / "old.tex").write_text("废弃正文。\n", encoding="utf-8")
            self.assertEqual(
                [path.name for path in audit_paper_prose.iter_sources(main)],
                ["main.tex", "live.tex"],
            )

    def test_prose_audit_flags_argument_and_engineering_risks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "section.tex"
            tex.write_text(
                "本节读取上游结果并完成数据审计，随后锁定模型，相关记录写入项目清单。\n\n"
                "在统一测试集上模型RMSE为0.20，MAE为0.11，准确率达到92.4%，"
                "五个验证窗口的计算均已完成并得到对应评价指标。\n\n"
                "SHAP相关分析证明投药量增加导致出水浊度下降。\n",
                encoding="utf-8",
            )
            findings = audit_paper_prose.analyze_file(tex)["findings"]
            kinds = {item["kind"] for item in findings}
            self.assertIn("internal_engineering_jargon", kinds)
            self.assertIn("result_without_interpretation", kinds)
            self.assertIn("causal_overreach", kinds)

    def test_prose_audit_ignores_table_length_and_accepts_evidence_interpretation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "section.tex"
            tex.write_text(
                "\\begin{longtable}{lll}\\caption{符号表}\\\\\n"
                + "符号与含义及单位\\\\\n" * 80
                + "\\end{longtable}\n\n"
                "模型RMSE由0.31下降到0.18，相较基线改善41.9%，因此采用该模型。\n\n"
                "表用于核对平均指标，图进一步展示逐折RMSE及其波动。\n\n"
                "预测区间只反映样本外残差，不包含未来结构变化。\n",
                encoding="utf-8",
            )
            findings = audit_paper_prose.analyze_file(tex)["findings"]
            kinds = {item["kind"] for item in findings}
            self.assertNotIn("long_sentence", kinds)
            self.assertNotIn("long_paragraph", kinds)
            self.assertNotIn("result_without_interpretation", kinds)

    def test_prose_audit_flags_evidence_progression_breaks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "section.tex"
            tex.write_text(
                "\\begin{table}\\caption{精确结果}\\end{table}\n"
                "\\begin{figure}\\caption{变化趋势}\\end{figure}\n"
                "\\subsection{下一项分析}\n正文。\n",
                encoding="utf-8",
            )
            findings = audit_paper_prose.analyze_file(tex)["findings"]
            kinds = {item["kind"] for item in findings}
            self.assertIn("adjacent_table_figure_without_bridge", kinds)
            self.assertIn("evidence_block_without_followup", kinds)

    def test_prose_audit_accepts_explained_table_figure_progression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tex = Path(tmp) / "section.tex"
            tex.write_text(
                "表1给出逐日精确值，图1进一步展示变化趋势与区间宽度。\n\n"
                "\\begin{table}\\caption{精确结果}\\end{table}\n\n"
                "为观察时间变化及不确定性，将上述结果绘制为图1。\n\n"
                "\\begin{figure}\\caption{变化趋势}\\end{figure}\n\n"
                "预测值先下降后回升，区间宽度基本稳定，因此采用滚动更新方案。\n",
                encoding="utf-8",
            )
            findings = audit_paper_prose.analyze_file(tex)["findings"]
            kinds = {item["kind"] for item in findings}
            self.assertNotIn("adjacent_table_figure_without_bridge", kinds)
            self.assertNotIn("evidence_block_without_followup", kinds)

    def test_adaptive_two_model_comparison_passes_without_ensemble(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            report = validate_project.validate(root, final=False)
            self.assertTrue(report["ok"], report["errors"])

    def test_structure_validation_reports_scope_and_pending_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            init_project.initialize(root, [(1, 2)], "结构校验范围测试")

            report = validate_project.validate(root, final=False)

            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["validation_scope"], "structure-only")
            self.assertEqual(report["completion_summary"]["total"], 2)
            self.assertEqual(report["completion_summary"]["pending"], 2)
            self.assertEqual(report["completion_summary"]["complete"], 0)
            self.assertTrue(any("ok=true 不代表项目已经完成" in item for item in report["warnings"]))

    def test_final_validation_reports_completion_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            add_valid_compile_proof(root)

            report = validate_project.validate(root, final=True)

            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["validation_scope"], "final-delivery")
            self.assertEqual(report["completion_summary"]["total"], 1)
            self.assertEqual(report["completion_summary"]["complete"], 1)
            self.assertFalse(any("仅执行结构校验" in item for item in report["warnings"]))

    def test_cli_keeps_structure_and_final_reports_separate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            init_project.initialize(root, [(1, 1)], "校验报告命名测试")

            structure = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_project.py"), str(root)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            final = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_project.py"), str(root), "--final"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(structure.returncode, 0, structure.stderr)
            self.assertNotEqual(final.returncode, 0)
            self.assertTrue((root / "结构校验报告.json").is_file())
            self.assertTrue((root / "最终交付校验报告.json").is_file())

    def test_invalid_figure_signature_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            (root / "求解" / "问题一" / "小问1" / "图" / "flow.pdf").write_bytes(b"%PDF fake")
            report = validate_project.validate(root, final=False)
            self.assertFalse(report["ok"])
            self.assertTrue(any("图文件为空或结构无效" in error for error in report["errors"]))

    def test_core_flowchart_requires_vector_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            sq = root / "求解" / "问题一" / "小问1"
            old_flow = sq / "图" / "flow.pdf"
            new_flow = sq / "图" / "flow.png"
            old_flow.unlink()
            new_flow.write_bytes(minimal_png_bytes())
            manifest_path = sq / "小问清单.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["figure_files"] = ["求解/问题一/小问1/图/flow.png"]
            manifest["algorithms"][1]["flowchart_file"] = "求解/问题一/小问1/图/flow.png"
            write_json(manifest_path, manifest)

            report = validate_project.validate(root, final=False)
            self.assertFalse(report["ok"])
            self.assertTrue(any("流程图必须为可编辑/可缩放的 PDF 或 SVG" in error for error in report["errors"]))

    def test_final_validation_binds_pdf_sources_and_visual_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            add_valid_compile_proof(root)
            report = validate_project.validate(root, final=True)
            self.assertTrue(report["ok"], report["errors"])

            # An inactive draft may contain stale labels without affecting the paper.
            (root / "论文" / "sections" / "old-draft.tex").write_text(
                "\\label{alg:q1-core}\n", encoding="utf-8"
            )
            report = validate_project.validate(root, final=True)
            self.assertTrue(report["ok"], report["errors"])

            # Any active-source edit invalidates both compile and review provenance.
            active = root / "论文" / "sections" / "question-1-sub-1.tex"
            active.write_text(active.read_text(encoding="utf-8") + "% changed\n", encoding="utf-8")
            report = validate_project.validate(root, final=True)
            self.assertFalse(report["ok"])
            self.assertTrue(any("编译后发生变化" in error for error in report["errors"]))

    def test_documented_user_override_can_change_default_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            paper = root / "论文"
            main = paper / "main.tex"
            main.write_text(
                main.read_text(encoding="utf-8").replace(
                    "\\input{sections/restatement.tex}\n"
                    "% BEGIN AUTO ASSUMPTIONS SYMBOLS INPUT\n"
                    "\\input{sections/assumptions-symbols.tex}\n"
                    "% END AUTO ASSUMPTIONS SYMBOLS INPUT",
                    "% BEGIN AUTO ASSUMPTIONS SYMBOLS INPUT\n"
                    "\\input{sections/assumptions-symbols.tex}\n"
                    "% END AUTO ASSUMPTIONS SYMBOLS INPUT\n"
                    "\\input{sections/restatement.tex}",
                ),
                encoding="utf-8",
            )
            question = paper / "sections" / "question-1.tex"
            question.write_text(
                question.read_text(encoding="utf-8").replace(
                    "\\section{问题一：样本外预测}", "\\section{官方模板第一项任务}"
                ),
                encoding="utf-8",
            )
            project = json.loads((root / "项目清单.json").read_text(encoding="utf-8"))
            profile = project["paper_profile"]
            profile.update({
                "mode": "user_override",
                "layout": "abstract-contents-assumptions-restatement-questions-tail",
                "override_reason": "用户明确要求采用另一份章节模板",
                "override_reference": "用户提供的目录要求，2026-09-10",
                "source_order": [
                    "sections/abstract.tex",
                    "sections/assumptions-symbols.tex",
                    "sections/restatement.tex",
                    "sections/question-1.tex",
                    "sections/model-evaluation.tex",
                    "sections/references.tex",
                    "sections/appendix.tex",
                ],
            })
            write_json(root / "项目清单.json", project)
            add_valid_compile_proof(root)
            report = validate_project.validate(root, final=True)
            self.assertTrue(report["ok"], report["errors"])

    def test_old_fake_compile_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            build_complete_project(root)
            paper = root / "论文"
            (paper / "main.pdf").write_bytes(b"%PDF fake")
            write_json(paper / "编译报告.json", {"ok": True, "engine": "xelatex", "pdf": "main.pdf", "passes": 2})
            report = validate_project.validate(root, final=True)
            self.assertFalse(report["ok"])
            self.assertTrue(any("版本过旧" in error for error in report["errors"]))
            self.assertTrue(any("基本结构检查" in error for error in report["errors"]))

    def test_final_default_structure_negative_cases(self) -> None:
        cases = {
            "placeholder title": (
                lambda root: (root / "论文" / "main.tex").write_text(
                    (root / "论文" / "main.tex").read_text(encoding="utf-8").replace(
                        "面向样本外预测的正则化建模",
                        "论文标题：用一句话概括对象、方法与目标",
                    ),
                    encoding="utf-8",
                ),
                "尚未填写正式题目",
            ),
            "front matter order": (
                lambda root: (root / "论文" / "main.tex").write_text(
                    (root / "论文" / "main.tex").read_text(encoding="utf-8").replace(
                        "\\input{sections/abstract.tex}\n\n\\clearpage\n\\tableofcontents",
                        "\\tableofcontents\n\n\\clearpage\n\\input{sections/abstract.tex}",
                    ),
                    encoding="utf-8",
                ),
                "摘要—目录—问题重述",
            ),
            "unrequested shared data": (
                lambda root: (root / "论文" / "main.tex").write_text(
                    (root / "论文" / "main.tex").read_text(encoding="utf-8").replace(
                        "% BEGIN OPTIONAL SHARED DATA INPUT\n",
                        "% BEGIN OPTIONAL SHARED DATA INPUT\n\\input{sections/data-preprocessing.tex}\n",
                    ),
                    encoding="utf-8",
                ),
                "仍存在“数据说明与预处理”",
            ),
            "wrong subquestion label": (
                lambda root: (root / "论文" / "sections" / "question-1-sub-1.tex").write_text(
                    (root / "论文" / "sections" / "question-1-sub-1.tex").read_text(encoding="utf-8").replace(
                        "\\subsection{小问 a}", "\\subsection{小问 b}"
                    ),
                    encoding="utf-8",
                ),
                "标题应与题面顺序对应",
            ),
        }
        for name, (mutate, expected) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "project"
                build_complete_project(root)
                mutate(root)
                add_valid_compile_proof(root)
                report = validate_project.validate(root, final=True)
                self.assertFalse(report["ok"])
                self.assertTrue(any(expected in error for error in report["errors"]), report["errors"])

    def test_compile_timeout_returns_report_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp)
            (paper / "main.tex").write_text("test", encoding="utf-8")
            timeout = subprocess.TimeoutExpired(cmd=["xelatex"], timeout=180, output="partial", stderr="late")
            with mock.patch.object(compile_paper.shutil, "which", return_value="xelatex"), mock.patch.object(
                compile_paper.subprocess, "run", side_effect=timeout
            ):
                report = compile_paper.compile_paper(paper, "main.tex", "xelatex")
            self.assertFalse(report["ok"])
            self.assertEqual(report["passes"], [{"pass": 1, "returncode": None, "status": "timeout"}])

    def test_xelatex_is_auto_discovered_outside_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install_root = Path(tmp) / "texlive-min"
            older = install_root / "2025" / "bin" / "windows" / "xelatex.exe"
            newer = install_root / "2026" / "bin" / "windows" / "xelatex.exe"
            older.parent.mkdir(parents=True)
            newer.parent.mkdir(parents=True)
            older.write_bytes(b"old")
            newer.write_bytes(b"new")
            with mock.patch.object(compile_paper.shutil, "which", return_value=None), mock.patch.object(
                compile_paper, "TEXLIVE_SEARCH_ROOTS", (install_root,)
            ), mock.patch.dict(compile_paper.os.environ, {"TEXLIVE_BIN": "", "TEXLIVE_ROOT": ""}):
                executable, resolution = compile_paper.resolve_xelatex()
            self.assertEqual(Path(executable or ""), newer.resolve())
            self.assertEqual(resolution, "texlive-auto-discovery")

    def test_explicit_xelatex_path_has_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "xelatex.exe"
            executable.write_bytes(b"test")
            with mock.patch.object(compile_paper.shutil, "which", return_value="PATH/xelatex.exe"):
                resolved, resolution = compile_paper.resolve_xelatex(executable)
            self.assertEqual(Path(resolved or ""), executable.resolve())
            self.assertEqual(resolution, "explicit")

    def test_compile_rejects_source_outside_paper_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paper = root / "paper"
            paper.mkdir()
            (root / "outside.tex").write_text("outside", encoding="utf-8")
            report = compile_paper.compile_paper(paper, "../outside.tex", "xelatex")
            self.assertFalse(report["ok"])
            self.assertIn("越出论文目录", report["error"])


if __name__ == "__main__":
    unittest.main()

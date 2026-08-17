#!/usr/bin/env python3
"""Initialize a graduate mathematical modeling project with per-subquestion ownership."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


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


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def subquestion_section(section_no: int, question_no: int, sub_no: int) -> str:
    return f"""\\subsection{{小问{sub_no}：模型建立、求解与验证}}

\\subsubsection{{任务目标与模型口径}}
说明本小问要求的输出、单位、粒度、验收标准及 exact/statistical/simulation/heuristic/fallback 属性。

\\subsubsection{{数据、假设与符号}}
说明本小问输入字段、数据质量、关键假设以及首次使用的符号与量纲。

\\subsubsection{{从题意到数学模型}}
依次给出基础模型、约束或边界条件、参数来源与完整模型，解释每一项的现实含义。

\\subsubsection{{求解方法与实现}}
说明基线、最终算法、选择理由、随机种子、训练或求解设置以及实际采用的 fallback。

\\subsubsection{{结果与验证}}
从问题{chinese_number(question_no)}小问{sub_no}的结果目录引用核心结果表，并解释误差、可行性、敏感性或鲁棒性。

% 图片必须保存在本小问的“图”目录。示例：
% \\includegraphics[width=0.82\\textwidth]{{../求解/问题{chinese_number(question_no)}/小问{sub_no}/图/示例图.pdf}}

\\subsubsection{{直接回答}}
用与结果文件一致的口径直接回答本小问，并说明适用边界。
"""


def initialize(output: Path, mapping: list[tuple[int, int]], competition: str) -> None:
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
        "paper_workflow": {
            "results_locked": False,
            "abstract_status": "placeholder",
            "abstract_evidence_check": "pending",
            "abstract_evidence": [],
        },
        "questions": [],
        "handoffs": [],
    }
    question_inputs: list[str] = []

    for section_no, (question_no, sub_count) in enumerate(mapping, start=5):
        q_cn = chinese_number(question_no)
        q_dir = output / "求解" / f"问题{q_cn}"
        q_dir.mkdir(parents=True)
        section_inputs: list[str] = []
        question_entry = {"question": question_no, "folder": f"求解/问题{q_cn}", "subquestions": []}

        for sub_no in range(1, sub_count + 1):
            sq_dir = q_dir / f"小问{sub_no}"
            for child in ("代码", "图", "结果"):
                (sq_dir / child).mkdir(parents=True)
            sq_manifest = {
                "question": question_no,
                "subquestion": sub_no,
                "target_output": "",
                "units": "",
                "inputs": [],
                "dependencies": [],
                "contract": {
                    "objective": "",
                    "non_goals": [],
                    "acceptance_criteria": [],
                    "dependencies": [],
                },
                "literature_candidates": [],
                "model_comparison": {
                    "applicability": "pending",
                    "reason": "",
                    "primary_metric": "",
                    "candidates": [],
                    "ensemble": {},
                    "result_file": "",
                    "decision": "",
                },
                "algorithms": [],
                "experiments": [],
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
                {"subquestion": sub_no, "folder": f"求解/问题{q_cn}/小问{sub_no}"}
            )

            filename = f"{section_no}.{sub_no}.问题{q_cn}小问{sub_no}.tex"
            (output / "论文" / "章节" / filename).write_text(
                subquestion_section(section_no, question_no, sub_no), encoding="utf-8"
            )
            section_inputs.append(f"\\input{{章节/{filename}}}")

        question_entry["subquestion_count"] = sub_count
        manifest["questions"].append(question_entry)
        question_filename = f"{section_no}.问题{q_cn}.tex"
        question_text = (
            f"\\section{{问题{q_cn}的模型建立、求解与验证}}\n\n"
            + "\n".join(section_inputs)
            + "\n"
        )
        (output / "论文" / "章节" / question_filename).write_text(question_text, encoding="utf-8")
        question_inputs.append(f"\\input{{章节/{question_filename}}}")

    main_path = output / "论文" / "main.tex"
    main_text = main_path.read_text(encoding="utf-8")
    begin = "% BEGIN AUTO QUESTION INPUTS"
    end = "% END AUTO QUESTION INPUTS"
    before, remainder = main_text.split(begin, 1)
    _, after = remainder.split(end, 1)
    main_text = before + begin + "\n" + "\n".join(question_inputs) + "\n" + end + after

    # Keep the paper file numbering sequential when a task has other than three
    # top-level questions. Read all tail files before deleting because desired
    # names can overlap existing names (for example 8 -> 10 while 10 exists).
    tail_start = 5 + len(mapping)
    tail_specs = (
        ("8.敏感性与鲁棒性.tex", f"{tail_start}.敏感性与鲁棒性.tex"),
        ("9.模型评价与推广.tex", f"{tail_start + 1}.模型评价与推广.tex"),
        ("10.参考文献.tex", f"{tail_start + 2}.参考文献.tex"),
        ("11.附录.tex", f"{tail_start + 3}.附录.tex"),
    )
    sections_dir = output / "论文" / "章节"
    tail_contents = [
        (old_name, new_name, (sections_dir / old_name).read_text(encoding="utf-8"))
        for old_name, new_name in tail_specs
    ]
    for old_name, _, _ in tail_contents:
        (sections_dir / old_name).unlink()
    for old_name, new_name, content in tail_contents:
        (sections_dir / new_name).write_text(content, encoding="utf-8")
        main_text = main_text.replace(f"章节/{old_name}", f"章节/{new_name}")

    main_path.write_text(main_text, encoding="utf-8")

    write_json(output / "项目清单.json", manifest)
    (output / "求解计划.md").write_text(
        "# 求解计划\n\n"
        "按问题与小问填写目标、输入、模型、输出、依赖、验证方案和文件归属。"
        "任何方法选择都应有数据规模、约束结构或评价指标依据。\n",
        encoding="utf-8",
    )
    print(f"已创建研究生数学建模项目：{output.resolve()}")
    print("问题映射：" + ", ".join(f"{q}:{count}" for q, count in mapping))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="新项目目录（必须为空或不存在）")
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
    args = parser.parse_args()
    initialize(args.output, args.question_map, args.competition)


if __name__ == "__main__":
    main()

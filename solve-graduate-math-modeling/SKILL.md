---
name: solve-graduate-math-modeling
description: End-to-end workflow and reusable LaTeX template for Chinese graduate mathematical modeling competitions, especially the Huawei Cup / China Graduate Mathematical Contest in Modeling. Use when Codex must read a modeling problem and attachments, decompose every problem into subquestions, keep each subquestion's code, figures, and results in its own folder, build auditable models, run and validate computations, write an anonymous Chinese competition paper, compile PDF, or check a graduate modeling submission.
---

# Solve Graduate Math Modeling

Use an evidence-first workflow for Chinese graduate mathematical modeling competitions. Treat the current year's official rules, cover, filename, attachment, and AI-use requirements as authoritative.

## Start a project

1. Read the problem statement and all attachments before choosing methods.
2. Identify every problem and subquestion. Record dependencies between them.
3. Initialize the workspace with:

```powershell
python scripts/init_project.py <output-directory> --map "1:3,2:2,3:1" --competition "中国研究生数学建模竞赛"
```

The map means problem 1 has three subquestions, problem 2 has two, and problem 3 has one. Do not invent a subquestion count when the statement is ambiguous; inspect headings, numbering, and required outputs first.

4. Read [workspace-layout.md](references/workspace-layout.md) before creating or moving computation artifacts.

## Enforce subquestion ownership

Keep every subquestion self-contained:

```text
求解/问题一/小问1/
├── 代码/
├── 图/
├── 结果/
└── 小问清单.json
```

- Put code used only by one subquestion in that subquestion's `代码/` folder.
- Put every accepted figure generated for that subquestion in its `图/` folder.
- Put tables, metrics, predictions, solver exports, and other machine-readable outputs in its `结果/` folder.
- Put genuinely shared utilities only in `求解/公共/代码/`; list all callers and keep task-specific outputs out of the public folder.
- Never mix figures or results from different subquestions. Never use a paper-side figure copy as the source of truth.
- Define cross-question handoffs with field names, units, granularity, quality flags, and fallback behavior.
- Update each `小问清单.json` after running code. Mark a subquestion complete only when its direct answer is supported by saved outputs.
- Maintain the modeling contract, experiment log, findings, claim-evidence matrix, and four stage gates inside the same manifest. Read [evidence-workflow.md](references/evidence-workflow.md) before selecting the final model.

Run the structural validator before writing and again before delivery:

```powershell
python scripts/validate_project.py <project-directory>
```

After the paper is compiled and visually inspected, mark the paper gate passed and run `python scripts/validate_project.py <project-directory> --final`.

## Model each subquestion

For every subquestion, build this evidence loop:

1. State the requested output, units, granularity, and acceptance criterion.
2. Audit input fields, joins, missing values, outliers, leakage risk, and assumptions.
3. Map the problem to sets, indices, parameters, variables, objectives or losses, constraints, and boundary conditions.
4. Read [literature-algorithm-screening.md](references/literature-algorithm-screening.md), search current primary sources, verify publisher pages or DOI records, and record the candidate method's data requirements and transfer decision. Prefer problem relevance and data compatibility over prestige or novelty.
5. Establish a defensible baseline before adding complexity.
6. For prediction or classification, read [model-comparison-and-ensemble.md](references/model-comparison-and-ensemble.md) and compare at least three non-ensemble candidates, including a baseline, plus at least one auditable ensemble. Use the same leakage-free split, horizon, objective, and metrics. Mark genuinely non-applicable problem types explicitly instead of forcing an ensemble.
7. Compare literature-derived candidates under that same protocol. Retain rejected and data-blocked candidates instead of silently discarding them.
8. Justify the final model using data scale, variable types, constraints, interpretability, and computational budget.
9. Implement the agreed model, fix random seeds, and record solver or training status.
10. Save an auditable core result table and validate feasibility, dimensions, physical/business bounds, and uncertainty.
11. Perform sensitivity, robustness, error, or out-of-sample checks appropriate to the problem.
12. Give a direct answer and state whether it is exact, statistical, simulated, heuristic, near-optimal, or fallback.

Record failed and inconclusive experiments as well as successful ones. Every accepted algorithm must be covered by a passed experiment, and every headline claim must point to an existing result file plus a field, row, key, or sheet locator.

For every newly introduced algorithm, enforce the formula-and-lineage contract in [algorithm-parameter-lineage.md](references/algorithm-parameter-lineage.md). Do not name or run an algorithm without writing its mathematical expression and tracing every material parameter to a problem statement, upstream result field, data estimate, literature standard, calibration experiment, or explicitly labeled scenario assumption.

Read [modeling-quality.md](references/modeling-quality.md) for the derivation contract and problem-type checks. Do not force extra formulas, algorithms, or figures merely to increase quantity.

## Create figures

- Create a figure only when it answers a named analytical question better than a compact table.
- Generate it from the current subquestion's verified data and save it directly under that subquestion's `图/` folder.
- Read [visualization-backend-selection.md](references/visualization-backend-selection.md) before plotting. Select the backend figure by figure from the analytical task: prefer Seaborn for distributions, grouped statistical comparisons, correlation/error heatmaps and faceting; Matplotlib for precise time-series, interval, annotation and multi-layer control; MATLAB for justified surfaces, contours, optimization geometry, PDE, signal/control and engineering plots; specialized Python libraries for networks or maps; Plotly only when interaction adds value.
- Run `python scripts/check_visualization_env.py` in the actual project environment before relying on an optional Python plotting library. If Seaborn is selected but absent, install it into the active project/controlled environment with `python -m pip install "seaborn>=0.13,<0.14" matplotlib pandas numpy`, rerun the check, and record versions or fallback reasons. Do not silently switch environments.
- Read [visualization-matlab.md](references/visualization-matlab.md) whenever MATLAB is selected or the user asks for three-dimensional, surface, contour, response-surface, or especially polished mathematical figures.
- Save the MATLAB source in the owning subquestion's `代码/` folder. Do not keep a single opaque root plotting script as the only source; a root runner may only dispatch the subquestion scripts.
- Use Chinese labels, units, readable legends, non-misleading axes, and print-safe colors.
- Reject duplicated, decorative, empty, singleton-distribution, clipped, or unverifiable figures.
- Use Seaborn and MATLAB for their analytical strengths, not as cosmetic filters. A visually attractive figure that hides sample size, uncertainty, units, constraints, or exact comparison must be rejected.
- Cite and interpret every accepted figure in the corresponding paper subsection.

## Write the paper

Copy `assets/graduate-latex-template/` into the project's `论文/` directory through `init_project.py`. Read [paper-writing.md](references/paper-writing.md) before drafting.

- Keep the anonymous body free of school, team, member, contact, API, local-path, and internal-log information.
- Use the official cover supplied for the current competition year as a separate submission artifact.
- Keep the abstract as `ABSTRACT_STATUS: placeholder` while any subquestion, experiment, result, claim, or computation gate is unfinished. After all subquestions are complete, lock the result set in `项目清单.json.paper_workflow`, register one abstract evidence entry per top-level problem, then write the abstract and change the marker/status to `final`. Read the abstract rules in [paper-writing.md](references/paper-writing.md). After a short background/route sentence, use a separate paragraph beginning with bold `针对问题一：`、`针对问题二：` ... for every top-level problem, and cover its subquestions in order. Each paragraph must contain the task, named method/model, audited key result, and direct conclusion; do not merge several problems into one “再次/最后” paragraph.
- Keep formulation, solution, result, validation, and direct answer adjacent for every subquestion.
- Place each algorithm's formula, symbol definitions, parameter-source paragraph, solution procedure, and result interpretation in one continuous subsection. Do not make the reader search backward for an unexplained number or forward for a missing definition.
- Reference figures from their owning `求解/问题X/小问Y/图/` folders.
- Use only real, verified references and resolve citations in both directions.
- Disclose public code, online material, and AI assistance according to the current rules.

Compile with:

```powershell
python scripts/compile_paper.py <project-directory>\论文
```

Inspect the rendered PDF, not only the exit code. Check Chinese glyphs, margins, tables, equations, captions, page numbers, blank space, clipping, and unresolved references.

## Finish

Read [verification-checklist.md](references/verification-checklist.md), then require:

- every problem and subquestion appears in the project manifest;
- every completed subquestion has code and an auditable result file in its own folder;
- every figure is owned by exactly one subquestion and exists at the cited path;
- every headline number traces to a saved result artifact;
- every completed major subquestion has a verified literature candidate record, including required data and an explicit adopt/benchmark/reject/data-blocked decision;
- every predictive/classification subquestion compares at least three non-ensemble models and one ensemble under the same out-of-sample protocol, or records why the requirement is genuinely not applicable;
- the abstract contains a separately labeled paragraph for every top-level problem, in problem order, with method, audited result, and direct conclusion;
- every accepted algorithm has a passed experiment and every core claim has an existing evidence file;
- the problem-analysis, modeling, computation, and paper stage gates have passed in final validation;
- downstream questions consume documented handoffs;
- the PDF compiles and passes visual inspection;
- the official cover, filename, attachment list, and AI declaration follow the current notice.

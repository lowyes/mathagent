---
name: solve-graduate-math-modeling
description: End-to-end workflow and reusable LaTeX template for Chinese graduate mathematical modeling competitions, especially the Huawei Cup / China Graduate Mathematical Contest in Modeling. Use when Codex must read a modeling problem and attachments, decompose every problem into subquestions, keep each subquestion's code, figures, and results in its own folder, build auditable models, run and validate computations, write an anonymous Chinese competition paper, compile PDF, or check a graduate modeling submission.
metadata:
  version: "3.0.1"
---

# Solve Graduate Math Modeling

Use an evidence-first workflow for Chinese graduate mathematical modeling competitions. Treat the current year's official rules, cover, filename, attachment, and AI-use requirements as authoritative.

## Start a project

1. Read the problem statement and all attachments before choosing methods.
2. Identify every problem and real solution unit. Do not invent `(a)(b)` labels when the statement has none. For each unit, record a semantic title, the primary task type and why it governs the unit, every required output with unit/granularity/acceptance, dependencies, whether literature transfer is needed, the evidence needed for the final judgment, the strongest interpretation the evidence may support, and the planned methods/representations in `problem-spec.json`. Read [task-driven-quality-gates.md](references/task-driven-quality-gates.md) and begin from the schema-v2 [problem-spec.example.json](assets/problem-spec.example.json).
3. Before initialization, choose the paper structure from the problem: `shared-data` when multiple questions reuse the same audit and preprocessing, `problem-local` when their data operations differ, or `mixed` when only a small common core is shared. Also decide whether assumptions and symbols should be combined, where each question's analysis belongs, and whether a separate model-evaluation chapter adds new information. Prefer task-driven initialization:

```powershell
python scripts/init_project.py <output-directory> --spec <problem-spec.json>
```

For an old project without a blueprint, the legacy `--map`, `--titles`, and structure flags remain supported. Do not invent mappings or structural reasons when the statement is ambiguous; inspect headings, numbering, required outputs, shared fields, and task dependencies first.

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

A non-final `ok: true` certifies structure and manifest consistency only. Read `validation_scope`, `completion_summary`, and warnings; it does not mean the solution or paper is complete.

After the paper is compiled and visually inspected, mark the paper gate passed and run `python scripts/validate_project.py <project-directory> --final`.

## Model each subquestion

For every solution unit, build this evidence loop. The loop is complete but its gates are task-driven; a deterministic rule is not forced to imitate a prediction experiment.

1. State the requested output, units, granularity, and acceptance criterion.
2. Audit input fields, joins, missing values, outliers, leakage risk, and assumptions.
3. Map the problem to sets, indices, parameters, variables, objectives or losses, constraints, and boundary conditions.
4. Apply the declared literature gate. When transfer from research or standards affects method choice, read [literature-algorithm-screening.md](references/literature-algorithm-screening.md), verify primary sources and record data requirements and transfer decisions. When the task is fully defined by the statement, a proved identity, or an official standard, record `not_required` or `conditional` with the reason instead of inventing a literature review.
5. Establish a defensible baseline when the task involves predictive or comparative empirical claims. A pure rule, exact derivation, or direct statistical test may instead use a boundary, identity, or hand-check case.
6. For prediction tasks, read [model-comparison-and-ensemble.md](references/model-comparison-and-ensemble.md). Compare a reliable baseline with at least one serious candidate under the same leakage-free split, horizon, objective, and metrics. For other task types, compare alternatives only when the choice affects the conclusion.
7. Where candidate comparison applies, retain rejected and data-blocked candidates instead of silently discarding them.
8. Justify the final model using data scale, variable types, constraints, interpretability, and computational budget.
9. Implement the agreed model, fix random seeds, and record solver or training status.
10. Save an auditable result carrier that directly answers the task: this may be a table, figure, equation result, decision list, trajectory, or machine-readable file. Use a table when exact values need comparison; do not force one when it adds no evidence.
11. Perform sensitivity, robustness, error, out-of-sample, feasibility, convergence, or other checks appropriate to the problem. Read [validation-evaluation-integration.md](references/validation-evaluation-integration.md), register every validation or evaluation method, and keep its definition, actual protocol, result, interpretation, and decision impact adjacent to the model or claim it evaluates.
12. Review whether any validation result invalidates the current acceptance criterion, claim strength, or deployment boundary. If so, use the `revision_workflow` in [evidence-workflow.md](references/evidence-workflow.md) to record the trigger, diagnosis, actual change, rerun and decision before continuing. If no revision is needed, record why; do not treat every rejected candidate as a model failure.
13. Give a direct answer and state whether it is exact, statistical, simulated, heuristic, near-optimal, or fallback.

For empirical, optimization, fitting, clustering, evaluation, or simulation tasks, record failed and inconclusive experiments as well as successful ones and cover every accepted computational method with a passed experiment. Every headline claim, regardless of task type, must point to an existing result file plus a field, row, key, sheet, or named object locator.

For every newly introduced method, enforce the definition/formula-and-lineage contract in [algorithm-parameter-lineage.md](references/algorithm-parameter-lineage.md). Register either a mathematical formula or an explicit operational definition. If the method has tunable or material parameters, trace each one to the problem statement, upstream result, data estimate, literature standard, calibration experiment, or labeled scenario assumption; otherwise declare `parameter_applicability: not_required` and explain why.

Before drafting, identify the small set of methods that carry the main results or methodological contribution and mark every registered method as core or supporting. Choose representations by information need: formulas/definitions for mathematical meaning, flowcharts for multi-stage branching pipelines, pseudocode for iterative or non-obvious execution, and tables/figures for evidence. A core iterative algorithm requires both flowchart and pseudocode; a core regression equation or deterministic rule does not. When either representation is declared, follow [core-algorithm-flowcharts.md](references/core-algorithm-flowcharts.md) or [core-algorithm-pseudocode.md](references/core-algorithm-pseudocode.md). Neither replaces real code, result interpretation, or parameter lineage.

Read [modeling-quality.md](references/modeling-quality.md) for the derivation contract and problem-type checks. Do not force extra formulas, algorithms, or figures merely to increase quantity.

## Create figures

- Create a figure only when it answers a named analytical question better than a compact table.
- Generate it from the current subquestion's verified data and save it directly under that subquestion's `图/` folder.
- Read [visualization.md](references/visualization.md) before plotting. It is the single source for backend selection per analytical task, the Python environment precheck and install path, Seaborn paper styling, the MATLAB route including the three-dimensional justification test, and per-figure acceptance checks.
- Use Chinese labels, units, readable legends, non-misleading axes, and print-safe colors.
- Reject duplicated, decorative, empty, singleton-distribution, clipped, or unverifiable figures.
- When a method declares `flowchart` in `representations`, save a reproducible source in the owning unit's code folder and the rendered PDF or SVG in its figure folder. Register both paths in the method record and the relevant file lists.
- Use Seaborn and MATLAB for their analytical strengths, not as cosmetic filters. A visually attractive figure that hides sample size, uncertainty, units, constraints, or exact comparison must be rejected.
- Cite and interpret every accepted figure in the corresponding paper subsection.

## Write the paper

Copy `assets/graduate-latex-template/` into the project's `论文/` directory through `init_project.py`. Read [paper-writing.md](references/paper-writing.md) before drafting. Treat [competition-paper-structure-evidence.md](references/competition-paper-structure-evidence.md) as the sole authority for chapter order and evidence organization. Read [competition-problem-restatement.md](references/competition-problem-restatement.md) before writing or revising the problem-restatement section. Read [competition-assumptions-symbols.md](references/competition-assumptions-symbols.md) before writing or revising model assumptions, modeling conventions, or the symbol table. If the user supplies example papers, read [competition-style-transfer.md](references/competition-style-transfer.md), create a source-located project style card, and transfer only structure and evidence rhythm. After the current paper is compiled, complete the six-dimension write-back review before marking the style transfer checked. Read [competition-paper-prose.md](references/competition-paper-prose.md) afterward when drafting or compressing prose.

- Keep the anonymous body free of school, team, member, contact, API, local-path, and internal-log information.
- Use the official cover supplied for the current competition year as a separate submission artifact.
- Build a problem-statement coverage matrix before drafting the restatement. Keep background short, then restate every problem in order with its inputs, hard conditions, outputs, and dependencies. Preserve all consequential numbers, units, thresholds, time windows, and inequalities; do not include model choices, procedures, or results.
- Separate unverifiable modeling assumptions from problem facts, computational conventions, decision preferences, and limitations. State each material assumption's object, rationale, and consequence if violated. Keep global assumptions centralized and local assumptions adjacent to their model.
- Include in the global symbol table only symbols reused across core formulas or requiring dimension, unit, domain, or subscript clarification. Define local one-use symbols beside their formula, and audit in both directions for undefined and unused symbols.
- Keep abstract, contents and problem restatement first, then choose the remaining skeleton from the problem rather than copying a reference paper: assumptions and symbols may be combined or separate; a public data chapter appears only for genuinely shared material; problem analysis may be top-level, per-subquestion or hybrid; and model evaluation is a conditional chapter. Record all decisions and rationales in `paper_profile`. When an optional chapter is absent, later numbering shifts automatically. Keep short front sections continuous; do not insert `\newpage`, `\clearpage`, or `\pagebreak` merely to give each a fresh page. If an official template or explicit user instruction changes even these semantic constraints, use `official_override` or `user_override` and record the reference plus actual `source_order`.
- Completeness requirements are not fixed heading requirements. Internally audit task, data, formula, parameters, solution, result, validation, direct answer, and boundary, while using only the few headings that make the current argument easier to follow.
- Keep the abstract as `ABSTRACT_STATUS: placeholder` while any subquestion, experiment, result, claim, or computation gate is unfinished. After results are locked, read both [paper-writing.md](references/paper-writing.md) and [competition-abstract-writing.md](references/competition-abstract-writing.md). Register evidence and an `abstract_plan` for every included problem before drafting: distinguish independent problems from inherited extensions, qualify or decline any claimed model highlight, and bind task, method, key result, direct answer, and any real boundary. Then write natural evidence-adjacent prose and change the marker/status to `final`. Default to all top-level problems; if the user or official template explicitly limits the abstract, record `paper_workflow.abstract_questions` and `abstract_scope_reason` instead of inserting empty or hidden problem labels.
- Keep formulation, solution, result, validation, and direct answer adjacent for every subquestion.
- Let headings follow visible research actions such as data cleaning, feature construction, model solution and error analysis; keep parameter lineage, evidence locators and downstream consumers in the manifest rather than exposing them as paper headings.
- Draft each result-bearing subsection in two passes: first extract only verified facts from result carriers, then convert them into an argument that states what the evidence supports, which choice it changes, and where the conclusion stops. Afterward translate internal terms such as “审计、锁定、上游字段、下游消费者、质量门” into natural mathematical-modeling prose; never infer a mechanism merely because one model or ablation performs better.
- After a chapter is drafted, audit its progression by reading only headings, paragraph openings/endings, captions and conclusions. The chain should remain recoverable as task/data difficulty → choice criterion → method/parameters → result evidence → validation/decision → direct answer/boundary. When a table and figure share one result, state their different evidence roles; adjacency is acceptable only when that division and the resulting conclusion are already clear.
- When a later subquestion inherits an earlier one, open with what stays unchanged, what information or constraint is added, what new difficulty follows, and what additional processing is therefore required.
- Preserve a four-level evidence chain: data/audit evidence, model-execution evidence, comparable result evidence, and conclusion evidence. Every headline conclusion must trace backward through these levels, and each downstream question must identify its upstream result fields and units.
- Write model sections from the current problem outward: data difficulty and choice criterion first, then only the theory needed to understand the implemented model. Avoid model histories, dictionary definitions, generic advantages, and public benchmark facts that do not change a modeling decision.
- After drafting or materially revising a chapter, run `python scripts/audit_paper_prose.py <paper-directory-or-TeX-file>`. Review its long-paragraph, long-sentence, encyclopedic-introduction, vague-result, and repeated-transition warnings in context; do not delete text mechanically.
- Do not create detached textbook-style sections for validation methods or metrics. At first use, define the method or metric briefly, then immediately connect it to the current model, actual data protocol, evidence result, interpretation, and model or conclusion decision.
- Place each algorithm's formula, symbol definitions, parameter-source paragraph, solution procedure, and result interpretation in one continuous subsection. Put an overall route diagram after the problem analysis when it helps orient the reader; keep an internal algorithm flowchart near that algorithm. Do not make the reader search backward for an unexplained number or forward for a missing definition.
- When a method declares `pseudocode`, typeset a numbered block with explicit input, output, initialization, real loops or branches, stopping/fallback logic, and returned fields. Do not create pseudocode for a closed-form formula merely to satisfy appearance.
- Reference figures from their owning `求解/问题X/小问Y/图/` folders.
- Use only real, verified references and resolve citations in both directions.
- For schema-v3 paper workflows, complete the evidence-backed `model_review` and `citation_ledger`: connect each limitation to a concrete improvement, distinguish implemented work from future proposals, state the mathematical structure and revalidation needed for any extension, and reconcile every in-text citation with its ledger and bibliography entry. Do not force a separate evaluation chapter when the review is better integrated into the relevant questions.
- Disclose public code, online material, and AI assistance according to the current rules.

Compile with:

```powershell
python scripts/compile_paper.py <project-directory>\论文
```

`compile_paper.py` first checks `PATH`, then optional `TEXLIVE_BIN`/`TEXLIVE_ROOT`, common TeX Live roots on `C:` and `D:`, and common MiKTeX locations. Use `--compiler <path-to-xelatex.exe>` when an installation is elsewhere. The report records how the engine was resolved as well as its exact path.

Inspect the rendered PDF, not only the exit code. Check Chinese glyphs, margins, tables, equations, captions, page numbers, blank space, clipping, and unresolved references. Record the inspected PDF hash and concrete checks in `paper_workflow.pdf_visual_review`; any subsequent source change invalidates that review and requires recompilation and reinspection.

## Finish

Work through [verification-checklist.md](references/verification-checklist.md) item by item. It is the only list of delivery checks; this file does not restate them.

Then run final validation:

```powershell
python scripts/validate_project.py <project-directory> --final
```

The validator enforces the machine-checkable subset — manifest coverage, per-unit artifacts, figure ownership, method and lineage records, task-appropriate literature/experiment/comparison/representation gates, validation methods, claims, stage gates, and abstract structure. Legacy manifests remain accepted. A passing run is necessary, not sufficient.

Three classes of check have no automated equivalent, so confirm them by hand:

- rendered-PDF inspection: Chinese glyphs, margins, tables, equations, captions, page numbers, blank space, clipping, unresolved references;
- prose quality: run `python scripts/audit_paper_prose.py <paper-directory>` and resolve remaining encyclopedic history, dictionary definitions, vague performance claims, and repeated generic explanations in context;
- the current year's official notice: cover, page limit, filename, attachment list, and AI declaration.

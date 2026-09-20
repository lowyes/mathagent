# Changelog

## 3.0.1 - 2026-09-20

### Changed

- Distinguished early structural validation from final-delivery validation through explicit `validation_scope` and per-status `completion_summary` fields.
- Added a prominent warning when structural validation passes while one or more subquestions remain unfinished, preventing `ok=true` from being mistaken for project completion.
- Kept structural and final reports separately as `结构校验报告.json` and `最终交付校验报告.json`.
- Clarified that stage-gate requirements in ordinary validation apply when a subquestion is marked `complete`; pending work remains visible but is not misreported as delivered.

### Tests

- Added regression coverage for validation scope, completion counts, warning behavior, completed-project final scope, and distinct report filenames.

## 3.0.0 - 2026-09-20

### Added

- Task-aware paper planning through `problem-spec.json`, including chapter structure, subquestion inheritance, model highlights, evidence bindings, and source order.
- Progressive abstract planning that links each subproblem's task, method, immediate result, model highlight, metric, and final answer.
- Model revision and review records for assumptions, baselines, validation, sensitivity, stability, limitations, and deployment boundaries.
- Citation ledger checks that connect claims, sources, manuscript locations, and reference entries.
- Competition-paper prose, structure, style-transfer, visualization, pseudocode, and evidence-quality guidance.
- Regression coverage for initialization, schema migration, writing gates, model review, citation audit, and final delivery checks.

### Changed

- Upgraded the generated paper workflow to schema version 3 while retaining compatibility with earlier projects.
- Reworked the LaTeX template around the standard competition order: abstract, restatement, assumptions and symbols, conditional shared-data chapter, problem chapters, model evaluation, references, and appendix.
- Replaced fixed algorithm-stacking requirements with task-driven model selection, fair comparison, and evidence-first writing.
- Strengthened the validator so that polished prose cannot substitute for missing numerical evidence, validation, or traceable sources.

### Removed

- Redundant backend-specific visualization notes superseded by the unified visualization guide.
- Legacy template fragments that no longer match the schema-v3 paper structure.

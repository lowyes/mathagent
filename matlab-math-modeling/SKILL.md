---
name: matlab-math-modeling
description: Use MATLAB to complete mathematical-modeling data analysis, numerical modeling, optimization, simulation, scientific visualization, and reproducible result export. Trigger when a modeling subquestion should be solved or plotted in MATLAB; when the user requests MATLAB, MATLAB MCP Server, three-dimensional surfaces, contours, optimization visualizations, engineering plots, or .m code; or when an existing mathematical-modeling workflow needs MATLAB execution and validation.
---

# MATLAB Mathematical Modeling

Use MATLAB as an analytical backend, not a cosmetic plotting filter. Keep every script, result table, and figure inside the owning problem/subquestion directory.

## Start with execution preflight

1. Read [execution-and-toolboxes.md](references/execution-and-toolboxes.md).
2. Prefer a connected MATLAB MCP execution tool when available because it preserves the MATLAB session and returns diagnostics directly.
3. Otherwise locate MATLAB and use non-interactive `matlab -batch` execution. Do not assume `matlab` is on `PATH`; check common installation locations on Windows.
4. Run `scripts/check_environment.m` and record the MATLAB release and installed products in the project environment report.
5. Verify every proposed function and option against the installed release. Do not emit R2025a live-script syntax for an R2022a installation.

## Route the task

- For tables, time series, cleaning, grouping, or descriptive statistics, use MATLAB table/timetable operations and document all filtering rules.
- For regression, classification, forecasting, or neural networks, use leakage-safe training/validation/test splits and compare multiple models under identical folds and metrics.
- For optimization, classify the structure before choosing a solver. Prefer the narrowest valid solver: linear, quadratic, mixed-integer, least-squares, constrained nonlinear, then global or heuristic methods.
- For simulation, state governing equations, initial/boundary conditions, discretization, solver tolerances, and numerical stability checks.
- For visualization, read [visualization-recipes.md](references/visualization-recipes.md). Use MATLAB when its surface, contour, scientific, optimization, signal, PDE, or engineering graphics materially clarify the answer.

## Maintain mathematical continuity

Before implementing each new model or solver:

1. Write its governing formula in the paper notation.
2. Define every symbol, unit, index range, objective term, and constraint.
3. Map each code variable to the paper symbol.
4. Record where every parameter originates: raw field, preceding equation, calibrated result, literature value, or explicit assumption.
5. Save fitted/calibrated parameters as machine-readable results and load them downstream; never retype them silently.

Read [modeling-and-validation.md](references/modeling-and-validation.md) for model comparison, fusion, optimization checks, and robustness requirements.

## Implement per subquestion

Store MATLAB artifacts under the owning subquestion:

```text
问题X/小问Y/
├── 代码/
│   ├── main.m
│   └── functions/
├── 结果/
│   ├── metrics.csv
│   ├── parameters.csv
│   └── environment.json
└── 图/
    ├── figure_name.png
    └── figure_name.pdf
```

- Make `main.m` reproduce the subquestion from declared inputs.
- Use relative paths derived from the project root; do not commit machine-specific absolute paths.
- Set random seeds with `rng(seed,"twister")` when stochastic procedures are used.
- Export numerical results with units and full-precision machine-readable values; round only in the manuscript-facing table.
- Save every accepted figure as 300 DPI PNG and vector PDF when supported.
- Use `scripts/apply_paper_style.m` and `scripts/export_paper_figure.m` as reusable helpers or copy them into the subquestion's `代码/functions/` directory.

## Validate before accepting results

- Check array sizes, finite values, units, and feasible domains before solving.
- For predictive models, report at least one scale-dependent and one relative/error-normalized metric when appropriate; include out-of-sample baselines, multiple candidates, and one justified fusion model.
- For optimization, report `exitflag`, objective value, iterations, maximum constraint violation, bound activity, and at least one perturbation or multi-start check when local optima are possible.
- For simulation, run step-size or tolerance sensitivity and verify conservation/balance laws where applicable.
- For every figure, verify labels, units, legend, sample size/uncertainty, non-misleading axes, and correspondence to the saved data.
- Run `scripts/smoke_test.m` after installing this Skill or changing the MATLAB environment.

## Finish

Deliver the `.m` source, environment record, machine-readable results, figures, and a short run command. State missing toolboxes or fallback methods explicitly. Never claim MATLAB execution succeeded without an actual clean run and verified output files.

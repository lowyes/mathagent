# Execution and toolbox routing

## Execution order

1. Use a connected MATLAB MCP Server or MATLAB execution tool when callable.
2. If the official MathWorks Agentic Toolkit is installed, use its task-specific skills for data analysis, optimization, machine learning, live scripts, debugging, tests, or documentation lookup.
3. Otherwise execute through MATLAB CLI:

```powershell
$matlabExe = (Get-Command matlab -ErrorAction Stop).Source
& $matlabExe -batch `
  "addpath('path/to/scripts'); check_environment('environment.json')"
```

Discover the executable rather than copying a machine-specific path. If it is absent from `PATH`, search each filesystem drive under `Program Files/MATLAB/R20*/bin/matlab.exe`, then select the newest compatible release explicitly.

## Preflight

Run:

```matlab
addpath("path/to/matlab-math-modeling/scripts");
check_environment("environment.json");
```

Inspect `environment.json` before selecting functions. Match code to `release` and installed products.

## Toolbox routing

| Task | Preferred product | Base-MATLAB fallback |
|---|---|---|
| Tabular cleaning and aggregation | MATLAB | `table`, `groupsummary`, `rowfun` where available |
| Statistical regression | Statistics and Machine Learning Toolbox | matrix least squares with explicit diagnostics |
| Time-series forecasting | Econometrics/Statistics toolboxes as appropriate | transparent seasonal/lag baselines |
| LP/QP/NLP/MILP | Optimization Toolbox | implement only mathematically valid small alternatives; otherwise report dependency |
| GA/PSO/global search | Global Optimization Toolbox | multi-start local search only when justified |
| Neural networks | Deep Learning Toolbox | use another verified backend rather than pretending support |
| PDE/FEM | Partial Differential Equation Toolbox | problem-specific discretization only with numerical validation |

Never replace a missing toolbox with an unrelated algorithm merely to keep the script running. Record the fallback and its consequences.

## Official Toolkit boundary

The MathWorks Agentic Toolkit remains a separate upstream dependency with its own license. This Skill does not copy it. When present, route to its specialized skills; when absent, use the workflows and scripts bundled here. MATLAB itself and relevant toolboxes require valid MathWorks installations and licenses.

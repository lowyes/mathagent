# Modeling and validation rules

## Prediction and model fusion

- Freeze the evaluation protocol before tuning models.
- For temporal data, split chronologically and use rolling or expanding validation; never random-shuffle future observations into training.
- Compare a transparent baseline, at least two credible candidate families, and one fusion model when data support it.
- Learn fusion weights only from validation or out-of-fold predictions. Do not optimize weights on the final test set.
- Report fold-level metrics, mean and dispersion, not only the best single score.
- Preserve the exact metric definition, aggregation level, zero-handling rule, and units.

For a convex weighted fusion,

\[
\hat y_t^{(ens)}=\sum_{m=1}^{M}w_m\hat y_{t,m},\qquad
w_m\ge0,\quad\sum_{m=1}^{M}w_m=1.
\]

Record the source predictions, fitted weights, fitting split, objective, and final held-out performance.

## Optimization

Classify the problem before selecting a solver:

- LP: `linprog`
- QP: `quadprog`
- MILP: `intlinprog`
- constrained nonlinear: `fmincon`
- nonlinear least squares: `lsqnonlin` or `lsqcurvefit`
- derivative-free/global: use only when nonconvexity or unavailable gradients justify it

Always validate:

- objective and constraints are finite at the initial point;
- bounds and dimensions are consistent;
- returned `exitflag` indicates an acceptable termination;
- maximum equality and inequality violations are below declared tolerances;
- results remain credible under initial-point, parameter, or data perturbations.

## Simulation and numerical methods

- State equations and physical/statistical interpretation before code.
- Record initial conditions, boundary conditions, time/space grids, solver, and tolerances.
- Compare at least two resolutions or tolerances for convergence-sensitive results.
- Check known limiting cases, balance laws, monotonicity, or conservation identities.

## Evidence chain

For each reported result preserve:

```text
paper claim -> table/figure -> result file -> MATLAB script -> input fields and parameters
```

If any link is missing, treat the result as provisional rather than paper-ready.

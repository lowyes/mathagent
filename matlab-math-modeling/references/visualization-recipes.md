# MATLAB paper-figure recipes

## Choose MATLAB for analytical value

Use MATLAB for response surfaces, contour maps, feasible regions, optimization geometry, PDE fields, signal/control diagrams, and engineering plots. Prefer Seaborn for grouped statistical distributions and ordinary correlation heatmaps; prefer Matplotlib when exact custom multi-layer annotation is the main need.

Do not use three-dimensional graphics for one-dimensional or categorical results. A 3D surface is justified only when both horizontal axes are meaningful continuous variables and the surface reveals a relationship needed by the argument.

## Style

- Use Chinese labels when the manuscript is Chinese and always include units.
- Use `tiledlayout` instead of manually positioned subplot axes.
- Use perceptually ordered colormaps such as `parula`, `turbo` with care, or a task-appropriate sequential/diverging map.
- Avoid rainbow palettes, unnecessary gradients, opaque surfaces hiding data, and excessive mesh lines.
- Mark observed data, feasible boundaries, optima, uncertainty, or reference thresholds when they support interpretation.
- Keep titles concise; put experimental conditions in the caption or subtitle.
- Use consistent font, line width, marker size, and color mapping across all subquestions.

## Export

Call:

```matlab
apply_paper_style(gcf);
export_paper_figure(gcf, fullfile(outputDir,"response_surface"));
```

This produces a 300 DPI PNG and vector PDF where supported. Inspect both files after export; vector export may rasterize unsupported transparency or complex surface content.

## Required figure record

For every accepted figure record:

- analytical question answered;
- source data/result file;
- owning subquestion script;
- MATLAB release and relevant toolbox;
- plot type and why it was selected;
- output PNG/PDF path;
- one- or two-sentence manuscript interpretation.

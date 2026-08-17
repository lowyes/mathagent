# MATLAB visualization route

Read this reference when MATLAB is available, the user requests MATLAB, or the model benefits from three-dimensional or publication-style scientific graphics.

## Choose the backend

Choose the renderer figure by figure; one paper may use both backends.

| Analytical need | Preferred backend | Typical chart |
|---|---|---|
| response surface, two-factor sensitivity, terrain or field | MATLAB | `surf`, `mesh`, `contourf`, `surfc` |
| optimization landscape, feasible region, Pareto front | MATLAB | surface plus projected contour, 2-D/3-D scatter |
| differential equation, signal, spectrum, control response | MATLAB | phase portrait, spectrogram, Bode/step plot |
| polished multi-panel scientific comparison | MATLAB | `tiledlayout` with shared legend/color scale |
| grouped distributions, categorical comparisons, correlation/error heatmaps | Seaborn + Matplotlib | box/violin/strip/ECDF, annotated heatmap, faceting |
| ordinary time series, prediction intervals, custom residual diagnostics | Matplotlib or MATLAB | line with band, scatter, histogram, QQ/residual plot |
| geographic map, complex network, interactive graphic | Python | map, Sankey, network graph, interactive HTML |

Prefer MATLAB only when the installed release supports the required functions. Record the release and toolboxes used. If MATLAB or a required toolbox is unavailable, fall back to base MATLAB or Python and record the fallback in the subquestion manifest.

## Decide whether 3-D is justified

Use 3-D only when all conditions hold:

1. Two independent explanatory dimensions and one meaningful response dimension exist.
2. The surface shape, interaction, optimum, ridge, basin, or boundary is part of the argument.
3. Units and sampling density are defensible; interpolation is disclosed.
4. A fixed camera angle and color scale do not hide important regions.
5. A 2-D contour, projection, or key-point table accompanies the surface when exact comparison matters.

Do not turn categories, a single time series, or unrelated columns into decorative 3-D bars. Prefer 2-D when depth adds no analytical meaning.

## Build figures

1. Read only verified result files from the current subquestion's `结果/` folder.
2. Put `matlab_plot_qX_Y.m` or an equally explicit script in that subquestion's `代码/` folder.
3. Use a root `matlab_run_all.m` only as a dispatcher. It must not own subquestion-specific logic.
4. Set a white canvas, consistent font, 220--300 dpi export, restrained print-safe palette, outward ticks, light grid, and sufficient margins.
5. Include units on axes and colorbars. Keep legends short and outside dense data regions.
6. For `surf`/`mesh`, use perceptually ordered colormaps such as `parula` or `turbo`, add `colorbar`, set `view`, and consider a projected `contourf` panel.
7. Export accepted raster figures with `exportgraphics(...,'Resolution',240)`; also export PDF/SVG when vector output is stable and the paper toolchain supports it.
8. Save directly to the owning `图/` folder with the final cited filename. Avoid manual screenshots.

Suggested surface pattern:

For a reusable implementation, copy or call `scripts/matlab/plot_response_surface.m`. Validate that its paired surface and contour answer the analytical question before citing the image.

```matlab
f = figure('Color','w','Position',[100 100 1100 520]);
tl = tiledlayout(f,1,2,'TileSpacing','compact','Padding','compact');
nexttile; surf(X,Y,Z,'EdgeColor','none'); view(42,28);
xlabel('x (unit)'); ylabel('y (unit)'); zlabel('response (unit)');
colormap(parula); colorbar; grid on;
nexttile; contourf(X,Y,Z,14,'LineColor','none'); axis tight;
xlabel('x (unit)'); ylabel('y (unit)'); colorbar;
exportgraphics(f,outputFile,'Resolution',240);
```

## Handle text and release compatibility

- Test scripts with the actual installed MATLAB release, not only by inspection.
- On older Windows releases, verify `.m` file encoding before using Chinese literals. If command-line parsing fails, use an encoding compatible with that MATLAB installation or keep source literals ASCII and read Chinese labels from UTF-8 result data.
- Avoid functions introduced after the recorded release unless a compatible fallback is present.
- Treat warnings, empty tables, missing fonts, clipped labels, and invisible legends as failures requiring correction.

## Validate

- Confirm every source table exists and row filters are nonempty.
- Confirm the script exits successfully in batch or through MATLAB MCP.
- Open every exported image and inspect text, color contrast, occlusion, and crop.
- Confirm every image belongs to one subquestion, appears in its manifest, and is cited and interpreted in the paper.
- Retain a 2-D alternative when a 3-D view could distort quantitative comparison.

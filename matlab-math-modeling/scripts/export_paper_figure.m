function paths = export_paper_figure(fig, outputBase)
%EXPORT_PAPER_FIGURE Export a figure as 300 DPI PNG and vector PDF.
arguments
    fig (1,1) matlab.ui.Figure
    outputBase (1,1) string
end

parent = fileparts(outputBase);
if strlength(parent) > 0 && ~isfolder(parent)
    mkdir(parent);
end

apply_paper_style(fig);
paths = struct("png", outputBase + ".png", "pdf", outputBase + ".pdf");
exportgraphics(fig, paths.png, "Resolution", 300, "BackgroundColor", "white");
exportgraphics(fig, paths.pdf, "ContentType", "vector", "BackgroundColor", "white");
assert(isfile(paths.png) && isfile(paths.pdf), "Figure export did not create both files.");
end

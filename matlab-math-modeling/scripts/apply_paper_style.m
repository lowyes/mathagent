function apply_paper_style(fig)
%APPLY_PAPER_STYLE Apply consistent publication-oriented defaults to a figure.
if nargin < 1 || isempty(fig)
    fig = gcf;
end

set(fig, "Color", "white", "Units", "centimeters", "Position", [2 2 18 11]);
fontName = "Microsoft YaHei";
availableFonts = string(listfonts);
if ~any(strcmpi(availableFonts, fontName))
    fontName = "Helvetica";
end

axesObjects = findall(fig, "Type", "axes");
for ax = reshape(axesObjects, 1, [])
    set(ax, "FontName", fontName, "FontSize", 10, "LineWidth", 0.8, ...
        "Box", "off", "TickDir", "out", "Layer", "top");
    grid(ax, "on");
    ax.GridAlpha = 0.16;
    ax.MinorGridAlpha = 0.08;
end

lineObjects = findall(fig, "Type", "line");
for lineObject = reshape(lineObjects, 1, [])
    if lineObject.LineWidth < 1.2
        lineObject.LineWidth = 1.2;
    end
end
end

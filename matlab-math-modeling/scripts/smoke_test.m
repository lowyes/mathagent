function outputs = smoke_test(outputDir)
%SMOKE_TEST Generate and export a response-surface/contour test figure.
if nargin < 1
    outputDir = fullfile(tempdir, "matlab-math-modeling-smoke");
end
if ~isfolder(outputDir)
    mkdir(outputDir);
end

[x, y] = meshgrid(linspace(-3, 3, 81));
z = 0.6 .* (x - 0.8).^2 + 0.9 .* (y + 0.5).^2 + 0.18 .* x .* y;
[minimumValue, index] = min(z, [], "all", "linear");

fig = figure("Visible", "off");
layout = tiledlayout(fig, 1, 2, "TileSpacing", "compact", "Padding", "compact");
nexttile(layout);
surf(x, y, z, "EdgeColor", "none");
hold on;
plot3(x(index), y(index), minimumValue, "p", "MarkerSize", 11, ...
    "MarkerFaceColor", [0.85 0.20 0.16], "MarkerEdgeColor", "white");
xlabel("参数 x"); ylabel("参数 y"); zlabel("目标函数值");
title("响应曲面"); view(42, 28); colormap(parula); colorbar;

nexttile(layout);
contourf(x, y, z, 18, "LineColor", "none");
hold on;
plot(x(index), y(index), "p", "MarkerSize", 11, ...
    "MarkerFaceColor", [0.85 0.20 0.16], "MarkerEdgeColor", "white");
xlabel("参数 x"); ylabel("参数 y"); title("等高线与最优点");
axis equal tight; colorbar;
title(layout, "MATLAB 数学建模绘图环境测试");

outputs = export_paper_figure(fig, fullfile(string(outputDir), "response_surface_smoke"));
close(fig);
check_environment(fullfile(string(outputDir), "environment.json"));
disp(outputs);
end

function plot_response_surface(X,Y,Z,xLabel,yLabel,zLabel,outputFile)
%PLOT_RESPONSE_SURFACE Export a publication-style surface and contour pair.
% X, Y and Z must be equally sized numeric matrices, typically from meshgrid.

arguments
    X double
    Y double
    Z double
    xLabel (1,1) string
    yLabel (1,1) string
    zLabel (1,1) string
    outputFile (1,1) string
end

if ~isequal(size(X),size(Y),size(Z))
    error('X, Y and Z must have identical sizes.');
end
if any(~isfinite(X(:))) || any(~isfinite(Y(:))) || any(~isfinite(Z(:)))
    error('X, Y and Z must contain only finite values.');
end

f = figure('Visible','off','Color','w','Position',[100 100 1180 520]);
tl = tiledlayout(f,1,2,'TileSpacing','compact','Padding','compact');

nexttile(tl);
surf(X,Y,Z,'EdgeColor','none','FaceAlpha',0.96);
view(42,28); grid on; box on;
xlabel(xLabel); ylabel(yLabel); zlabel(zLabel);
title('Response surface','FontWeight','bold');
colorbar;

nexttile(tl);
contourf(X,Y,Z,16,'LineColor','none');
axis tight; grid on; box on;
xlabel(xLabel); ylabel(yLabel);
title('Projected contour','FontWeight','bold');
colorbar;

colormap(f,parula);
exportgraphics(f,outputFile,'Resolution',240);
close(f);
end

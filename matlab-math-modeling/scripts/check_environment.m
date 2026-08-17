function report = check_environment(outputPath)
%CHECK_ENVIRONMENT Report the MATLAB release and installed products as JSON.
if nargin < 1
    outputPath = "";
end

products = ver;
productInfo = repmat(struct("name", "", "version", "", "release", ""), numel(products), 1);
for k = 1:numel(products)
    productInfo(k).name = string(products(k).Name);
    productInfo(k).version = string(products(k).Version);
    productInfo(k).release = string(products(k).Release);
end

report = struct;
report.matlabVersion = string(version);
report.release = string(version("-release"));
report.root = string(matlabroot);
report.computer = string(computer);
report.products = productInfo;

encoded = jsonencode(report, PrettyPrint=true);
disp(encoded);
if strlength(string(outputPath)) > 0
    target = string(outputPath);
    parent = fileparts(target);
    if strlength(parent) > 0 && ~isfolder(parent)
        mkdir(parent);
    end
    fid = fopen(target, "w", "n", "UTF-8");
    assert(fid >= 0, "Could not open environment report for writing: %s", target);
    cleanup = onCleanup(@() fclose(fid));
    fwrite(fid, encoded, "char");
end
end

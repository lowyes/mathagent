# 可视化：后端选择与出图规范

先确定图要回答的分析问题，再选择库。不要因为某个库“好看”就把不适合的数据强行画成该图型；同一篇论文可以混合使用多个后端，但每张图只有一个所属小问和一个可复现源脚本。

## 图形任务与首选后端

逐图选择后端，依据分析任务而非工具偏好。

| 分析任务 | 首选后端 | 适合图型 | 选择理由 |
|---|---|---|---|
| 分布、组间差异、分类变量与连续变量关系 | Seaborn + Matplotlib | violin、box、boxen、strip、swarm、ECDF、分面图 | 统计语义清楚，分组与置信区间接口简洁，默认样式适合论文静态图 |
| 相关矩阵、模型误差矩阵、混淆矩阵 | Seaborn | heatmap、clustermap | 注释、色标、掩膜和聚类展示方便 |
| 普通时间序列、预测区间、残差、定制多面板 | Matplotlib | line、bar、scatter、hist、QQ、calibration | 坐标、日期、图层和排版控制最精确 |
| 响应面、二因子敏感性、地形或场分布 | MATLAB | surf、mesh、contourf、surfc | 曲面几何与投影等高线衔接成熟 |
| 优化景观、可行域、Pareto 前沿 | MATLAB | 曲面叠加投影等高线、二维/三维散点 | 便于同时表达约束边界与最优结构 |
| PDE、信号、频谱、控制响应 | MATLAB | 相图、spectrogram、Bode/step 图 | 科学计算结果与绘图衔接稳定 |
| 精修多面板科学对比 | MATLAB 或 Matplotlib | tiledlayout / subplots，共享图例与色标 | 面板对齐、共享色标可控 |
| 网络结构、路径、社团 | NetworkX + Matplotlib | network、DAG、路径高亮 | 图结构计算与绘制分离，适合拓扑解释 |
| 地理空间 | GeoPandas/Cartopy + Matplotlib | choropleth、点线面叠加 | 保留坐标参考系和空间语义 |
| 交互探索、悬停筛查 | Plotly | interactive scatter、surface、parallel coordinates | 适合探索和补充 HTML；正式 PDF 仍需导出并检查静态可读性 |

Seaborn 建立在 Matplotlib 之上。优先用 Seaborn 表达统计关系，再用 Matplotlib 控制标题、坐标、单位、标注、日期刻度和导出。复杂科学图不因 Seaborn 风格漂亮而改用不合适的图型。

选择 MATLAB 前确认已安装版本支持所需函数，并记录版本与工具箱。MATLAB 或必需工具箱不可用时，回退到基础 MATLAB 或 Python，并在小问清单登记回退原因。

## 环境预检与安装

先在实际运行论文代码的 Python 环境执行：

```powershell
python scripts/check_visualization_env.py
```

若 Seaborn 或 Matplotlib 缺失，在项目虚拟环境或当前受控运行环境安装，不要写入未知的系统 Python：

```powershell
python -m pip install "seaborn>=0.13,<0.14" matplotlib pandas numpy
```

安装后重新运行预检，并在小问清单的 `solver_or_training_status` 或实验配置中记录 Python、Seaborn、Matplotlib 版本。离线环境不能安装时，回退到现有 Matplotlib 或 MATLAB，并登记回退原因。不要为一张图安装重量级可选库。

## Seaborn 论文样式

建议从以下配置开始，再根据信息密度调整：

```python
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(
    context="paper",
    style="whitegrid",
    palette="colorblind",
    font="Microsoft YaHei",
    rc={"axes.unicode_minus": False, "figure.dpi": 120},
)
fig, ax = plt.subplots(figsize=(7.2, 4.6))
# sns.boxplot(..., ax=ax) / sns.heatmap(..., ax=ax)
fig.tight_layout()
fig.savefig(output_file, dpi=260, bbox_inches="tight", facecolor="white")
```

- 分布图优先同时呈现中心、离散程度和样本点/样本量；小样本不得用平滑密度制造虚假连续性。
- 相关热力图只放分析所需变量；使用对称色标表示正负相关，并标出有效样本数或显著性口径。
- 分类色彩使用色盲友好调色板；同一语义在全篇保持同一颜色。
- `whitegrid` 只用于需要读数的图；图像密集时改用 `white` 并弱化网格。
- 不使用彩虹色、过饱和渐变、3D 饼图、装饰阴影和无法打印区分的颜色。

## MATLAB 路线

MATLAB 可用、用户要求 MATLAB，或模型确实需要三维与科学出版风格图形时阅读本节。

### 判断三维是否成立

只有全部满足下列条件才使用三维：

1. 存在两个独立解释维度和一个有意义的响应维度。
2. 曲面形状、交互作用、最优点、脊、盆地或边界本身就是论据。
3. 单位与采样密度站得住脚，插值方式已说明。
4. 固定视角与色标不会遮蔽重要区域。
5. 需要精确比较时，同时给出二维等高线、投影或关键点表。

不要把分类数据、单条时间序列或互不相关的列画成装饰性三维柱。深度没有分析含义时优先二维。

### 出图流程

1. 只读取当前小问 `结果/` 目录中已验证的结果文件。
2. 将 `matlab_plot_qX_Y.m` 或同样明确命名的脚本放在该小问的 `代码/` 目录。
3. 根目录 `matlab_run_all.m` 只能作为调度器，不得承载小问特有逻辑。
4. 设置白色画布、统一字体、220--300 dpi 导出、克制的打印安全配色、外向刻度、浅网格和充足边距。
5. 坐标轴与色标标注单位；图例简短且避开数据密集区。
6. `surf`/`mesh` 使用 `parula`、`turbo` 等感知有序色图，加 `colorbar`，设定 `view`，并考虑配一幅投影 `contourf` 面板。
7. 接受的位图用 `exportgraphics(...,'Resolution',240)` 导出；矢量输出稳定且论文工具链支持时同时导出 PDF/SVG。
8. 直接保存到所属 `图/` 目录并使用正文引用的最终文件名，不要手工截图。

可复用实现见 `scripts/matlab/plot_response_surface.m`；引用图片前先确认成对的曲面与等高线确实回答了分析问题。

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

### 文本与版本兼容

- 用实际安装的 MATLAB 版本运行脚本，不要只靠阅读判断。
- 在较旧的 Windows 版本上，使用中文字面量前先确认 `.m` 文件编码。命令行解析失败时，改用与该安装兼容的编码，或让源码字面量保持 ASCII 并从 UTF-8 结果数据读取中文标签。
- 除非有兼容回退，不要使用晚于所记录版本引入的函数。
- 警告、空表、缺字体、标签裁切和不可见图例都视为必须修正的失败。

## 每图决策记录与验收

生成前写清四项：分析问题、候选图型、最终后端、拒绝其他后端的理由。例如：“比较四个预测模型跨折误差分布，选择 Seaborn boxplot + stripplot；不用柱状图，因为均值会隐藏折间波动。”

生成后必须检查：

- 源结果表真实存在，行筛选结果非空。
- 脚本在批处理、MATLAB MCP 或项目 Python 环境中成功退出。
- 坐标、单位、中文字体、图例遮挡、色标一致性、标签重叠逐项确认；灰度打印仍可区分。
- 220--300 dpi 或稳定矢量导出；打开每张导出图检查文字、对比度、遮挡与裁切。
- 登记到清单的图文件必须是真实、非空且可打开的 PNG/JPEG/PDF/SVG/EPS/TIFF；不得用改后缀、占位字节或损坏文件通过交付检查。正文由 XeLaTeX 直接引用时优先使用 PDF、PNG 或 JPEG；TIFF 只作为高分辨率归档版本，不直接写入 `\includegraphics`。
- 核心算法流程图必须同时保留生成源文件与 PDF/SVG 矢量成品；PNG 截图可作预览，但不能作为唯一正式流程图。
- 每张图只归属一个小问，已登记在该小问清单，并在正文对应小节被引用和解释。
- 三维视角可能扭曲定量比较时，保留二维替代图。

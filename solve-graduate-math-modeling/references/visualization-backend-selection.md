# 可视化后端选择

先确定图要回答的分析问题，再选择库。不要因为某个库“好看”就把不适合的数据强行画成该图型；同一篇论文可以混合使用多个后端，但每张图只有一个所属小问和一个可复现源脚本。

## 图形任务与首选后端

| 分析任务 | 首选后端 | 适合图型 | 选择理由 |
|---|---|---|---|
| 分布、组间差异、分类变量与连续变量关系 | Seaborn + Matplotlib | violin、box、boxen、strip、swarm、ECDF、分面图 | 统计语义清楚，分组与置信区间接口简洁，默认样式适合论文静态图 |
| 相关矩阵、模型误差矩阵、混淆矩阵 | Seaborn | heatmap、clustermap | 注释、色标、掩膜和聚类展示方便 |
| 普通时间序列、预测区间、残差、定制多面板 | Matplotlib | line、bar、scatter、hist、QQ、calibration | 坐标、日期、图层和排版控制最精确 |
| 三维曲面、等高线、优化几何、PDE/信号/控制 | MATLAB | surf、mesh、contourf、tiledlayout、Bode、spectrogram | 科学计算结果与绘图衔接稳定，三维和工程图成熟 |
| 网络结构、路径、社团 | NetworkX + Matplotlib | network、DAG、路径高亮 | 图结构计算与绘制分离，适合拓扑解释 |
| 地理空间 | GeoPandas/Cartopy + Matplotlib | choropleth、点线面叠加 | 保留坐标参考系和空间语义 |
| 交互探索、悬停筛查 | Plotly | interactive scatter、surface、parallel coordinates | 适合探索和补充HTML；正式PDF仍需导出并检查静态可读性 |

Seaborn 建立在 Matplotlib 之上。优先用 Seaborn 表达统计关系，再用 Matplotlib 控制标题、坐标、单位、标注、日期刻度和导出。复杂科学图不因 Seaborn 风格漂亮而改用不合适的图型。

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
- 不使用彩虹色、过饱和渐变、3D饼图、装饰阴影和无法打印区分的颜色。

## 每图决策记录

生成前写清四项：分析问题、候选图型、最终后端、拒绝其他后端的理由。例如：“比较四个预测模型跨折误差分布，选择 Seaborn boxplot + stripplot；不用柱状图，因为均值会隐藏折间波动。”

生成后必须检查：源数据非空；坐标和单位正确；中文字体存在；图例无遮挡；色标一致；标签不重叠；在灰度打印时仍能区分；220--300 dpi 或稳定矢量导出；图已登记在所属小问清单并在正文解释。

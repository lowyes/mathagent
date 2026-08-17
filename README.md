# mathagent

面向中国研究生数学建模竞赛的 Codex Skill，提供从赛题读取、数据审计、逐问建模、模型比较与融合，到论文生成和交付验证的完整工作流。

仓库包含两个可以独立安装、也可以协同调用的 Skill：

- `solve-graduate-math-modeling/`：研究生数学建模端到端主流程。
- `matlab-math-modeling/`：MATLAB 数据分析、数值建模、优化、科学绘图与结果验证后端。

## 主要能力

- 按“问题—小问”拆分工程，每个小问独立保存代码、结果和图片。
- 在建模前完成数据字典、字段口径、缺失值、异常值和时间泄漏检查。
- 每次引入算法时给出数学公式、符号定义、参数来源和跨章节参数传递关系。
- 对多个候选模型进行统一切分、统一指标的公平比较，并至少包含一个融合模型。
- 支持时间序列、回归、分类、优化、敏感性分析和稳健性分析等常见数模任务。
- 按分析目的选择绘图库：Seaborn 用于统计分布和分组比较，Matplotlib 用于定制论文图，MATLAB 用于三维曲面和科学工程图。
- 摘要在正文结果稳定后撰写，并按问题逐段报告方法、关键数值和结论。
- 提供研究生数模 LaTeX 模板、项目初始化脚本、环境检查和交付前验证脚本。

## 仓库结构

```text
matlab-math-modeling/          # MATLAB 数模执行与绘图 Skill
solve-graduate-math-modeling/
├── SKILL.md                  # Skill 入口与端到端流程
├── agents/openai.yaml        # Codex 界面元数据
├── assets/                   # 研究生数模 LaTeX 模板
├── references/               # 建模、论文、可视化与验证规范
└── scripts/                  # 初始化、编译、环境检查和项目验证脚本
```

## 安装

将 Skill 目录复制到 Codex Skills 目录：

```powershell
Copy-Item -Recurse -Force `
  .\solve-graduate-math-modeling `
  "$env:USERPROFILE\.codex\skills\solve-graduate-math-modeling"

Copy-Item -Recurse -Force `
  .\matlab-math-modeling `
  "$env:USERPROFILE\.codex\skills\matlab-math-modeling"
```

重启或刷新 Codex 后，可用类似下面的请求触发：

> 使用 solve-graduate-math-modeling 读取这道赛题及附件，按每个问题和小问建立独立代码、结果与图片目录，完成模型比较、融合、论文和最终验证。

需要单独调用 MATLAB 后端时：

> 使用 matlab-math-modeling 完成这个小问的数据分析、优化求解、论文绘图和结果验证。

## 常用检查

检查绘图环境：

```powershell
python .\solve-graduate-math-modeling\scripts\check_visualization_env.py
```

生成 Seaborn 中文论文图测试：

```powershell
python .\solve-graduate-math-modeling\scripts\smoke_test_seaborn.py .\seaborn-smoke.png
```

初始化一个新的数模项目：

```powershell
python .\solve-graduate-math-modeling\scripts\init_project.py --help
```

验证已生成项目：

```powershell
python .\solve-graduate-math-modeling\scripts\validate_project.py --help
```

Python 绘图的基础依赖为 `numpy`、`pandas`、`matplotlib` 和 `seaborn`；MATLAB、LaTeX 及其他专业绘图库按具体赛题选用。

## 设计原则

这个 Skill 不以堆叠算法或装饰性图片为目标。所有模型、参数、图表和论文结论都应能追溯到题面、数据、代码与结果文件，并服务于具体小问的回答。

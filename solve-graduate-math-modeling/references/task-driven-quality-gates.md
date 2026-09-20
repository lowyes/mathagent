# 任务驱动的题目蓝图与质量门

## 为什么先写 problem-spec

题面编号、求解任务和论文证据不总是一一对应。一个显式小问可能同时要求拟合与预测；一个没有 `(a)(b)` 的问题也可能需要多个自然研究动作。初始化前先把题面转换为 `problem-spec.json`，让目录、标题、方法、验证和证据门由真实任务决定，而不是套用“每问都要文献、三模型、流程图、伪代码”的固定模板。

以 `assets/problem-spec.example.json` 的 schema v2 为起点，读完题面与附件后再填写。v2要求说明题型判定理由，把每项输出写成“名称、单位、粒度、验收口径”，并为每个求解单元登记一个简短的 `argument_plan`。旧版 schema v1 继续兼容。`scripts/init_project.py --spec` 会先校验蓝图，随后生成项目清单、语义标题、小问清单和可选 Style Card，并把蓝图复制到项目根目录。

## 求解单元识别

对题面逐条登记：

- `label`：题面显式出现的 `a/b/c` 或内部稳定标识；
- `explicit`：题面是否真的给出该小问编号；若为 `false`，论文只使用语义标题，不伪造“小问 a”；
- `title`：用研究动作概括，如“拟合测量误差分布”，不用算法名或结果；
- `task_profile.primary`：决定主要质量门；按最终必须交付和验证的核心结果判定，不按所用算法名称判定；
- `task_profile.primary_reason`：用题面动作、输出形态和验证需求说明为什么由该题型主导；
- `task_profile.secondary`：登记兼具的任务性质或特殊结构，如 `prediction`、`longitudinal`、`recommendation`；
- `outputs`：逐项覆盖题面要求的数值、分类、曲线、方案或解释；schema v2中每项写明 `name`、`unit`、`granularity` 和 `acceptance`，不接受“给出结果”“进行分析”等空泛输出；
- `dependencies`：后续写入小问清单，并在项目 `handoffs` 中登记字段、单位、粒度、质量标记和 fallback。

每个schema v2求解单元同时填写 `argument_plan`：`decision_question` 说明论文最终要作出的判断，`evidence_required` 列出作出该判断前必须出现的真实证据，`interpretation_boundary` 限定结论强度。它是内部写作蓝图，不生成固定正文标题。

## 主任务类型

| 类型 | 典型输出 | 关键验证 | 是否默认强制模型比较 |
|---|---|---|---|
| `deterministic_rule` | 标签、计数、按题面规则计算值 | 边界、手算样例、单位与完整性 | 否 |
| `prediction` | 样本外预测、概率或分类 | 无泄漏外样本指标、误差诊断 | 是 |
| `classification` | 类别、概率、混淆矩阵 | 无泄漏分类指标、类别误差 | 是 |
| `fitting` | 参数、曲线、区间 | 残差、拟合优度、参数稳定性 | 否，存在实质选择时比较 |
| `clustering` | 分群、中心、解释 | 稳定性、轮廓/间隔、业务可解释性 | 否，存在实质选择时比较 |
| `optimization` | 可行方案、目标值 | 可行性、收敛/界、敏感性 | 否，必要时比较求解器或策略 |
| `evaluation` | 指数、排序、等级 | 权重与标准化稳定性、情景扰动 | 否 |
| `simulation` | 轨迹、分布、风险区间 | 收敛、重复性、区间与边界 | 否 |
| `association_decision` | 关联判断、风险因素、建议 | 统计检验、稳健性、非因果边界 | 否 |

这里的“否”不是禁止比较，而是不把预测任务的基线门机械移植到别的题型。

## 文献门

每个单元明确填写 `literature_review`：

- `required`：方法、阈值、机理或验证协议依赖外部知识，必须检索并核验；
- `conditional`：题面或基本理论足以求解，但可能需要标准/相邻研究解释边界；可暂不列候选，但要说明理由；
- `not_required`：题面已完整给定确定性规则、要求直接代入或可由文中已证恒等式推出；不得为形式完整虚构综述；
- `pending`：仅初始化阶段使用，完成前必须改写。

采用或作为基准的候选以 `used_by_methods` 指向真实方法名。旧项目的 `used_by_algorithms` 继续兼容。

## 方法与表达载体

`methods` 统一覆盖规则、统计检验、回归/分类、聚类、优化、仿真、机理方程和多阶段管线。完成阶段每种方法至少包含：`id`、`name`、`purpose`、`method_type`、`is_core`、`core_reason`、`representations`，以及 `formula_reference` 或 `definition_reference`。

表达载体按信息需要选择：

- `definition`：确定性规则、指标口径、集合与映射；
- `formula`：模型关系、目标函数、约束或统计量；
- `flowchart`：多阶段、分支、回退或跨模块管线；
- `pseudocode`：迭代、搜索、递推或非显然执行逻辑；
- `result_table` / `experiment_table` / `ablation_table` / `case_table`：精确数值与可比较证据；
- 各类 `*_figure`：趋势、结构、诊断、相关或轨迹证据；
- `recommendation_text`：直接决策建议及适用边界。

只有核心 `iterative_algorithm` 强制同时声明流程图与伪代码。其他核心方法依照信息需要选择，不为“看起来高级”重复表达。

## 参数适用性

完成方法时填写：

- `parameter_applicability: required`：存在材料参数、超参数、阈值或情景量，逐项登记值/规则、单位、来源类型、来源与下游用途；
- `parameter_applicability: not_required`：方法没有待估或待选参数，填写 `parameter_reason`，保持 `parameters: []`。

题面常量若会影响答案，仍应在正文定义并在结果血缘中可追溯；“不需要调参”不等于“可以不说明题面阈值”。

## 完成门矩阵

所有完成单元都需要：代码或可执行计算、机器可读结果、直接回答、至少一种与任务匹配的验证、发现记录、结论—证据链接和阶段质量门。

条件门如下：

| 门 | 触发条件 |
|---|---|
| 文献候选 | `literature_review.applicability=required` |
| 通过的实验记录 | `prediction/fitting/clustering/optimization/evaluation/simulation` |
| 可靠基线 + 主要候选 | `prediction` |
| 流程图文件 | 任一方法声明 `flowchart` |
| 算法伪代码块 | 任一方法声明 `pseudocode` |
| 参数血缘 | `parameter_applicability=required` |

对非实验任务，验证记录不必绑定 `experiment_id`，但仍必须指向真实结果文件和正文位置。对实验任务，验证必须关联已登记实验。

## 范文结构试验的判定原则

使用优秀论文检验 Skill 时，先逐页恢复题面任务—正文方法—结果载体映射，再用蓝图初始化，不把范文目录直接复制为固定规则。Style Card 分为“共同特征、可选择变体、当前赛题采用”三部分；共同特征才可能固化为一般规则，单篇论文的特例只登记为变体。

最终审计至少回答：

1. 蓝图是否覆盖题面的每个实际输出？
2. 任务类型变化是否真实改变了质量门？
3. 非预测任务是否被错误强迫做模型锦标赛？
4. 公式、流程图、伪代码和表图是否各自提供增量信息？
5. 任何结论能否回到机器可读结果与精确定位？

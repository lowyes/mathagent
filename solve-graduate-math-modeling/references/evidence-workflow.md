# 建模契约、实验记录与质量门

每个 `小问清单.json` 是该小问唯一的结构化事实源。不要另建内容重复的实验台账。运行过程中持续更新以下六组字段。

## 文献候选 `literature_candidates`

在确定最终算法前，按 [literature-algorithm-screening.md](literature-algorithm-screening.md) 登记真实、可核验的论文候选。每条记录必须说明问题匹配度、论文算法、必要数据、本题可用字段、迁移决定与状态。`adopted` 或 `benchmarked` 的记录必须通过 `used_by_algorithms` 指向本小问清单中的真实算法名；`rejected` 与 `data_blocked` 同样保留。

网络不可用或正式来源无法核验时，质量门不得伪造为通过。可把建模门保持为 `pending`，并在发现记录中说明阻断原因。

## 建模契约 `contract`

- `objective`：本小问要交付什么。
- `non_goals`：明确不解决或不能宣称的内容，至少一项。
- `acceptance_criteria`：可计算、可核对的验收标准。
- `dependencies`：上游问题、外部标准或题面条件；无依赖时使用空数组。

契约在选算法前完成。改变目标或验收标准时，先更新契约并记录一条 `decision` 类型发现。

## 多模型比较 `model_comparison`

预测与分类小问按 [model-comparison-and-ensemble.md](model-comparison-and-ensemble.md) 登记至少三个非融合候选和一个融合模型。记录统一主指标、候选模型族与角色、实验编号、融合成员、权重来源、泄漏控制、结果文件和最终决定。非预测类任务可设 `applicability=not_applicable`，但必须填写可核验原因。

## 实验记录 `experiments`

每次会影响模型选择或论文结论的运行都登记，不只记录成功结果：

```json
{
  "id": "E01",
  "name": "基线与候选模型滚动比较",
  "algorithm_names": ["星期中位数", "岭回归"],
  "purpose": "选择样本外误差更稳健的模型",
  "status": "passed",
  "command_or_entry": "求解/问题二/小问1/代码/滚动验证.py",
  "config": "5折，每折28个观测日",
  "result_files": ["求解/问题二/小问1/结果/滚动验证指标.csv"],
  "verdict": "星期中位数在主要目标上更稳健"
}
```

`status` 只能是 `passed`、`failed` 或 `inconclusive`。失败实验保留真实结果和失败含义，不删除、不改写成成功。每个进入最终方案的算法至少由一条 `passed` 实验覆盖。

## 发现与决策 `findings`

记录跨阶段仍会影响后续工作的短结论：

```json
{
  "type": "decision",
  "statement": "晚餐采用5%保障场景并与历史基线并列",
  "evidence": "晚餐历史订单占比不足1%",
  "implication": "5%不得表述为客流估计真值"
}
```

`type` 只能是 `research`、`engineering` 或 `decision`。至少保留一条关键发现，防止后续会话重复试错或遗失限制条件。

## 结论—证据矩阵 `claims`

论文中的每个核心结论都要登记证据：

```json
{
  "id": "C01",
  "statement": "星期中位数是当前数据上的稳健基线",
  "status": "verified",
  "paper_location": "问题二/五折滚动时间验证",
  "evidence": [
    {
      "file": "求解/问题二/小问1/结果/滚动验证指标.csv",
      "locator": "target, model, WMAPE",
      "relation": "五折平均WMAPE直接支持模型排序"
    }
  ]
}
```

`status` 只能是 `verified`、`qualified` 或 `rejected`。`qualified` 必须在正文保留边界；`rejected` 不得继续作为摘要或结论中的正向主张。证据文件必须真实存在，`locator` 必须指出字段、行、键或工作表。

## 四阶段质量门 `stage_gates`

固定使用四个键：

1. `problem_analysis`：问题、输出、单位、边界与依赖已确认。
2. `modeling`：真实文献候选已核验；适用时多模型与融合方案已登记；公式、参数血缘、基线、约束与验证方案已确认。
3. `computation`：代码运行、实验记录、结果文件和可行性检查已通过。
4. `paper`：结论—证据矩阵、引用、排版、PDF视觉检查和提交规则已通过。

每个门包含 `status` 与 `checks`。普通结构校验要求前三门通过；最终交付校验 `validate_project.py --final` 还要求论文门通过。

## 状态规则

- 契约未完成：`pending`。
- 已建模或正在实验：`in_progress`。
- 计算与论文证据全部闭环：`complete`。
- 外部数据、软件或授权确实不可得：`blocked`，写明原因。

禁止为了通过校验虚构实验、证据或质量门。不能通过的结论应标为 `qualified` 或 `rejected`，而不是修改原始结果。

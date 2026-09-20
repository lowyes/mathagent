# 建模契约、实验记录与质量门

每个 `小问清单.json` 是该小问唯一的结构化事实源。不要另建内容重复的实验台账。运行过程中持续更新以下六组字段。

## 文献候选 `literature_candidates`

先在 `literature_review` 登记 `required/conditional/not_required` 与理由。需要文献迁移时，按 [literature-algorithm-screening.md](literature-algorithm-screening.md) 登记真实候选，并通过 `used_by_methods` 指向本小问清单中的方法名；旧项目的 `used_by_algorithms` 继续兼容。题面已完整给出规则时可不列候选，但不得省略适用性理由。

网络不可用或正式来源无法核验时，质量门不得伪造为通过。可把建模门保持为 `pending`，并在发现记录中说明阻断原因。

## 建模契约 `contract`

- `objective`：本小问要交付什么。
- `non_goals`：明确不解决或不能宣称的内容，至少一项。
- `acceptance_criteria`：可计算、可核对的验收标准。
- `dependencies`：上游问题、外部标准或题面条件；无依赖时使用空数组。

契约在选算法前完成。改变目标或验收标准时，先更新契约并记录一条 `decision` 类型发现。

## 论证计划 `argument_plan`

schema v2 项目还要在建模前写清三件事：

- `decision_question`：本小问最终必须回答的判断句，而不是算法名。
- `evidence_required`：哪些样本外指标、敏感性结果、可行性检查或解析推导足以支持该判断。
- `interpretation_boundary`：证据最多允许解释到什么程度，例如只能说明预测关联、不能宣称因果。

它不是论文中的固定三级标题，而是贯穿写作的内部论证骨架。完成项目时，应把 `decision_question` 落到正文的直接回答，把 `evidence_required` 落到 `validation_methods` 与 `claims.evidence`，并让 `interpretation_boundary` 同步出现在局限说明或 `qualified` 结论中。不得出现“计划要求样本外证据，正文却只给训练拟合图”或“计划限定为条件关联，摘要却改写成因果关系”的断层。

## 多模型比较 `model_comparison`

预测与分类小问按 [model-comparison-and-ensemble.md](model-comparison-and-ensemble.md) 至少登记一个可靠基线和一个主要候选。额外模型必须对应真实待检验选择；融合只有在成员合格、误差互补并具有严格样本外成员预测时才登记，否则填写 `ensemble_reason`。记录统一主指标、候选模型族与角色、实验编号、结果文件和最终决定。非预测类任务可设 `applicability=not_applicable`，但必须填写可核验原因。

## 实验记录 `experiments`

对预测、拟合、聚类、优化、评价或仿真等实验型任务，每次会影响模型选择或论文结论的运行都登记，不只记录成功结果：

```json
{
  "id": "E01",
  "name": "基线与候选模型滚动比较",
  "method_names": ["星期中位数", "岭回归"],
  "purpose": "选择样本外误差更稳健的模型",
  "status": "passed",
  "command_or_entry": "求解/问题二/小问1/代码/滚动验证.py",
  "config": "5折，每折28个观测日",
  "result_files": ["求解/问题二/小问1/结果/滚动验证指标.csv"],
  "verdict": "星期中位数在主要目标上更稳健"
}
```

`status` 只能是 `passed`、`failed` 或 `inconclusive`。它描述这次运行本身是否有效，不是模型是否胜出：基线在比较中落败但运行正常、结果可用，仍是 `passed`；只有运行失败、配置错误或结果不可信才是 `failed`，证据不足以判断才是 `inconclusive`。失败实验保留真实结果和失败含义，不删除、不改写成成功。

实验型任务中，`methods` 登记的每个计算方法名都应由 `passed` 实验覆盖，包括真实运行但未胜出的基线和候选。确定性规则或解析推导不强制实验，可用边界检查、手算样例或恒等式验证。真正没有运行的方法不要写入已完成方法清单；只在文献中考察且未实现的候选保留为 `rejected` 或 `data_blocked`。

## 验证失败后的模型修订 `revision_workflow`

新项目在每个小问清单中保留模型修订复核。它不是要求所有低分模型都反复调参，而是区分“被合理淘汰的候选”和“会破坏当前结论的验证失败”。小问完成前把 `status` 设为 `passed`：若全部验收通过且无需修订，填写 `no_revision_reason`；若发生修订，则逐轮登记触发证据、诊断、实际修改、新旧实验和最终决定。

```json
{
  "revision_workflow": {
    "schema_version": 1,
    "status": "passed",
    "no_revision_reason": "",
    "cycles": [
      {
        "id": "R01",
        "trigger": {
          "type": "validation",
          "id": "V03",
          "evidence_file": "求解/问题二/小问1/结果/多步递推.csv",
          "locator": "horizon=12h 行的 R2 字段"
        },
        "diagnosis": "长时距递推反馈造成误差累积",
        "changed_components": ["feature", "validation_protocol", "claim_boundary"],
        "previous_experiment": "E04",
        "revised_experiment": "E07",
        "outcome": "2--4 h恢复稳定，12 h仍明显退化",
        "decision": "保留短期预测，限制长期外推"
      }
    ]
  }
}
```

`changed_components` 只记录真正改变的部分，可取 `problem_scope`、`assumption`、`data`、`preprocessing`、`feature`、`model`、`parameter`、`solver`、`validation_protocol` 或 `claim_boundary`。修订后的实验必须是真实存在且可用的 `passed` 运行。不得仅因某个候选落败就声称“重新建模”，也不得删除修订前的不理想结果。

## 验证评估记录 `validation_methods`

按 [validation-evaluation-integration.md](validation-evaluation-integration.md) 登记实际采用的交叉验证、误差分析、敏感性、鲁棒性、可行性、收敛性、统计检验或边界检查。每条记录必须关联结果文件与定位，并通过 `paper_anchor` 指向正文相邻段落；实验型任务还要关联真实实验。验证结果必须写出解释和决策影响。

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
2. `modeling`：文献适用性已判断，必需候选已核验；适用时多模型与融合方案已登记；公式/定义、参数血缘、约束与验证方案已确认。
3. `computation`：代码运行、实验记录、结果文件、可行性检查及模型修订复核已通过。
4. `paper`：结论—证据矩阵、模型评价、引用台账及双向引用、排版、PDF视觉检查和提交规则已通过。

每个门包含 `status` 与 `checks`，`checks` 至少一项。门的 `status` 只有 `pending` 和 `passed` 两个取值，不要复用小问的 `in_progress` 或 `blocked`：门只回答"是否已经通过"。普通结构校验要求前三门通过；论文门可以暂留 `pending`（只报警告）。最终交付校验 `validate_project.py --final` 要求四门全部通过。

## 小问状态 `status`

- 契约未完成：`pending`。
- 已建模或正在实验：`in_progress`。
- 计算与论文证据全部闭环：`complete`。
- 外部数据、软件或授权确实不可得：`blocked`，在发现记录中写明原因。

`blocked` 是过程中的诚实状态，不是可交付状态。最终交付校验要求所有小问为 `complete`，因此在提交前必须把每个 `blocked` 小问收敛：改用可得数据实现一个口径更弱但完整的方案，或按题面允许的范围重新界定该小问的验收标准，然后在契约与发现记录中留下这次降级的理由和影响。若确实无法收敛，说明该小问不能作为已完成成果提交，此时应向用户说明，而不是把状态改成 `complete` 掩盖缺口。

## 验证状态 `validation`

除了逐条登记的 `validation_methods`，小问清单还有一个汇总对象 `validation`，含 `status` 与 `checks`。`status` 必须改写成 `passed` 该小问才算完成——它表示本小问的验证结论已经人工确认，`checks` 记录实际确认了哪些内容。初始化写入的 `pending` 是占位值。

禁止为了通过校验虚构实验、证据或质量门。不能通过的结论应标为 `qualified` 或 `rejected`，而不是修改原始结果。

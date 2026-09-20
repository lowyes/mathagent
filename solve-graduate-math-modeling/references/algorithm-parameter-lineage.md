# 方法定义与参数血缘契约

每次首次使用方法时覆盖下列适用信息；这些是完整性检查项，不代表固定段落或小标题。新版清单使用 `methods`，旧项目的 `algorithms` 继续兼容。流程图和伪代码按 `representations` 选择，不是所有核心方法的固定附件。

## 1. 使用目的

写明方法解决哪个题面要求、输入粒度、输出粒度和接受标准。预测任务说明基线不足及新增能力；确定性规则或直接检验不强制构造基线。

## 2. 核心公式

给出实际实现所对应的目标函数、损失函数、递推式、概率模型、检验统计量或决策规则。软件函数调用不能替代数学表达或明确操作定义。若实现使用简化或修改版本，正文必须与代码一致。

## 3. 符号与单位

在公式首次使用前定义集合、索引、变量、参数、单位和取值域。不同量纲相加前说明归一化或无量纲化方式。

## 4. 参数适用性与来源表

先声明 `parameter_applicability`。有待估、待选或会改变结论的参数时取 `required` 并填写来源链；方法没有此类参数时取 `not_required`，填写 `parameter_reason` 且保持 `parameters: []`。题面阈值仍需在正文定义并追踪，不因“无需调参”而省略。

机器清单保留完整血缘字段；正文只展示评委理解和复核当前模型真正需要的信息。正文参数表通常压缩为：

| 符号 | 含义 | 取值/单位 | 确定依据 |
|---|---|---|---|
| $\lambda$ | 正则强度 | 10，无量纲 | 五折滚动验证平均 WMAPE 最小 |
| $\hat N_t$ | 日客流预测 | 逐日值，人/日 | 上游锁定预测表的 `diner_count` 字段 |
| $b$ | 损耗缓冲 | 5%--15% | 以8%为基准的情景扫描 |

对改变结论的关键参数，正文“确定依据”仍须可定位到题面条款、上游文件与字段、原始数据统计过程、真实文献或校准结果，不得只写“经验值”。完整的 `source_type`、源文件、转换、结果字段与 `downstream_use` 保存在 `小问清单.json`，供机器审计和附录复核，不把八列内部台账原样搬进正文。

清单里每个参数使用以下六个字段，由 `scripts/validate_project.py` 强制校验；“含义”由正文说明，“标定/转换”并入规则或来源描述：

| 信息项 | 清单字段 |
|---|---|
| 符号 | `symbol` |
| 含义 | 只写在论文里，清单不登记 |
| 数值或规则 | `value_or_rule` |
| 单位 | `unit` |
| 来源类型 | `source_type` |
| 精确来源 | `source` |
| 标定/转换 | 并入 `value_or_rule` 或 `source` 的描述 |
| 下游用途 | `downstream_use` |

论文中的符号写成 LaTeX 数学式（`$\lambda$`），清单中的 `symbol` 写成可检索的纯文本（`lambda`）；单位在论文中用中文（`无量纲`），清单中可用中文或英文，但同一小问内保持一致。

## 5. 求解与输出

说明训练/求解顺序、数据切分、随机种子、停止条件、求解器状态、fallback，以及公式变量对应的结果文件字段。

## 6. 连贯性检查

逐条核对：

1. 每个公式参数在参数表中出现。
2. 每个参数来源真实存在且单位一致。
3. 上游字段经过的聚合、缩放或单位转换已写出。
4. 当前输出说明被哪个下游问题消费。
5. 上游误差、覆盖率或质量标记已传播。
6. 论文公式、代码实现、清单登记和结果字段四者一致。

在每个 `小问清单.json` 中登记：

```json
{
  "methods": [
    {
      "id": "Q2-M1",
      "name": "算法名",
      "purpose": "对应任务",
      "method_type": "iterative_algorithm",
      "representations": ["formula", "pseudocode", "flowchart", "result_table"],
      "formula_reference": "论文节号或公式标签",
      "is_core": true,
      "core_reason": "产生全文关键结论并包含迭代与模型选择过程",
      "pseudocode_anchor": "alg:q2-core",
      "pseudocode_reference": "算法2",
      "flowchart_source": "求解/问题二/小问1/代码/绘制核心算法流程图.py",
      "flowchart_file": "求解/问题二/小问1/图/核心算法流程图.pdf",
      "flowchart_reference": "正文图6",
      "parameter_applicability": "required",
      "parameters": [
        {
          "symbol": "lambda",
          "value_or_rule": "10",
          "unit": "dimensionless",
          "source_type": "calibration",
          "source": "五折滚动验证平均 WMAPE 最小",
          "downstream_use": "模型训练"
        }
      ]
    }
  ]
}
```

小问完成时 `methods` 不得为空；纯规则、统计判定或管理建议也应登记其操作定义、证据映射与结果载体，而不是假装成复杂算法。

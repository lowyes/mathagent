# 真实文献与方法筛选

当 `literature_review.applicability` 为 `required` 或 `conditional` 时使用本筛选。目标不是追逐“最新”或“最复杂”，而是从真实、可核验且与赛题数据条件相容的研究中形成候选集，再用与任务匹配的验证决定采用、拒绝或暂缓。题面已完整给出确定规则时可以登记 `not_required` 及理由，不为形式完整虚构引用。

## 检索与核验

1. 按“业务对象 + 小问任务 + 方法类别 + forecasting/optimization”等组合检索 Google Scholar、Crossref、出版社页面和作者公开稿。
2. 优先核验出版社论文页、DOI 落地页、期刊/会议官网或作者机构仓储。搜索摘要只能用于发现线索，不能作为最终引文依据。
3. 主要小问在网络可用时形成足以覆盖“可靠基线、主要方法选择及关键替代方案”的候选证据集；候选数量服从真实决策需要，不为凑数添加无关论文。优先寻找直接研究相同业务场景的来源；没有直接文献时，明确标为相邻领域或方法迁移。
4. 不凭记忆填写题名、作者、年份、卷期、页码或 DOI。无法核验时将文献门标为 pending/blocked，禁止虚构引用。
5. “顶刊”“一区”等分区结论具有年份和口径依赖。除非已核验当年 JCR、中科院分区或赛事指定目录，否则使用“领域主流期刊”“高质量同行评议研究”等可证实表述。

## 三层相关性

- `direct`：研究对象、预测/优化目标和数据粒度与赛题基本一致。
- `adjacent`：业务或数据结构相近，可迁移评估设计、特征、约束或算法。
- `method`：仅方法本身有价值，必须额外论证为何适用于本题。

期刊声望不能代替相关性。与当前任务直接匹配的朴素研究，通常比数据条件不匹配的复杂通用模型更有迁移价值。

## 候选记录

每条 `literature_candidates` 至少包含：

```json
{
  "id": "L01",
  "title": "论文题名",
  "year": 2024,
  "venue": "期刊或会议",
  "doi_or_url": "10.xxxx/xxxx 或正式论文 URL",
  "verification_url": "https://出版社或官方页面",
  "problem_match": "与本小问相同和不同之处",
  "directness": "direct",
  "method": "论文采用的核心方法",
  "formula_or_method": "需要迁移的公式、模型结构或实验设计",
  "required_data": "训练长度、字段、频率、层级、标签及外生变量",
  "available_fields": "本题实际拥有及缺失的字段",
  "transfer_decision": "为何采用、仅基准测试、拒绝或等待数据",
  "status": "benchmarked",
  "used_by_methods": ["本项目方法名"]
}
```

`status` 只能为：

- `adopted`：已迁移进入最终方案；
- `benchmarked`：已在统一验证框架下测试，但未必最终采用；
- `rejected`：因效果、假设、复杂度或解释性不合适而拒绝；
- `data_blocked`：文献方法有价值，但题目缺少其必要数据。

`adopted` 和 `benchmarked` 必须指向清单中真实存在的方法名；实验型任务还要由实验记录覆盖。拒绝与数据受限的候选也要保留，防止后续重复试错或把不可实现的方法写成创新点。

`used_by_methods` 里的名称逐个比对本小问 `methods` 的 `name`，拼写不一致会直接报错；旧项目的 `algorithm`、`used_by_algorithms` 与 `algorithms` 继续兼容。`adopted` 和 `benchmarked` 的关联不允许留空。`year` 必须是整数（不是 `"2024"` 这样的字符串），`verification_url` 必须以 `http://` 或 `https://` 开头，`directness` 和 `status` 必须取本文列出的枚举值。

“候选证据足以支撑当前方法选择”和“优先包含 `direct` 来源”是人工写作要求，不是简单数量门。校验器只在文献门为 `required` 且候选为空时报错，在必需筛选中没有 `direct` 候选时给出警告；`conditional` 可以暂时为空但会提示复核。校验通过不等于筛选充分，仍需人工说明候选集为何足以支持采用或拒绝决定。

## 从论文提取什么

至少提取研究对象、样本数量/时间跨度、预测跨度、输入特征、损失或目标函数、约束、数据划分、基线、评价指标、主要局限。只摘录算法名称不算完成筛选。

将论文方法转入本题时，必须重新写出本题符号下的公式或操作定义，并在 `methods.parameters` 中追踪适用参数来源。论文中的超参数、成本系数或阈值不能无条件照搬；应通过本题数据校准、敏感性分析或明确的场景假设获得。

所有候选必须在相同时间切分、相同预测窗口、相同目标与指标下比较。时间序列禁止随机打乱；优化方法必须比较可行性、目标值、稳定性和计算成本。复杂模型若没有显著且稳定改进，不因“论文先进”而采用。

## 证据链要求

筛选结果应形成一条连续证据链：真实论文提出候选与条件 → 本题字段审计判断可迁移性 → 本题公式和参数血缘 → 无泄漏实验 → 最终采用或拒绝 → 论文中如实表述边界。

## 论文级引用台账

`literature_candidates` 管理方法候选，`methods.parameters` 管理参数来源；正式论文还需在 `paper_workflow.citation_ledger` 汇总实际进入正文的外部主张。不要复制整套文献记录，只登记正文真正引用的主张、引用键、核验来源和使用位置：

```json
{
  "id": "S01",
  "claim": "某工艺参数范围来自官方标准",
  "claim_role": "core",
  "source_type": "standard",
  "authority": "primary",
  "citation_key": "standard2025",
  "verification_source": "标准正式页面、DOI或可定位的官方文件",
  "used_in": ["问题三式(18)", "表6参数来源"],
  "verified": true
}
```

`source_type` 可取 `official_rule`、`standard`、`dataset`、`primary_research`、`application_research`、`book`、`technical_document`、`web_resource` 或 `software`；`authority` 可取 `primary`、`peer_reviewed`、`authoritative_secondary` 或 `discovery_only`。博客、论坛和普通网页可用于发现线索，但 `discovery_only` 不得支撑 `core` 主张。

最终检查同时核对四组键：正文 `\cite{}`、`citation_ledger.citation_key`、`\bibitem{}` 或 `.bib` 条目、参考文献表实际条目。四者应双向一致；无正文引用的条目删除，有正文引用但未定义或未核验的条目补齐。引用格式服从当届官方规范，台账不把某一种期刊格式永久硬编码进 Skill。

# 核心算法伪代码

仅当方法在 `representations` 中声明 `pseudocode` 时应用本规范。伪代码用于迭代、搜索、递推或非显然执行逻辑；闭式公式和确定性规则不为形式完整强制添加。核心 `iterative_algorithm` 必须同时声明伪代码与流程图。

## 适用范围

全文通常只将 1--3 个承担关键结果、最终决策或主要方法贡献的方法标为核心。只有声明 `pseudocode` 的方法需要提供伪代码；辅助方法、常规数据清洗、单个统计量和可由一条闭式公式完整表达的步骤不机械增加伪代码。

伪代码用于精确说明“怎样执行”，图形流程图用于快速展示“整体怎样流动”。二者相互校验，不能彼此替代。

## 必含结构

每个已声明的算法伪代码必须包含：

1. 与正文一致的算法名称和编号；
2. 输入数据、上游字段、关键参数及必要单位；
3. 输出变量、结果字段或方案；
4. 初始化和真实预处理；
5. 与核心公式对应的计算、更新或决策步骤；
6. 实际存在的循环、条件分支、队列或递归；
7. 停止、收敛、可行性判断和 fallback；
8. 返回值及其下游用途。

不得把 Python、MATLAB、SQL 或求解器 API 原样粘贴进正文。使用集合、索引和数学变量表达逻辑；函数名只在其具有明确数学或业务含义时保留。没有循环、分支或 fallback 时不要虚构复杂结构。

## 一致性要求

- 输入、输出和参数名称与正文符号表及参数来源表一致。
- 每个关键计算步骤能对应公式、约束、损失函数或决策规则。
- 循环、分支、更新和终止条件与真实代码一致。
- 输出名称与结果文件字段和下游交接一致。
- 伪代码、图形流程图和文字步骤采用相同的处理顺序；发现不一致时以实际运行代码和结果证据为准，并同步修正文稿。

## LaTeX 写法

模板使用 `algorithm2e`，自动生成标题、边框和行号。示例：

```latex
\begin{algorithm}[H]
  \caption{约束加权模型融合}
  \label{alg:q2-constrained-ensemble}
  \KwIn{训练折预测 $\hat y_{tm}$，真实值 $y_t$，成员集合 $\mathcal M$}
  \KwOut{融合权重 $\boldsymbol w$，样本外预测 $\hat y_t^{\mathrm{ens}}$}
  初始化 $w_m\gets 1/|\mathcal M|$\;
  \ForEach{训练期内部验证折 $k$}{
    仅使用第 $k$ 折训练段拟合各成员模型\;
    保存验证段样本外预测\;
  }
  求解 $\min_{\boldsymbol w}L(\boldsymbol w)$，满足
  $w_m\ge 0$ 且 $\sum_m w_m=1$\;
  \If{求解器未返回可行解}{
    令 $w_m\gets 1/|\mathcal M|$ 作为 fallback\;
  }
  计算 $\hat y_t^{\mathrm{ens}}\gets\sum_mw_m\hat y_{tm}$\;
  \Return{$\boldsymbol w$ 与 $\hat y_t^{\mathrm{ens}}$}\;
\end{algorithm}
```

正文在算法前说明它解决的当前任务，在算法后解释关键分支、终止或 fallback，并指向真实代码入口和结果文件。伪代码较长时拆分为有明确调用关系的主过程和子过程，不缩小到无法阅读。

## 清单字段

声明伪代码的方法登记：

```json
{
  "is_core": true,
  "pseudocode_anchor": "alg:q2-constrained-ensemble",
  "pseudocode_reference": "算法2"
}
```

`pseudocode_anchor` 必须对应正文 `algorithm` 环境内部的 `\label{...}`。校验器同时检查该环境是否包含 `\caption`、`\KwIn` 和 `\KwOut`。未声明 `pseudocode` 的方法将两个字段留空。

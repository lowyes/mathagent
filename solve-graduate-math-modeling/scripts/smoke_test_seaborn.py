#!/usr/bin/env python3
"""Generate a publication-style Chinese Seaborn figure as an environment smoke test."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, help="Output PNG path")
    args = parser.parse_args()

    values = {
        "季节基线": [0.196, 0.188, 0.203, 0.191, 0.199],
        "随机森林": [0.154, 0.148, 0.161, 0.151, 0.157],
        "梯度提升": [0.141, 0.136, 0.145, 0.139, 0.143],
        "融合模型": [0.132, 0.128, 0.136, 0.130, 0.134],
    }
    data = pd.DataFrame(
        [(model, fold + 1, score) for model, scores in values.items() for fold, score in enumerate(scores)],
        columns=["模型", "验证折", "WMAPE"],
    )

    sns.set_theme(style="whitegrid", context="paper", palette="colorblind")
    plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"], "axes.unicode_minus": False})
    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    sns.boxplot(data=data, x="模型", y="WMAPE", hue="模型", legend=False, width=0.55, ax=ax)
    sns.stripplot(data=data, x="模型", y="WMAPE", color="#273142", size=4.5, jitter=0.12, ax=ax)
    ax.set_title("候选模型交叉验证误差比较（示例）")
    ax.set_xlabel("")
    ax.set_ylabel("加权平均绝对百分比误差（WMAPE）")
    ax.spines[["top", "right"]].set_visible(False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(args.output.resolve())


if __name__ == "__main__":
    main()

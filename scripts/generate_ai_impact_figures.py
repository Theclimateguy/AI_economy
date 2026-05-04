from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output" / "figures"

FIGSIZE = (14, 9)
TARGET_PIXELS = (1400, 900)
SAVE_DPI = 300

CLASS_COLORS = {
    "software": "#7C3AED",
    "hybrid": "#EA580C",
    "hardware": "#0891B2",
}

SCENARIO_COLORS = {
    "Fast": "#2563EB",
    "Base": "#16A34A",
    "Friction": "#DC2626",
}

TASK_SHIFT_COLORS = {
    "task_creating": "#059669",
    "task_displacing": "#DC2626",
}

LINESTYLES = {
    "Fast": "-",
    "Base": "--",
    "Friction": ":",
}

CLASS_LABELS = {
    "software": "Software",
    "hybrid": "Hybrid",
    "hardware": "Hardware",
}

SECTOR_LABELS = {
    "B": "Mining",
    "C": "Manufactur.",
    "C_mach": "Machinery",
    "DE": "Energy",
    "F": "Constr.",
    "G": "Trade",
    "H": "Transport",
    "J": "IT",
    "K": "Finance",
    "M": "Prof.Svcs",
}

SCENARIO_ORDER = ["Fast", "Base", "Friction"]


def configure_style() -> None:
    """Apply the shared figure style contract."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.sans-serif": ["DejaVu Sans", "sans-serif"],
            "axes.titlesize": 16,
            "axes.titleweight": "bold",
            "axes.labelsize": 13,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 11,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def read_csv(path: Path) -> pd.DataFrame:
    """Load a CSV and normalize column names for minor schema variation."""
    df = pd.read_csv(path)
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df


def style_axes(ax: plt.Axes, grid_axis: str = "y") -> None:
    """Remove extra spines and apply a light grid."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#111827")
    ax.spines["bottom"].set_color("#111827")
    ax.grid(axis=grid_axis, color="#E5E7EB", linewidth=0.7)
    ax.tick_params(axis="both", labelrotation=0)
    ax.set_axisbelow(True)


def save_figure(fig: plt.Figure, output_path: Path) -> None:
    """Save with tight bbox, then normalize to exact output pixels and dpi metadata."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(".tmp.png")

    fig.tight_layout()
    fig.savefig(temp_path, dpi=SAVE_DPI, bbox_inches="tight")
    plt.close(fig)

    with Image.open(temp_path) as image:
        resized = image.resize(TARGET_PIXELS, Image.Resampling.LANCZOS)
        resized.save(output_path, dpi=(SAVE_DPI, SAVE_DPI))

    temp_path.unlink(missing_ok=True)
    relative = output_path.relative_to(ROOT).as_posix()
    print(f"Saved: {relative}")


def ensure_adjust_text():
    """Import adjustText, installing it inline if missing."""
    try:
        from adjustText import adjust_text
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "adjusttext", "-q"])
        from adjustText import adjust_text

    return adjust_text


def add_direct_labels(ax: plt.Axes, end_points: pd.DataFrame, x_text: float) -> None:
    """Place end labels with a simple collision-avoidance pass."""
    labels = end_points.sort_values("adaptation").reset_index(drop=True).copy()
    min_gap = 0.035
    y_positions = labels["adaptation"].to_numpy(dtype=float).copy()

    for idx in range(1, len(y_positions)):
        if y_positions[idx] - y_positions[idx - 1] < min_gap:
            y_positions[idx] = y_positions[idx - 1] + min_gap

    upper_bound = 0.98
    lower_bound = 0.02
    if len(y_positions):
        overflow = y_positions[-1] - upper_bound
        if overflow > 0:
            y_positions -= overflow
        underflow = lower_bound - y_positions[0]
        if underflow > 0:
            y_positions += underflow

    for (_, row), y_adj in zip(labels.iterrows(), y_positions):
        x_end = float(row["year"])
        y_end = float(row["adaptation"])
        text = f"{CLASS_LABELS[row['class_id']]} · {row['scenario']}"
        color = CLASS_COLORS[row["class_id"]]

        if abs(y_adj - y_end) > 1e-3:
            ax.plot([x_end, x_text - 0.05], [y_end, y_adj], color=color, linewidth=0.8, alpha=0.6)

        ax.text(
            x_text,
            y_adj,
            text,
            fontsize=10,
            color=color,
            va="center",
            ha="left",
            path_effects=[pe.withStroke(linewidth=3, foreground="white")],
        )


def load_labour_share_proxy_if_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Recover labour_share_proxy from a companion processed table when absent."""
    if "labour_share_proxy" in df.columns:
        return df

    fallback_paths = [
        DATA_DIR / "russia_ai_sector_impact_summary_2024.csv",
        DATA_DIR / "russia_sector_baseline_2024.csv",
    ]

    for path in fallback_paths:
        if path.exists():
            fallback = read_csv(path)
            if "labour_share_proxy" in fallback.columns:
                merged = df.merge(
                    fallback[["sector_id", "labour_share_proxy"]],
                    on="sector_id",
                    how="left",
                )
                if merged["labour_share_proxy"].notna().all():
                    return merged

    raise KeyError("Could not resolve labour_share_proxy for Figure 2.")


def make_fig1() -> None:
    """AI Diffusion by technology class and scenario."""
    df = read_csv(DATA_DIR / "ai_diffusion_paths_2025_2035.csv")
    grouped = (
        df.groupby(["scenario", "class_id", "year"], as_index=False)["adaptation"]
        .mean()
        .sort_values(["class_id", "scenario", "year"])
    )

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=SAVE_DPI)

    for class_id in ["hardware", "hybrid", "software"]:
        for scenario in SCENARIO_ORDER:
            subset = grouped[(grouped["class_id"] == class_id) & (grouped["scenario"] == scenario)]
            ax.plot(
                subset["year"],
                subset["adaptation"],
                color=CLASS_COLORS[class_id],
                linestyle=LINESTYLES[scenario],
                linewidth=2.4,
            )

    end_points = grouped[grouped["year"] == 2035][["scenario", "class_id", "year", "adaptation"]]
    add_direct_labels(ax, end_points, x_text=2035.7)

    ax.axhline(0.5, color="#9CA3AF", linestyle="--", linewidth=1.1)
    ax.text(
        2025.1,
        0.515,
        "50% adoption",
        color="#6B7280",
        fontsize=10,
        ha="left",
        va="bottom",
    )

    scenario_handles = [
        Line2D([0], [0], color="#374151", linestyle=LINESTYLES[scenario], linewidth=2.4, label=scenario)
        for scenario in SCENARIO_ORDER
    ]
    ax.legend(
        handles=scenario_handles,
        loc="upper left",
        ncol=3,
        frameon=False,
        title=None,
    )

    ax.set_xlim(2025, 2036.9)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Year")
    ax.set_ylabel("AI Adoption Rate A(t)")
    ax.set_title("AI Diffusion by Technology Class & Scenario (2025–2035)")
    style_axes(ax, grid_axis="y")
    save_figure(fig, OUTPUT_DIR / "fig1_diffusion_curves.png")


def make_fig2() -> None:
    """Task-shock matrix for sector labour-share exposure."""
    df = read_csv(DATA_DIR / "russia_ai_sector_scenarios.csv")
    df = load_labour_share_proxy_if_missing(df)

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=SAVE_DPI)

    for task_shift, subset in df.groupby("dominant_task_shift"):
        ax.scatter(
            subset["delta_sl_core"],
            subset["labour_share_proxy"],
            s=120,
            color=TASK_SHIFT_COLORS[task_shift],
            edgecolors="white",
            linewidths=0.9,
            alpha=0.92,
            label=task_shift,
            zorder=3,
        )

    for _, row in df.iterrows():
        ax.annotate(
            row["sector_id"],
            (row["delta_sl_core"], row["labour_share_proxy"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=10,
            ha="left",
            va="bottom",
            color="#111827",
            path_effects=[pe.withStroke(linewidth=3, foreground="white")],
        )

    xmin = min(df["delta_sl_core"].min() - 0.03, -0.22)
    xmax = max(df["delta_sl_core"].max() + 0.03, 0.08)
    ymin = max(0.0, df["labour_share_proxy"].min() - 0.06)
    ymax = min(1.0, df["labour_share_proxy"].max() + 0.08)

    ax.axvline(0, color="#9CA3AF", linestyle="--", linewidth=1.1, zorder=1)
    ax.axhline(0.5, color="#9CA3AF", linestyle="--", linewidth=1.1, zorder=1)
    ax.text(0.003, ymax - 0.01, "No shock", color="#6B7280", fontsize=10, ha="left", va="top")
    ax.text(xmax - 0.002, 0.512, "High labour share", color="#6B7280", fontsize=10, ha="right", va="bottom")

    quadrant_positions = {
        "Q1": ((xmin + 0) / 2, (0.5 + ymax) / 2, "High exposure\nhigh labour share"),
        "Q2": ((0 + xmax) / 2, (0.5 + ymax) / 2, "Task creating\nhigh labour share"),
        "Q3": ((xmin + 0) / 2, (ymin + 0.5) / 2, "Displacement\nlow labour share"),
        "Q4": ((0 + xmax) / 2, (ymin + 0.5) / 2, "Task creating\nlow labour share"),
    }
    for x_pos, y_pos, text in quadrant_positions.values():
        ax.text(
            x_pos,
            y_pos,
            text,
            fontsize=10,
            color="#9CA3AF",
            fontstyle="italic",
            ha="center",
            va="center",
        )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=TASK_SHIFT_COLORS[key],
            markeredgecolor="white",
            markersize=10,
            label=key,
        )
        for key in ["task_creating", "task_displacing"]
    ]
    ax.legend(handles=legend_handles, loc="lower left", frameon=False)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("ΔLabour Share (Core scenario)")
    ax.set_ylabel("Labour Share 2024")
    ax.set_title("Task-Shock Matrix: Labour Share vs AI Displacement Risk")
    style_axes(ax, grid_axis="y")
    save_figure(fig, OUTPUT_DIR / "fig2_task_shock_matrix.png")


def make_fig3() -> None:
    """Base-scenario net return on new capital by sector."""
    df = read_csv(DATA_DIR / "ai_capital_return_sector_summary.csv")
    base = df[df["scenario"] == "Base"].copy()
    base = base.sort_values("net_return_on_new_capital_cf_2035", ascending=True)
    base["sector_label"] = base["sector_id"].map(SECTOR_LABELS)

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=SAVE_DPI)
    colors = base["class_id"].map(CLASS_COLORS)
    bars = ax.barh(
        base["sector_label"],
        base["net_return_on_new_capital_cf_2035"],
        color=colors,
        edgecolor="none",
        height=0.72,
    )

    pad = base["net_return_on_new_capital_cf_2035"].max() * 0.015
    for bar, value in zip(bars, base["net_return_on_new_capital_cf_2035"]):
        y_pos = bar.get_y() + bar.get_height() / 2
        ax.text(
            value + pad,
            y_pos,
            f"{value:.0f}x",
            fontsize=11,
            ha="left",
            va="center",
            color="#111827",
        )

    ax.axvline(1, color="#9CA3AF", linestyle="--", linewidth=1.1)
    ax.text(1.2, len(base) - 0.4, "Break-even", color="#6B7280", fontsize=10, ha="left", va="bottom")
    ax.text(
        0.98,
        0.05,
        "Colors: purple=software · orange=hybrid · blue=hardware",
        transform=ax.transAxes,
        fontsize=10,
        ha="right",
        va="bottom",
        color="#4B5563",
    )

    ax.set_xlim(0, base["net_return_on_new_capital_cf_2035"].max() * 1.15)
    ax.set_xlabel("Net RONC (×)")
    ax.set_ylabel("")
    ax.set_title("Net Return on New AI Capital by Sector — Base 2035")
    ax.invert_yaxis()
    style_axes(ax, grid_axis="x")
    save_figure(fig, OUTPUT_DIR / "fig3_net_ronc_base.png")


def make_fig4() -> None:
    """Base-scenario capital allocation map."""
    df = read_csv(DATA_DIR / "ai_capital_return_sector_summary.csv")
    base = df[df["scenario"] == "Base"].copy()
    adjust_text = ensure_adjust_text()

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=SAVE_DPI)

    texts = []
    for _, row in base.iterrows():
        marker = "o" if pd.notna(row["net_payback_year_cf"]) else "X"
        ax.scatter(
            row["cumulative_delta_k_need_bn_rub"],
            row["net_return_on_new_capital_cf_2035"],
            s=180,
            color=CLASS_COLORS[row["class_id"]],
            marker=marker,
            edgecolors="white",
            linewidths=1.0,
            alpha=0.95,
            zorder=3,
        )
        texts.append(
            ax.text(
                row["cumulative_delta_k_need_bn_rub"] + 8,
                row["net_return_on_new_capital_cf_2035"] + 1.2,
                SECTOR_LABELS[row["sector_id"]],
                fontsize=10,
                ha="left",
                va="bottom",
                color="#111827",
            )
        )

    ymax = base["net_return_on_new_capital_cf_2035"].max() * 1.12
    xmax = base["cumulative_delta_k_need_bn_rub"].max() * 1.12
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)

    trap_width = max(xmax - 400, 0)
    trap_height = max(min(5, ymax) - 0, 0)
    if trap_width > 0 and trap_height > 0:
        rect = Rectangle((400, 0), trap_width, trap_height, facecolor="#DC2626", alpha=0.08, edgecolor="none")
        ax.add_patch(rect)
        ax.text(
            400 + trap_width / 2,
            min(2.7, trap_height * 0.55),
            "CapEx trap zone",
            color="#B91C1C",
            fontsize=10,
            ha="center",
            va="center",
        )

    try:
        adjust_text(
            texts,
            ax=ax,
            expand=(1.08, 1.16),
            force_points=0.4,
            force_text=0.3,
        )
    except Exception:
        pass

    ax.axhline(1, color="#9CA3AF", linestyle="--", linewidth=1.1)
    ax.text(xmax - 5, 1.15, "Break-even", color="#6B7280", fontsize=10, ha="right", va="bottom")

    legend_handles: list[Line2D] = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=CLASS_COLORS[class_id],
            markeredgecolor="white",
            markersize=10,
            label=CLASS_LABELS[class_id],
        )
        for class_id in ["software", "hybrid", "hardware"]
    ]
    legend_handles.extend(
        [
            Line2D([0], [0], marker="o", color="#374151", linestyle="None", markersize=9, label="Payback by 2035"),
            Line2D([0], [0], marker="X", color="#374151", linestyle="None", markersize=9, label="No payback by 2035"),
        ]
    )
    ax.legend(handles=legend_handles, loc="upper left", frameon=False, ncol=2)

    ax.set_xlabel("Cumulative AI CapEx 2025–2035 (bn rub)")
    ax.set_ylabel("Net RONC by 2035 (×)")
    ax.set_title("Capital Allocation Map — Base Scenario 2035")
    style_axes(ax, grid_axis="y")
    save_figure(fig, OUTPUT_DIR / "fig4_capex_vs_ronc.png")


def make_fig5() -> None:
    """Grouped payback-year chart by sector and scenario."""
    df = read_csv(DATA_DIR / "ai_capital_return_sector_summary.csv")
    pivot = df.pivot(index="sector_id", columns="scenario", values="net_payback_year_cf")

    sector_order = ["B", "DE", "H", "F", "C", "J", "K", "M"]
    pivot = pivot.reindex(sector_order)

    x = np.arange(len(sector_order))
    width = 0.24
    offsets = {
        "Fast": -width,
        "Base": 0.0,
        "Friction": width,
    }

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=SAVE_DPI)

    for scenario in SCENARIO_ORDER:
        values = pivot[scenario]
        heights = values.fillna(2036.0)
        bars = ax.bar(
            x + offsets[scenario],
            heights,
            width=width,
            color=SCENARIO_COLORS[scenario],
            edgecolor="none",
            label=scenario,
        )
        for bar, original_value in zip(bars, values):
            if pd.isna(original_value):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    2036.18,
                    "N/A",
                    fontsize=10,
                    ha="center",
                    va="bottom",
                    color="#6B7280",
                )

    ax.axhline(2035, color="#9CA3AF", linestyle="--", linewidth=1.1)
    ax.text(len(sector_order) - 0.35, 2035.15, "2035 horizon", color="#6B7280", fontsize=10, ha="right", va="bottom")

    ax.set_xticks(x, [SECTOR_LABELS[sector] for sector in sector_order])
    ax.set_ylim(2024.5, 2037.5)
    ax.set_yticks(np.arange(2025, 2038, 2))
    ax.set_xlabel("")
    ax.set_ylabel("Payback Year")
    ax.set_title("AI Investment Net Payback Year — Base / Fast / Friction")
    ax.legend(loc="upper left", frameon=False)
    style_axes(ax, grid_axis="y")
    save_figure(fig, OUTPUT_DIR / "fig5_payback_year.png")


def make_fig6_io_heatmap() -> None:
    """Supplier-recipient heatmap for indirect VA effects."""
    path = DATA_DIR / "io_indirect_decomposition.csv"
    if not path.exists():
        return
    df = read_csv(path)
    base = df[
        (df["table_year"] == 2019)
        & (df["scenario"] == "Base")
        & (df["throttle_scenario"] == "BaseThrottle")
    ].copy()
    if base.empty:
        return
    order = [sector for sector in SECTOR_LABELS if sector in set(base["supplier_sector"])]
    matrix = base.pivot_table(
        index="supplier_sector",
        columns="recipient_sector",
        values="indirect_va_effect_bn_rub",
        aggfunc="sum",
        fill_value=0.0,
    ).reindex(index=order, columns=order, fill_value=0.0)

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=SAVE_DPI)
    im = ax.imshow(matrix.to_numpy(), cmap="Blues", aspect="auto")
    ax.set_xticks(np.arange(len(order)), [SECTOR_LABELS[s] for s in order], rotation=35, ha="right")
    ax.set_yticks(np.arange(len(order)), [SECTOR_LABELS[s] for s in order])
    ax.set_xlabel("Recipient sector receiving direct AI impulse")
    ax.set_ylabel("Supplier sector with induced VA")
    ax.set_title("IO Indirect VA Decomposition — Base / BaseThrottle, 2019 table")
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Indirect VA effect, bn rub")
    save_figure(fig, OUTPUT_DIR / "fig6_io_indirect_heatmap.png")


def main() -> None:
    """Generate the five publication figures for the AI-sector impact study."""
    configure_style()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    make_fig1()
    make_fig2()
    make_fig3()
    make_fig4()
    make_fig5()
    make_fig6_io_heatmap()


if __name__ == "__main__":
    main()

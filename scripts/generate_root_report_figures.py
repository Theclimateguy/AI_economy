"""Regenerate root-level PNG figures referenced by ai-economy-analytical-note.md.

Figures produced (all under repo root or output/):
  - ai-economy-sector-shift.png   — 10-sector Δ доли ВДС, п.п. (2035)
  - ai-economy-macro-bridge.png   — Прямой vs IO ВДС/занятость (2035)
  - output/io_indirect_heatmap.png — IO heatmap (mirrors output/figures/fig6_*)

The other root PNGs (diffusion-return, monte-carlo, welfare-quintiles) are
left as committed because their data has not changed in the 10-sector update.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output"

POSITIVE = "#0F6E78"
NEGATIVE = "#A93B4A"
DARK_POS = "#0E5159"
BG = "#FAF8F4"
GRID = "#E5E7EB"
TEXT = "#1F2937"

SECTOR_LABELS = {
    "K": "K Финансы",
    "M": "M Проф. услуги",
    "J": "J ИТ/связь",
    "DE": "DE Энергетика",
    "C_mach": "C_mach Машиностр.",
    "G": "G Торговля",
    "F": "F Строит.",
    "C": "C Обработка",
    "H": "H Транспорт",
    "B": "B Добыча",
}


def _style_axes(ax: plt.Axes, grid_axis: str = "x") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(TEXT)
    ax.spines["bottom"].set_color(TEXT)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)


def _configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 16,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
        }
    )


def _load_structure_base() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "russia_economy_structure_sector_summary.csv")
    return df[(df["scenario"] == "Base") & (df["throttle_scenario"] == "BaseThrottle")].copy()


def make_sector_shift() -> Path:
    base = _load_structure_base()
    base = base.sort_values("delta_va_share_pp_2035", ascending=False).reset_index(drop=True)
    base["label"] = base["sector_id"].map(SECTOR_LABELS)
    values = base["delta_va_share_pp_2035"].astype(float).to_numpy()
    labels = base["label"].tolist()

    fig, ax = plt.subplots(figsize=(12, 7.2), dpi=200)
    colors = [POSITIVE if v >= 0 else NEGATIVE for v in values]
    bars = ax.barh(range(len(values)), values, color=colors, edgecolor="none", height=0.7)
    ax.invert_yaxis()
    ax.set_yticks(range(len(values)))
    ax.set_yticklabels(labels)

    span = max(abs(values.min()), abs(values.max()))
    pad = span * 0.04
    for bar, value in zip(bars, values):
        y = bar.get_y() + bar.get_height() / 2
        if value >= 0:
            x = value + pad
            ha = "left"
        else:
            x = value - pad
            ha = "right"
        ax.text(
            x,
            y,
            f"{value:+.2f}",
            fontsize=11,
            fontweight="bold",
            ha=ha,
            va="center",
            color=TEXT,
        )

    ax.axvline(0, color=TEXT, linewidth=1.0)
    ax.set_xlim(-span * 1.25, span * 1.25)
    ax.set_xlabel("п.п. доли ВДС")

    fig.suptitle(
        "ИИ перераспределяет долю экономики от B/C/H/G/C_mach к K/M/J\n"
        "Δ доли ВДС, п.п., сценарий ИИ 2035 против контрфакта",
        fontsize=15,
        fontweight="bold",
        ha="center",
        y=0.98,
    )
    _style_axes(ax, grid_axis="x")
    fig.text(
        0.02,
        0.02,
        "Источник: расчеты репозитория AI_economy, таблица T11; базовый сценарий с ограничением внедрения, 2035.",
        fontsize=9,
        color="#4B5563",
    )

    output_path = ROOT / "ai-economy-sector-shift.png"
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"Saved: {output_path.relative_to(ROOT)}")
    return output_path


def make_macro_bridge() -> Path:
    """Direct vs IO-closure pair chart for VA% and employment, 2035 base scenario."""
    direct_va_pct = 4.27
    io_va_pct = 7.23
    direct_emp = -978
    io_emp = 373

    fig, axes = plt.subplots(1, 2, figsize=(13, 6.4), dpi=200)
    fig.patch.set_facecolor(BG)

    # Left panel: VA%
    ax = axes[0]
    bars = ax.bar(
        ["Прямой\nучет", "Частичное\nмежотраслевое\nзакрытие"],
        [direct_va_pct, io_va_pct],
        color=[POSITIVE, DARK_POS],
        edgecolor="none",
        width=0.55,
    )
    for bar, value in zip(bars, [direct_va_pct, io_va_pct]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.18,
            f"+{value:.2f}%",
            fontsize=13,
            fontweight="bold",
            ha="center",
            va="bottom",
            color=TEXT,
        )
    ax.set_ylim(0, max(direct_va_pct, io_va_pct) * 1.2)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title("Прирост ВДС к 2035, % к контрфакту", loc="left", fontsize=13)
    _style_axes(ax, grid_axis="y")

    # Right panel: employment
    ax = axes[1]
    values = [direct_emp, io_emp]
    colors = [NEGATIVE if v < 0 else POSITIVE for v in values]
    bars = ax.bar(
        ["Прямой\nучет", "Частичное\nмежотраслевое\nзакрытие"],
        values,
        color=colors,
        edgecolor="none",
        width=0.55,
    )
    for bar, value in zip(bars, values):
        offset = 30 if value >= 0 else -30
        va = "bottom" if value >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + offset,
            f"{value:+d}",
            fontsize=13,
            fontweight="bold",
            ha="center",
            va=va,
            color=TEXT,
        )
    ax.axhline(0, color=TEXT, linewidth=1.0)
    span = max(abs(min(values)), abs(max(values)))
    ax.set_ylim(-span * 1.45, span * 1.45)
    ax.set_title("Δ занятости к 2035, тыс. человек", loc="left", fontsize=13)
    _style_axes(ax, grid_axis="y")

    fig.suptitle(
        "Межотраслевые связи усиливают эффект по ВДС, но меняют знак занятости",
        fontsize=16,
        fontweight="bold",
        x=0.02,
        ha="left",
        y=0.98,
    )
    fig.text(
        0.02,
        0.02,
        "Источник: расчеты репозитория AI_economy, таблицы T1 и T13; базовый сценарий с ограничением внедрения, 2035.",
        fontsize=9,
        color="#4B5563",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    output_path = ROOT / "ai-economy-macro-bridge.png"
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"Saved: {output_path.relative_to(ROOT)}")
    return output_path


def mirror_io_heatmap() -> Path:
    src = OUTPUT_DIR / "figures" / "fig6_io_indirect_heatmap.png"
    dst = OUTPUT_DIR / "io_indirect_heatmap.png"
    if not src.exists():
        raise FileNotFoundError(
            f"{src} not found — run scripts/generate_ai_impact_figures.py first."
        )
    shutil.copyfile(src, dst)
    print(f"Saved: {dst.relative_to(ROOT)}")
    return dst


def main() -> None:
    _configure_style()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    make_sector_shift()
    make_macro_bridge()
    mirror_io_heatmap()


if __name__ == "__main__":
    main()

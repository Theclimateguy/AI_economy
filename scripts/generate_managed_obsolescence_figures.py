from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
RAW_WORLD_DIR = ROOT / "data" / "raw" / "world_tech"
DATA_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output" / "figures" / "managed_obsolescence"

OWID_URL = "https://ourworldindata.org/grapher/technology-adoption-by-households-in-the-united-states.csv"
OWID_PATH = RAW_WORLD_DIR / "owid_us_technology_adoption.csv"
CASES_PATH = RAW_WORLD_DIR / "managed_obsolescence_cases.csv"
DIFFUSION_BENCHMARK_PATH = DATA_DIR / "world_technology_diffusion_benchmarks.csv"

TECH_VALUE_COL = "Technology Diffusion (Comin and Hobijn (2004) and others)"

SECTOR_LABELS = {
    "B": "Mining",
    "C": "Manufacturing",
    "DE": "Energy & utilities",
    "F": "Construction",
    "H": "Transport",
    "J": "IT & comms",
    "K": "Finance",
    "M": "Professional svcs",
}

CLASS_COLORS = {
    "software": "#2563EB",
    "hybrid": "#D97706",
    "hardware": "#059669",
}

MECHANISM_COLORS = {
    "Physical lifetime standardization": "#DC2626",
    "Dynamic/style obsolescence": "#D97706",
    "Software capability throttling": "#2563EB",
    "Repair/access restriction": "#7C3AED",
    "Counter-policy": "#059669",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.sans-serif": ["DejaVu Sans", "sans-serif"],
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 9.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def style_axes(ax: plt.Axes, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#111827")
    ax.spines["bottom"].set_color("#111827")
    ax.grid(axis=grid_axis, color="#E5E7EB", linewidth=0.7)
    ax.set_axisbelow(True)


def save_figure(fig: plt.Figure, filename: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path.relative_to(ROOT).as_posix()}")


def ensure_owid_source() -> Path:
    RAW_WORLD_DIR.mkdir(parents=True, exist_ok=True)
    if OWID_PATH.exists():
        return OWID_PATH
    response = requests.get(OWID_URL, timeout=120)
    response.raise_for_status()
    OWID_PATH.write_bytes(response.content)
    return OWID_PATH


def first_crossing(df: pd.DataFrame, threshold: float) -> float:
    rows = df.sort_values("Year")
    above = rows.loc[rows[TECH_VALUE_COL].ge(threshold)]
    if above.empty:
        return np.nan
    return float(above.iloc[0]["Year"])


def build_diffusion_benchmark() -> pd.DataFrame:
    path = ensure_owid_source()
    df = pd.read_csv(path)
    selected = [
        "Electric power",
        "Automobile",
        "Radio",
        "Refrigerator",
        "Colour TV",
        "Internet",
        "Cellular phone",
        "Smartphone usage",
        "Social media usage",
    ]
    rows = df.loc[df["Entity"].isin(selected)].copy()
    rows[TECH_VALUE_COL] = pd.to_numeric(rows[TECH_VALUE_COL], errors="coerce")
    rows = rows.dropna(subset=[TECH_VALUE_COL])

    metrics = []
    for technology, group in rows.groupby("Entity"):
        y10 = first_crossing(group, 10.0)
        y50 = first_crossing(group, 50.0)
        y80 = first_crossing(group, 80.0)
        metrics.append(
            {
                "technology": technology,
                "year_10": y10,
                "year_50": y50,
                "year_80": y80,
                "years_10_to_80": y80 - y10 if np.isfinite(y10) and np.isfinite(y80) else np.nan,
                "first_year": int(group["Year"].min()),
                "last_year": int(group["Year"].max()),
                "max_observed_share_pct": float(group[TECH_VALUE_COL].max()),
            }
        )
    benchmark = pd.DataFrame(metrics).sort_values("year_10")
    benchmark.to_csv(DIFFUSION_BENCHMARK_PATH, index=False)
    return rows.merge(benchmark[["technology", "year_10"]], left_on="Entity", right_on="technology", how="left")


def make_world_s_curves(curves: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 7))
    palette = {
        "Electric power": "#0F766E",
        "Automobile": "#475569",
        "Radio": "#9333EA",
        "Refrigerator": "#0891B2",
        "Colour TV": "#DB2777",
        "Internet": "#2563EB",
        "Cellular phone": "#16A34A",
        "Smartphone usage": "#EA580C",
        "Social media usage": "#7C3AED",
    }
    for technology, group in curves.groupby("Entity"):
        if group["year_10"].isna().all():
            continue
        plotted = group.assign(year_since_10=group["Year"] - group["year_10"].iloc[0])
        plotted = plotted.loc[plotted["year_since_10"].between(0, 55)]
        ax.plot(
            plotted["year_since_10"],
            plotted[TECH_VALUE_COL],
            linewidth=2.2,
            color=palette.get(technology, "#111827"),
            label=technology,
        )

    ax.axhline(80, color="#9CA3AF", linestyle="--", linewidth=1)
    ax.axhline(50, color="#D1D5DB", linestyle=":", linewidth=1)
    ax.set_xlim(0, 58)
    ax.set_ylim(0, 105)
    ax.set_xlabel("Years after first reaching 10% adoption")
    ax.set_ylabel("Household / user adoption, %")
    ax.set_title("World Benchmark: Mass Technologies Usually Diffuse as S-Curves")
    ax.text(
        0,
        -0.28,
        "Source: OWID grapher, Technology Diffusion (Comin and Hobijn 2004 and others). US long-run series used as a benchmark, not a world panel.",
        transform=ax.transAxes,
        fontsize=9,
        color="#4B5563",
    )
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    style_axes(ax)
    save_figure(fig, "fig6_world_technology_s_curves.png")


def make_diffusion_speed_bars() -> None:
    benchmark = pd.read_csv(DIFFUSION_BENCHMARK_PATH)
    plot = benchmark.dropna(subset=["years_10_to_80"]).sort_values("years_10_to_80", ascending=False)
    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = np.where(plot["year_10"].ge(1990), "#2563EB", "#059669")
    ax.barh(plot["technology"], plot["years_10_to_80"], color=colors, alpha=0.88)
    ax.invert_yaxis()
    ax.set_xlabel("Years from 10% to 80% adoption")
    ax.set_ylabel("")
    ax.set_title("Diffusion Speed Benchmark: Newer Network Technologies Compress Adoption Time")
    for idx, row in plot.iterrows():
        ax.text(
            row["years_10_to_80"] + 0.8,
            list(plot.index).index(idx),
            f"{row['years_10_to_80']:.0f}y",
            va="center",
            fontsize=10,
            color="#111827",
        )
    legend = [
        Line2D([0], [0], color="#059669", linewidth=8, label="Pre-digital household/infra"),
        Line2D([0], [0], color="#2563EB", linewidth=8, label="Digital/network tech"),
    ]
    ax.legend(handles=legend, frameon=False, loc="lower right")
    style_axes(ax)
    save_figure(fig, "fig7_world_diffusion_speed_benchmark.png")


def make_obsolescence_timeline() -> None:
    cases = pd.read_csv(CASES_PATH)
    cases = cases.sort_values("start_year").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(12, 6.8))
    y_positions = np.arange(len(cases))
    for y, row in zip(y_positions, cases.itertuples(index=False)):
        color = MECHANISM_COLORS.get(row.mechanism, "#111827")
        ax.hlines(y, row.start_year, row.end_year, color=color, linewidth=7, alpha=0.82)
        ax.scatter([row.start_year, row.end_year], [y, y], s=70, color=color, edgecolor="white", linewidth=1.2)
        if pd.notna(row.capability_wedge_pct):
            ax.text(
                row.end_year + 1.2,
                y,
                f"service/capability wedge ~{row.capability_wedge_pct:.0%}",
                fontsize=9,
                va="center",
                color="#991B1B",
            )
        else:
            ax.text(row.end_year + 1.2, y, row.mechanism, fontsize=9, va="center", color="#374151")

    ax.set_yticks(y_positions)
    ax.set_yticklabels(cases["case_label"])
    ax.invert_yaxis()
    ax.set_xlim(1918, 2032)
    ax.set_xlabel("Year")
    ax.set_title("Historical Mechanisms: Obsolescence Throttles Effective Capability, Not Just Adoption")
    ax.text(
        0,
        -0.18,
        "Evidence-coded cases. Only Phoebus has a direct service-life wedge; other rows document channels such as styling cycles, software throttling and repair/access restrictions.",
        transform=ax.transAxes,
        fontsize=9,
        color="#4B5563",
    )
    handles = [
        Line2D([0], [0], color=color, linewidth=6, label=mechanism)
        for mechanism, color in MECHANISM_COLORS.items()
    ]
    ax.legend(handles=handles, frameon=False, loc="upper left", bbox_to_anchor=(0.0, -0.26), ncol=2)
    style_axes(ax, grid_axis="x")
    save_figure(fig, "fig8_historical_obsolescence_mechanisms.png")


def make_world_labour_stress() -> None:
    df = pd.read_csv(DATA_DIR / "task_content_longdiff_1995_2005.csv")
    df = df.loc[df["is_full_window"].eq(True)].copy()
    order = (
        df.groupby("sector_id")["delta_tc_long"]
        .median()
        .sort_values()
        .index.tolist()
    )
    data = [df.loc[df["sector_id"].eq(sector), "delta_tc_long"].dropna().values * 100 for sector in order]
    fig, ax = plt.subplots(figsize=(12, 7))
    parts = ax.violinplot(data, showmeans=False, showmedians=False, showextrema=False)
    for body in parts["bodies"]:
        body.set_facecolor("#94A3B8")
        body.set_edgecolor("#334155")
        body.set_alpha(0.45)
    ax.boxplot(
        data,
        widths=0.18,
        patch_artist=True,
        showfliers=False,
        boxprops={"facecolor": "white", "edgecolor": "#111827", "linewidth": 1.1},
        medianprops={"color": "#DC2626", "linewidth": 1.6},
        whiskerprops={"color": "#111827", "linewidth": 1},
        capprops={"color": "#111827", "linewidth": 1},
    )
    ax.axhline(0, color="#111827", linewidth=1)
    ax.set_xticks(np.arange(1, len(order) + 1))
    ax.set_xticklabels([SECTOR_LABELS.get(sector, sector) for sector in order], rotation=20, ha="right")
    ax.set_ylabel("Change in structural labour share, pp, 1995-2005")
    ax.set_title("ICT-Era Comparator Panel: Labour-Market Stress Was Heterogeneous")
    ax.text(
        0,
        -0.20,
        "Source: repo Stage 1 task-content long differences from EU KLEMS/OECD STAN comparator countries. Negative values indicate labour-share compression.",
        transform=ax.transAxes,
        fontsize=9,
        color="#4B5563",
    )
    style_axes(ax)
    save_figure(fig, "fig9_world_ict_labour_stress_distribution.png")


def make_russia_pressure_bar() -> None:
    proxy = pd.read_csv(DATA_DIR / "managed_obsolescence_sector_proxy.csv").sort_values(
        "managed_obsolescence_pressure_score",
        ascending=True,
    )
    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = proxy["fit_quality"].map(
        {
            "exact_old_nace": "#059669",
            "partial_old_nace": "#D97706",
            "weak_proxy": "#DC2626",
        }
    ).fillna("#64748B")
    ax.barh(proxy["sector_id"].map(SECTOR_LABELS), proxy["managed_obsolescence_pressure_score"], color=colors, alpha=0.86)
    ax.set_xlabel("Managed-obsolescence pressure score, 0-1")
    ax.set_ylabel("")
    ax.set_title("Russia: Where Staged AI Deployment Pressure Is Highest")
    for i, row in enumerate(proxy.itertuples(index=False)):
        ax.text(
            row.managed_obsolescence_pressure_score + 0.018,
            i,
            f"{row.managed_obsolescence_pressure_score:.2f}",
            va="center",
            fontsize=10,
        )
    handles = [
        Line2D([0], [0], color="#059669", linewidth=8, label="Exact old-NACE mapping"),
        Line2D([0], [0], color="#D97706", linewidth=8, label="Partial mapping"),
        Line2D([0], [0], color="#DC2626", linewidth=8, label="Weak proxy"),
    ]
    ax.legend(handles=handles, frameon=False, loc="lower right")
    style_axes(ax)
    save_figure(fig, "fig10_russia_managed_obsolescence_pressure.png")


def make_russia_managed_forecast() -> None:
    diffusion = pd.read_csv(DATA_DIR / "ai_diffusion_sector_summary.csv")
    base = diffusion.loc[diffusion["scenario"].eq("Base")].copy()
    proxy = pd.read_csv(DATA_DIR / "managed_obsolescence_sector_proxy.csv")[
        ["sector_id", "managed_obsolescence_pressure_score"]
    ]
    plot = base.merge(proxy, on="sector_id", how="left")
    plot["A_2035_managed_base_rho030"] = plot["A_2035"] * (1.0 - 0.30 * plot["managed_obsolescence_pressure_score"])
    plot["A_2035_managed_stress_rho050"] = plot["A_2035"] * (1.0 - 0.50 * plot["managed_obsolescence_pressure_score"])
    plot = plot.sort_values("A_2035", ascending=False)

    x = np.arange(len(plot))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.bar(x - width, plot["A_2035"], width, label="Base diffusion", color="#2563EB", alpha=0.88)
    ax.bar(x, plot["A_2035_managed_base_rho030"], width, label="Managed, rho=0.30", color="#D97706", alpha=0.88)
    ax.bar(x + width, plot["A_2035_managed_stress_rho050"], width, label="Managed, rho=0.50", color="#DC2626", alpha=0.82)
    ax.set_xticks(x)
    ax.set_xticklabels(plot["sector_id"].map(SECTOR_LABELS), rotation=20, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("2035 deployed adoption/capability")
    ax.set_title("Russia Forecast: Managed Obsolescence Lowers Deployed AI Capability")
    ax.legend(frameon=False, loc="upper right")
    ax.text(
        0,
        -0.20,
        "Formula: A_managed = A_base * (1 - rho * MOS). MOS is the Russia KLEMS pressure score; rho is the strength of institutional throttling.",
        transform=ax.transAxes,
        fontsize=9,
        color="#4B5563",
    )
    style_axes(ax)
    save_figure(fig, "fig11_russia_base_vs_managed_ai_2035.png")


def make_russia_quadrant() -> None:
    diffusion = pd.read_csv(DATA_DIR / "ai_diffusion_sector_summary.csv")
    base = diffusion.loc[diffusion["scenario"].eq("Base")].copy()
    proxy = pd.read_csv(DATA_DIR / "managed_obsolescence_sector_proxy.csv")[
        ["sector_id", "managed_obsolescence_pressure_score", "fit_quality"]
    ]
    baseline = pd.read_csv(DATA_DIR / "russia_sector_baseline_2024.csv")[
        ["sector_id", "va_current_bn_rub", "employment_thousand_persons"]
    ]
    plot = base.merge(proxy, on="sector_id", how="left").merge(baseline, on="sector_id", how="left")
    plot["bubble_size"] = 120 + 900 * plot["va_current_bn_rub"] / plot["va_current_bn_rub"].max()
    x_cut = float(plot["A_2035"].median())
    y_cut = float(plot["managed_obsolescence_pressure_score"].median())

    fig, ax = plt.subplots(figsize=(11, 7))
    for class_id, rows in plot.groupby("class_id"):
        ax.scatter(
            rows["A_2035"],
            rows["managed_obsolescence_pressure_score"],
            s=rows["bubble_size"],
            color=CLASS_COLORS.get(class_id, "#64748B"),
            alpha=0.72,
            edgecolor="white",
            linewidth=1.2,
            label=class_id,
        )
    for row in plot.itertuples(index=False):
        ax.text(
            row.A_2035 + 0.012,
            row.managed_obsolescence_pressure_score + 0.008,
            row.sector_id,
            fontsize=10,
            weight="bold",
            color="#111827",
        )
    ax.axvline(x_cut, color="#9CA3AF", linestyle="--", linewidth=1)
    ax.axhline(y_cut, color="#9CA3AF", linestyle="--", linewidth=1)
    ax.text(0.02, y_cut + 0.025, "higher throttling pressure", fontsize=9, color="#4B5563")
    ax.text(x_cut + 0.02, 0.02, "higher AI adoption", fontsize=9, color="#4B5563")
    ax.set_xlim(0, 0.98)
    ax.set_ylim(0, 0.98)
    ax.set_xlabel("Base AI adoption/capability in 2035")
    ax.set_ylabel("Managed-obsolescence pressure score")
    ax.set_title("Russia Forecast Map: High AI Exposure vs High Throttling Pressure")
    ax.legend(frameon=False, loc="upper left", title="Adoption class")
    ax.text(
        0,
        -0.18,
        "Bubble size is 2024 sector VA. Upper-right means both large AI deployment potential and strong pressure for staged deployment.",
        transform=ax.transAxes,
        fontsize=9,
        color="#4B5563",
    )
    style_axes(ax)
    save_figure(fig, "fig12_russia_ai_throttling_quadrants.png")


def main() -> None:
    configure_style()
    curves = build_diffusion_benchmark()
    make_world_s_curves(curves)
    make_diffusion_speed_bars()
    make_obsolescence_timeline()
    make_world_labour_stress()
    make_russia_pressure_bar()
    make_russia_managed_forecast()
    make_russia_quadrant()


if __name__ == "__main__":
    main()

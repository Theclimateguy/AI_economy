from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

STRUCTURE_PATH = ROOT / "data" / "processed" / "russia_economy_structure_paths_2025_2035.csv"
CLIMATE_PATH = ROOT / "data" / "processed" / "climate_energy_transition_paths_2025_2035.csv"
BASE_RANKING_PATH = ROOT / "data" / "processed" / "okved_resilience_ranking_2024.csv"

OUT_PANEL_PATH = ROOT / "data" / "processed" / "okved_resilience_forward_paths_2025_2030.csv"
OUT_SUMMARY_PATH = ROOT / "data" / "processed" / "okved_resilience_forward_summary_2030.csv"
OUT_WEIGHTS_PATH = ROOT / "data" / "processed" / "okved_resilience_forward_weights_2030.csv"
OUT_METADATA_PATH = ROOT / "data" / "processed" / "okved_resilience_forward_metadata.json"
DOC_PATH = ROOT / "docs" / "okved_resilience_2030_figures.md"
FIG_DIR = ROOT / "output" / "figures" / "okved_resilience"

EPS = 0.01
RISK_GATE_THRESHOLD = 0.35
RISK_GATE_LAMBDA = 3.0


@dataclass(frozen=True)
class FeatureSpec:
    column: str
    positive: bool
    label: str


FORWARD_SPECS: dict[str, list[FeatureSpec]] = {
    "adaptive_potential": [
        FeatureSpec("adaptation_managed", True, "Managed AI adaptation"),
        FeatureSpec("diffusion_speed_managed", True, "Managed diffusion speed"),
        FeatureSpec("va_ai_growth_yoy_pct", True, "AI-path VA growth"),
        FeatureSpec("lp_gain_vs_cf_pct", True, "Labour productivity gain"),
    ],
    "credit_potential": [
        FeatureSpec("va_share_ai", True, "AI-path VA share"),
        FeatureSpec("delta_k_need_managed_bn_rub", True, "Annual capital need"),
        FeatureSpec("cumulative_delta_k_need_managed_bn_rub", True, "Cumulative capital need"),
        FeatureSpec("capital_need_share_pct", True, "Capital need to VA"),
    ],
    "bank_profitability": [
        FeatureSpec("margin_ai", True, "AI-path margin proxy"),
        FeatureSpec("incremental_profit_pool_vs_cf_bn_rub", True, "Annual incremental profit pool"),
        FeatureSpec("profit_uplift_pct", True, "Profit uplift vs counterfactual"),
        FeatureSpec("cumulative_net_value_after_capex_bn_rub", True, "Cumulative net value after capex"),
    ],
    "financial_stability": [
        FeatureSpec("margin_ai", True, "AI-path margin proxy"),
        FeatureSpec("import_dependency_score", False, "Import dependency"),
        FeatureSpec("market_concentration_score", False, "Market concentration risk"),
        FeatureSpec("managed_obsolescence_pressure_score", False, "Managed obsolescence pressure"),
        FeatureSpec("transition_risk_score", False, "Climate-transition risk"),
    ],
    "strategic_convergence": [
        FeatureSpec("adaptation_managed", True, "Managed AI adaptation"),
        FeatureSpec("lp_gain_vs_cf_pct", True, "Labour productivity gain"),
        FeatureSpec("strategy_capacity_index", True, "Strategy capacity"),
        FeatureSpec("diversification_upside_score", True, "Diversification upside"),
        FeatureSpec("net_transformation_score", True, "Net transformation score"),
    ],
}

BLOCK_LABELS = {
    "adaptive_potential": "Адаптивность",
    "credit_potential": "Кредитный\nпотенциал",
    "bank_profitability": "Доходность\nдля банка",
    "financial_stability": "Финансовая\nустойчивость",
    "strategic_convergence": "Стратегическая\nконвергенция",
}

SECTOR_SHORT = {
    "B": "Добыча",
    "C": "Обработка",
    "C_mach": "Машиностр.",
    "DE": "Энергетика",
    "F": "Стройка",
    "G": "Торговля",
    "H": "Транспорт",
    "J": "ИТ/связь",
    "K": "Финансы",
    "M": "Проф. услуги",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def selected_rows(df: pd.DataFrame, **filters: Any) -> pd.DataFrame:
    out = df.copy()
    for column, value in filters.items():
        if column in out.columns:
            out = out.loc[out[column].eq(value)].copy()
    return out


def impute_numeric(series: pd.Series) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce").astype(float)
    if out.notna().any():
        return out.fillna(out.median())
    return pd.Series(0.0, index=series.index, dtype=float)


def fit_winsor_bounds(panel: pd.DataFrame, specs: dict[str, list[FeatureSpec]]) -> dict[str, tuple[float, float]]:
    bounds = {}
    for block_specs in specs.values():
        for spec in block_specs:
            if spec.column in bounds:
                continue
            x = impute_numeric(panel[spec.column])
            low = float(x.quantile(0.05))
            high = float(x.quantile(0.95))
            if not np.isfinite(low) or not np.isfinite(high) or math.isclose(low, high):
                low, high = float(x.min()), float(x.max())
            bounds[spec.column] = (low, high)
    return bounds


def transform_feature(series: pd.Series, positive: bool, bounds: tuple[float, float]) -> pd.Series:
    x = impute_numeric(series)
    low, high = bounds
    if not np.isfinite(low) or not np.isfinite(high) or math.isclose(low, high):
        z = pd.Series(0.5, index=series.index, dtype=float)
    else:
        z = (x.clip(low, high) - low) / (high - low)
    if not positive:
        z = 1.0 - z
    return z.clip(EPS, 1.0)


def critic_weights(z: pd.DataFrame) -> pd.Series:
    if z.shape[1] == 1:
        return pd.Series([1.0], index=z.columns)
    sigma = z.std(axis=0, ddof=0)
    corr = z.corr().fillna(0.0).clip(-1.0, 1.0)
    contrast = (1.0 - corr).sum(axis=1)
    c = sigma * contrast
    total = float(c.sum())
    if not np.isfinite(total) or total <= 0:
        return pd.Series(1.0 / len(c), index=z.columns)
    return c / total


def geometric_score(z: pd.DataFrame, weights: pd.Series) -> pd.Series:
    weights = weights.reindex(z.columns).fillna(0.0)
    weights = weights / weights.sum() if weights.sum() > 0 else pd.Series(1.0 / z.shape[1], index=z.columns)
    return np.exp(np.log(z.clip(EPS, 1.0)).mul(weights, axis=1).sum(axis=1))


def build_forward_panel(scenario: str, throttle: str, climate_scenario: str) -> pd.DataFrame:
    structure = selected_rows(read_csv(STRUCTURE_PATH), scenario=scenario, throttle_scenario=throttle)
    structure = structure.loc[structure["year"].between(2025, 2030)].copy()

    climate = selected_rows(
        read_csv(CLIMATE_PATH),
        scenario=scenario,
        throttle_scenario=throttle,
        complex_scenario=climate_scenario,
    )
    climate = climate.loc[climate["year"].between(2025, 2030)].copy()
    climate_cols = [
        "year",
        "sector_id",
        "transition_risk_score",
        "diversification_upside_score",
        "net_transformation_score",
        "strategy_capacity_index",
    ]
    panel = structure.merge(climate[climate_cols], on=["year", "sector_id"], how="left")

    panel = panel.sort_values(["sector_id", "year"]).reset_index(drop=True)
    panel["va_ai_growth_yoy_pct"] = panel.groupby("sector_id")["va_ai_bn_rub"].pct_change() * 100.0
    panel["va_ai_growth_yoy_pct"] = panel["va_ai_growth_yoy_pct"].fillna(panel["va_cf_growth_rate_annual"] * 100.0)
    panel["capital_need_share_pct"] = panel["delta_k_need_managed_bn_rub"] / panel["va_ai_bn_rub"] * 100.0
    panel["profit_uplift_pct"] = (
        panel["incremental_profit_pool_vs_cf_bn_rub"] / panel["profit_pool_cf_bn_rub"].replace(0, np.nan) * 100.0
    )
    return panel


def score_forward_panel(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    bounds = fit_winsor_bounds(panel, FORWARD_SPECS)
    z_blocks_panel: dict[str, pd.DataFrame] = {}
    z_blocks_2030: dict[str, pd.DataFrame] = {}
    weights_rows = []

    panel_2030 = panel.loc[panel["year"].eq(2030)].copy()
    panel_scores = pd.DataFrame(index=panel.index)
    scores_2030 = pd.DataFrame(index=panel_2030.index)

    for block, specs in FORWARD_SPECS.items():
        z_panel = pd.DataFrame(index=panel.index)
        z_2030 = pd.DataFrame(index=panel_2030.index)
        for spec in specs:
            z_panel[spec.column] = transform_feature(panel[spec.column], spec.positive, bounds[spec.column])
            z_2030[spec.column] = transform_feature(panel_2030[spec.column], spec.positive, bounds[spec.column])
        indicator_weights = critic_weights(z_2030)
        z_blocks_panel[block] = z_panel
        z_blocks_2030[block] = z_2030
        panel_scores[block] = geometric_score(z_panel, indicator_weights)
        scores_2030[block] = geometric_score(z_2030, indicator_weights)

        for criterion, weight in indicator_weights.items():
            direction = "positive"
            label = criterion
            for spec in specs:
                if spec.column == criterion:
                    direction = "positive" if spec.positive else "negative"
                    label = spec.label
                    break
            weights_rows.append(
                {
                    "level": "indicator",
                    "block": block,
                    "criterion": criterion,
                    "label": label,
                    "direction": direction,
                    "weight": weight,
                }
            )

    block_weights = critic_weights(scores_2030)
    for block, weight in block_weights.items():
        weights_rows.append(
            {
                "level": "block",
                "block": block,
                "criterion": block,
                "label": BLOCK_LABELS.get(block, block).replace("\n", " "),
                "direction": "",
                "weight": weight,
            }
        )

    base_index = geometric_score(panel_scores, block_weights)
    shortfall = (RISK_GATE_THRESHOLD - panel_scores["financial_stability"]).clip(lower=0.0)
    risk_penalty = np.exp(-RISK_GATE_LAMBDA * shortfall.pow(2))

    scored = panel[
        [
            "scenario",
            "throttle_scenario",
            "year",
            "sector_id",
            "sector_name_ru",
            "class_id",
            "ai_intensity",
            "va_ai_bn_rub",
            "va_share_ai",
            "margin_ai",
            "adaptation_managed",
            "lp_gain_vs_cf_pct",
            "delta_k_need_managed_bn_rub",
            "cumulative_delta_k_need_managed_bn_rub",
            "incremental_profit_pool_vs_cf_bn_rub",
            "cumulative_net_value_after_capex_bn_rub",
            "transition_risk_score",
            "strategy_capacity_index",
        ]
    ].copy()
    for block in FORWARD_SPECS:
        scored[block] = panel_scores[block].to_numpy()
    scored["base_forward_index_no_gate"] = base_index.to_numpy()
    scored["financial_risk_penalty"] = risk_penalty.to_numpy()
    scored["forward_resilience_index"] = (base_index * risk_penalty).to_numpy()
    scored["forward_rank"] = scored.groupby("year")["forward_resilience_index"].rank(ascending=False, method="dense").astype(int)

    return scored, pd.DataFrame(weights_rows)


def plot_critic_index_paths(scored: pd.DataFrame, summary_2030: pd.DataFrame) -> Path:
    top_ids = summary_2030.sort_values("forward_rank").head(5)["sector_id"].tolist()
    plot_data = scored.loc[scored["sector_id"].isin(top_ids)].copy()

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    for sector_id, group in plot_data.groupby("sector_id"):
        group = group.sort_values("year")
        ax.plot(
            group["year"],
            group["forward_resilience_index"],
            marker="o",
            linewidth=2,
            label=f"{sector_id} · {SECTOR_SHORT.get(sector_id, sector_id)}",
        )
    ax.set_title("CRITIC-индекс устойчивости: траектории топ-5 к 2030")
    ax.set_xlabel("Год")
    ax.set_ylabel("Forward CRITIC index")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    path = FIG_DIR / "critic_resilience_index_paths_top5_2025_2030.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_critic_rank_shift(summary_2030: pd.DataFrame, base_ranking: pd.DataFrame) -> Path:
    merged = summary_2030.merge(base_ranking[["sector_id", "rank"]], on="sector_id", how="left")
    merged = merged.rename(columns={"rank": "rank_2024", "forward_rank": "rank_2030"}).sort_values("rank_2030")
    merged["label"] = merged["sector_id"].map(SECTOR_SHORT).fillna(merged["sector_id"])

    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(merged))
    ax.hlines(y, merged["rank_2024"], merged["rank_2030"], color="#909090", linewidth=2)
    ax.scatter(merged["rank_2024"], y, s=70, color="#b5651d", label="2024 base")
    ax.scatter(merged["rank_2030"], y, s=80, color="#2f6f73", label="2030 forward")
    for idx, row in merged.reset_index(drop=True).iterrows():
        ax.text(10.65, idx, row["sector_id"], va="center", ha="left", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(merged["label"])
    ax.set_xlabel("Ранг, 1 = лучше")
    ax.set_title("CRITIC-устойчивость: сдвиг рангов 2024 → 2030")
    ax.set_xlim(10.9, 0.6)
    ax.grid(axis="x", alpha=0.20)
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout()
    path = FIG_DIR / "critic_resilience_rank_shift_2024_2030.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_critic_rank_paths(scored: pd.DataFrame, summary_2030: pd.DataFrame) -> Path:
    top_ids = summary_2030.sort_values("forward_rank").head(8)["sector_id"].tolist()
    plot_data = scored.loc[scored["sector_id"].isin(top_ids)].copy()

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    for sector_id, group in plot_data.groupby("sector_id"):
        group = group.sort_values("year")
        ax.plot(
            group["year"],
            group["forward_rank"],
            marker="o",
            linewidth=2,
            label=f"{sector_id} · {SECTOR_SHORT.get(sector_id, sector_id)}",
        )
    ax.set_title("CRITIC-ранг устойчивости по годам")
    ax.set_xlabel("Год")
    ax.set_ylabel("Ранг, 1 = лучше")
    ax.set_ylim(10.5, 0.5)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(ncol=2, frameon=False, fontsize=8)
    fig.tight_layout()
    path = FIG_DIR / "critic_resilience_rank_paths_2025_2030.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_critic_index_bar(summary_2030: pd.DataFrame) -> Path:
    data = summary_2030.sort_values("forward_resilience_index", ascending=True).copy()
    labels = [f"{row.sector_id} · {SECTOR_SHORT.get(row.sector_id, row.sector_id)}" for row in data.itertuples()]

    fig, ax = plt.subplots(figsize=(9, 5.8))
    ax.barh(labels, data["forward_resilience_index"], color="#2f6f73")
    ax.set_xlabel("CRITIC-индекс устойчивости, 2030")
    ax.set_title("Итоговый CRITIC-рейтинг устойчивости ОКВЭД, 2030")
    ax.grid(axis="x", alpha=0.20)
    fig.tight_layout()
    path = FIG_DIR / "critic_resilience_index_2030.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_critic_block_heatmap(summary_2030: pd.DataFrame) -> Path:
    blocks = list(FORWARD_SPECS)
    heat = summary_2030.sort_values("forward_rank").set_index("sector_id")[blocks]
    labels = [SECTOR_SHORT.get(sector_id, sector_id) for sector_id in heat.index]

    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    im = ax.imshow(heat.to_numpy(), aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(blocks)))
    ax.set_xticklabels([BLOCK_LABELS[b] for b in blocks], rotation=0, ha="center")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    for row in range(heat.shape[0]):
        for col in range(heat.shape[1]):
            value = heat.iloc[row, col]
            ax.text(col, row, f"{value:.2f}", ha="center", va="center", color="white" if value < 0.45 else "black", fontsize=8)
    ax.set_title("CRITIC-блоки устойчивости по ОКВЭД, 2030")
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Нормированный блоковый score")
    fig.tight_layout()
    path = FIG_DIR / "critic_resilience_block_heatmap_2030.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_critic_block_weights(weights: pd.DataFrame) -> Path:
    data = weights.loc[weights["level"].eq("block")].copy()
    data = data.sort_values("weight", ascending=True)

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.barh(data["label"], data["weight"], color="#6b5b95")
    ax.set_xlabel("CRITIC-вес")
    ax.set_title("CRITIC-веса блоков устойчивости, калибровка 2030")
    ax.grid(axis="x", alpha=0.20)
    fig.tight_layout()
    path = FIG_DIR / "critic_resilience_block_weights_2030.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def df_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    work = df.copy()
    for column in work.select_dtypes(include=[np.number]).columns:
        work[column] = work[column].round(3)
    work = work.astype(str)
    header = "| " + " | ".join(work.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(work.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in work.to_numpy(dtype=str)]
    return "\n".join([header, separator, *rows])


def write_report(summary_2030: pd.DataFrame, weights: pd.DataFrame, figure_paths: list[Path], metadata: dict[str, Any]) -> None:
    top = summary_2030.sort_values("forward_rank")[
        [
            "forward_rank",
            "sector_id",
            "sector_name_ru",
            "forward_resilience_index",
            "adaptive_potential",
            "credit_potential",
            "bank_profitability",
            "financial_stability",
            "strategic_convergence",
        ]
    ]
    block_weights = weights.loc[weights["level"].eq("block"), ["criterion", "label", "weight"]].sort_values(
        "weight", ascending=False
    )
    lines = [
        "# Графики CRITIC-устойчивости ОКВЭД до 2030",
        "",
        "Построены только графики по самой модели устойчивости CRITIC: итоговый индекс, ранги, блоковые scores и CRITIC-веса. "
        "Экономические scatter/opportunity-графики не включены.",
        "",
        "## Веса блоков 2030",
        "",
        df_to_markdown(block_weights),
        "",
        "## Forward-рейтинг 2030",
        "",
        df_to_markdown(top),
        "",
        "## Файлы графиков",
        "",
        *[f"- `{path.relative_to(ROOT)}`" for path in figure_paths],
        "",
        "## Воспроизводимость",
        "",
        f"- Скрипт: `python scripts/plot_okved_resilience_2030.py --scenario {metadata['scenario']} --throttle {metadata['throttle_scenario']} --climate-scenario {metadata['climate_scenario']}`",
        f"- Панель: `{OUT_PANEL_PATH.relative_to(ROOT)}`",
        f"- Summary 2030: `{OUT_SUMMARY_PATH.relative_to(ROOT)}`",
        f"- Веса: `{OUT_WEIGHTS_PATH.relative_to(ROOT)}`",
        "",
        "## Интерпретационное ограничение",
        "",
        "Это не новая банковская production-модель, а визуализация CRITIC-устойчивости на имеющихся сценарных прокси. "
        "Фактические RAROC, выдачи, NPL и cost of risk по ОКВЭД всё ещё нужны для калибровки банковских блоков.",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot OKVED forward resilience diagnostics up to 2030.")
    parser.add_argument("--scenario", default="Base")
    parser.add_argument("--throttle", default="BaseThrottle")
    parser.add_argument("--climate-scenario", default="OrderlyTransition")
    args = parser.parse_args()

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel = build_forward_panel(args.scenario, args.throttle, args.climate_scenario)
    scored, weights = score_forward_panel(panel)

    base_ranking = read_csv(BASE_RANKING_PATH)
    summary_2030 = scored.loc[scored["year"].eq(2030)].copy()
    summary_2030 = summary_2030.sort_values("forward_rank").reset_index(drop=True)
    summary_2030 = summary_2030.merge(
        base_ranking[["sector_id", "rank", "resilience_index"]].rename(
            columns={"rank": "base_rank_2024", "resilience_index": "base_resilience_index_2024"}
        ),
        on="sector_id",
        how="left",
    )
    summary_2030["rank_change_2030_vs_2024"] = summary_2030["base_rank_2024"] - summary_2030["forward_rank"]

    figure_paths = [
        plot_critic_index_paths(scored, summary_2030),
        plot_critic_rank_paths(scored, summary_2030),
        plot_critic_rank_shift(summary_2030, base_ranking),
        plot_critic_index_bar(summary_2030),
        plot_critic_block_heatmap(summary_2030),
        plot_critic_block_weights(weights),
    ]

    scored.to_csv(OUT_PANEL_PATH, index=False)
    summary_2030.to_csv(OUT_SUMMARY_PATH, index=False)
    weights.to_csv(OUT_WEIGHTS_PATH, index=False)
    metadata = {
        "scenario": args.scenario,
        "throttle_scenario": args.throttle,
        "climate_scenario": args.climate_scenario,
        "risk_gate_threshold": RISK_GATE_THRESHOLD,
        "risk_gate_lambda": RISK_GATE_LAMBDA,
        "figures": [str(path.relative_to(ROOT)) for path in figure_paths],
    }
    OUT_METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(summary_2030, weights, figure_paths, metadata)

    print(f"Wrote {OUT_PANEL_PATH.relative_to(ROOT)}")
    print(f"Wrote {OUT_SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Wrote {DOC_PATH.relative_to(ROOT)}")
    for path in figure_paths:
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

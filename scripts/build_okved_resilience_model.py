from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:  # Figures are optional; table outputs are the reproducibility core.
    plt = None


ROOT = Path(__file__).resolve().parents[1]

OFFICIAL_PANEL = ROOT / "data" / "processed" / "russia_sector_panel_official_2011_2025.csv"
BASELINE_2024 = ROOT / "data" / "processed" / "russia_sector_baseline_2024.csv"
AI_DIFFUSION = ROOT / "data" / "processed" / "ai_diffusion_sector_summary.csv"
AI_CAPITAL_RETURNS = ROOT / "data" / "processed" / "ai_capital_return_sector_summary.csv"
IMPORT_DEPENDENCY = ROOT / "data" / "processed" / "import_dependency_sector.csv"
ECONOMY_STRUCTURE = ROOT / "data" / "processed" / "russia_economy_structure_sector_summary.csv"
CLIMATE_TRANSITION = ROOT / "data" / "processed" / "climate_energy_transition_sector_summary.csv"
IO_MULTIPLIERS = ROOT / "data" / "processed" / "io_multiplier_sector_summary.csv"

OUT_DIR = ROOT / "data" / "processed"
FIG_DIR = ROOT / "output" / "figures" / "okved_resilience"
DOC_PATH = ROOT / "docs" / "okved_resilience_model.md"

FEATURE_MATRIX_PATH = OUT_DIR / "okved_resilience_feature_matrix_2024.csv"
BLOCK_SCORES_PATH = OUT_DIR / "okved_resilience_block_scores_2024.csv"
RANKING_PATH = OUT_DIR / "okved_resilience_ranking_2024.csv"
WEIGHTS_PATH = OUT_DIR / "okved_resilience_weights_2024.csv"
ROBUSTNESS_PATH = OUT_DIR / "okved_resilience_robustness_checks.csv"
ROBUSTNESS_SUMMARY_PATH = OUT_DIR / "okved_resilience_robustness_summary.csv"
BACKTEST_PATH = OUT_DIR / "okved_resilience_historical_backtest.csv"
BACKTEST_SUMMARY_PATH = OUT_DIR / "okved_resilience_historical_backtest_summary.csv"
DATA_QUALITY_PATH = OUT_DIR / "okved_resilience_data_quality_2024.csv"
METADATA_PATH = OUT_DIR / "okved_resilience_metadata.json"

EPS = 0.01
DEFAULT_SEED = 42
RISK_GATE_THRESHOLD = 0.35
RISK_GATE_LAMBDA = 3.0


@dataclass(frozen=True)
class FeatureSpec:
    column: str
    positive: bool
    label: str


MODEL_SPECS: dict[str, list[FeatureSpec]] = {
    "adaptive_potential": [
        FeatureSpec("va_real_growth_median_2019_2024_pct", True, "Median real VA growth, 2019-2024"),
        FeatureSpec("va_real_growth_volatility_2019_2024_pct", False, "Real VA growth volatility, 2019-2024"),
        FeatureSpec("va_real_cagr_2019_2024_pct", True, "Real VA CAGR, 2019-2024"),
        FeatureSpec("shock_recovery_2022_2024_pct", True, "Real VA recovery CAGR, 2022-2024"),
        FeatureSpec("labour_productivity_cagr_2019_2024_pct", True, "Labour productivity CAGR, 2019-2024"),
    ],
    "credit_potential": [
        FeatureSpec("va_share_2024", True, "Current VA market share, 2024"),
        FeatureSpec("employment_share_2024", True, "Employment share, 2024"),
        FeatureSpec("va_real_growth_pct", True, "Real VA growth, 2024"),
        FeatureSpec("cumulative_capex_2030_bn_rub", True, "AI-related cumulative capex proxy by 2030"),
        FeatureSpec("fixed_asset_renewal_pct", True, "Fixed asset renewal rate"),
        FeatureSpec("backward_linkage_multiplier", True, "Input-output backward linkage multiplier"),
    ],
    "bank_profitability": [
        FeatureSpec("net_return_on_new_capital_cf_2035", True, "Net return on new capital, 2035"),
        FeatureSpec("net_return_cf_2035", True, "Net capital-flow return, 2035"),
        FeatureSpec("margin_2030", True, "AI margin proxy, 2030"),
        FeatureSpec("profit_margin_proxy_2024", True, "Current profit margin proxy"),
        FeatureSpec("cumulative_net_value_after_capex_2030_bn_rub", True, "Net value after capex by 2030"),
        FeatureSpec("incremental_profit_pool_2030_bn_rub", True, "Incremental profit pool by 2030"),
    ],
    "financial_stability": [
        FeatureSpec("profit_margin_proxy_2024", True, "Current profit margin proxy"),
        FeatureSpec("va_real_growth_median_2019_2024_pct", True, "Median real VA growth, 2019-2024"),
        FeatureSpec("va_real_growth_volatility_2019_2024_pct", False, "Real VA growth volatility, 2019-2024"),
        FeatureSpec("deflator_volatility_2019_2024_pct", False, "Deflator volatility, 2019-2024"),
        FeatureSpec("min_real_growth_2019_2024_pct", True, "Worst annual real growth, 2019-2024"),
        FeatureSpec("import_dependency_score", False, "Import dependency score"),
        FeatureSpec("sanction_wedge_base", False, "Base sanction wedge"),
    ],
    "strategic_convergence": [
        FeatureSpec("A_2030", True, "AI diffusion level, 2030"),
        FeatureSpec("adaptation_managed_2030", True, "Managed adaptation, 2030"),
        FeatureSpec("lp_gain_vs_cf_2030_pct", True, "Productivity gain vs counterfactual, 2030"),
        FeatureSpec("ict_digital_share_proxy_pct", True, "ICT and digital-use proxy"),
        FeatureSpec("clean_energy_readiness", True, "Clean-energy readiness"),
        FeatureSpec("ai_service_leverage", True, "AI-service leverage"),
        FeatureSpec("strategy_capacity_index_2030", True, "Strategy capacity index, 2030"),
    ],
}

HISTORICAL_SPECS: dict[str, list[FeatureSpec]] = {
    "adaptive_potential": [
        FeatureSpec("hist_real_growth_median_pct", True, "Rolling median real VA growth"),
        FeatureSpec("hist_real_growth_volatility_pct", False, "Rolling real VA growth volatility"),
        FeatureSpec("hist_va_real_cagr_pct", True, "Rolling real VA CAGR"),
        FeatureSpec("hist_lp_cagr_pct", True, "Rolling labour productivity CAGR"),
    ],
    "credit_potential": [
        FeatureSpec("hist_va_share_current", True, "Current VA share"),
        FeatureSpec("hist_employment_share_current", True, "Current employment share"),
        FeatureSpec("hist_va_current_cagr_pct", True, "Rolling nominal VA CAGR"),
        FeatureSpec("hist_wage_cagr_pct", True, "Rolling wage CAGR"),
    ],
    "bank_profitability": [
        FeatureSpec("hist_margin_proxy_current", True, "Current margin proxy"),
        FeatureSpec("hist_margin_proxy_trend_pp", True, "Rolling margin-proxy trend"),
        FeatureSpec("hist_va_current_cagr_pct", True, "Rolling nominal VA CAGR"),
        FeatureSpec("hist_wage_level_current", True, "Current wage level proxy"),
    ],
    "financial_stability": [
        FeatureSpec("hist_margin_proxy_current", True, "Current margin proxy"),
        FeatureSpec("hist_real_growth_median_pct", True, "Rolling median real VA growth"),
        FeatureSpec("hist_real_growth_volatility_pct", False, "Rolling real VA growth volatility"),
        FeatureSpec("hist_deflator_volatility_pct", False, "Rolling deflator volatility"),
        FeatureSpec("hist_min_real_growth_pct", True, "Rolling worst annual real growth"),
    ],
    "strategic_convergence": [
        FeatureSpec("hist_ai_intensity_score", True, "Static AI-intensity class score"),
        FeatureSpec("hist_lp_cagr_pct", True, "Rolling labour productivity CAGR"),
        FeatureSpec("hist_wage_level_current", True, "Current wage level proxy"),
        FeatureSpec("hist_wage_cagr_pct", True, "Rolling wage CAGR"),
    ],
}

AI_INTENSITY_SCORE = {
    "low": 0.25,
    "low_medium": 0.40,
    "medium": 0.60,
    "high": 0.90,
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


def finite_or_nan(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if np.isfinite(out) else float("nan")


def cagr_from_points(first: float, last: float, years: int) -> float:
    first = finite_or_nan(first)
    last = finite_or_nan(last)
    if years <= 0 or not np.isfinite(first) or not np.isfinite(last) or first <= 0 or last <= 0:
        return float("nan")
    return (last / first) ** (1.0 / years) - 1.0


def cagr_from_group(group: pd.DataFrame, column: str) -> float:
    values = group[["year", column]].dropna().sort_values("year")
    if len(values) < 2:
        return float("nan")
    first = values.iloc[0]
    last = values.iloc[-1]
    return cagr_from_points(first[column], last[column], int(last["year"] - first["year"]))


def weighted_average(group: pd.DataFrame, value: str, weight: str) -> float:
    valid = group[[value, weight]].dropna()
    if valid.empty or valid[weight].sum() <= 0:
        return float(group[value].mean())
    return float(np.average(valid[value], weights=valid[weight]))


def build_official_rolling_features(panel: pd.DataFrame) -> pd.DataFrame:
    work = panel.loc[panel["year"].between(2019, 2024)].copy()
    work["labour_productivity"] = work["va_constant_2021_bn_rub"] / work["employment_thousand_persons"]
    work["profit_margin_proxy"] = 1.0 - work["labour_share_proxy"]

    rows = []
    for sector_id, group in work.groupby("sector_id"):
        group = group.sort_values("year")
        sector_row = {
            "sector_id": sector_id,
            "va_real_growth_median_2019_2024_pct": group["va_real_growth_pct"].median(),
            "va_real_growth_volatility_2019_2024_pct": group["va_real_growth_pct"].std(ddof=0),
            "deflator_volatility_2019_2024_pct": group["va_deflator_growth_pct"].std(ddof=0),
            "min_real_growth_2019_2024_pct": group["va_real_growth_pct"].min(),
            "va_real_cagr_2019_2024_pct": 100.0 * cagr_from_group(group, "va_constant_2021_bn_rub"),
            "labour_productivity_cagr_2019_2024_pct": 100.0 * cagr_from_group(group, "labour_productivity"),
            "wage_cagr_2019_2024_pct": 100.0 * cagr_from_group(group, "avg_monthly_wage_rub"),
        }
        y2022 = group.loc[group["year"].eq(2022), "va_constant_2021_bn_rub"]
        y2024 = group.loc[group["year"].eq(2024), "va_constant_2021_bn_rub"]
        sector_row["shock_recovery_2022_2024_pct"] = (
            100.0 * cagr_from_points(y2022.iloc[0], y2024.iloc[0], 2)
            if not y2022.empty and not y2024.empty
            else float("nan")
        )
        rows.append(sector_row)
    return pd.DataFrame(rows)


def build_feature_matrix_2024() -> pd.DataFrame:
    panel = read_csv(OFFICIAL_PANEL)
    baseline = read_csv(BASELINE_2024)
    baseline = baseline.copy()
    baseline["va_share_2024"] = baseline["va_current_bn_rub"] / baseline["va_current_bn_rub"].sum()
    baseline["employment_share_2024"] = (
        baseline["employment_thousand_persons"] / baseline["employment_thousand_persons"].sum()
    )
    baseline["profit_margin_proxy_2024"] = 1.0 - baseline["labour_share_proxy"]

    features = baseline[
        [
            "sector_id",
            "sector_name_ru",
            "okved",
            "ai_intensity",
            "va_current_bn_rub",
            "va_share_2024",
            "employment_share_2024",
            "va_real_growth_pct",
            "labour_share_proxy",
            "profit_margin_proxy_2024",
        ]
    ].copy()
    features = features.merge(build_official_rolling_features(panel), on="sector_id", how="left")

    ai_diffusion = selected_rows(read_csv(AI_DIFFUSION), scenario="Base")[
        ["sector_id", "A_2030", "A_2035", "peak_speed", "margin_2030", "margin_2035"]
    ]
    features = features.merge(ai_diffusion, on="sector_id", how="left")

    ai_capital = selected_rows(read_csv(AI_CAPITAL_RETURNS), scenario="Base")[
        [
            "sector_id",
            "net_return_cf_2035",
            "gross_return_on_new_capital_2035",
            "net_return_on_new_capital_cf_2035",
        ]
    ]
    features = features.merge(ai_capital, on="sector_id", how="left")

    imports = read_csv(IMPORT_DEPENDENCY)[
        [
            "sector_id",
            "ict_digital_share_proxy_pct",
            "fixed_asset_renewal_pct",
            "import_dependency_score",
            "market_concentration_score",
            "sanction_wedge_base",
        ]
    ]
    features = features.merge(imports, on="sector_id", how="left")

    structure = selected_rows(
        read_csv(ECONOMY_STRUCTURE),
        scenario="Base",
        throttle_scenario="BaseThrottle",
    )[
        [
            "sector_id",
            "managed_obsolescence_pressure_score",
            "adaptation_managed_2030",
            "lp_gain_vs_cf_2030_pct",
            "cumulative_capex_2030_bn_rub",
            "cumulative_net_value_after_capex_2030_bn_rub",
            "incremental_profit_pool_2030_bn_rub",
        ]
    ]
    features = features.merge(structure, on="sector_id", how="left")

    climate = selected_rows(read_csv(CLIMATE_TRANSITION), complex_scenario="OrderlyTransition")[
        [
            "sector_id",
            "clean_energy_readiness",
            "ai_service_leverage",
            "transition_risk_score_2030",
            "strategy_capacity_index_2030",
        ]
    ]
    features = features.merge(climate, on="sector_id", how="left")

    io = selected_rows(read_csv(IO_MULTIPLIERS), record_type="sector", scenario="Base", throttle_scenario="BaseThrottle")
    if "table_year" in io.columns and not io.empty:
        io = io.loc[io["table_year"].eq(io["table_year"].max())].copy()
    io = io[["sector_id", "backward_linkage_multiplier", "io_total_output_gain_2035_bn_rub"]]
    features = features.merge(io, on="sector_id", how="left")

    return features.sort_values("sector_id").reset_index(drop=True)


def impute_numeric(series: pd.Series) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce").astype(float)
    if out.notna().any():
        return out.fillna(out.median())
    return pd.Series(0.0, index=series.index, dtype=float)


def normalize_series(series: pd.Series, positive: bool, method: str = "winsor", eps: float = EPS) -> pd.Series:
    x = impute_numeric(series)
    if method == "rank":
        ranks = x.rank(method="average", pct=True)
        z = ranks if positive else 1.0 - ranks + 1.0 / len(ranks)
        return z.clip(eps, 1.0)

    if method == "minmax":
        low = float(x.min())
        high = float(x.max())
        clipped = x
    elif method == "winsor":
        low = float(x.quantile(0.05))
        high = float(x.quantile(0.95))
        clipped = x.clip(low, high)
    else:
        raise ValueError(f"Unknown normalization method: {method}")

    if not np.isfinite(low) or not np.isfinite(high) or math.isclose(high, low):
        z = pd.Series(0.5, index=x.index, dtype=float)
    else:
        z = (clipped - low) / (high - low)
    if not positive:
        z = 1.0 - z
    return z.clip(eps, 1.0)


def normalized_matrix(raw: pd.DataFrame, specs: list[FeatureSpec], method: str) -> pd.DataFrame:
    columns = {}
    for spec in specs:
        columns[spec.column] = normalize_series(raw[spec.column], spec.positive, method=method)
    return pd.DataFrame(columns, index=raw.index)


def critic_weights(z: pd.DataFrame) -> pd.Series:
    if z.shape[1] == 0:
        raise ValueError("CRITIC cannot run with zero columns.")
    if z.shape[1] == 1:
        return pd.Series([1.0], index=z.columns)

    z = z.apply(pd.to_numeric, errors="coerce").fillna(0.5)
    sigma = z.std(axis=0, ddof=0)
    corr = z.corr().fillna(0.0).clip(-1.0, 1.0)
    contrast = (1.0 - corr).sum(axis=1)
    c = sigma * contrast
    total = float(c.sum())
    if not np.isfinite(total) or total <= 0:
        return pd.Series(1.0 / len(c), index=z.columns)
    return c / total


def aggregate(z: pd.DataFrame, weights: pd.Series, method: str) -> pd.Series:
    weights = weights.reindex(z.columns).fillna(0.0)
    if weights.sum() <= 0:
        weights = pd.Series(1.0 / z.shape[1], index=z.columns)
    else:
        weights = weights / weights.sum()

    z = z.clip(EPS, 1.0)
    if method == "geometric":
        return np.exp(np.log(z).mul(weights, axis=1).sum(axis=1))
    if method == "additive":
        return z.mul(weights, axis=1).sum(axis=1)
    raise ValueError(f"Unknown aggregation method: {method}")


def specs_to_columns(specs: dict[str, list[FeatureSpec]]) -> list[str]:
    columns: list[str] = []
    for block_specs in specs.values():
        for spec in block_specs:
            if spec.column not in columns:
                columns.append(spec.column)
    return columns


def filter_specs(specs: dict[str, list[FeatureSpec]], raw: pd.DataFrame) -> dict[str, list[FeatureSpec]]:
    filtered: dict[str, list[FeatureSpec]] = {}
    for block, block_specs in specs.items():
        available = [spec for spec in block_specs if spec.column in raw.columns]
        if available:
            filtered[block] = available
    return filtered


def equal_weight_bundle(specs: dict[str, list[FeatureSpec]]) -> dict[str, Any]:
    return {
        "indicator": {
            block: pd.Series(1.0 / len(block_specs), index=[spec.column for spec in block_specs])
            for block, block_specs in specs.items()
        },
        "block": pd.Series(1.0 / len(specs), index=list(specs)),
    }


def fit_hierarchical_critic(
    raw: pd.DataFrame,
    specs: dict[str, list[FeatureSpec]],
    *,
    normalization: str = "winsor",
    aggregation_method: str = "geometric",
    use_risk_gate: bool = True,
    fixed_weights: dict[str, Any] | None = None,
) -> dict[str, Any]:
    specs = filter_specs(specs, raw)
    block_scores = pd.DataFrame(index=raw.index)
    normalized_blocks: dict[str, pd.DataFrame] = {}
    indicator_weights: dict[str, pd.Series] = {}

    for block, block_specs in specs.items():
        z = normalized_matrix(raw, block_specs, method=normalization)
        normalized_blocks[block] = z
        if fixed_weights is None:
            weights = critic_weights(z)
        else:
            weights = fixed_weights["indicator"][block].reindex(z.columns).fillna(0.0)
            weights = weights / weights.sum() if weights.sum() > 0 else pd.Series(1.0 / z.shape[1], index=z.columns)
        indicator_weights[block] = weights
        block_scores[block] = aggregate(z, weights, method=aggregation_method)

    if fixed_weights is None:
        block_weights = critic_weights(block_scores)
    else:
        block_weights = fixed_weights["block"].reindex(block_scores.columns).fillna(0.0)
        block_weights = (
            block_weights / block_weights.sum()
            if block_weights.sum() > 0
            else pd.Series(1.0 / block_scores.shape[1], index=block_scores.columns)
        )

    base_index = aggregate(block_scores, block_weights, method=aggregation_method)
    if use_risk_gate and "financial_stability" in block_scores.columns:
        shortfall = (RISK_GATE_THRESHOLD - block_scores["financial_stability"]).clip(lower=0.0)
        risk_penalty = np.exp(-RISK_GATE_LAMBDA * shortfall.pow(2))
    else:
        risk_penalty = pd.Series(1.0, index=raw.index)

    resilience_index = base_index * risk_penalty
    ranks = resilience_index.rank(ascending=False, method="dense").astype(int)

    return {
        "normalized_blocks": normalized_blocks,
        "block_scores": block_scores,
        "indicator_weights": indicator_weights,
        "block_weights": block_weights,
        "base_index_no_gate": base_index,
        "financial_risk_penalty": risk_penalty,
        "resilience_index": resilience_index,
        "rank": ranks,
    }


def weights_to_frame(model: dict[str, Any], specs: dict[str, list[FeatureSpec]]) -> pd.DataFrame:
    rows = []
    block_labels = {
        "adaptive_potential": "Adaptive potential",
        "credit_potential": "Credit potential",
        "bank_profitability": "Bank profitability proxy",
        "financial_stability": "Financial stability",
        "strategic_convergence": "Strategic convergence",
    }
    for block, weight in model["block_weights"].items():
        rows.append(
            {
                "level": "block",
                "block": block,
                "criterion": block,
                "label": block_labels.get(block, block),
                "weight": weight,
            }
        )
    for block, weights in model["indicator_weights"].items():
        labels = {spec.column: spec.label for spec in specs.get(block, [])}
        directions = {spec.column: "positive" if spec.positive else "negative" for spec in specs.get(block, [])}
        for criterion, weight in weights.items():
            rows.append(
                {
                    "level": "indicator",
                    "block": block,
                    "criterion": criterion,
                    "label": labels.get(criterion, criterion),
                    "direction": directions.get(criterion, ""),
                    "weight": weight,
                }
            )
    return pd.DataFrame(rows)


def data_quality_frame(raw: pd.DataFrame, specs: dict[str, list[FeatureSpec]]) -> pd.DataFrame:
    rows = []
    for block, block_specs in specs.items():
        for spec in block_specs:
            series = pd.to_numeric(raw[spec.column], errors="coerce") if spec.column in raw.columns else pd.Series(dtype=float)
            rows.append(
                {
                    "block": block,
                    "criterion": spec.column,
                    "label": spec.label,
                    "direction": "positive" if spec.positive else "negative",
                    "n": len(raw),
                    "n_missing": int(series.isna().sum()) if len(series) else len(raw),
                    "missing_share": float(series.isna().mean()) if len(series) else 1.0,
                    "min": float(series.min()) if series.notna().any() else np.nan,
                    "median": float(series.median()) if series.notna().any() else np.nan,
                    "max": float(series.max()) if series.notna().any() else np.nan,
                }
            )
    return pd.DataFrame(rows)


def spearman_rank_corr(a: pd.Series, b: pd.Series) -> float:
    aligned = pd.concat([a, b], axis=1).dropna()
    if len(aligned) < 3:
        return float("nan")
    return float(aligned.iloc[:, 0].rank().corr(aligned.iloc[:, 1].rank()))


def kendall_tau_a(a: pd.Series, b: pd.Series) -> float:
    aligned = pd.concat([a, b], axis=1).dropna()
    if len(aligned) < 3:
        return float("nan")
    x = aligned.iloc[:, 0].to_numpy()
    y = aligned.iloc[:, 1].to_numpy()
    concordant = 0
    discordant = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            sx = np.sign(x[i] - x[j])
            sy = np.sign(y[i] - y[j])
            prod = sx * sy
            if prod > 0:
                concordant += 1
            elif prod < 0:
                discordant += 1
    denom = concordant + discordant
    if denom == 0:
        return float("nan")
    return float((concordant - discordant) / denom)


def top_overlap(a: pd.Series, b: pd.Series, k: int = 3) -> float:
    a_top = set(a.sort_values(ascending=False).head(k).index)
    b_top = set(b.sort_values(ascending=False).head(k).index)
    if not a_top:
        return float("nan")
    return len(a_top & b_top) / len(a_top)


def compare_to_base(base: pd.Series, alternative: pd.Series, check_type: str, variant: str) -> dict[str, Any]:
    return {
        "check_type": check_type,
        "variant": variant,
        "spearman": spearman_rank_corr(base, alternative),
        "kendall_tau": kendall_tau_a(base, alternative),
        "top3_overlap": top_overlap(base, alternative, k=min(3, len(base))),
    }


def clone_specs_without_feature(
    specs: dict[str, list[FeatureSpec]], block_to_edit: str, column_to_drop: str
) -> dict[str, list[FeatureSpec]]:
    out: dict[str, list[FeatureSpec]] = {}
    for block, block_specs in specs.items():
        if block == block_to_edit:
            kept = [spec for spec in block_specs if spec.column != column_to_drop]
            if kept:
                out[block] = kept
        else:
            out[block] = list(block_specs)
    return out


def clone_specs_without_block(specs: dict[str, list[FeatureSpec]], block_to_drop: str) -> dict[str, list[FeatureSpec]]:
    return {block: list(block_specs) for block, block_specs in specs.items() if block != block_to_drop}


def score_with_bootstrap_weights(
    raw: pd.DataFrame,
    specs: dict[str, list[FeatureSpec]],
    sample_positions: np.ndarray,
    normalization: str,
    aggregation_method: str,
) -> pd.Series:
    sampled = raw.iloc[sample_positions].copy()
    fitted = fit_hierarchical_critic(
        sampled,
        specs,
        normalization=normalization,
        aggregation_method=aggregation_method,
        use_risk_gate=True,
    )
    fixed = {
        "indicator": fitted["indicator_weights"],
        "block": fitted["block_weights"],
    }
    scored = fit_hierarchical_critic(
        raw,
        specs,
        normalization=normalization,
        aggregation_method=aggregation_method,
        use_risk_gate=True,
        fixed_weights=fixed,
    )
    return scored["resilience_index"]


def run_robustness_checks(
    raw: pd.DataFrame,
    specs: dict[str, list[FeatureSpec]],
    base_model: dict[str, Any],
    *,
    n_bootstrap: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    base = base_model["resilience_index"]
    rows = []

    for normalization in ["minmax", "rank"]:
        model = fit_hierarchical_critic(raw, specs, normalization=normalization, aggregation_method="geometric")
        rows.append(compare_to_base(base, model["resilience_index"], "normalization", normalization))

    additive = fit_hierarchical_critic(raw, specs, normalization="winsor", aggregation_method="additive")
    rows.append(compare_to_base(base, additive["resilience_index"], "aggregation", "additive"))

    no_gate = fit_hierarchical_critic(
        raw,
        specs,
        normalization="winsor",
        aggregation_method="geometric",
        use_risk_gate=False,
    )
    rows.append(compare_to_base(base, no_gate["resilience_index"], "risk_gate", "no_financial_gate"))

    equal_weights = fit_hierarchical_critic(
        raw,
        specs,
        normalization="winsor",
        aggregation_method="geometric",
        fixed_weights=equal_weight_bundle(filter_specs(specs, raw)),
    )
    rows.append(compare_to_base(base, equal_weights["resilience_index"], "weights", "equal_weights"))

    for block in specs:
        reduced = clone_specs_without_block(specs, block)
        model = fit_hierarchical_critic(raw, reduced, normalization="winsor", aggregation_method="geometric")
        rows.append(compare_to_base(base, model["resilience_index"], "leave_one_block", block))

    for block, block_specs in specs.items():
        if len(block_specs) <= 1:
            continue
        for spec in block_specs:
            reduced = clone_specs_without_feature(specs, block, spec.column)
            model = fit_hierarchical_critic(raw, reduced, normalization="winsor", aggregation_method="geometric")
            rows.append(compare_to_base(base, model["resilience_index"], "leave_one_indicator", f"{block}:{spec.column}"))

    for sector_id in raw.index:
        fitted_raw = raw.drop(index=sector_id)
        fitted = fit_hierarchical_critic(
            fitted_raw,
            specs,
            normalization="winsor",
            aggregation_method="geometric",
            use_risk_gate=True,
        )
        fixed = {"indicator": fitted["indicator_weights"], "block": fitted["block_weights"]}
        scored = fit_hierarchical_critic(
            raw,
            specs,
            normalization="winsor",
            aggregation_method="geometric",
            use_risk_gate=True,
            fixed_weights=fixed,
        )
        rows.append(compare_to_base(base, scored["resilience_index"], "leave_one_sector_weight_fit", str(sector_id)))

    for idx in range(n_bootstrap):
        positions = rng.integers(0, len(raw), size=len(raw))
        score = score_with_bootstrap_weights(raw, specs, positions, "winsor", "geometric")
        rows.append(compare_to_base(base, score, "bootstrap_sector_weights", f"bootstrap_{idx + 1:04d}"))

    checks = pd.DataFrame(rows)
    summary = (
        checks.groupby("check_type", as_index=False)
        .agg(
            n=("spearman", "size"),
            median_spearman=("spearman", "median"),
            p10_spearman=("spearman", lambda s: s.quantile(0.10)),
            min_spearman=("spearman", "min"),
            median_kendall=("kendall_tau", "median"),
            min_top3_overlap=("top3_overlap", "min"),
        )
        .sort_values("check_type")
    )
    summary["decision"] = np.select(
        [
            (summary["median_spearman"] >= 0.80) & (summary["p10_spearman"] >= 0.60),
            (summary["median_spearman"] >= 0.60) & (summary["p10_spearman"] >= 0.40),
        ],
        ["pass", "tentative"],
        default="fail",
    )
    return checks, summary


def build_historical_origin_features(panel: pd.DataFrame, origin_year: int, window: int = 4) -> pd.DataFrame:
    start_year = origin_year - window + 1
    current = panel.loc[panel["year"].eq(origin_year)].copy()
    current = current.dropna(subset=["va_current_bn_rub"])
    work = panel.loc[panel["year"].between(start_year, origin_year)].copy()
    work["labour_productivity"] = work["va_constant_2021_bn_rub"] / work["employment_thousand_persons"]
    work["margin_proxy"] = 1.0 - work["labour_share_proxy"]

    total_va = current["va_current_bn_rub"].sum()
    total_emp = current["employment_thousand_persons"].sum()
    rows = []
    for _, cur in current.iterrows():
        sector_id = cur["sector_id"]
        group = work.loc[work["sector_id"].eq(sector_id)].sort_values("year")
        if group.empty:
            continue
        margin_values = group[["year", "margin_proxy"]].dropna().sort_values("year")
        if len(margin_values) >= 2:
            margin_trend = (
                margin_values["margin_proxy"].iloc[-1] - margin_values["margin_proxy"].iloc[0]
            ) / (margin_values["year"].iloc[-1] - margin_values["year"].iloc[0])
        else:
            margin_trend = np.nan

        rows.append(
            {
                "year": origin_year,
                "sector_id": sector_id,
                "sector_name_ru": cur["sector_name_ru"],
                "okved": cur["okved"],
                "ai_intensity": cur["ai_intensity"],
                "hist_real_growth_median_pct": group["va_real_growth_pct"].median(),
                "hist_real_growth_volatility_pct": group["va_real_growth_pct"].std(ddof=0),
                "hist_min_real_growth_pct": group["va_real_growth_pct"].min(),
                "hist_deflator_volatility_pct": group["va_deflator_growth_pct"].std(ddof=0),
                "hist_va_real_cagr_pct": 100.0 * cagr_from_group(group, "va_constant_2021_bn_rub"),
                "hist_lp_cagr_pct": 100.0 * cagr_from_group(group, "labour_productivity"),
                "hist_va_share_current": cur["va_current_bn_rub"] / total_va if total_va > 0 else np.nan,
                "hist_employment_share_current": (
                    cur["employment_thousand_persons"] / total_emp if total_emp > 0 else np.nan
                ),
                "hist_va_current_cagr_pct": 100.0 * cagr_from_group(group, "va_current_bn_rub"),
                "hist_wage_cagr_pct": 100.0 * cagr_from_group(group, "avg_monthly_wage_rub"),
                "hist_margin_proxy_current": 1.0 - cur["labour_share_proxy"],
                "hist_margin_proxy_trend_pp": 100.0 * margin_trend,
                "hist_wage_level_current": cur["avg_monthly_wage_rub"],
                "hist_ai_intensity_score": AI_INTENSITY_SCORE.get(str(cur["ai_intensity"]), 0.5),
            }
        )
    return pd.DataFrame(rows).sort_values("sector_id").reset_index(drop=True)


def build_future_target(panel: pd.DataFrame, origin_year: int, horizon: int) -> pd.DataFrame:
    future = panel.loc[panel["year"].between(origin_year + 1, origin_year + horizon)].copy()
    rows = []
    for sector_id, group in future.groupby("sector_id"):
        growth = pd.to_numeric(group["va_real_growth_pct"], errors="coerce").dropna()
        if growth.empty:
            continue
        volatility = float(growth.std(ddof=0)) if len(growth) > 1 else 0.0
        mean_growth = float(growth.mean())
        min_growth = float(growth.min())
        target = mean_growth - 0.5 * volatility + 0.25 * min_growth
        rows.append(
            {
                "sector_id": sector_id,
                "future_mean_real_growth_pct": mean_growth,
                "future_growth_volatility_pct": volatility,
                "future_min_real_growth_pct": min_growth,
                "future_resilience_target": target,
            }
        )
    return pd.DataFrame(rows)


def robust_ols_slope(y: pd.Series, x: pd.Series) -> tuple[float, float]:
    data = pd.concat([y, x], axis=1).dropna()
    if len(data) < 5:
        return float("nan"), float("nan")
    yv = data.iloc[:, 0]
    xv = sm.add_constant(data.iloc[:, 1])
    try:
        model = sm.OLS(yv, xv).fit(cov_type="HC3")
    except Exception:
        return float("nan"), float("nan")
    return float(model.params.iloc[1]), float(model.pvalues.iloc[1])


def run_historical_backtest(panel: pd.DataFrame, origin_years: list[int], horizons: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for origin_year in origin_years:
        raw = build_historical_origin_features(panel, origin_year, window=4)
        if raw.empty or raw["sector_id"].nunique() < 5:
            continue
        raw = raw.set_index("sector_id")
        model = fit_hierarchical_critic(
            raw,
            HISTORICAL_SPECS,
            normalization="winsor",
            aggregation_method="geometric",
            use_risk_gate=True,
        )
        score = model["resilience_index"].rename("score")
        rank = model["rank"].rename("rank")
        for horizon in horizons:
            target = build_future_target(panel, origin_year, horizon).set_index("sector_id")
            joined = pd.concat([score, rank, target], axis=1).dropna(subset=["score", "future_resilience_target"])
            if len(joined) < 5:
                continue
            top_n = max(2, math.ceil(len(joined) * 0.30))
            top = joined.sort_values("score", ascending=False).head(top_n)
            bottom = joined.sort_values("score", ascending=True).head(top_n)
            slope, pvalue = robust_ols_slope(joined["future_resilience_target"], joined["score"])
            rows.append(
                {
                    "origin_year": origin_year,
                    "horizon_years": horizon,
                    "n_sectors": len(joined),
                    "spearman": spearman_rank_corr(joined["score"], joined["future_resilience_target"]),
                    "kendall_tau": kendall_tau_a(joined["score"], joined["future_resilience_target"]),
                    "top_bottom_spread_pp": top["future_resilience_target"].mean()
                    - bottom["future_resilience_target"].mean(),
                    "ols_slope_hc3": slope,
                    "ols_pvalue_hc3": pvalue,
                    "target_mean": joined["future_resilience_target"].mean(),
                    "target_std": joined["future_resilience_target"].std(ddof=0),
                    "top_sectors": ", ".join(top.index.astype(str)),
                    "bottom_sectors": ", ".join(bottom.index.astype(str)),
                }
            )
    backtest = pd.DataFrame(rows)
    if backtest.empty:
        return backtest, backtest

    summary = (
        backtest.groupby("horizon_years", as_index=False)
        .agg(
            n_origins=("origin_year", "nunique"),
            median_spearman=("spearman", "median"),
            mean_spearman=("spearman", "mean"),
            share_positive_spearman=("spearman", lambda s: float((s > 0).mean())),
            median_kendall=("kendall_tau", "median"),
            mean_top_bottom_spread_pp=("top_bottom_spread_pp", "mean"),
            share_positive_top_bottom_spread=("top_bottom_spread_pp", lambda s: float((s > 0).mean())),
            median_ols_slope=("ols_slope_hc3", "median"),
            share_positive_ols_slope=("ols_slope_hc3", lambda s: float((s > 0).mean())),
        )
        .sort_values("horizon_years")
    )
    summary["decision"] = np.select(
        [
            (summary["median_spearman"] >= 0.30) & (summary["share_positive_top_bottom_spread"] >= 0.70),
            (summary["median_spearman"] > 0.00) & (summary["share_positive_top_bottom_spread"] >= 0.60),
        ],
        ["pass", "tentative"],
        default="fail",
    )
    return backtest, summary


def plot_outputs(ranking: pd.DataFrame, weights: pd.DataFrame, robustness: pd.DataFrame, backtest: pd.DataFrame) -> None:
    if plt is None:
        print("matplotlib is not installed; skipping figures.")
        return

    FIG_DIR.mkdir(parents=True, exist_ok=True)

    top = ranking.sort_values("resilience_index", ascending=True)
    plt.figure(figsize=(9, 5.5))
    plt.barh(top["sector_name_ru"], top["resilience_index"], color="#2f6f73")
    plt.xlabel("CRITIC resilience index")
    plt.title("OKVED sector resilience ranking, base model")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "okved_resilience_ranking_2024.png", dpi=180)
    plt.close()

    block_weights = weights.loc[weights["level"].eq("block")].sort_values("weight", ascending=True)
    plt.figure(figsize=(8, 4.5))
    plt.barh(block_weights["label"], block_weights["weight"], color="#6b5b95")
    plt.xlabel("CRITIC weight")
    plt.title("Top-level block weights")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "okved_resilience_block_weights_2024.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8.5, 5))
    plot_data = robustness.copy()
    order = plot_data.groupby("check_type")["spearman"].median().sort_values().index
    data = [plot_data.loc[plot_data["check_type"].eq(check), "spearman"].dropna().to_numpy() for check in order]
    plt.boxplot(data, labels=order, vert=False)
    plt.axvline(0.8, color="#2f6f73", linestyle="--", linewidth=1)
    plt.axvline(0.6, color="#b5651d", linestyle=":", linewidth=1)
    plt.xlabel("Spearman rank correlation vs base ranking")
    plt.title("Robustness of sector ranks")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "okved_resilience_robustness_2024.png", dpi=180)
    plt.close()

    if not backtest.empty:
        plt.figure(figsize=(8.5, 5))
        for horizon, group in backtest.groupby("horizon_years"):
            group = group.sort_values("origin_year")
            plt.plot(group["origin_year"], group["spearman"], marker="o", label=f"h={horizon}")
        plt.axhline(0, color="#444444", linewidth=0.8)
        plt.xlabel("Origin year")
        plt.ylabel("Spearman(score, future target)")
        plt.title("Historical rolling-origin backtest")
        plt.legend(title="Horizon")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "okved_resilience_historical_backtest.png", dpi=180)
        plt.close()


def df_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    work = df.copy()
    for column in work.columns:
        work[column] = work[column].map(lambda value: "" if pd.isna(value) else str(value))
    header = "| " + " | ".join(work.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(work.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in work.to_numpy(dtype=str)]
    return "\n".join([header, separator, *rows])


def write_report(
    ranking: pd.DataFrame,
    weights: pd.DataFrame,
    robustness_summary: pd.DataFrame,
    backtest_summary: pd.DataFrame,
    metadata: dict[str, Any],
) -> None:
    top_rows = ranking.sort_values("rank").head(10)
    top_table = top_rows[
        [
            "rank",
            "sector_id",
            "sector_name_ru",
            "okved",
            "resilience_index",
            "adaptive_potential",
            "credit_potential",
            "bank_profitability",
            "financial_stability",
            "strategic_convergence",
        ]
    ].copy()
    for column in top_table.select_dtypes(include=[np.number]).columns:
        if column != "rank":
            top_table[column] = top_table[column].round(3)

    block_table = weights.loc[weights["level"].eq("block"), ["criterion", "label", "weight"]].copy()
    block_table["weight"] = block_table["weight"].round(3)

    robust_table = robustness_summary.copy()
    for column in robust_table.select_dtypes(include=[np.number]).columns:
        robust_table[column] = robust_table[column].round(3)

    backtest_table = backtest_summary.copy()
    if not backtest_table.empty:
        for column in backtest_table.select_dtypes(include=[np.number]).columns:
            backtest_table[column] = backtest_table[column].round(3)

    lines = [
        "# CRITIC-модель устойчивости отраслей по ОКВЭД",
        "",
        "## Постановка",
        "",
        "Индекс строится как иерархический CRITIC: сначала CRITIC-веса внутри пяти блоков, затем CRITIC-веса самих блоков. "
        "Агрегация базово геометрическая, чтобы слабый блок не полностью компенсировался сильным. Для банковской логики добавлен мягкий risk-gate по финансовой устойчивости:",
        "",
        r"$$R_i=\left(\prod_b B_{ib}^{W_b}\right)\exp\{-\lambda\max(0,\delta-B_{i,financial})^2\},$$",
        "",
        f"где $\\delta={RISK_GATE_THRESHOLD}$, $\\lambda={RISK_GATE_LAMBDA}$. "
        "Данные банковской доходности и кредитного портфеля в папке отсутствуют, поэтому эти блоки собраны как явно помеченные отраслевые прокси.",
        "",
        "## Топ-уровневые веса",
        "",
        df_to_markdown(block_table),
        "",
        "## Рейтинг 2024",
        "",
        df_to_markdown(top_table),
        "",
        "## Робастность рангов",
        "",
        df_to_markdown(robust_table),
        "",
        "Правило: `pass`, если медианная Spearman-корреляция с базовым рейтингом >= 0.80 и 10-й перцентиль >= 0.60; "
        "`tentative`, если >= 0.60 и >= 0.40; иначе `fail`.",
        "",
        "## Исторический rolling-origin backtest",
        "",
        "Историческая версия использует только официальные метрики, доступные в панели 2011-2025: рост ВДС, волатильность, доли ВДС/занятости, зарплаты, proxy margin и класс AI-интенсивности. "
        "Целевая переменная:",
        "",
        r"$$Y_{i,t,h}=\bar g_{i,t+1:t+h}-0.5\sigma(g_{i,t+1:t+h})+0.25\min(g_{i,t+1:t+h}).$$",
        "",
        df_to_markdown(backtest_table) if not backtest_table.empty else "Backtest не построен: недостаточно исторических наблюдений.",
        "",
        "Правило: `pass`, если median Spearman >= 0.30 и top-bottom spread положителен минимум в 70% origin-years; "
        "`tentative`, если median Spearman > 0 и spread положителен минимум в 60%; иначе `fail`.",
        "",
        "## Воспроизводимость",
        "",
        f"- Скрипт: `python scripts/build_okved_resilience_model.py --bootstrap {metadata['n_bootstrap']} --seed {metadata['seed']}`",
        f"- Матрица признаков: `{FEATURE_MATRIX_PATH.relative_to(ROOT)}`",
        f"- Рейтинг: `{RANKING_PATH.relative_to(ROOT)}`",
        f"- Веса: `{WEIGHTS_PATH.relative_to(ROOT)}`",
        f"- Робастность: `{ROBUSTNESS_PATH.relative_to(ROOT)}`",
        f"- Backtest: `{BACKTEST_PATH.relative_to(ROOT)}`",
        "",
        "## Ограничения",
        "",
        "- Наблюдений всего 10 секторов, поэтому CRITIC-веса чувствительны к составу отраслей; bootstrap/leave-one-sector это прямо проверяют.",
        "- Банковские метрики заменены прокси; для production-версии нужны фактические RAROC, cost of risk, NPL, лимиты, портфель и выдачи по ОКВЭД.",
        "- Исторический backtest проверяет не тот же полный forward-рейтинг, а его официальную историческую проекцию без AI/климат/капиталоотдачи будущих сценариев.",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a CRITIC-based OKVED sector resilience model.")
    parser.add_argument("--bootstrap", type=int, default=500, help="Number of sector bootstrap draws for robustness.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--skip-figures", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_features = build_feature_matrix_2024()
    model_raw = raw_features.set_index("sector_id")
    model = fit_hierarchical_critic(model_raw, MODEL_SPECS, normalization="winsor", aggregation_method="geometric")

    block_scores = model["block_scores"].copy()
    block_scores["base_index_no_gate"] = model["base_index_no_gate"]
    block_scores["financial_risk_penalty"] = model["financial_risk_penalty"]
    block_scores["resilience_index"] = model["resilience_index"]
    block_scores["rank"] = model["rank"]
    block_scores = block_scores.reset_index()

    ranking = raw_features[
        ["sector_id", "sector_name_ru", "okved", "ai_intensity", "va_current_bn_rub", "va_share_2024"]
    ].merge(block_scores, on="sector_id", how="left")
    ranking = ranking.sort_values(["rank", "sector_id"]).reset_index(drop=True)

    weights = weights_to_frame(model, MODEL_SPECS)
    data_quality = data_quality_frame(raw_features, MODEL_SPECS)
    robustness, robustness_summary = run_robustness_checks(
        model_raw,
        MODEL_SPECS,
        model,
        n_bootstrap=args.bootstrap,
        seed=args.seed,
    )

    panel = read_csv(OFFICIAL_PANEL)
    backtest, backtest_summary = run_historical_backtest(panel, origin_years=list(range(2018, 2023)), horizons=[1, 2, 3])

    raw_features.to_csv(FEATURE_MATRIX_PATH, index=False)
    block_scores.to_csv(BLOCK_SCORES_PATH, index=False)
    ranking.to_csv(RANKING_PATH, index=False)
    weights.to_csv(WEIGHTS_PATH, index=False)
    robustness.to_csv(ROBUSTNESS_PATH, index=False)
    robustness_summary.to_csv(ROBUSTNESS_SUMMARY_PATH, index=False)
    backtest.to_csv(BACKTEST_PATH, index=False)
    backtest_summary.to_csv(BACKTEST_SUMMARY_PATH, index=False)
    data_quality.to_csv(DATA_QUALITY_PATH, index=False)

    metadata = {
        "model": "hierarchical_critic_geometric_with_financial_risk_gate",
        "seed": args.seed,
        "n_bootstrap": args.bootstrap,
        "risk_gate_threshold": RISK_GATE_THRESHOLD,
        "risk_gate_lambda": RISK_GATE_LAMBDA,
        "inputs": [
            str(path.relative_to(ROOT))
            for path in [
                OFFICIAL_PANEL,
                BASELINE_2024,
                AI_DIFFUSION,
                AI_CAPITAL_RETURNS,
                IMPORT_DEPENDENCY,
                ECONOMY_STRUCTURE,
                CLIMATE_TRANSITION,
                IO_MULTIPLIERS,
            ]
        ],
        "outputs": [
            str(path.relative_to(ROOT))
            for path in [
                FEATURE_MATRIX_PATH,
                BLOCK_SCORES_PATH,
                RANKING_PATH,
                WEIGHTS_PATH,
                ROBUSTNESS_PATH,
                ROBUSTNESS_SUMMARY_PATH,
                BACKTEST_PATH,
                BACKTEST_SUMMARY_PATH,
                DATA_QUALITY_PATH,
                DOC_PATH,
            ]
        ],
    }
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_figures:
        plot_outputs(ranking, weights, robustness, backtest)

    write_report(ranking, weights, robustness_summary, backtest_summary, metadata)

    print(f"Wrote {RANKING_PATH.relative_to(ROOT)}")
    print(f"Wrote {ROBUSTNESS_SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Wrote {BACKTEST_SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Wrote {DOC_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

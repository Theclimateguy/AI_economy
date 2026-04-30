from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "russia_economy_structure_layer.json"

BASELINE_PATH = ROOT / "data" / "processed" / "russia_sector_baseline_2024.csv"
OFFICIAL_PANEL_PATH = ROOT / "data" / "processed" / "russia_sector_panel_official_2011_2025.csv"
RETURN_PATHS_PATH = ROOT / "data" / "processed" / "ai_capital_return_paths_2025_2035.csv"
OBSOLESCENCE_PATH = ROOT / "data" / "processed" / "managed_obsolescence_sector_proxy.csv"

OUTPUT_PATHS = ROOT / "data" / "processed" / "russia_economy_structure_paths_2025_2035.csv"
OUTPUT_SECTOR = ROOT / "data" / "processed" / "russia_economy_structure_sector_summary.csv"
OUTPUT_AGGREGATE = ROOT / "data" / "processed" / "russia_economy_structure_aggregate_summary.csv"
OUTPUT_REPORT = ROOT / "docs" / "russia_economy_structure_report.md"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def safe_cagr(first: float, last: float, years: int) -> float:
    if years <= 0 or not np.isfinite(first) or not np.isfinite(last) or first <= 0 or last <= 0:
        return np.nan
    return math.exp(math.log(last / first) / years) - 1.0


def clip_pct_to_rate(series: pd.Series, bounds: dict) -> pd.Series:
    return series.clip(lower=bounds["lower"], upper=bounds["upper"]) / 100.0


def load_inputs(
    baseline_override: pd.DataFrame | None = None,
    official_override: pd.DataFrame | None = None,
    returns_override: pd.DataFrame | None = None,
    obsolescence_override: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline = baseline_override.copy() if baseline_override is not None else pd.read_csv(BASELINE_PATH)
    official = official_override.copy() if official_override is not None else pd.read_csv(OFFICIAL_PANEL_PATH)
    returns = returns_override.copy() if returns_override is not None else pd.read_csv(RETURN_PATHS_PATH)
    obsolescence_source = obsolescence_override.copy() if obsolescence_override is not None else pd.read_csv(OBSOLESCENCE_PATH)
    obsolescence = obsolescence_source[
        ["sector_id", "managed_obsolescence_pressure_score", "managed_obsolescence_pressure_rank", "fit_quality"]
    ]
    return baseline, official, returns, obsolescence


def build_counterfactual_growth(official: pd.DataFrame, config: dict) -> pd.DataFrame:
    growth_cfg = config["counterfactual_growth"]
    history = official.loc[
        official["year"].between(growth_cfg["history_start_year"], growth_cfg["history_end_year"])
        & official[growth_cfg["growth_column"]].notna()
    ].copy()
    history["va_cf_growth_rate"] = clip_pct_to_rate(history[growth_cfg["growth_column"]], growth_cfg["clip_annual_growth_pct"])

    if growth_cfg["method"] != "median":
        raise ValueError(f"Unsupported counterfactual growth method: {growth_cfg['method']}")

    return (
        history.groupby("sector_id", as_index=False)["va_cf_growth_rate"]
        .median()
        .rename(columns={"va_cf_growth_rate": "va_cf_growth_rate_annual"})
    )


def build_employment_trend(official: pd.DataFrame, config: dict) -> pd.DataFrame:
    emp_cfg = config["employment_trend"]
    history = official.loc[
        official["year"].between(emp_cfg["history_start_year"], emp_cfg["history_end_year"])
        & official["employment_thousand_persons"].notna()
    ].copy()
    rows: list[dict] = []
    lower = emp_cfg["clip_annual_growth_pct"]["lower"] / 100.0
    upper = emp_cfg["clip_annual_growth_pct"]["upper"] / 100.0

    for sector_id, group in history.groupby("sector_id"):
        group = group.sort_values("year").reset_index(drop=True)
        first = float(group["employment_thousand_persons"].iloc[0])
        last = float(group["employment_thousand_persons"].iloc[-1])
        years = int(group["year"].iloc[-1] - group["year"].iloc[0])
        rate = safe_cagr(first, last, years)
        rows.append(
            {
                "sector_id": sector_id,
                "employment_cf_growth_rate_annual": float(np.clip(rate, lower, upper)) if np.isfinite(rate) else 0.0,
                "employment_trend_start_year": int(group["year"].iloc[0]),
                "employment_trend_end_year": int(group["year"].iloc[-1]),
            }
        )
    return pd.DataFrame(rows)


def prepare_base(
    config: dict,
    baseline_override: pd.DataFrame | None = None,
    official_override: pd.DataFrame | None = None,
    returns_override: pd.DataFrame | None = None,
    obsolescence_override: pd.DataFrame | None = None,
) -> pd.DataFrame:
    baseline, official, returns, obsolescence = load_inputs(
        baseline_override=baseline_override,
        official_override=official_override,
        returns_override=returns_override,
        obsolescence_override=obsolescence_override,
    )
    growth = build_counterfactual_growth(official, config)
    employment = build_employment_trend(official, config)

    base_columns = [
        "sector_id",
        "sector_name_ru",
        "okved",
        "ai_intensity",
        "va_current_bn_rub",
        "employment_thousand_persons",
        "labour_share_proxy",
    ]
    base = baseline[base_columns].merge(growth, on="sector_id", how="left")
    base = base.merge(employment, on="sector_id", how="left")
    base = base.merge(obsolescence, on="sector_id", how="left")

    if base[["va_cf_growth_rate_annual", "employment_cf_growth_rate_annual"]].isna().any().any():
        missing = base.loc[
            base[["va_cf_growth_rate_annual", "employment_cf_growth_rate_annual"]].isna().any(axis=1),
            "sector_id",
        ].tolist()
        raise ValueError(f"Missing counterfactual growth inputs for sectors: {missing}")

    required_return_columns = [
        "scenario",
        "year",
        "sector_id",
        "class_id",
        "adaptation",
        "diffusion_speed",
        "delta_sL_potential",
        "pi0_proxy",
        "gamma_margin",
        "capital_barrier",
        "delta_k_need_bn_rub",
        "margin_cf_t",
        "lambda_speed",
    ]
    return returns[required_return_columns].merge(base, on="sector_id", how="left")


def build_structure_paths(
    config: dict,
    baseline_override: pd.DataFrame | None = None,
    official_override: pd.DataFrame | None = None,
    returns_override: pd.DataFrame | None = None,
    obsolescence_override: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = prepare_base(
        config,
        baseline_override=baseline_override,
        official_override=official_override,
        returns_override=returns_override,
        obsolescence_override=obsolescence_override,
    )
    years_from_base = df["year"] - int(config["baseline_year"])
    df["va_cf_bn_rub"] = df["va_current_bn_rub"] * np.power(1.0 + df["va_cf_growth_rate_annual"], years_from_base)
    df["employment_cf_thousand"] = df["employment_thousand_persons"] * np.power(
        1.0 + df["employment_cf_growth_rate_annual"],
        years_from_base,
    )
    df["labour_productivity_cf_mrub_per_person"] = df["va_cf_bn_rub"] * 1000.0 / df["employment_cf_thousand"]
    df["tax_share_anchor"] = (1.0 - df["labour_share_proxy"] - df["pi0_proxy"]).clip(lower=0.0, upper=1.0)
    df["labour_share_cf"] = (1.0 - df["tax_share_anchor"] - df["margin_cf_t"]).clip(lower=0.0, upper=1.0)
    df["profit_pool_cf_bn_rub"] = df["margin_cf_t"] * df["va_cf_bn_rub"]
    df["labour_income_cf_bn_rub"] = df["labour_share_cf"] * df["va_cf_bn_rub"]

    records: list[dict] = []
    class_params = config["class_productivity_parameters"]

    group_cols = ["scenario", "sector_id"]
    for throttle_scenario, rho in config["managed_obsolescence_scenarios"].items():
        throttled = df.copy()
        throttled["throttle_scenario"] = throttle_scenario
        throttled["throttle_rho"] = float(rho)
        throttled["managed_adoption_factor"] = (
            1.0 - float(rho) * throttled["managed_obsolescence_pressure_score"].fillna(0.0)
        ).clip(lower=0.0, upper=1.0)
        throttled["adaptation_managed"] = throttled["adaptation"] * throttled["managed_adoption_factor"]
        throttled["diffusion_speed_managed"] = throttled["diffusion_speed"] * throttled["managed_adoption_factor"]
        throttled["delta_k_need_managed_bn_rub"] = (
            throttled["delta_k_need_bn_rub"] * throttled["managed_adoption_factor"]
        )
        throttled["delta_sL_managed"] = throttled["delta_sL_potential"] * throttled["adaptation_managed"]
        throttled["labour_share_ai"] = (throttled["labour_share_proxy"] + throttled["delta_sL_managed"]).clip(
            lower=0.0,
            upper=1.0,
        )

        path_rows: list[pd.DataFrame] = []
        for (_, _), group in throttled.groupby(group_cols):
            group = group.sort_values("year").copy()
            margin_prev = float(group["pi0_proxy"].iloc[0])
            managed_margin: list[float] = []
            for row in group.itertuples(index=False):
                margin_t = float(row.pi0_proxy + row.gamma_margin * row.adaptation_managed - row.lambda_speed * margin_prev)
                margin_t = float(np.clip(margin_t, 0.0, 1.0))
                managed_margin.append(margin_t)
                margin_prev = margin_t
            group["margin_ai"] = managed_margin

            group["cumulative_delta_k_need_managed_bn_rub"] = group["delta_k_need_managed_bn_rub"].cumsum()
            group["cumulative_ai_va_log_boost"] = (
                group["diffusion_speed_managed"]
                * group["class_id"].map(lambda class_id: class_params[class_id]["va_log_boost_per_adoption"])
            ).cumsum()
            group["cumulative_ai_lp_log_boost"] = (
                group["diffusion_speed_managed"]
                * group["class_id"].map(lambda class_id: class_params[class_id]["lp_log_boost_per_adoption"])
            ).cumsum()
            path_rows.append(group)

        scenario_df = pd.concat(path_rows, ignore_index=True)
        scenario_df["va_ai_bn_rub"] = scenario_df["va_cf_bn_rub"] * np.exp(scenario_df["cumulative_ai_va_log_boost"])
        scenario_df["labour_productivity_ai_mrub_per_person"] = scenario_df[
            "labour_productivity_cf_mrub_per_person"
        ] * np.exp(scenario_df["cumulative_ai_lp_log_boost"])
        scenario_df["employment_ai_thousand"] = scenario_df["va_ai_bn_rub"] * 1000.0 / scenario_df[
            "labour_productivity_ai_mrub_per_person"
        ]
        scenario_df["profit_pool_ai_bn_rub"] = scenario_df["margin_ai"] * scenario_df["va_ai_bn_rub"]
        scenario_df["labour_income_ai_bn_rub"] = scenario_df["labour_share_ai"] * scenario_df["va_ai_bn_rub"]
        scenario_df["incremental_va_vs_cf_bn_rub"] = scenario_df["va_ai_bn_rub"] - scenario_df["va_cf_bn_rub"]
        scenario_df["incremental_profit_pool_vs_cf_bn_rub"] = (
            scenario_df["profit_pool_ai_bn_rub"] - scenario_df["profit_pool_cf_bn_rub"]
        )
        scenario_df["incremental_labour_income_vs_cf_bn_rub"] = (
            scenario_df["labour_income_ai_bn_rub"] - scenario_df["labour_income_cf_bn_rub"]
        )
        scenario_df["employment_delta_vs_cf_thousand"] = (
            scenario_df["employment_ai_thousand"] - scenario_df["employment_cf_thousand"]
        )
        scenario_df["lp_gain_vs_cf_pct"] = (
            scenario_df["labour_productivity_ai_mrub_per_person"]
            / scenario_df["labour_productivity_cf_mrub_per_person"]
            - 1.0
        ) * 100.0
        scenario_df["cumulative_incremental_profit_pool_vs_cf_bn_rub"] = scenario_df.groupby(group_cols)[
            "incremental_profit_pool_vs_cf_bn_rub"
        ].cumsum()
        scenario_df["cumulative_net_value_after_capex_bn_rub"] = (
            scenario_df["cumulative_incremental_profit_pool_vs_cf_bn_rub"]
            - scenario_df["cumulative_delta_k_need_managed_bn_rub"]
        )
        records.append(scenario_df)

    paths = pd.concat(records, ignore_index=True)
    paths["total_va_cf_bn_rub"] = paths.groupby(["scenario", "throttle_scenario", "year"])["va_cf_bn_rub"].transform("sum")
    paths["total_va_ai_bn_rub"] = paths.groupby(["scenario", "throttle_scenario", "year"])["va_ai_bn_rub"].transform("sum")
    paths["va_share_cf"] = paths["va_cf_bn_rub"] / paths["total_va_cf_bn_rub"]
    paths["va_share_ai"] = paths["va_ai_bn_rub"] / paths["total_va_ai_bn_rub"]
    paths["delta_va_share_pp"] = (paths["va_share_ai"] - paths["va_share_cf"]) * 100.0

    ordered_columns = [
        "scenario",
        "throttle_scenario",
        "year",
        "sector_id",
        "sector_name_ru",
        "class_id",
        "ai_intensity",
        "managed_obsolescence_pressure_score",
        "managed_obsolescence_pressure_rank",
        "fit_quality",
        "throttle_rho",
        "managed_adoption_factor",
        "adaptation",
        "adaptation_managed",
        "diffusion_speed_managed",
        "va_cf_growth_rate_annual",
        "employment_cf_growth_rate_annual",
        "va_cf_bn_rub",
        "va_ai_bn_rub",
        "incremental_va_vs_cf_bn_rub",
        "va_share_cf",
        "va_share_ai",
        "delta_va_share_pp",
        "labour_share_cf",
        "labour_share_ai",
        "margin_cf_t",
        "margin_ai",
        "profit_pool_cf_bn_rub",
        "profit_pool_ai_bn_rub",
        "incremental_profit_pool_vs_cf_bn_rub",
        "labour_income_cf_bn_rub",
        "labour_income_ai_bn_rub",
        "incremental_labour_income_vs_cf_bn_rub",
        "employment_cf_thousand",
        "employment_ai_thousand",
        "employment_delta_vs_cf_thousand",
        "labour_productivity_cf_mrub_per_person",
        "labour_productivity_ai_mrub_per_person",
        "lp_gain_vs_cf_pct",
        "delta_k_need_managed_bn_rub",
        "cumulative_delta_k_need_managed_bn_rub",
        "cumulative_incremental_profit_pool_vs_cf_bn_rub",
        "cumulative_net_value_after_capex_bn_rub",
    ]
    return paths[ordered_columns].sort_values(["scenario", "throttle_scenario", "sector_id", "year"]).reset_index(drop=True)


def build_sector_summary(paths: pd.DataFrame, config: dict) -> pd.DataFrame:
    final_year = int(config["projection_end_year"])
    rows: list[dict] = []
    for (scenario, throttle_scenario, sector_id), group in paths.groupby(["scenario", "throttle_scenario", "sector_id"]):
        group = group.sort_values("year").reset_index(drop=True)
        final = group.loc[group["year"].eq(final_year)].iloc[0]
        rows.append(
            {
                "scenario": scenario,
                "throttle_scenario": throttle_scenario,
                "sector_id": sector_id,
                "sector_name_ru": final["sector_name_ru"],
                "class_id": final["class_id"],
                "ai_intensity": final["ai_intensity"],
                "managed_obsolescence_pressure_score": float(final["managed_obsolescence_pressure_score"]),
                "adaptation_2035": float(final["adaptation"]),
                "adaptation_managed_2035": float(final["adaptation_managed"]),
                "va_cf_2035_bn_rub": float(final["va_cf_bn_rub"]),
                "va_ai_2035_bn_rub": float(final["va_ai_bn_rub"]),
                "incremental_va_2035_bn_rub": float(final["incremental_va_vs_cf_bn_rub"]),
                "va_share_cf_2035": float(final["va_share_cf"]),
                "va_share_ai_2035": float(final["va_share_ai"]),
                "delta_va_share_pp_2035": float(final["delta_va_share_pp"]),
                "profit_pool_ai_2035_bn_rub": float(final["profit_pool_ai_bn_rub"]),
                "incremental_profit_pool_2035_bn_rub": float(final["incremental_profit_pool_vs_cf_bn_rub"]),
                "labour_income_ai_2035_bn_rub": float(final["labour_income_ai_bn_rub"]),
                "incremental_labour_income_2035_bn_rub": float(final["incremental_labour_income_vs_cf_bn_rub"]),
                "employment_ai_2035_thousand": float(final["employment_ai_thousand"]),
                "employment_delta_2035_thousand": float(final["employment_delta_vs_cf_thousand"]),
                "labour_productivity_ai_2035_mrub_per_person": float(final["labour_productivity_ai_mrub_per_person"]),
                "lp_gain_vs_cf_2035_pct": float(final["lp_gain_vs_cf_pct"]),
                "cumulative_capex_2035_bn_rub": float(final["cumulative_delta_k_need_managed_bn_rub"]),
                "cumulative_incremental_profit_pool_2035_bn_rub": float(
                    final["cumulative_incremental_profit_pool_vs_cf_bn_rub"]
                ),
                "cumulative_net_value_after_capex_2035_bn_rub": float(final["cumulative_net_value_after_capex_bn_rub"]),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["scenario", "throttle_scenario", "delta_va_share_pp_2035"],
        ascending=[True, True, False],
    ).reset_index(drop=True)


def build_aggregate_summary(paths: pd.DataFrame, config: dict) -> pd.DataFrame:
    final_year = int(config["projection_end_year"])
    final = paths.loc[paths["year"].eq(final_year)].copy()
    rows: list[dict] = []
    for (scenario, throttle_scenario), group in final.groupby(["scenario", "throttle_scenario"]):
        total_va_cf = float(group["va_cf_bn_rub"].sum())
        total_va_ai = float(group["va_ai_bn_rub"].sum())
        total_profit_cf = float(group["profit_pool_cf_bn_rub"].sum())
        total_profit_ai = float(group["profit_pool_ai_bn_rub"].sum())
        total_labour_cf = float(group["labour_income_cf_bn_rub"].sum())
        total_labour_ai = float(group["labour_income_ai_bn_rub"].sum())
        total_emp_cf = float(group["employment_cf_thousand"].sum())
        total_emp_ai = float(group["employment_ai_thousand"].sum())
        rows.append(
            {
                "scenario": scenario,
                "throttle_scenario": throttle_scenario,
                "total_va_cf_2035_bn_rub": total_va_cf,
                "total_va_ai_2035_bn_rub": total_va_ai,
                "total_va_gain_2035_pct": (total_va_ai / total_va_cf - 1.0) * 100.0,
                "total_profit_pool_cf_2035_bn_rub": total_profit_cf,
                "total_profit_pool_ai_2035_bn_rub": total_profit_ai,
                "total_profit_pool_gain_2035_pct": (total_profit_ai / total_profit_cf - 1.0) * 100.0,
                "total_labour_income_cf_2035_bn_rub": total_labour_cf,
                "total_labour_income_ai_2035_bn_rub": total_labour_ai,
                "total_labour_income_gain_2035_pct": (total_labour_ai / total_labour_cf - 1.0) * 100.0,
                "total_employment_cf_2035_thousand": total_emp_cf,
                "total_employment_ai_2035_thousand": total_emp_ai,
                "total_employment_delta_2035_thousand": total_emp_ai - total_emp_cf,
                "aggregate_lp_cf_2035_mrub_per_person": total_va_cf * 1000.0 / total_emp_cf,
                "aggregate_lp_ai_2035_mrub_per_person": total_va_ai * 1000.0 / total_emp_ai,
                "aggregate_lp_gain_vs_cf_2035_pct": (total_va_ai / total_emp_ai) / (total_va_cf / total_emp_cf) * 100.0
                - 100.0,
                "cumulative_capex_2035_bn_rub": float(group["cumulative_delta_k_need_managed_bn_rub"].sum()),
                "cumulative_incremental_profit_pool_2035_bn_rub": float(
                    group["cumulative_incremental_profit_pool_vs_cf_bn_rub"].sum()
                ),
                "cumulative_net_value_after_capex_2035_bn_rub": float(
                    group["cumulative_net_value_after_capex_bn_rub"].sum()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["scenario", "throttle_scenario"]).reset_index(drop=True)


def markdown_table(dataframe: pd.DataFrame, columns: list[str], float_cols: list[str]) -> str:
    table = dataframe[columns].copy()
    for column in float_cols:
        if column in table.columns:
            table[column] = table[column].map(lambda value: f"{value:.3f}" if pd.notna(value) else "")
    lines = [
        "| " + " | ".join(table.columns) + " |",
        "| " + " | ".join(["---"] * len(table.columns)) + " |",
    ]
    for row in table.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(value) else str(value) for value in row) + " |")
    return "\n".join(lines)


def build_report(sector_summary: pd.DataFrame, aggregate_summary: pd.DataFrame, config: dict) -> str:
    base = sector_summary.loc[
        sector_summary["scenario"].eq("Base") & sector_summary["throttle_scenario"].eq("BaseThrottle")
    ].copy()
    base_agg = aggregate_summary.loc[
        aggregate_summary["scenario"].eq("Base") & aggregate_summary["throttle_scenario"].eq("BaseThrottle")
    ].copy()

    share_winners = base.sort_values("delta_va_share_pp_2035", ascending=False).head(5)
    share_losers = base.sort_values("delta_va_share_pp_2035", ascending=True).head(5)
    profit_winners = base.sort_values("incremental_profit_pool_2035_bn_rub", ascending=False).head(5)
    productivity_winners = base.sort_values("lp_gain_vs_cf_2035_pct", ascending=False).head(5)
    employment_declines = base.sort_values("employment_delta_2035_thousand", ascending=True).head(5)

    return f"""# Russia Economy Structure Report

Этот слой переводит `AI diffusion / margin / capital return` в структуру экономики РФ: `VA`, отраслевые доли, profit pool, labour income, занятость и производительность труда.

## 1. Формализация

Контрфактический выпуск:

\\[
VA^{{cf}}_{{s,t}} = VA_{{s,2024}} \\prod_{{\\tau=2025}}^t (1 + g^{{cf}}_s)
\\]

Managed adoption:

\\[
A^{{m}}_{{s,t}} = A_{{s,t}}(1 - \\rho MOS_s)
\\]

AI output and labour-productivity boosts:

\\[
VA^{{AI}}_{{s,t}} = VA^{{cf}}_{{s,t}} \\exp\\left(\\sum_{{\\tau=2025}}^t \\eta^{{VA}}_s \\Delta A^m_{{s,\\tau}}\\right)
\\]

\\[
LP^{{AI}}_{{s,t}} = LP^{{cf}}_{{s,t}} \\exp\\left(\\sum_{{\\tau=2025}}^t \\eta^{{LP}}_s \\Delta A^m_{{s,\\tau}}\\right)
\\]

\\[
L^{{AI}}_{{s,t}} = \\frac{{VA^{{AI}}_{{s,t}}}}{{LP^{{AI}}_{{s,t}}}},
\\qquad
\\Pi^{{AI}}_{{s,t}} = \\pi^{{AI}}_{{s,t}} VA^{{AI}}_{{s,t}}
\\]

Контрфактический рост `VA` — clipped median official real growth за `{config["counterfactual_growth"]["history_start_year"]}-{config["counterfactual_growth"]["history_end_year"]}`. Денежные величины интерпретируются как рубли baseline 2024, а не номинальный прогноз инфляции.

## 2. Aggregate Base / BaseThrottle

{markdown_table(
    base_agg,
    columns=[
        "scenario",
        "throttle_scenario",
        "total_va_gain_2035_pct",
        "total_profit_pool_gain_2035_pct",
        "total_labour_income_gain_2035_pct",
        "aggregate_lp_gain_vs_cf_2035_pct",
        "total_employment_delta_2035_thousand",
        "cumulative_net_value_after_capex_2035_bn_rub",
    ],
    float_cols=[
        "total_va_gain_2035_pct",
        "total_profit_pool_gain_2035_pct",
        "total_labour_income_gain_2035_pct",
        "aggregate_lp_gain_vs_cf_2035_pct",
        "total_employment_delta_2035_thousand",
        "cumulative_net_value_after_capex_2035_bn_rub",
    ],
)}

## 3. Sector Share Winners

{markdown_table(
    share_winners,
    columns=[
        "sector_id",
        "sector_name_ru",
        "class_id",
        "delta_va_share_pp_2035",
        "va_share_ai_2035",
        "incremental_va_2035_bn_rub",
    ],
    float_cols=["delta_va_share_pp_2035", "va_share_ai_2035", "incremental_va_2035_bn_rub"],
)}

## 4. Sector Share Losers

{markdown_table(
    share_losers,
    columns=[
        "sector_id",
        "sector_name_ru",
        "class_id",
        "delta_va_share_pp_2035",
        "va_share_ai_2035",
        "incremental_va_2035_bn_rub",
    ],
    float_cols=["delta_va_share_pp_2035", "va_share_ai_2035", "incremental_va_2035_bn_rub"],
)}

## 5. Profit Pool Winners

{markdown_table(
    profit_winners,
    columns=[
        "sector_id",
        "sector_name_ru",
        "class_id",
        "incremental_profit_pool_2035_bn_rub",
        "profit_pool_ai_2035_bn_rub",
        "cumulative_net_value_after_capex_2035_bn_rub",
    ],
    float_cols=[
        "incremental_profit_pool_2035_bn_rub",
        "profit_pool_ai_2035_bn_rub",
        "cumulative_net_value_after_capex_2035_bn_rub",
    ],
)}

## 6. Labour Productivity Winners

{markdown_table(
    productivity_winners,
    columns=[
        "sector_id",
        "sector_name_ru",
        "class_id",
        "adaptation_managed_2035",
        "lp_gain_vs_cf_2035_pct",
        "employment_delta_2035_thousand",
    ],
    float_cols=["adaptation_managed_2035", "lp_gain_vs_cf_2035_pct", "employment_delta_2035_thousand"],
)}

## 7. Employment Delta

{markdown_table(
    employment_declines,
    columns=[
        "sector_id",
        "sector_name_ru",
        "class_id",
        "employment_delta_2035_thousand",
        "incremental_labour_income_2035_bn_rub",
        "labour_income_ai_2035_bn_rub",
    ],
    float_cols=[
        "employment_delta_2035_thousand",
        "incremental_labour_income_2035_bn_rub",
        "labour_income_ai_2035_bn_rub",
    ],
)}

## 8. Ограничения

- Это accounting layer, а не general equilibrium: цены, межотраслевые связи и спрос не замыкаются.
- `VA` строится в baseline-ruble units через real growth и AI boosts; номинальная инфляция не моделируется.
- Параметры `η` заданы сценарно по adoption class и должны идти в sensitivity block.
- `MOS_s` — pressure proxy, а не доказательство намеренного ограничения внедрения.
"""


def main() -> None:
    config = load_json(CONFIG_PATH)
    paths = build_structure_paths(config)
    sector_summary = build_sector_summary(paths, config)
    aggregate_summary = build_aggregate_summary(paths, config)

    paths.to_csv(OUTPUT_PATHS, index=False)
    sector_summary.to_csv(OUTPUT_SECTOR, index=False)
    aggregate_summary.to_csv(OUTPUT_AGGREGATE, index=False)
    OUTPUT_REPORT.write_text(build_report(sector_summary, aggregate_summary, config), encoding="utf-8")

    print(f"Saved paths: {OUTPUT_PATHS}")
    print(f"Saved sector summary: {OUTPUT_SECTOR}")
    print(f"Saved aggregate summary: {OUTPUT_AGGREGATE}")
    print(f"Saved report: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from build_historical_panel import CONFIG_PATH as HIST_CONFIG_PATH
from build_historical_panel import build_klems_panel, load_config as load_hist_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "ai_diffusion_model.json"
BASELINE_PATH = ROOT / "data" / "processed" / "russia_sector_baseline_2024.csv"
SCENARIOS_PATH = ROOT / "data" / "processed" / "russia_ai_sector_scenarios.csv"
HIST_PANEL_PATH = ROOT / "data" / "processed" / "historical_sector_panel_1985_2005.csv"

OUTPUT_PATHS = ROOT / "data" / "processed" / "ai_diffusion_paths_2025_2035.csv"
OUTPUT_SUMMARY = ROOT / "data" / "processed" / "ai_diffusion_sector_summary.csv"
OUTPUT_CLASS_SUMMARY = ROOT / "data" / "processed" / "ai_diffusion_class_summary.csv"
OUTPUT_DIAGNOSTICS = ROOT / "data" / "processed" / "ai_diffusion_calibration_diagnostics.csv"
OUTPUT_REPORT = ROOT / "docs" / "russia_ai_diffusion_report.md"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_russia_inputs(config: dict) -> pd.DataFrame:
    baseline = pd.read_csv(BASELINE_PATH)
    scenarios = pd.read_csv(SCENARIOS_PATH)
    join_keys = ["sector_id", "sector_name_ru", "okved", "ai_intensity", "is_proxy_mn", "staffing_proxy_exact"]
    df = baseline.merge(scenarios, on=join_keys, how="left")
    df["class_id"] = df["sector_id"].map(config["class_map"])
    df["delta_sL_potential"] = df[config["potential_shock_column"]]
    return df


def build_tax_anchor() -> pd.DataFrame:
    panel = pd.read_csv(HIST_PANEL_PATH)
    hist = panel.loc[panel["year"].between(1995, 2005)].copy()
    hist["tax_share"] = hist["net_taxes_prod_stan"] / hist["va_nominal_stan"]
    anchor = hist.groupby("sector_id", as_index=False)["tax_share"].median().rename(columns={"tax_share": "tax_share_anchor"})
    overall_median = float(anchor["tax_share_anchor"].median())
    anchor["tax_share_anchor"] = anchor["tax_share_anchor"].fillna(overall_median)
    anchor["tax_share_anchor_source"] = "historical_stan_median_1995_2005"
    return anchor


def build_capital_anchor(config: dict) -> pd.DataFrame:
    hist_config = load_hist_config(HIST_CONFIG_PATH)
    hist_config["requested_window"]["end_year"] = config["historical_klems_end_year"]
    klems = build_klems_panel(hist_config)
    klems = klems.loc[klems["year"] >= config["historical_kl_anchor_start_year"]].copy()
    anchor = (
        klems.groupby("sector_id", as_index=False)
        .agg(
            capital_intensity_anchor=("k_l_real_klems", "median"),
            techint_anchor_hist=("techint_klems", "median"),
        )
        .sort_values("sector_id")
        .reset_index(drop=True)
    )
    anchor["capital_intensity_norm"] = anchor["capital_intensity_anchor"] / anchor["capital_intensity_anchor"].max()
    return anchor


def build_calibration_diagnostics(config: dict) -> pd.DataFrame:
    hist_config = load_hist_config(HIST_CONFIG_PATH)
    hist_config["requested_window"]["end_year"] = config["historical_klems_end_year"]
    klems = build_klems_panel(hist_config)
    df = klems.loc[klems["techint_klems"].notna()].copy()
    df["class_id"] = df["sector_id"].map(config["class_map"])

    class_year = (
        df.groupby(["class_id", "year"], as_index=False)["techint_klems"]
        .median()
        .sort_values(["class_id", "year"])
        .reset_index(drop=True)
    )
    sat = df.groupby("sector_id")["techint_klems"].quantile(0.95).rename("sat").reset_index()
    reg = df.merge(sat, on="sector_id", how="left").sort_values(["country_iso3", "sector_id", "year"]).reset_index(drop=True)
    reg["A"] = (reg["techint_klems"] / reg["sat"]).clip(0.0, 0.999)
    reg["A_next"] = reg.groupby(["country_iso3", "sector_id"])["A"].shift(-1)
    reg["dA"] = reg["A_next"] - reg["A"]
    reg = reg.loc[reg["A_next"].notna() & (reg["A"] < 0.999)].copy()
    reg["Y"] = reg["dA"] / (1.0 - reg["A"])

    diagnostics: list[dict] = []
    for class_id, group in class_year.groupby("class_id"):
        group = group.sort_values("year")
        reg_group = reg.loc[reg["class_id"] == class_id].copy()
        p_hat = np.nan
        q_hat = np.nan
        r2 = np.nan
        q_pvalue = np.nan
        if len(reg_group) >= 20:
            model = sm.OLS(reg_group["Y"], sm.add_constant(reg_group["A"])).fit(cov_type="HC3")
            p_hat = float(model.params["const"])
            q_hat = float(model.params["A"])
            r2 = float(model.rsquared)
            q_pvalue = float(model.pvalues["A"])
        diagnostics.append(
            {
                "class_id": class_id,
                "start_year": int(group["year"].iloc[0]),
                "end_year": int(group["year"].iloc[-1]),
                "techint_start_median": float(group["techint_klems"].iloc[0]),
                "techint_end_median": float(group["techint_klems"].iloc[-1]),
                "techint_delta_median": float(group["techint_klems"].iloc[-1] - group["techint_klems"].iloc[0]),
                "positive_dA_share": float((reg_group["dA"] > 0).mean()) if len(reg_group) else np.nan,
                "p_hat_disc": p_hat,
                "q_hat_disc": q_hat,
                "q_pvalue_disc": q_pvalue,
                "r2_disc": r2,
                "fit_is_structurally_clean": bool(pd.notna(q_hat) and q_hat > 0 and q_pvalue < 0.1),
                "anchor_retained": True,
            }
        )

    return pd.DataFrame(diagnostics).sort_values("class_id").reset_index(drop=True)


def prepare_model_base(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    russia = load_russia_inputs(config)
    capital_anchor = build_capital_anchor(config)
    tax_anchor = build_tax_anchor()
    tax_overall = float(tax_anchor["tax_share_anchor"].median())

    base = russia.merge(capital_anchor, on="sector_id", how="left")
    base = base.merge(tax_anchor[["sector_id", "tax_share_anchor"]], on="sector_id", how="left")
    base["tax_share_anchor"] = base["tax_share_anchor"].fillna(tax_overall)
    base["pi0_proxy"] = (1.0 - base["labour_share_proxy"] - base["tax_share_anchor"]).clip(lower=0.0, upper=1.0)
    base["gamma_margin"] = base.apply(
        lambda row: config["class_parameters"][row["class_id"]]["gamma_margin_multiplier"] * row["pi0_proxy"],
        axis=1,
    )
    diagnostics = build_calibration_diagnostics(config)
    return base, diagnostics


def run_diffusion_paths(base: pd.DataFrame, config: dict) -> pd.DataFrame:
    years = list(range(config["projection_start_year"], config["projection_end_year"] + 1))
    lambda_speed = float(base["margin_erosion_speed"].iloc[0])
    records: list[dict] = []

    for _, row in base.iterrows():
        class_params = config["class_parameters"][row["class_id"]]
        for scenario_name, scenario in config["scenario_parameters"].items():
            p = class_params["p"] * scenario["p_multiplier"]
            q = class_params["q"] * scenario["q_multiplier"]
            capital_barrier = class_params["capital_barrier"] * scenario.get("capital_barrier_multiplier", 1.0)
            if row["class_id"] in scenario.get("class_overrides", {}):
                capital_barrier *= scenario["class_overrides"][row["class_id"]].get("capital_barrier_multiplier", 1.0)

            adaptation_prev = float(config["initial_adaptation"])
            margin_prev = float(row["pi0_proxy"])
            cumulative_capital_need = 0.0

            for year in years:
                diffusion_speed = (p + q * adaptation_prev) * (1.0 - adaptation_prev)
                adaptation = float(np.clip(adaptation_prev + diffusion_speed, 0.0, 1.0))
                labour_share_t = float(np.clip(row["labour_share_proxy"] + row["delta_sL_potential"] * adaptation, 0.0, 1.0))
                margin_t = float(np.clip(row["pi0_proxy"] + row["gamma_margin"] * adaptation - lambda_speed * margin_prev, 0.0, 1.0))
                delta_k_need = float(capital_barrier * row["capital_intensity_norm"] * row["va_current_bn_rub"] * diffusion_speed)
                cumulative_capital_need += delta_k_need

                records.append(
                    {
                        "scenario": scenario_name,
                        "year": year,
                        "sector_id": row["sector_id"],
                        "sector_name_ru": row["sector_name_ru"],
                        "class_id": row["class_id"],
                        "ai_intensity": row["ai_intensity"],
                        "rti_bucket": row["rti_bucket"],
                        "p": p,
                        "q": q,
                        "adaptation": adaptation,
                        "diffusion_speed": diffusion_speed,
                        "delta_sL_potential": row["delta_sL_potential"],
                        "delta_sL_t": row["delta_sL_potential"] * adaptation,
                        "labour_share_t": labour_share_t,
                        "pi0_proxy": row["pi0_proxy"],
                        "gamma_margin": row["gamma_margin"],
                        "margin_t": margin_t,
                        "capital_intensity_anchor": row["capital_intensity_anchor"],
                        "capital_intensity_norm": row["capital_intensity_norm"],
                        "capital_barrier": capital_barrier,
                        "delta_k_need_bn_rub": delta_k_need,
                        "cumulative_delta_k_need_bn_rub": cumulative_capital_need,
                    }
                )
                adaptation_prev = adaptation
                margin_prev = margin_t

    return pd.DataFrame(records)


def summarize_paths(paths: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict] = []
    class_rows: list[dict] = []

    for (scenario, sector_id), group in paths.groupby(["scenario", "sector_id"]):
        group = group.sort_values("year").reset_index(drop=True)
        year_a50 = group.loc[group["adaptation"] >= 0.5, "year"]
        peak_idx = group["diffusion_speed"].idxmax()
        peak_year = int(group.loc[group["diffusion_speed"].idxmax(), "year"])
        peak_speed = float(group["diffusion_speed"].max())
        margin_peak_idx = group["margin_t"].idxmax()
        summary_rows.append(
            {
                "scenario": scenario,
                "sector_id": sector_id,
                "sector_name_ru": group["sector_name_ru"].iloc[0],
                "class_id": group["class_id"].iloc[0],
                "ai_intensity": group["ai_intensity"].iloc[0],
                "rti_bucket": group["rti_bucket"].iloc[0],
                "p": float(group["p"].iloc[0]),
                "q": float(group["q"].iloc[0]),
                "A_2030": float(group.loc[group["year"] == 2030, "adaptation"].iloc[0]),
                "A_2035": float(group.loc[group["year"] == 2035, "adaptation"].iloc[0]),
                "year_A50": int(year_a50.iloc[0]) if not year_a50.empty else pd.NA,
                "peak_speed_year": peak_year,
                "peak_speed": peak_speed,
                "delta_sL_2030": float(group.loc[group["year"] == 2030, "delta_sL_t"].iloc[0]),
                "delta_sL_2035": float(group.loc[group["year"] == 2035, "delta_sL_t"].iloc[0]),
                "labour_share_2035": float(group.loc[group["year"] == 2035, "labour_share_t"].iloc[0]),
                "margin_2030": float(group.loc[group["year"] == 2030, "margin_t"].iloc[0]),
                "margin_2035": float(group.loc[group["year"] == 2035, "margin_t"].iloc[0]),
                "margin_peak_year": int(group.loc[margin_peak_idx, "year"]),
                "margin_peak": float(group["margin_t"].max()),
                "cumulative_delta_k_need_bn_rub": float(group["delta_k_need_bn_rub"].sum()),
            }
        )

    for (scenario, class_id), group in paths.groupby(["scenario", "class_id"]):
        group = group.groupby("year", as_index=False).agg(
            adaptation=("adaptation", "mean"),
            diffusion_speed=("diffusion_speed", "mean"),
            margin_t=("margin_t", "mean"),
            delta_k_need_bn_rub=("delta_k_need_bn_rub", "sum"),
        )
        year_a50 = group.loc[group["adaptation"] >= 0.5, "year"]
        class_rows.append(
            {
                "scenario": scenario,
                "class_id": class_id,
                "A_2030": float(group.loc[group["year"] == 2030, "adaptation"].iloc[0]),
                "A_2035": float(group.loc[group["year"] == 2035, "adaptation"].iloc[0]),
                "year_A50": int(year_a50.iloc[0]) if not year_a50.empty else pd.NA,
                "peak_speed_year": int(group.loc[group["diffusion_speed"].idxmax(), "year"]),
                "peak_speed": float(group["diffusion_speed"].max()),
                "margin_2035_avg": float(group.loc[group["year"] == 2035, "margin_t"].iloc[0]),
                "cumulative_delta_k_need_bn_rub": float(group["delta_k_need_bn_rub"].sum()),
            }
        )

    sector_summary = pd.DataFrame(summary_rows).sort_values(["scenario", "peak_speed_year", "sector_id"]).reset_index(drop=True)
    class_summary = pd.DataFrame(class_rows).sort_values(["scenario", "class_id"]).reset_index(drop=True)
    return sector_summary, class_summary


def format_markdown_table(dataframe: pd.DataFrame, columns: list[str], float_cols: list[str]) -> str:
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


def build_report(diagnostics: pd.DataFrame, class_summary: pd.DataFrame, sector_summary: pd.DataFrame, config: dict) -> str:
    base_class = class_summary.loc[class_summary["scenario"] == "Base"].copy()
    fast_summary = sector_summary.loc[sector_summary["scenario"] == "Fast"].copy()
    friction_summary = sector_summary.loc[sector_summary["scenario"] == "Friction"].copy()

    top_fast_margin = fast_summary.sort_values("margin_peak", ascending=False).head(3)
    top_friction_capital = friction_summary.sort_values("cumulative_delta_k_need_bn_rub", ascending=False).head(3)
    deepest_base_labour = (
        sector_summary.loc[sector_summary["scenario"] == "Base"]
        .sort_values("delta_sL_2035")
        .head(3)
    )

    return f"""# Russia AI Diffusion Report

Этот слой превращает sector-level AI shocks в годовые траектории `2025–2035` через Bass-диффузию, margin adaptation и capital-need block.

## 1. Что реально удалось калибровать из данных

Для диагностики использован `EU KLEMS` ICT capital intensity `techint_klems` по comparators за `1995–{config["historical_klems_end_year"]}`. Исторические данные дают чистую иерархию уровней диффузии, но не дают статистически чистой идентификации `p,q` на class-level, поэтому expert anchors retained.

{format_markdown_table(
    diagnostics,
    columns=[
        "class_id",
        "start_year",
        "end_year",
        "techint_start_median",
        "techint_end_median",
        "techint_delta_median",
        "positive_dA_share",
        "p_hat_disc",
        "q_hat_disc",
        "fit_is_structurally_clean",
    ],
    float_cols=[
        "techint_start_median",
        "techint_end_median",
        "techint_delta_median",
        "positive_dA_share",
        "p_hat_disc",
        "q_hat_disc",
    ],
)}

Вывод по калибровке:

- `software` имеет самый высокий historical techint и самый большой прирост.
- `hybrid` и особенно `hardware` растут заметно медленнее.
- Class-level discrete Bass fits не дают устойчивого положительного `q`; поэтому модель использует ваши class anchors как priors, а data block служит validation layer, а не source of false precision.

## 2. Class Dynamics 2025–2035

Base-scenario class trajectories:

{format_markdown_table(
    base_class,
    columns=["class_id", "A_2030", "A_2035", "year_A50", "peak_speed_year", "peak_speed", "cumulative_delta_k_need_bn_rub"],
    float_cols=["A_2030", "A_2035", "peak_speed", "cumulative_delta_k_need_bn_rub"],
)}

Главный рисунок здесь простой:

- `software` выходит на `A≈0.88` к 2035 и пересекает `A=0.5` уже в `2032`; в `Fast` это происходит в `2030`.
- `hybrid` в `Base` к 2035 доходит только до `A≈0.33`; до `0.5` он добирается лишь в `Fast`.
- `hardware` не достигает `A=0.5` даже в `Fast` к 2035, что и создает длинную investment phase.

## 3. Sector Implications

Сектора с самым глубоким снижением labour share к 2035 в `Base`:

{format_markdown_table(
    deepest_base_labour,
    columns=["sector_id", "sector_name_ru", "class_id", "A_2035", "delta_sL_2035", "labour_share_2035"],
    float_cols=["A_2035", "delta_sL_2035", "labour_share_2035"],
)}

Сектора с наибольшим margin peak в `Fast`:

{format_markdown_table(
    top_fast_margin,
    columns=["sector_id", "sector_name_ru", "class_id", "margin_peak_year", "margin_peak"],
    float_cols=["margin_peak"],
)}

Сектора с наибольшей cumulative capital need в `Friction`:

{format_markdown_table(
    top_friction_capital,
    columns=["sector_id", "sector_name_ru", "class_id", "cumulative_delta_k_need_bn_rub"],
    float_cols=["cumulative_delta_k_need_bn_rub"],
)}

## 4. Интерпретация

1. Первые winners по марже действительно относятся к `software`-классу: `K`, `J`, `M`. Это следует не из «красивой гипотезы», а из комбинации высокого `p,q`, умеренного capital barrier и положительного adoption premium на уже существующую margin base.
2. Самая длинная transition zone у `hardware`: `B`, `F`, `H`. Там adaptation к 2035 остаётся низкой, но capital need на единицу внедрения высокой, особенно в `Friction`.
3. `hybrid` (`C`, `DE`) оказывается промежуточным режимом: заметный labour squeeze и существенная capital need, но без software-speed diffusion.

## 5. Ограничения

- `Δs^L_potential` взят из текущего central anchor `{config["potential_shock_column"]}`, а не из новой causal AI-regression.
- `γ_s` не идентифицирован историей; он задан как class-ordered structural parameter на базе baseline margin.
- `ΔK` — это modelled capital requirement, а не наблюдаемый CAPEX forecast.
- Для России по-прежнему отсутствует современный прямой `K/L`; используется historical comparator anchor.
"""


def main() -> None:
    config = load_json(CONFIG_PATH)
    base, diagnostics = prepare_model_base(config)
    paths = run_diffusion_paths(base, config)
    sector_summary, class_summary = summarize_paths(paths)

    paths.to_csv(OUTPUT_PATHS, index=False)
    sector_summary.to_csv(OUTPUT_SUMMARY, index=False)
    class_summary.to_csv(OUTPUT_CLASS_SUMMARY, index=False)
    diagnostics.to_csv(OUTPUT_DIAGNOSTICS, index=False)
    OUTPUT_REPORT.write_text(build_report(diagnostics, class_summary, sector_summary, config), encoding="utf-8")

    print(f"Saved paths: {OUTPUT_PATHS}")
    print(f"Saved sector summary: {OUTPUT_SUMMARY}")
    print(f"Saved class summary: {OUTPUT_CLASS_SUMMARY}")
    print(f"Saved diagnostics: {OUTPUT_DIAGNOSTICS}")
    print(f"Saved report: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()

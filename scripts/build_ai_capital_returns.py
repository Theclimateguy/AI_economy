from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PATHS_PATH = ROOT / "data" / "processed" / "ai_diffusion_paths_2025_2035.csv"
DIAGNOSTICS_PATH = ROOT / "data" / "processed" / "ai_diffusion_calibration_diagnostics.csv"
BASELINE_PATH = ROOT / "data" / "processed" / "russia_sector_baseline_2024.csv"

OUTPUT_PATHS = ROOT / "data" / "processed" / "ai_capital_return_paths_2025_2035.csv"
OUTPUT_SECTOR = ROOT / "data" / "processed" / "ai_capital_return_sector_summary.csv"
OUTPUT_CLASS = ROOT / "data" / "processed" / "ai_capital_return_class_summary.csv"
OUTPUT_REPORT = ROOT / "docs" / "russia_ai_capital_return_report.md"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    paths = pd.read_csv(PATHS_PATH)
    diagnostics = pd.read_csv(DIAGNOSTICS_PATH)
    baseline = pd.read_csv(BASELINE_PATH)[["sector_id", "va_current_bn_rub"]]
    paths = paths.merge(baseline, on="sector_id", how="left")
    return paths.sort_values(["scenario", "sector_id", "year"]).reset_index(drop=True), diagnostics


def build_counterfactual_margin(paths: pd.DataFrame) -> pd.DataFrame:
    records: list[dict] = []
    for (scenario, sector_id), group in paths.groupby(["scenario", "sector_id"]):
        group = group.sort_values("year").reset_index(drop=True)
        lambda_speed = float((group["pi0_proxy"].iloc[0] + group["gamma_margin"].iloc[0] * group["adaptation"].iloc[0] - group["margin_t"].iloc[0]) / group["pi0_proxy"].iloc[0])
        pi_cf_prev = float(group["pi0_proxy"].iloc[0])
        for row in group.itertuples(index=False):
            pi_cf = row.pi0_proxy - lambda_speed * pi_cf_prev
            records.append(
                {
                    "scenario": row.scenario,
                    "sector_id": row.sector_id,
                    "year": row.year,
                    "margin_cf_t": pi_cf,
                    "lambda_speed": lambda_speed,
                }
            )
            pi_cf_prev = pi_cf
    cf = pd.DataFrame(records)
    return paths.merge(cf, on=["scenario", "sector_id", "year"], how="left")


def compute_return_paths(paths: pd.DataFrame) -> pd.DataFrame:
    df = build_counterfactual_margin(paths)
    df["gross_margin_premium_share"] = df["gamma_margin"] * df["adaptation"]
    df["gross_margin_gain_bn_rub"] = df["gross_margin_premium_share"] * df["va_current_bn_rub"]
    df["net_margin_gain_cf_share"] = df["margin_t"] - df["margin_cf_t"]
    df["net_margin_gain_cf_bn_rub"] = df["net_margin_gain_cf_share"] * df["va_current_bn_rub"]
    df["gross_return_on_new_capital"] = df["gross_margin_gain_bn_rub"] / df["delta_k_need_bn_rub"]
    df["net_return_on_new_capital_cf"] = df["net_margin_gain_cf_bn_rub"] / df["delta_k_need_bn_rub"]
    df["cumulative_gross_margin_gain_bn_rub"] = df.groupby(["scenario", "sector_id"])["gross_margin_gain_bn_rub"].cumsum()
    df["cumulative_net_margin_gain_cf_bn_rub"] = df.groupby(["scenario", "sector_id"])["net_margin_gain_cf_bn_rub"].cumsum()
    df["cumulative_gross_return_on_capital"] = df["cumulative_gross_margin_gain_bn_rub"] / df["cumulative_delta_k_need_bn_rub"]
    df["cumulative_net_return_on_capital_cf"] = df["cumulative_net_margin_gain_cf_bn_rub"] / df["cumulative_delta_k_need_bn_rub"]
    return df


def first_year_at_or_above(group: pd.DataFrame, column: str, threshold: float) -> int | None:
    hit = group.loc[group[column] >= threshold, "year"]
    return int(hit.iloc[0]) if not hit.empty else None


def build_sector_summary(paths: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (scenario, sector_id), group in paths.groupby(["scenario", "sector_id"]):
        group = group.sort_values("year").reset_index(drop=True)
        row = group.iloc[-1]
        rows.append(
            {
                "scenario": scenario,
                "sector_id": sector_id,
                "sector_name_ru": row["sector_name_ru"],
                "class_id": row["class_id"],
                "A_2035": float(row["adaptation"]),
                "gross_return_2035": float(row["cumulative_gross_return_on_capital"]),
                "net_return_cf_2035": float(row["cumulative_net_return_on_capital_cf"]),
                "gross_payback_year": first_year_at_or_above(group, "cumulative_gross_return_on_capital", 1.0),
                "net_payback_year_cf": first_year_at_or_above(group, "cumulative_net_return_on_capital_cf", 1.0),
                "cumulative_delta_k_need_bn_rub": float(row["cumulative_delta_k_need_bn_rub"]),
                "cumulative_gross_margin_gain_bn_rub": float(row["cumulative_gross_margin_gain_bn_rub"]),
                "cumulative_net_margin_gain_cf_bn_rub": float(row["cumulative_net_margin_gain_cf_bn_rub"]),
                "gross_return_on_new_capital_2035": float(row["gross_return_on_new_capital"]),
                "net_return_on_new_capital_cf_2035": float(row["net_return_on_new_capital_cf"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["scenario", "net_return_cf_2035"], ascending=[True, False]).reset_index(drop=True)


def build_class_summary(paths: pd.DataFrame, diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for (scenario, class_id), group in paths.groupby(["scenario", "class_id"]):
        by_year = (
            group.groupby("year", as_index=False)
            .agg(
                cumulative_delta_k_need_bn_rub=("delta_k_need_bn_rub", "sum"),
                cumulative_gross_margin_gain_bn_rub=("gross_margin_gain_bn_rub", "sum"),
                cumulative_net_margin_gain_cf_bn_rub=("net_margin_gain_cf_bn_rub", "sum"),
                adaptation=("adaptation", "mean"),
            )
            .sort_values("year")
            .reset_index(drop=True)
        )
        by_year["cum_capex"] = by_year["cumulative_delta_k_need_bn_rub"].cumsum()
        by_year["cum_gross_gain"] = by_year["cumulative_gross_margin_gain_bn_rub"].cumsum()
        by_year["cum_net_gain_cf"] = by_year["cumulative_net_margin_gain_cf_bn_rub"].cumsum()
        by_year["cum_gross_return"] = by_year["cum_gross_gain"] / by_year["cum_capex"]
        by_year["cum_net_return_cf"] = by_year["cum_net_gain_cf"] / by_year["cum_capex"]
        last = by_year.iloc[-1]
        rows.append(
            {
                "scenario": scenario,
                "class_id": class_id,
                "A_2035": float(last["adaptation"]),
                "gross_return_cf_2035": float(last["cum_gross_return"]),
                "net_return_cf_2035": float(last["cum_net_return_cf"]),
                "gross_payback_year": first_year_at_or_above(by_year, "cum_gross_return", 1.0),
                "net_payback_year_cf": first_year_at_or_above(by_year, "cum_net_return_cf", 1.0),
                "cum_capex_2035_bn_rub": float(last["cum_capex"]),
                "cum_net_gain_cf_2035_bn_rub": float(last["cum_net_gain_cf"]),
            }
        )

    class_summary = pd.DataFrame(rows).merge(diagnostics, on="class_id", how="left")
    return class_summary.sort_values(["scenario", "net_return_cf_2035"], ascending=[True, False]).reset_index(drop=True)


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


def build_report(class_summary: pd.DataFrame, sector_summary: pd.DataFrame) -> str:
    base_class = class_summary.loc[class_summary["scenario"] == "Base"].copy()
    fast_sector = sector_summary.loc[sector_summary["scenario"] == "Fast"].head(3)
    friction_sector = sector_summary.loc[sector_summary["scenario"] == "Friction"].sort_values(
        "cumulative_delta_k_need_bn_rub", ascending=False
    ).head(3)
    base_sector = sector_summary.loc[sector_summary["scenario"] == "Base"].head(5)

    return f"""# Russia AI Capital Return Report

Этот слой переводит диффузионную модель в функцию капитальной отдачи по классам и секторам.

Используем две величины:

\\[
R^{{K,gross}}_{{s,t}} = \\frac{{\\gamma_s A_s(t) \\cdot VA_{{s,0}}}}{{\\Delta K_{{s,t}}}},
\\qquad
R^{{K,net}}_{{s,t}} = \\frac{{\\left(\\pi_{{s,t}} - \\pi^{{cf}}_{{s,t}}\\right) \\cdot VA_{{s,0}}}}{{\\Delta K_{{s,t}}}},
\\]

где контрфактуал маржи задан как

\\[
\\pi^{{cf}}_{{s,t}} = \\pi_{{s,0}} - \\lambda \\pi^{{cf}}_{{s,t-1}},
\\]

то есть сравнение идет не со статическим `π0`, а с той же траекторией historical erosion без AI-premium.

## 1. Class Return Function

Base-scenario:

{markdown_table(
    base_class,
    columns=[
        "class_id",
        "A_2035",
        "net_return_cf_2035",
        "net_payback_year_cf",
        "cum_capex_2035_bn_rub",
        "cum_net_gain_cf_2035_bn_rub",
        "techint_delta_median",
    ],
    float_cols=[
        "A_2035",
        "net_return_cf_2035",
        "cum_capex_2035_bn_rub",
        "cum_net_gain_cf_2035_bn_rub",
        "techint_delta_median",
    ],
)}

Здесь видно три разных режима:

- `software`: very high net return, payback внутри горизонта практически сразу, низкий capex.
- `hybrid`: положительная, но сильно более низкая капитальная отдача; payback зависит от сценария.
- `hardware`: самая слабая отдача и максимальная зависимость от frictions.

## 2. Sector Leaders in Base

{markdown_table(
    base_sector,
    columns=[
        "sector_id",
        "sector_name_ru",
        "class_id",
        "net_return_cf_2035",
        "net_payback_year_cf",
        "cumulative_delta_k_need_bn_rub",
    ],
    float_cols=["net_return_cf_2035", "cumulative_delta_k_need_bn_rub"],
)}

## 3. Fast Winners

{markdown_table(
    fast_sector,
    columns=[
        "sector_id",
        "sector_name_ru",
        "class_id",
        "net_return_cf_2035",
        "gross_payback_year",
    ],
    float_cols=["net_return_cf_2035"],
)}

## 4. Friction Bottlenecks

{markdown_table(
    friction_sector,
    columns=[
        "sector_id",
        "sector_name_ru",
        "class_id",
        "cumulative_delta_k_need_bn_rub",
        "net_return_cf_2035",
        "net_payback_year_cf",
    ],
    float_cols=["cumulative_delta_k_need_bn_rub", "net_return_cf_2035"],
)}

## 5. Главный вывод

1. `software` действительно реализует режим `high adoption / low capex / high return`. В `Base` net return к `2035` уже очень высок, а в `Fast` еще сильнее.
2. `hardware` реализует режим `low adoption / high capex / late or absent payback`. Во `Friction` часть hardware-секторов не достигает net payback к `2035`.
3. `hybrid` это transition regime: положительная отдача есть, но она зависит от длины горизонта и стоимости капитала намного сильнее, чем в software.
"""


def main() -> None:
    paths, diagnostics = load_inputs()
    return_paths = compute_return_paths(paths)
    sector_summary = build_sector_summary(return_paths)
    class_summary = build_class_summary(return_paths, diagnostics)

    return_paths.to_csv(OUTPUT_PATHS, index=False)
    sector_summary.to_csv(OUTPUT_SECTOR, index=False)
    class_summary.to_csv(OUTPUT_CLASS, index=False)
    OUTPUT_REPORT.write_text(build_report(class_summary, sector_summary), encoding="utf-8")

    print(f"Saved return paths: {OUTPUT_PATHS}")
    print(f"Saved sector return summary: {OUTPUT_SECTOR}")
    print(f"Saved class return summary: {OUTPUT_CLASS}")
    print(f"Saved report: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()

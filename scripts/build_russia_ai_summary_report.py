from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "data" / "processed" / "russia_sector_baseline_2024.csv"
SCENARIOS_PATH = ROOT / "data" / "processed" / "russia_ai_sector_scenarios.csv"
OUTPUT_TABLE = ROOT / "data" / "processed" / "russia_ai_sector_impact_summary_2024.csv"
OUTPUT_AGG = ROOT / "data" / "processed" / "russia_ai_aggregate_summary_2024.json"
OUTPUT_REPORT = ROOT / "docs" / "russia_ai_sector_report.md"


def load_inputs() -> pd.DataFrame:
    baseline = pd.read_csv(BASELINE_PATH)
    scenarios = pd.read_csv(SCENARIOS_PATH)
    join_keys = ["sector_id", "sector_name_ru", "okved", "ai_intensity", "is_proxy_mn", "staffing_proxy_exact"]
    return baseline.merge(scenarios, on=join_keys, how="left")


def apply_scenarios(dataframe: pd.DataFrame) -> pd.DataFrame:
    df = dataframe.copy()
    for kind in ["baseline_mean", "core", "stress", "tail_q25", "tail_q10"]:
        df[f"labour_share_{kind}"] = (df["labour_share_proxy"] + df[f"delta_sL_{kind}"]).clip(lower=0.0)
        df[f"fot_{kind}_bn_rub"] = df[f"labour_share_{kind}"] * df["va_current_bn_rub"]
        df[f"delta_fot_{kind}_bn_rub"] = df[f"fot_{kind}_bn_rub"] - df["fot_proxy_bn_rub"]
        df[f"delta_emp_eq_{kind}_thousand"] = df[f"delta_fot_{kind}_bn_rub"] * 1_000_000.0 / df["annual_wage_rub"]

    total_va = df["va_current_bn_rub"].sum()
    total_employment = df["employment_persons"].sum()
    total_fot = df["fot_proxy_bn_rub"].sum()
    df["va_share_2024"] = df["va_current_bn_rub"] / total_va
    df["employment_share_2024"] = df["employment_persons"] / total_employment
    df["fot_share_2024"] = df["fot_proxy_bn_rub"] / total_fot
    return df


def build_aggregate_summary(df: pd.DataFrame) -> dict:
    total_va = float(df["va_current_bn_rub"].sum())
    total_fot = float(df["fot_proxy_bn_rub"].sum())
    lambda_speed = float(df["margin_erosion_speed"].iloc[0])
    half_life_years = math.log(0.5) / math.log(1.0 - lambda_speed)

    return {
        "year": int(df["year"].iloc[0]),
        "n_sectors": int(len(df)),
        "total_va_bn_rub": total_va,
        "total_fot_bn_rub": total_fot,
        "weighted_labour_share_2024": total_fot / total_va,
        "weighted_labour_share_core": float(df["fot_core_bn_rub"].sum() / total_va),
        "weighted_labour_share_stress": float(df["fot_stress_bn_rub"].sum() / total_va),
        "delta_fot_core_bn_rub": float(df["delta_fot_core_bn_rub"].sum()),
        "delta_fot_stress_bn_rub": float(df["delta_fot_stress_bn_rub"].sum()),
        "delta_emp_eq_core_thousand": float(df["delta_emp_eq_core_thousand"].sum()),
        "delta_emp_eq_stress_thousand": float(df["delta_emp_eq_stress_thousand"].sum()),
        "margin_erosion_speed": lambda_speed,
        "margin_half_life_years": float(half_life_years),
        "margin_pulse_retention_5y": float((1.0 - lambda_speed) ** 5),
        "margin_pulse_retention_10y": float((1.0 - lambda_speed) ** 10),
    }


def format_sector_table(df: pd.DataFrame) -> str:
    table = (
        df[
            [
                "sector_id",
                "sector_name_ru",
                "ai_intensity",
                "rti_bucket",
                "va_share_2024",
                "labour_share_proxy",
                "va_real_growth_pct",
                "delta_sL_core",
                "delta_sL_stress",
                "delta_fot_core_bn_rub",
                "delta_fot_stress_bn_rub",
            ]
        ]
        .copy()
        .sort_values("delta_sL_core")
    )
    for column in [
        "va_share_2024",
        "labour_share_proxy",
        "va_real_growth_pct",
        "delta_sL_core",
        "delta_sL_stress",
        "delta_fot_core_bn_rub",
        "delta_fot_stress_bn_rub",
    ]:
        table[column] = table[column].map(lambda value: f"{value:.3f}")
    headers = list(table.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in table.itertuples(index=False):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def format_top_lines(df: pd.DataFrame, value_col: str, label: str, top_n: int = 3) -> list[str]:
    top = df.sort_values(value_col, ascending=False).head(top_n)
    return [f"- {row.sector_id}: {row.sector_name_ru} ({label}={getattr(row, value_col):.3f})" for row in top.itertuples()]


def format_bottom_lines(df: pd.DataFrame, value_col: str, label: str, top_n: int = 3) -> list[str]:
    bottom = df.sort_values(value_col, ascending=True).head(top_n)
    return [f"- {row.sector_id}: {row.sector_name_ru} ({label}={getattr(row, value_col):.3f})" for row in bottom.itertuples()]


def build_report(df: pd.DataFrame, aggregate: dict) -> str:
    top_va = format_top_lines(df, "va_share_2024", "share_VA_2024")
    top_growth = format_top_lines(df, "va_real_growth_pct", "real_growth_2024")
    worst_core = format_bottom_lines(df, "delta_sL_core", "delta_sL_core")
    biggest_core_fot = format_bottom_lines(df, "delta_fot_core_bn_rub", "delta_fot_core_trln")

    return f"""# Russia AI Sector Report

Отчет объединяет официальный baseline РФ за 2024 год и исторически откалиброванный сценарный слой AI-shocks. Это не causal forecast AI-beta; это scenario calibration на базе historical `ΔTC` и единственного выжившего динамического параметра маржинальности.

## 1. Baseline 2024

- Суммарная ВДС по 8 секторам: `{aggregate["total_va_bn_rub"]:.2f}` млрд руб.
- Суммарный proxy ФОТ: `{aggregate["total_fot_bn_rub"]:.2f}` млрд руб.
- Взвешенная доля труда: `{aggregate["weighted_labour_share_2024"]:.3f}`.

Крупнейшие сектора по ВДС:
{chr(10).join(top_va)}

Лидеры по реальному росту ВДС в 2024 году:
{chr(10).join(top_growth)}

## 2. Сценарный эффект AI на labour share

При фиксированном выпуске и текущих средних зарплатах:

- `core`-сценарий снижает взвешенную долю труда с `{aggregate["weighted_labour_share_2024"]:.3f}` до `{aggregate["weighted_labour_share_core"]:.3f}`.
- `stress`-сценарий снижает ее до `{aggregate["weighted_labour_share_stress"]:.3f}`.
- Это соответствует изменению proxy ФОТ на `{aggregate["delta_fot_core_bn_rub"]:.2f}` млрд руб. в `core` и `{aggregate["delta_fot_stress_bn_rub"]:.2f}` млрд руб. в `stress`.
- Employment-equivalent при фиксированной зарплате: `{aggregate["delta_emp_eq_core_thousand"]:.0f}` тыс. в `core` и `{aggregate["delta_emp_eq_stress_thousand"]:.0f}` тыс. в `stress`.

Важно: employment-equivalent — это не прогноз занятости, а перевод изменения wage bill в эквивалент голов при неизменной средней зарплате. Actual employment должна считать уже балансовая / CGE-модель.

Сектора с самым сильным downside по `delta_sL_core`:
{chr(10).join(worst_core)}

Сектора с наибольшим сокращением proxy ФОТ в `core`:
{chr(10).join(biggest_core_fot)}

## 3. Что реально следует из данных

1. High-AI sectors уже сегодня растут быстрее среднего, но это неоднородный блок. `K` и `J` дают самые высокие темпы реального роста в 2024 году, однако `K` входит в AI-переход с низкой текущей долей труда, а `J` — с высокой.
2. Наибольший downside в сценарии дают не только высоко-AI услуги. `H` и `C` оказываются макро-важнее за счет комбинации размера, RTI и исторического task-displacing профиля. `B` выглядит особенно labor-light уже в baseline и в stress-сценарии практически обнуляет labour share.
3. `M` качественно уязвим к ИИ, но количественно в текущей калибровке мягче, чем `K/J/H`, потому что historical `ΔTC` для него частично task-creating. Этот вывод слабее остальных, потому что сектор использует proxy-flags.

## 4. Маржа

Из history переносится только скорость эрозии маржи:

- `lambda = {aggregate["margin_erosion_speed"]:.5f}`
- half-life initial margin pulse: `{aggregate["margin_half_life_years"]:.2f}` года
- сохраняется `{aggregate["margin_pulse_retention_5y"]:.3f}` initial pulse через 5 лет
- сохраняется `{aggregate["margin_pulse_retention_10y"]:.3f}` initial pulse через 10 лет

Это означает: если AI сначала дает сверхприбыль, historical data не подтверждают устойчивую sector-specific tech beta по марже, но подтверждают постепенную эрозию rents.

## 5. Ограничения интерпретации

- `Δs^L` — это scenario anchor, а не оцененная causal elasticity AI.
- `RTI` для РФ пока не построен из российской `ОКВЭД × ОКЗ` staffing matrix; используются historical sector buckets.
- `ФОТ` пока proxy: `employment × wage × 12`.
- Для `H/J/M` historical staffing block частично proxy-based.

## 6. Sector Table

{format_sector_table(df)}
"""


def main() -> None:
    df = apply_scenarios(load_inputs())
    aggregate = build_aggregate_summary(df)

    ordered_columns = [
        "year",
        "sector_id",
        "sector_name_ru",
        "okved",
        "ai_intensity",
        "rti_bucket",
        "dominant_task_shift",
        "va_current_bn_rub",
        "va_share_2024",
        "va_real_growth_pct",
        "va_deflator_growth_pct",
        "employment_thousand_persons",
        "employment_share_2024",
        "avg_monthly_wage_rub",
        "fot_proxy_bn_rub",
        "fot_share_2024",
        "labour_share_proxy",
        "delta_sL_baseline_mean",
        "delta_sL_core",
        "delta_sL_stress",
        "labour_share_core",
        "labour_share_stress",
        "delta_fot_core_bn_rub",
        "delta_fot_stress_bn_rub",
        "delta_emp_eq_core_thousand",
        "delta_emp_eq_stress_thousand",
        "margin_erosion_speed",
        "margin_erosion_pvalue",
        "margin_erosion_qvalue",
        "staffing_proxy_exact",
        "is_proxy_mn",
    ]
    df[ordered_columns].sort_values("delta_sL_core").to_csv(OUTPUT_TABLE, index=False)

    with OUTPUT_AGG.open("w", encoding="utf-8") as handle:
        json.dump(aggregate, handle, ensure_ascii=False, indent=2)

    OUTPUT_REPORT.write_text(build_report(df, aggregate), encoding="utf-8")

    print(f"Saved sector summary: {OUTPUT_TABLE}")
    print(f"Saved aggregate summary: {OUTPUT_AGG}")
    print(f"Saved report: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()

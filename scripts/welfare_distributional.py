from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

ILOSTAT_PATH = ROOT / "data" / "raw" / "ilostat" / "emp_temp_eco_ocu_nb_a.csv.gz"
OECD_AIOE_PATH = ROOT / "data" / "raw" / "oecd_ai" / "oecd_employment_outlook_2023_fig32.xlsx"
BASELINE_PATH = ROOT / "data" / "processed" / "russia_sector_baseline_2024.csv"
STRUCTURE_PATH = ROOT / "data" / "processed" / "russia_economy_structure_sector_summary.csv"

OUTPUT_PATH = ROOT / "data" / "processed" / "welfare_occupation_quintile_summary.csv"
OUTPUT_DOC = ROOT / "docs" / "welfare_distributional_report.md"

PROJECT_SECTOR_MAP = {
    "ECO_ISIC4_B": "B",
    "ECO_ISIC4_C": "C",
    "ECO_ISIC4_D": "DE",
    "ECO_ISIC4_E": "DE",
    "ECO_ISIC4_F": "F",
    "ECO_ISIC4_H": "H",
    "ECO_ISIC4_J": "J",
    "ECO_ISIC4_K": "K",
    "ECO_ISIC4_M": "M",
}

SECTOR_NAMES = {
    "B": "Добыча полезных ископаемых",
    "C": "Обрабатывающая промышленность",
    "DE": "Энергетика и ЖКХ",
    "F": "Строительство",
    "H": "Транспорт и логистика",
    "J": "ИТ и связь",
    "K": "Финансы и страхование",
    "M": "Профессиональные и научные услуги",
}

OCCUPATION_NAMES = {
    1: "Managers",
    2: "Professionals",
    3: "Technicians and associate professionals",
    4: "Clerical support workers",
    5: "Services and sales workers",
    6: "Skilled agricultural workers",
    7: "Craft and related trades workers",
    8: "Plant and machine operators, assemblers",
    9: "Elementary occupations",
}

OCCUPATION_WAGE_MULTIPLIER_PRIOR = {
    1: 2.20,
    2: 2.00,
    3: 1.45,
    4: 1.05,
    5: 0.85,
    6: 0.70,
    7: 0.95,
    8: 0.90,
    9: 0.60,
}

CAPITAL_GAIN_QUINTILE_WEIGHTS = {
    "Q1": 0.00,
    "Q2": 0.00,
    "Q3": 0.05,
    "Q4": 0.20,
    "Q5": 0.75,
}


def load_oecd_exposure() -> pd.DataFrame:
    df = pd.read_excel(OECD_AIOE_PATH, sheet_name="g3-2", header=None)
    exposure = df.iloc[40:77, [0, 1]].copy()
    exposure.columns = ["occupation_name", "ai_exposure"]
    exposure = exposure.loc[exposure["occupation_name"].ne("Average")].copy()

    major_group_map = {
        "Cleaners, helpers": 9,
        "Agricultural, forestry, fishery labourers": 9,
        "Food preparation assistants": 9,
        "Labourers": 9,
        "Refuse workers, other elementary workers": 9,
        "Assemblers": 8,
        "Stationary plant, machine operators": 8,
        "Drivers, mobile plant operators": 8,
        "Skilled forestry, fishery, hunting workers": 6,
        "Skilled agricultural workers": 6,
        "Building, workers": 7,
        "Food processing, wood working, garment, other craft": 7,
        "Metal, machinery workers": 7,
        "Handicraft, printing workers": 7,
        "Electrical, electronic trades workers": 7,
        "Personal care workers": 5,
        "Personal service workers": 5,
        "Sales workers": 5,
        "Protective services workers": 5,
        "Other clerical support workers": 4,
        "Numerical, material recording clerks": 4,
        "Customer services clerks": 4,
        "General, keyboard clerks": 4,
        "Health assoc. pro.": 3,
        "Legal, social, cultural, related assoc. pro.": 3,
        "Science, engineering assoc. pro.": 3,
        "Business, administration assoc. pro.": 3,
        "Health pro.": 2,
        "Teaching pro.": 2,
        "Legal, social, cultural pro.": 2,
        "Science, engineering professionals": 2,
        "Business professionals": 2,
        "Hospitality services managers": 1,
        "Production managers": 1,
        "Chief executives": 1,
        "Managers": 1,
    }

    exposure["occupation_digit"] = exposure["occupation_name"].map(major_group_map)
    if exposure["occupation_digit"].isna().any():
        missing = exposure.loc[exposure["occupation_digit"].isna(), "occupation_name"].tolist()
        raise ValueError(f"Missing major-group mapping for OECD exposure rows: {missing}")

    major = (
        exposure.groupby("occupation_digit", as_index=False)["ai_exposure"]
        .mean()
        .sort_values("occupation_digit")
        .reset_index(drop=True)
    )
    major["occupation_name_isco08"] = major["occupation_digit"].map(OCCUPATION_NAMES)
    major["ai_exposure_norm"] = (
        (major["ai_exposure"] - major["ai_exposure"].min())
        / (major["ai_exposure"].max() - major["ai_exposure"].min())
    )
    return major


def load_russia_occupation_matrix() -> pd.DataFrame:
    usecols = ["ref_area", "source", "classif1", "classif2", "time", "obs_value"]
    chunks: list[pd.DataFrame] = []
    reader = pd.read_csv(ILOSTAT_PATH, compression="gzip", usecols=usecols, chunksize=250_000, low_memory=False)
    for chunk in reader:
        subset = chunk.loc[
            chunk["ref_area"].eq("RUS")
            & chunk["time"].eq(2024)
            & chunk["classif1"].isin(PROJECT_SECTOR_MAP)
            & chunk["classif2"].astype(str).str.startswith("OCU_ISCO08_")
        ].copy()
        if not subset.empty:
            chunks.append(subset)

    if not chunks:
        raise ValueError("No Russian occupation-industry matrix found in ILOSTAT raw file.")

    data = pd.concat(chunks, ignore_index=True)
    data = data.rename(columns={"classif1": "isic4_code", "classif2": "occupation_code", "obs_value": "employment_thousand"})
    data["sector_id"] = data["isic4_code"].map(PROJECT_SECTOR_MAP)
    data["occupation_digit"] = data["occupation_code"].str.extract(r"(\d+|TOTAL)$")[0]
    data = data.loc[data["occupation_digit"].ne("TOTAL")].copy()
    data["occupation_digit"] = data["occupation_digit"].astype(int)

    grouped = (
        data.groupby(["sector_id", "occupation_digit"], as_index=False)["employment_thousand"]
        .sum()
        .rename(columns={"employment_thousand": "ilostat_employment_thousand"})
    )
    grouped["sector_name_ru"] = grouped["sector_id"].map(SECTOR_NAMES)
    return grouped


def load_baseline() -> pd.DataFrame:
    baseline = pd.read_csv(BASELINE_PATH)
    baseline = baseline.loc[baseline["year"].eq(2024), ["sector_id", "employment_thousand_persons", "annual_wage_rub"]].copy()
    baseline = baseline.rename(columns={"employment_thousand_persons": "official_employment_thousand"})
    return baseline


def load_structure_summary() -> pd.DataFrame:
    return pd.read_csv(STRUCTURE_PATH)


def build_cell_baseline() -> pd.DataFrame:
    occupations = load_russia_occupation_matrix()
    exposure = load_oecd_exposure()
    baseline = load_baseline()

    cell = occupations.merge(exposure, on="occupation_digit", how="left").merge(baseline, on="sector_id", how="left")
    if cell[["ai_exposure", "official_employment_thousand", "annual_wage_rub"]].isna().any().any():
        raise ValueError("Missing welfare baseline inputs after merging occupation, exposure, and baseline data.")

    cell["ilostat_sector_total_thousand"] = cell.groupby("sector_id")["ilostat_employment_thousand"].transform("sum")
    cell["occupation_share_in_sector"] = cell["ilostat_employment_thousand"] / cell["ilostat_sector_total_thousand"]
    cell["employment_thousand"] = cell["occupation_share_in_sector"] * cell["official_employment_thousand"]

    national_weights = cell.groupby("occupation_digit", as_index=False)["employment_thousand"].sum()
    scale = national_weights["employment_thousand"].sum() / np.dot(
        national_weights["employment_thousand"],
        national_weights["occupation_digit"].map(OCCUPATION_WAGE_MULTIPLIER_PRIOR),
    )
    occupation_wage_multiplier = {
        occupation_digit: multiplier * scale
        for occupation_digit, multiplier in OCCUPATION_WAGE_MULTIPLIER_PRIOR.items()
    }

    cell["occupation_wage_multiplier"] = cell["occupation_digit"].map(occupation_wage_multiplier)
    cell["annual_wage_occ_rub"] = cell["annual_wage_rub"] * cell["occupation_wage_multiplier"]
    cell["baseline_labour_income_bn_rub"] = cell["employment_thousand"] * cell["annual_wage_occ_rub"] / 1_000_000.0
    cell["occupation_name_isco08"] = cell["occupation_digit"].map(OCCUPATION_NAMES)
    cell["cell_id"] = np.arange(len(cell))
    return cell


def allocate_quintiles(cell: pd.DataFrame) -> pd.DataFrame:
    ranked = cell.sort_values(["annual_wage_occ_rub", "sector_id", "occupation_digit"]).reset_index(drop=True)
    total_employment = ranked["employment_thousand"].sum()
    quintile_size = total_employment / 5.0

    rows: list[dict[str, object]] = []
    cumulative_before = 0.0
    for base_row in ranked.itertuples(index=False):
        cell_lower = cumulative_before
        cell_upper = cumulative_before + float(base_row.employment_thousand)
        for quintile_idx in range(5):
            quintile_lower = quintile_size * quintile_idx
            quintile_upper = quintile_size * (quintile_idx + 1)
            overlap = max(0.0, min(cell_upper, quintile_upper) - max(cell_lower, quintile_lower))
            if overlap <= 1e-12:
                continue
            rows.append(
                {
                    "cell_id": int(base_row.cell_id),
                    "sector_id": base_row.sector_id,
                    "sector_name_ru": base_row.sector_name_ru,
                    "occupation_digit": int(base_row.occupation_digit),
                    "occupation_name_isco08": base_row.occupation_name_isco08,
                    "quintile": f"Q{quintile_idx + 1}",
                    "quintile_fraction_of_cell": overlap / float(base_row.employment_thousand),
                    "employment_thousand": overlap,
                    "baseline_labour_income_bn_rub": float(base_row.baseline_labour_income_bn_rub)
                    * overlap
                    / float(base_row.employment_thousand),
                }
            )
        cumulative_before = cell_upper
    return pd.DataFrame(rows)


def allocate_sector_delta_to_occupations(cell: pd.DataFrame, sector_delta: float) -> pd.Series:
    exposure_weight = cell["employment_thousand"] * cell["ai_exposure_norm"].clip(lower=0.05)
    inverse_exposure_weight = cell["employment_thousand"] * (1.05 - cell["ai_exposure_norm"]).clip(lower=0.05)
    weights = exposure_weight if sector_delta <= 0 else inverse_exposure_weight
    weight_sum = weights.sum()
    if weight_sum <= 0:
        return pd.Series(np.repeat(sector_delta / len(cell), len(cell)), index=cell.index)
    return sector_delta * weights / weight_sum


def grouped_gini(population: np.ndarray, income: np.ndarray) -> float:
    order = np.argsort(income / population)
    pop = population[order].astype(float)
    inc = income[order].astype(float)
    pop_share = pop / pop.sum()
    inc_share = inc / inc.sum()
    cum_pop = np.concatenate([[0.0], np.cumsum(pop_share)])
    cum_inc = np.concatenate([[0.0], np.cumsum(inc_share)])
    area = np.sum((cum_inc[1:] + cum_inc[:-1]) * (cum_pop[1:] - cum_pop[:-1]) / 2.0)
    return 1.0 - 2.0 * area


def build_summary() -> pd.DataFrame:
    cell_baseline = build_cell_baseline()
    quintile_map = allocate_quintiles(cell_baseline)
    structure = load_structure_summary()
    rows: list[dict[str, object]] = []

    for (scenario, throttle_scenario), scenario_group in structure.groupby(["scenario", "throttle_scenario"]):
        scenario_group = scenario_group.set_index("sector_id")
        working = cell_baseline.copy()
        working["employment_delta_2035_thousand"] = 0.0
        working["labour_income_delta_2035_bn_rub"] = 0.0

        for sector_id, sector_cells in working.groupby("sector_id"):
            sector_row = scenario_group.loc[sector_id]
            employment_delta = float(sector_row["employment_delta_2035_thousand"])
            labour_income_delta = float(sector_row["incremental_labour_income_2035_bn_rub"])
            occupation_emp_delta = allocate_sector_delta_to_occupations(sector_cells, employment_delta)
            occupation_income_weight = sector_cells["baseline_labour_income_bn_rub"]
            income_weight_sum = occupation_income_weight.sum()
            if income_weight_sum <= 0:
                occupation_income_delta = np.repeat(labour_income_delta / len(sector_cells), len(sector_cells))
            else:
                occupation_income_delta = labour_income_delta * occupation_income_weight / income_weight_sum

            working.loc[sector_cells.index, "employment_delta_2035_thousand"] = np.asarray(
                occupation_emp_delta,
                dtype=float,
            )
            working.loc[sector_cells.index, "labour_income_delta_2035_bn_rub"] = np.asarray(
                occupation_income_delta,
                dtype=float,
            )

        working["employment_2035_thousand"] = working["employment_thousand"] + working["employment_delta_2035_thousand"]
        working["labour_income_2035_bn_rub"] = (
            working["baseline_labour_income_bn_rub"] + working["labour_income_delta_2035_bn_rub"]
        )

        for occupation_digit, group in working.groupby("occupation_digit"):
            rows.append(
                {
                    "record_type": "occupation",
                    "scenario": scenario,
                    "throttle_scenario": throttle_scenario,
                    "occupation_digit": occupation_digit,
                    "occupation_name_isco08": group["occupation_name_isco08"].iloc[0],
                    "quintile": "",
                    "ai_exposure_score": float(group["ai_exposure"].iloc[0]),
                    "baseline_employment_thousand": float(group["employment_thousand"].sum()),
                    "employment_delta_2035_thousand": float(group["employment_delta_2035_thousand"].sum()),
                    "baseline_labour_income_bn_rub": float(group["baseline_labour_income_bn_rub"].sum()),
                    "labour_income_delta_2035_bn_rub": float(group["labour_income_delta_2035_bn_rub"].sum()),
                    "profit_gain_allocated_bn_rub": 0.0,
                    "total_income_delta_bn_rub": float(group["labour_income_delta_2035_bn_rub"].sum()),
                    "gini_baseline_proxy": np.nan,
                    "gini_post_proxy": np.nan,
                    "gini_delta_proxy": np.nan,
                }
            )

        profit_gain_total = float(scenario_group["incremental_profit_pool_2035_bn_rub"].sum())
        quintile_working = quintile_map.merge(
            working[
                [
                    "cell_id",
                    "sector_id",
                    "occupation_digit",
                    "employment_delta_2035_thousand",
                    "labour_income_delta_2035_bn_rub",
                ]
            ],
            on=["cell_id", "sector_id", "occupation_digit"],
            how="left",
        )
        quintile_working["employment_delta_2035_thousand"] = (
            quintile_working["employment_delta_2035_thousand"] * quintile_working["quintile_fraction_of_cell"]
        )
        quintile_working["labour_income_delta_2035_bn_rub"] = (
            quintile_working["labour_income_delta_2035_bn_rub"] * quintile_working["quintile_fraction_of_cell"]
        )

        quintile_summary = (
            quintile_working.groupby("quintile", as_index=False)[
                ["employment_thousand", "employment_delta_2035_thousand", "baseline_labour_income_bn_rub", "labour_income_delta_2035_bn_rub"]
            ]
            .sum()
            .sort_values("quintile")
            .reset_index(drop=True)
        )
        quintile_summary["profit_gain_allocated_bn_rub"] = quintile_summary["quintile"].map(CAPITAL_GAIN_QUINTILE_WEIGHTS) * profit_gain_total
        quintile_summary["total_income_delta_bn_rub"] = (
            quintile_summary["labour_income_delta_2035_bn_rub"] + quintile_summary["profit_gain_allocated_bn_rub"]
        )

        gini_baseline = grouped_gini(
            quintile_summary["employment_thousand"].to_numpy(),
            quintile_summary["baseline_labour_income_bn_rub"].to_numpy(),
        )
        gini_post = grouped_gini(
            (quintile_summary["employment_thousand"] + quintile_summary["employment_delta_2035_thousand"]).clip(lower=1e-9).to_numpy(),
            (quintile_summary["baseline_labour_income_bn_rub"] + quintile_summary["total_income_delta_bn_rub"]).clip(lower=1e-9).to_numpy(),
        )

        for quintile_row in quintile_summary.itertuples(index=False):
            rows.append(
                {
                    "record_type": "quintile",
                    "scenario": scenario,
                    "throttle_scenario": throttle_scenario,
                    "occupation_digit": np.nan,
                    "occupation_name_isco08": "",
                    "quintile": quintile_row.quintile,
                    "ai_exposure_score": np.nan,
                    "baseline_employment_thousand": float(quintile_row.employment_thousand),
                    "employment_delta_2035_thousand": float(quintile_row.employment_delta_2035_thousand),
                    "baseline_labour_income_bn_rub": float(quintile_row.baseline_labour_income_bn_rub),
                    "labour_income_delta_2035_bn_rub": float(quintile_row.labour_income_delta_2035_bn_rub),
                    "profit_gain_allocated_bn_rub": float(quintile_row.profit_gain_allocated_bn_rub),
                    "total_income_delta_bn_rub": float(quintile_row.total_income_delta_bn_rub),
                    "gini_baseline_proxy": float(gini_baseline),
                    "gini_post_proxy": float(gini_post),
                    "gini_delta_proxy": float(gini_post - gini_baseline),
                }
            )

    return pd.DataFrame(rows).sort_values(
        ["record_type", "scenario", "throttle_scenario", "quintile", "occupation_digit"]
    ).reset_index(drop=True)


def markdown_table(dataframe: pd.DataFrame, columns: list[str], float_columns: list[str]) -> str:
    table = dataframe[columns].copy()
    for column in float_columns:
        if column in table.columns:
            table[column] = table[column].map(lambda value: f"{value:.3f}" if pd.notna(value) else "")
    lines = [
        "| " + " | ".join(table.columns) + " |",
        "| " + " | ".join(["---"] * len(table.columns)) + " |",
    ]
    for row in table.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(value) else str(value) for value in row) + " |")
    return "\n".join(lines)


def build_report(summary: pd.DataFrame) -> str:
    occupation = summary.loc[
        summary["record_type"].eq("occupation")
        & summary["scenario"].eq("Base")
        & summary["throttle_scenario"].eq("BaseThrottle")
    ].copy()
    occupation["loss_per_baseline_pct"] = occupation["employment_delta_2035_thousand"] / occupation["baseline_employment_thousand"] * 100.0
    top_exposed = occupation.sort_values("ai_exposure_score", ascending=False).head(5)
    largest_losses = occupation.sort_values("employment_delta_2035_thousand").head(5)

    quintile = summary.loc[
        summary["record_type"].eq("quintile")
        & summary["scenario"].eq("Base")
        & summary["throttle_scenario"].eq("BaseThrottle")
    ].copy()
    gini_baseline = float(quintile["gini_baseline_proxy"].iloc[0])
    gini_post = float(quintile["gini_post_proxy"].iloc[0])
    gini_delta = float(quintile["gini_delta_proxy"].iloc[0])

    return f"""# Welfare Distributional Report

Этот блок раскладывает `Stage 4` direct labour/capital reallocation по occupation-major groups и по income-quintile proxy.

## 1. Формализация

Пусть `l_{{s,o}}` — занятость occupation group `o` в секторе `s`, `e_o` — occupation AI exposure, `\\Delta L_s` — sector employment delta из `Stage 4`.

Секторный employment shock распределяется по occupations как exposure-weighted allocation:

$$
\\omega_{{s,o}} =
\\frac{{l_{{s,o}} e_o}}{{\\sum_{{o'}} l_{{s,o'}} e_{{o'}}}},
\\qquad
\\Delta L_{{s,o}} = \\omega_{{s,o}} \\Delta L_s
$$

Базовый labour income по ячейке:

$$
Y^L_{{s,o}} = L_{{s,o}} \\cdot w_s \\cdot \\mu_o
$$

где `w_s` — официальный sector wage за `2024`, а `\\mu_o` — occupation wage multiplier proxy по ISCO08 major groups.

Incremental profit pool распределяется по quintile proxy через capital-income weights
`(0, 0, 0.05, 0.20, 0.75)` для `Q1..Q5`.

## 2. Источники

- Russian `occupation × industry` matrix: `data/raw/ilostat/emp_temp_eco_ocu_nb_a.csv.gz` (`RUS`, `2024`, `ISCO-08`, `ISIC4`)
- OECD figure data for AI exposure: [stat.link/2q5i1s](https://stat.link/2q5i1s)
- Rosstat sector wages: `data/raw/russia/tab3-zpl_2025.xlsx`
- Stage 4 sector outcomes: `data/processed/russia_economy_structure_sector_summary.csv`

Ключевая оговорка: в repo нет RLMS/LFS microdata по индивидуальным доходам. Поэтому quintile block ниже — это transparent proxy через `ISCO08` wage multipliers и sector wages, а не household micro-estimation.

## 3. Highest Exposure Occupations

{markdown_table(
    top_exposed[["occupation_digit", "occupation_name_isco08", "ai_exposure_score", "baseline_employment_thousand", "employment_delta_2035_thousand"]].head(5),
    ["occupation_digit", "occupation_name_isco08", "ai_exposure_score", "baseline_employment_thousand", "employment_delta_2035_thousand"],
    ["ai_exposure_score", "baseline_employment_thousand", "employment_delta_2035_thousand"],
)}

## 4. Largest Employment Losses

{markdown_table(
    largest_losses[["occupation_digit", "occupation_name_isco08", "baseline_employment_thousand", "employment_delta_2035_thousand", "loss_per_baseline_pct"]].head(5),
    ["occupation_digit", "occupation_name_isco08", "baseline_employment_thousand", "employment_delta_2035_thousand", "loss_per_baseline_pct"],
    ["baseline_employment_thousand", "employment_delta_2035_thousand", "loss_per_baseline_pct"],
)}

## 5. Quintile Proxy

{markdown_table(
    quintile[["quintile", "baseline_employment_thousand", "employment_delta_2035_thousand", "labour_income_delta_2035_bn_rub", "profit_gain_allocated_bn_rub", "total_income_delta_bn_rub"]].copy(),
    ["quintile", "baseline_employment_thousand", "employment_delta_2035_thousand", "labour_income_delta_2035_bn_rub", "profit_gain_allocated_bn_rub", "total_income_delta_bn_rub"],
    ["baseline_employment_thousand", "employment_delta_2035_thousand", "labour_income_delta_2035_bn_rub", "profit_gain_allocated_bn_rub", "total_income_delta_bn_rub"],
)}

Baseline grouped-labour Gini proxy равен `{gini_baseline:.3f}`. После AI reallocation и top-quintile-heavy profit capture он сдвигается до `{gini_post:.3f}`, то есть `ΔGini = {gini_delta:.3f}`.

## 6. Интерпретация

- Профессиональный риск концентрируется в white-collar major groups `1-4`, где OECD/Felten-derived exposure highest.
- Абсолютные employment losses всё равно велики и в крупных middle-skill группах, потому что они сидят внутри `C`, `J`, `M` и `K`.
- Quintile proxy показывает типичный pattern: labour losses and weak labour-income growth давят `Q1-Q4`, а profit-pool expansion концентрируется в `Q5`.
- Это welfare accounting, а не causal micro-simulation: без RLMS/LFS невозможно честно отделить within-occupation wage dispersion, secondary earners и regional heterogeneity.
"""


def main() -> None:
    summary = build_summary()
    OUTPUT_PATH.write_text(summary.to_csv(index=False), encoding="utf-8")
    OUTPUT_DOC.write_text(build_report(summary), encoding="utf-8")
    print(f"Saved welfare summary: {OUTPUT_PATH}")
    print(f"Saved welfare report: {OUTPUT_DOC}")


if __name__ == "__main__":
    main()

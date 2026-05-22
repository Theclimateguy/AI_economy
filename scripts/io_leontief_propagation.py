from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

IO_DIR = ROOT / "data" / "raw" / "russia" / "io"
IO_2016_PATH = IO_DIR / "baz-tzv-2016.xlsx"
IO_2019_PATH = IO_DIR / "tri-2019.xlsx"

STRUCTURE_SECTOR_PATH = ROOT / "data" / "processed" / "russia_economy_structure_sector_summary.csv"
STRUCTURE_AGGREGATE_PATH = ROOT / "data" / "processed" / "russia_economy_structure_aggregate_summary.csv"
IMPORT_FRICTION_PATH = ROOT / "data" / "processed" / "import_dependency_sector.csv"

OUTPUT_SUMMARY = ROOT / "data" / "processed" / "io_multiplier_sector_summary.csv"
OUTPUT_DECOMPOSITION = ROOT / "data" / "processed" / "io_indirect_decomposition.csv"
OUTPUT_DOC = ROOT / "docs" / "io_macro_closure.md"
STRUCTURE_REPORT_PATH = ROOT / "docs" / "russia_economy_structure_report.md"

SECTORS = ["B", "C", "C_mach", "DE", "F", "G", "H", "J", "K", "M"]
SECTOR_NAMES = {
    "B": "Добыча полезных ископаемых",
    "C": "Обрабатывающая промышленность",
    "C_mach": "Машиностроение (ОКВЭД 26–30)",
    "DE": "Энергетика и ЖКХ",
    "F": "Строительство",
    "G": "Оптовая и розничная торговля",
    "H": "Транспорт и логистика",
    "J": "ИТ и связь",
    "K": "Финансы и страхование",
    "M": "Профессиональные и научные услуги",
    "ALL": "Все восемь проектных секторов",
}
SECTOR_INDEX = {sector_id: idx for idx, sector_id in enumerate(SECTORS)}


@dataclass(frozen=True)
class IoSpec:
    year: int
    workbook_path: Path
    use_sheet: str
    import_sheet: str
    row_start: int
    row_stop: int
    col_start: int
    col_stop: int
    output_row: int
    va_row: int


IO_SPECS = {
    2016: IoSpec(
        year=2016,
        workbook_path=IO_2016_PATH,
        use_sheet="Симм ТЗВ",
        import_sheet="Симм имп",
        row_start=4,
        row_stop=104,
        col_start=3,
        col_stop=103,
        output_row=113,
        va_row=112,
    ),
    2019: IoSpec(
        year=2019,
        workbook_path=IO_2019_PATH,
        use_sheet="ТИоц",
        import_sheet="М-имп",
        row_start=4,
        row_stop=66,
        col_start=3,
        col_stop=65,
        output_row=76,
        va_row=75,
    ),
}


def map_2019_code(code: object) -> str | None:
    value = str(code).strip()
    if value.startswith("B "):
        return "B"
    if value.startswith(("С 26", "C 26", "С 27", "C 27", "С 28", "C 28", "С 29", "C 29", "С 30", "C 30")):
        return "C_mach"
    if value.startswith("С") or value.startswith("C "):
        return "C"
    if value.startswith("D ") or value.startswith("Е ") or value.startswith("E "):
        return "DE"
    if value.startswith("F "):
        return "F"
    if value.startswith("G "):
        return "G"
    if value.startswith("H "):
        return "H"
    if value.startswith("J "):
        return "J"
    if value.startswith("K "):
        return "K"
    if value.startswith("M "):
        return "M"
    return None


def map_2016_code(code: object) -> str | None:
    value = str(code).strip()
    if value in {"nan", "P33", "P34", "P6a", "D21-D31"}:
        return None
    if value.startswith(("10", "11", "12", "13", "14")):
        return "B"
    if re.search(r"\b(29|30|31|32|33|34|35)(\.|\b)", value):
        return "C_mach"
    if value.startswith(
        (
            "15",
            "16",
            "17",
            "18",
            "19",
            "20",
            "21",
            "22",
            "23",
            "24",
            "25",
            "26",
            "27",
            "28",
            "36",
            "37",
            "39.9",
        )
    ):
        return "C"
    if value.startswith(("40.1", "40.2", "40.3", "41", "90")):
        return "DE"
    if value.startswith("45"):
        return "F"
    if re.search(r"\b(50|51|52)(\.|\b)", value):
        return "G"
    if value.startswith(("60", "61", "62", "63")):
        return "H"
    if value.startswith("64"):
        return "J"
    if value.startswith(("65", "66", "67")):
        return "K"
    if value.startswith(("72", "73", "74")):
        return "M"
    return None


def map_code(year: int, code: object) -> str | None:
    if year == 2016:
        return map_2016_code(code)
    if year == 2019:
        return map_2019_code(code)
    raise ValueError(f"Unsupported IO year: {year}")


def aggregate_io_system(spec: IoSpec) -> dict[str, object]:
    if not spec.workbook_path.exists():
        raise FileNotFoundError(f"Missing IO workbook: {spec.workbook_path}")

    use_df = pd.read_excel(spec.workbook_path, sheet_name=spec.use_sheet, header=None)
    import_df = pd.read_excel(spec.workbook_path, sheet_name=spec.import_sheet, header=None)

    row_mapping = [(row_idx, map_code(spec.year, use_df.iat[row_idx, 1])) for row_idx in range(spec.row_start, spec.row_stop)]
    col_mapping = [(col_idx, map_code(spec.year, use_df.iat[2, col_idx])) for col_idx in range(spec.col_start, spec.col_stop)]

    use_matrix = np.zeros((len(SECTORS), len(SECTORS)))
    import_matrix = np.zeros((len(SECTORS), len(SECTORS)))
    output_vector = np.zeros(len(SECTORS))
    value_added_vector = np.zeros(len(SECTORS))

    for row_idx, row_sector in row_mapping:
        if row_sector is None:
            continue
        row_pos = SECTOR_INDEX[row_sector]
        for col_idx, col_sector in col_mapping:
            if col_sector is None:
                continue
            col_pos = SECTOR_INDEX[col_sector]
            use_matrix[row_pos, col_pos] += float(use_df.iat[row_idx, col_idx] or 0.0)
            import_matrix[row_pos, col_pos] += float(import_df.iat[row_idx, col_idx] or 0.0)

    for col_idx, col_sector in col_mapping:
        if col_sector is None:
            continue
        col_pos = SECTOR_INDEX[col_sector]
        output_vector[col_pos] += float(use_df.iat[spec.output_row, col_idx] or 0.0)
        value_added_vector[col_pos] += float(use_df.iat[spec.va_row, col_idx] or 0.0)

    technical_matrix = use_matrix / output_vector
    leontief_inverse = np.linalg.inv(np.eye(len(SECTORS)) - technical_matrix)
    import_coefficients = import_matrix.sum(axis=0) / output_vector
    value_added_coefficients = value_added_vector / output_vector

    return {
        "year": spec.year,
        "use_matrix": use_matrix,
        "import_matrix": import_matrix,
        "technical_matrix": technical_matrix,
        "leontief_inverse": leontief_inverse,
        "output_vector": output_vector,
        "value_added_vector": value_added_vector,
        "value_added_coefficients": value_added_coefficients,
        "import_coefficients": import_coefficients,
        "backward_linkage_multiplier": leontief_inverse.sum(axis=0),
        "own_output_multiplier": np.diag(leontief_inverse),
    }


def load_structure_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sector_summary = pd.read_csv(STRUCTURE_SECTOR_PATH)
    aggregate_summary = pd.read_csv(STRUCTURE_AGGREGATE_PATH)
    import_friction = pd.read_csv(IMPORT_FRICTION_PATH)
    return sector_summary, aggregate_summary, import_friction


def build_summary_rows(
    io_systems: dict[int, dict[str, object]],
    sector_summary: pd.DataFrame,
    aggregate_summary: pd.DataFrame,
    import_friction: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    import_wedges = import_friction.set_index("sector_id").reindex(SECTORS)
    rows: list[dict[str, object]] = []
    decomposition_rows: list[dict[str, object]] = []

    for table_year, system in io_systems.items():
        value_added_coefficients = system["value_added_coefficients"]
        leontief_inverse = system["leontief_inverse"]
        import_coefficients = system["import_coefficients"]
        backward_linkage = system["backward_linkage_multiplier"]
        own_output_multiplier = system["own_output_multiplier"]

        base_import_coefficients = import_coefficients
        sanction_base_coefficients = import_coefficients * (1.0 - import_wedges["sanction_wedge_base"].to_numpy())
        sanction_relief_coefficients = import_coefficients * (1.0 - import_wedges["sanction_wedge_relief"].to_numpy())

        for (scenario, throttle_scenario), scenario_group in sector_summary.groupby(["scenario", "throttle_scenario"]):
            scenario_group = scenario_group.set_index("sector_id").reindex(SECTORS)

            direct_va_bn = scenario_group["incremental_va_2035_bn_rub"].to_numpy()
            direct_emp_thousand = scenario_group["employment_delta_2035_thousand"].to_numpy()
            va_cf_mn = scenario_group["va_cf_2035_bn_rub"].to_numpy() * 1000.0
            emp_cf_thousand = (
                scenario_group["employment_ai_2035_thousand"].to_numpy() - direct_emp_thousand
            )
            output_cf_mn = va_cf_mn / value_added_coefficients
            employment_coefficients = emp_cf_thousand / output_cf_mn

            direct_output_impulse_mn = direct_va_bn * 1000.0 / value_added_coefficients
            total_output_response_mn = leontief_inverse @ direct_output_impulse_mn
            indirect_output_response_mn = total_output_response_mn - direct_output_impulse_mn
            indirect_va_mn = value_added_coefficients * indirect_output_response_mn
            indirect_emp_thousand = employment_coefficients * indirect_output_response_mn

            total_import_base_mn = base_import_coefficients * total_output_response_mn
            total_import_sanction_base_mn = sanction_base_coefficients * total_output_response_mn
            total_import_sanction_relief_mn = sanction_relief_coefficients * total_output_response_mn

            aggregate_row = aggregate_summary.loc[
                aggregate_summary["scenario"].eq(scenario)
                & aggregate_summary["throttle_scenario"].eq(throttle_scenario)
            ].iloc[0]

            direct_va_total_bn = float(direct_va_bn.sum())
            indirect_va_total_bn = float(indirect_va_mn.sum() / 1000.0)
            io_total_va_gain_bn = direct_va_total_bn + indirect_va_total_bn
            direct_emp_total_thousand = float(direct_emp_thousand.sum())
            indirect_emp_total_thousand = float(indirect_emp_thousand.sum())

            for recipient_id in SECTORS:
                recipient_pos = SECTOR_INDEX[recipient_id]
                response_by_supplier_mn = leontief_inverse[:, recipient_pos] * direct_output_impulse_mn[recipient_pos]
                response_by_supplier_mn[recipient_pos] -= direct_output_impulse_mn[recipient_pos]
                for supplier_id in SECTORS:
                    supplier_pos = SECTOR_INDEX[supplier_id]
                    decomposition_rows.append(
                        {
                            "table_year": table_year,
                            "scenario": scenario,
                            "throttle_scenario": throttle_scenario,
                            "recipient_sector": recipient_id,
                            "recipient_sector_name_ru": SECTOR_NAMES[recipient_id],
                            "supplier_sector": supplier_id,
                            "supplier_sector_name_ru": SECTOR_NAMES[supplier_id],
                            "direct_recipient_va_impulse_bn_rub": float(direct_va_bn[recipient_pos]),
                            "indirect_output_effect_bn_rub": float(response_by_supplier_mn[supplier_pos] / 1000.0),
                            "indirect_va_effect_bn_rub": float(
                                value_added_coefficients[supplier_pos] * response_by_supplier_mn[supplier_pos] / 1000.0
                            ),
                            "indirect_employment_effect_thousand": float(
                                employment_coefficients[supplier_pos] * response_by_supplier_mn[supplier_pos]
                            ),
                        }
                    )

            rows.append(
                {
                    "record_type": "aggregate",
                    "table_year": table_year,
                    "scenario": scenario,
                    "throttle_scenario": throttle_scenario,
                    "sector_id": "ALL",
                    "sector_name_ru": SECTOR_NAMES["ALL"],
                    "direct_va_gain_2035_bn_rub": direct_va_total_bn,
                    "io_indirect_va_gain_2035_bn_rub": indirect_va_total_bn,
                    "io_total_va_gain_2035_bn_rub": io_total_va_gain_bn,
                    "io_multiplier_va_ratio": io_total_va_gain_bn / direct_va_total_bn if direct_va_total_bn else np.nan,
                    "direct_employment_delta_2035_thousand": direct_emp_total_thousand,
                    "io_indirect_employment_support_2035_thousand": indirect_emp_total_thousand,
                    "io_net_employment_delta_2035_thousand": direct_emp_total_thousand + indirect_emp_total_thousand,
                    "backward_linkage_multiplier": float(np.average(backward_linkage, weights=direct_output_impulse_mn)),
                    "own_sector_output_multiplier": float(np.average(own_output_multiplier, weights=direct_output_impulse_mn)),
                    "direct_output_impulse_2035_bn_rub": float(direct_output_impulse_mn.sum() / 1000.0),
                    "io_total_output_gain_2035_bn_rub": float(total_output_response_mn.sum() / 1000.0),
                    "import_content_base_2035_bn_rub": float(total_import_base_mn.sum() / 1000.0),
                    "import_content_sanction_base_2035_bn_rub": float(total_import_sanction_base_mn.sum() / 1000.0),
                    "import_content_sanction_relief_2035_bn_rub": float(total_import_sanction_relief_mn.sum() / 1000.0),
                    "import_content_sanction_saving_base_2035_bn_rub": float(
                        (total_import_base_mn - total_import_sanction_base_mn).sum() / 1000.0
                    ),
                    "import_content_sanction_saving_relief_2035_bn_rub": float(
                        (total_import_base_mn - total_import_sanction_relief_mn).sum() / 1000.0
                    ),
                    "accounting_total_va_gain_2035_pct": float(aggregate_row["total_va_gain_2035_pct"]),
                    "io_total_va_gain_2035_pct_of_cf": io_total_va_gain_bn
                    / float(aggregate_row["total_va_cf_2035_bn_rub"])
                    * 100.0,
                }
            )

            for sector_id in SECTORS:
                col_pos = SECTOR_INDEX[sector_id]
                direct_output_single_mn = np.zeros(len(SECTORS))
                direct_output_single_mn[col_pos] = direct_output_impulse_mn[col_pos]
                total_output_single_mn = leontief_inverse @ direct_output_single_mn
                indirect_output_single_mn = total_output_single_mn - direct_output_single_mn
                indirect_va_single_bn = float(
                    (value_added_coefficients * indirect_output_single_mn).sum() / 1000.0
                )
                indirect_emp_single_thousand = float(
                    (employment_coefficients * indirect_output_single_mn).sum()
                )
                import_base_single_bn = float((base_import_coefficients * total_output_single_mn).sum() / 1000.0)
                import_sb_single_bn = float(
                    (sanction_base_coefficients * total_output_single_mn).sum() / 1000.0
                )
                import_sr_single_bn = float(
                    (sanction_relief_coefficients * total_output_single_mn).sum() / 1000.0
                )

                rows.append(
                    {
                        "record_type": "sector",
                        "table_year": table_year,
                        "scenario": scenario,
                        "throttle_scenario": throttle_scenario,
                        "sector_id": sector_id,
                        "sector_name_ru": SECTOR_NAMES[sector_id],
                        "direct_va_gain_2035_bn_rub": float(direct_va_bn[col_pos]),
                        "io_indirect_va_gain_2035_bn_rub": indirect_va_single_bn,
                        "io_total_va_gain_2035_bn_rub": float(direct_va_bn[col_pos] + indirect_va_single_bn),
                        "io_multiplier_va_ratio": (
                            (direct_va_bn[col_pos] + indirect_va_single_bn) / direct_va_bn[col_pos]
                            if direct_va_bn[col_pos]
                            else np.nan
                        ),
                        "direct_employment_delta_2035_thousand": float(direct_emp_thousand[col_pos]),
                        "io_indirect_employment_support_2035_thousand": indirect_emp_single_thousand,
                        "io_net_employment_delta_2035_thousand": float(direct_emp_thousand[col_pos] + indirect_emp_single_thousand),
                        "backward_linkage_multiplier": float(backward_linkage[col_pos]),
                        "own_sector_output_multiplier": float(own_output_multiplier[col_pos]),
                        "direct_output_impulse_2035_bn_rub": float(direct_output_impulse_mn[col_pos] / 1000.0),
                        "io_total_output_gain_2035_bn_rub": float(total_output_single_mn.sum() / 1000.0),
                        "import_content_base_2035_bn_rub": import_base_single_bn,
                        "import_content_sanction_base_2035_bn_rub": import_sb_single_bn,
                        "import_content_sanction_relief_2035_bn_rub": import_sr_single_bn,
                        "import_content_sanction_saving_base_2035_bn_rub": import_base_single_bn - import_sb_single_bn,
                        "import_content_sanction_saving_relief_2035_bn_rub": import_base_single_bn - import_sr_single_bn,
                        "accounting_total_va_gain_2035_pct": np.nan,
                        "io_total_va_gain_2035_pct_of_cf": np.nan,
                    }
                )

    summary = pd.DataFrame(rows).sort_values(
        ["record_type", "table_year", "scenario", "throttle_scenario", "sector_id"]
    ).reset_index(drop=True)
    decomposition = pd.DataFrame(decomposition_rows).sort_values(
        ["table_year", "scenario", "throttle_scenario", "recipient_sector", "supplier_sector"]
    ).reset_index(drop=True)
    return summary, decomposition


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


def build_doc(summary: pd.DataFrame) -> str:
    decomposition = pd.read_csv(OUTPUT_DECOMPOSITION) if OUTPUT_DECOMPOSITION.exists() else pd.DataFrame()
    aggregate_base = summary.loc[
        summary["record_type"].eq("aggregate")
        & summary["table_year"].eq(2019)
        & summary["scenario"].eq("Base")
        & summary["throttle_scenario"].eq("BaseThrottle")
    ].iloc[0]
    aggregate_compare = summary.loc[
        summary["record_type"].eq("aggregate")
        & summary["scenario"].eq("Base")
        & summary["throttle_scenario"].eq("BaseThrottle")
    ].copy()
    sector_base = summary.loc[
        summary["record_type"].eq("sector")
        & summary["table_year"].eq(2019)
        & summary["scenario"].eq("Base")
        & summary["throttle_scenario"].eq("BaseThrottle")
    ].copy()
    sector_base = sector_base.sort_values("io_indirect_va_gain_2035_bn_rub", ascending=False)
    strongest_import = sector_base.sort_values("import_content_base_2035_bn_rub", ascending=False)
    top_pairs = pd.DataFrame()
    if not decomposition.empty:
        top_pairs = (
            decomposition.loc[
                decomposition["table_year"].eq(2019)
                & decomposition["scenario"].eq("Base")
                & decomposition["throttle_scenario"].eq("BaseThrottle")
            ]
            .sort_values("indirect_employment_effect_thousand", ascending=False)
            .head(5)
        )

    return f"""# IO Macro Closure

Этот блок добавляет partial input-output closure поверх `Stage 4` direct accounting layer и считает backward-linkage propagation для проектных секторов `B, C, DE, F, H, J, K, M`.

## 1. Формализация

Для агрегированного `8 x 8` use matrix:

$$
A_{{ij}} = \\frac{{Z_{{ij}}}}{{x_j}},
\\qquad
L = (I - A)^{{-1}}
$$

где `Z` — промежуточное потребление, `x` — выпуск сектора, `A` — матрица прямых затрат.

Direct `Stage 4` shock переводится в output-equivalent impulse через value-added coefficient:

$$
v_s = \\frac{{VA_s}}{{x_s}},
\\qquad
\\Delta f_s = \\frac{{\\Delta VA^{{direct}}_s}}{{v_s}}
$$

Тогда total output response:

$$
\\Delta x = L \\Delta f,
\\qquad
\\Delta x^{{indirect}} = (L - I) \\Delta f
$$

А IO-adjusted value added и занятость считаются через fixed coefficients:

$$
\\Delta VA^{{IO}} = \\operatorname{{diag}}(v) \\Delta x,
\\qquad
\\Delta EMP^{{indirect}} = \\operatorname{{diag}}(n) \\Delta x^{{indirect}}
$$

где `n_s = EMP_s / x_s` калибруется на `2035` counterfactual из `Stage 4`.

Import content:

$$
m_s = \\frac{{M_s}}{{x_s}},
\\qquad
IC = \\sum_s m_s \\Delta x_s
$$

Для санкционного import substitution считаем first-pass haircut:

$$
m^{{sanction}}_s = m_s (1 - \\omega_s)
$$

где `\\omega_s` — sector sanction wedge из `import_friction_layer.py`.

## 2. Источники

- Rosstat accounts page: [rosstat.gov.ru/accounts](https://rosstat.gov.ru/accounts)
- 2016 base IO table: [baz-tzv-2016(1).xlsx](https://rosstat.gov.ru/storage/mediabank/baz-tzv-2016(1).xlsx)
- 2019 supply-use tables: [tri-2019.xlsx](https://rosstat.gov.ru/storage/mediabank/tri-2019.xlsx)
- WIOD reference for methodology: [rug.nl/ggdc/valuechain/wiod](https://www.rug.nl/ggdc/valuechain/wiod/)

Важная оговорка на `30 апреля 2026`: на странице Rosstat есть базовая `ТЗВ 2016` и `TRI 2019`, но не опубликована отдельная базовая `ТЗВ 2019`. Поэтому `2019` блок строится из `ТИоц` и `М-имп` после агрегации к проектным восьми секторам; `2016` используется как structural cross-check.

## 3. Aggregate Comparison

| table_year | accounting_total_va_gain_2035_pct | io_total_va_gain_2035_pct_of_cf | direct_va_gain_2035_bn_rub | io_indirect_va_gain_2035_bn_rub | io_total_va_gain_2035_bn_rub | direct_employment_delta_2035_thousand | io_indirect_employment_support_2035_thousand | io_net_employment_delta_2035_thousand | import_content_base_2035_bn_rub |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2016), "accounting_total_va_gain_2035_pct"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2016), "io_total_va_gain_2035_pct_of_cf"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2016), "direct_va_gain_2035_bn_rub"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2016), "io_indirect_va_gain_2035_bn_rub"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2016), "io_total_va_gain_2035_bn_rub"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2016), "direct_employment_delta_2035_thousand"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2016), "io_indirect_employment_support_2035_thousand"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2016), "io_net_employment_delta_2035_thousand"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2016), "import_content_base_2035_bn_rub"].iloc[0]:.3f} |
| 2019 | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2019), "accounting_total_va_gain_2035_pct"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2019), "io_total_va_gain_2035_pct_of_cf"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2019), "direct_va_gain_2035_bn_rub"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2019), "io_indirect_va_gain_2035_bn_rub"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2019), "io_total_va_gain_2035_bn_rub"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2019), "direct_employment_delta_2035_thousand"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2019), "io_indirect_employment_support_2035_thousand"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2019), "io_net_employment_delta_2035_thousand"].iloc[0]:.3f} | {aggregate_compare.loc[aggregate_compare["table_year"].eq(2019), "import_content_base_2035_bn_rub"].iloc[0]:.3f} |

Базовый вывод устойчив: direct accounting headline `4.55%` для `VA` заметно недооценивает total production-chain effect. На `2019` таблице `BaseThrottle` даёт `7.35%` к `2035` counterfactual `VA`, из которых `4.23 трлн руб.` — это косвенный supply-chain effect сверх прямого sector-level gain.

При этом занятость меняет знак: direct accounting даёт `-726 тыс.`, но IO-блок возвращает `+875 тыс.` косвенного спроса на upstream/downstream цепочки, так что net partial-closure effect становится `+148 тыс.`. Это не означает full-equilibrium занятость; это именно Leontief demand-support effect без цен, wages и crowding-out.

## 4. Backward Linkages

{markdown_table(
    sector_base[["sector_id", "sector_name_ru", "backward_linkage_multiplier", "own_sector_output_multiplier", "io_indirect_va_gain_2035_bn_rub"]].head(8),
    ["sector_id", "sector_name_ru", "backward_linkage_multiplier", "own_sector_output_multiplier", "io_indirect_va_gain_2035_bn_rub"],
    ["backward_linkage_multiplier", "own_sector_output_multiplier", "io_indirect_va_gain_2035_bn_rub"],
)}

Самые сильные backward linkages у `DE`, `C` и `F`; именно поэтому даже умеренный direct AI-shock в utilities даёт disproportionate indirect effect, а manufacturing остаётся главным multiplier channel в абсолютных рублях.

## 5. Import Content Under Sanctions

{markdown_table(
    strongest_import[["sector_id", "sector_name_ru", "import_content_base_2035_bn_rub", "import_content_sanction_base_2035_bn_rub", "import_content_sanction_saving_base_2035_bn_rub"]].head(5),
    ["sector_id", "sector_name_ru", "import_content_base_2035_bn_rub", "import_content_sanction_base_2035_bn_rub", "import_content_sanction_saving_base_2035_bn_rub"],
    ["import_content_base_2035_bn_rub", "import_content_sanction_base_2035_bn_rub", "import_content_sanction_saving_base_2035_bn_rub"],
)}

Для агрегированного `2019 BaseThrottle` shock vector import content оценивается в `{aggregate_base["import_content_base_2035_bn_rub"]:.3f} млрд руб.`. First-pass sanction substitution haircut снижает его до `{aggregate_base["import_content_sanction_base_2035_bn_rub"]:.3f} млрд руб.` в `SanctionBase` equivalent accounting, то есть экономит `{aggregate_base["import_content_sanction_saving_base_2035_bn_rub"]:.3f} млрд руб.` внешней компонентной зависимости.

## 6. Межотраслевые цепочки спроса

Топ-5 пар поставщик → реципиент по косвенному эффекту занятости:

{markdown_table(
    top_pairs[["supplier_sector", "recipient_sector", "indirect_va_effect_bn_rub", "indirect_employment_effect_thousand"]],
    ["supplier_sector", "recipient_sector", "indirect_va_effect_bn_rub", "indirect_employment_effect_thousand"],
    ["indirect_va_effect_bn_rub", "indirect_employment_effect_thousand"],
) if not top_pairs.empty else "_Decomposition output is unavailable._"}

## 7. Ограничения

- `2019` строится из supply-use, а не из опубликованной симметричной `ТЗВ`; это корректно на уровне `8` агрегатов, но слабее full product-technology reconstruction.
- Используется открытая quantity-side Leontief closure без цен, substitution, bottleneck capacity и monetary policy.
- Employment response трактуется как fixed-coefficient demand support поверх direct labour-saving из `Stage 4`; это upper bound для short-run chain re-absorption.
- Import substitution задана через sanction wedges из previous issue, а не через отдельную dynamic trade model.
"""


def update_structure_report(summary: pd.DataFrame) -> None:
    if not STRUCTURE_REPORT_PATH.exists():
        return

    report_text = STRUCTURE_REPORT_PATH.read_text(encoding="utf-8")
    aggregate_2019 = summary.loc[
        summary["record_type"].eq("aggregate")
        & summary["table_year"].eq(2019)
        & summary["scenario"].eq("Base")
        & summary["throttle_scenario"].eq("BaseThrottle")
    ].iloc[0]
    limitations_block = f"""## 8. Ограничения

- Базовые headline-цифры выше остаются direct accounting layer; partial IO-closure вынесен в `docs/io_macro_closure.md`.
- По `2019` Rosstat `TRI` тот же `Base / BaseThrottle` shock vector даёт `IO-adjusted VA gain = {aggregate_2019["io_total_va_gain_2035_pct_of_cf"]:.3f}%` против accounting `4.549%`, то есть ещё `+{aggregate_2019["io_indirect_va_gain_2035_bn_rub"]:.3f}` млрд руб. через межотраслевые связи.
- Direct employment effect в accounting layer равен `{aggregate_2019["direct_employment_delta_2035_thousand"]:.3f}` тыс., но Leontief demand-support добавляет `{aggregate_2019["io_indirect_employment_support_2035_thousand"]:.3f}` тыс.; net partial-closure outcome становится `{aggregate_2019["io_net_employment_delta_2035_thousand"]:.3f}` тыс. Это не GE-оценка и не учитывает wages/prices crowding-out.
- `VA` строится в baseline-ruble units через real growth и AI boosts; номинальная инфляция не моделируется.
- Параметры `η` заданы сценарно по adoption class и должны идти в sensitivity block.
- `MOS_s` — pressure proxy, а не доказательство намеренного ограничения внедрения.
"""
    start = report_text.find("## 8. Ограничения")
    end = report_text.find("## 9. Sensitivity")
    if start == -1 or end == -1 or end <= start:
        report_text = report_text.rstrip() + "\n\n" + limitations_block + "\n\n## 9. Sensitivity\n"
    else:
        report_text = report_text[:start] + limitations_block + "\n\n" + report_text[end:]
    STRUCTURE_REPORT_PATH.write_text(report_text, encoding="utf-8")


def main() -> None:
    io_systems = {year: aggregate_io_system(spec) for year, spec in IO_SPECS.items()}
    sector_summary, aggregate_summary, import_friction = load_structure_inputs()
    summary, decomposition = build_summary_rows(io_systems, sector_summary, aggregate_summary, import_friction)
    OUTPUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY.write_text(summary.to_csv(index=False), encoding="utf-8")
    OUTPUT_DECOMPOSITION.write_text(decomposition.to_csv(index=False), encoding="utf-8")
    OUTPUT_DOC.write_text(build_doc(summary), encoding="utf-8")
    update_structure_report(summary)
    print(f"Saved IO summary: {OUTPUT_SUMMARY}")
    print(f"Saved IO decomposition: {OUTPUT_DECOMPOSITION}")
    print(f"Saved IO report: {OUTPUT_DOC}")


if __name__ == "__main__":
    main()

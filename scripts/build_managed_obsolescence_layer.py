from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "russia_klems_sources.json"

ABSOLUTE_VARIABLES = {"GO", "II", "VA", "LAB", "CAP", "EMP", "H_EMP"}
INDEX_VARIABLES = {
    "VA_QI",
    "GO_QI",
    "LP_I",
    "LAB_QI",
    "CAP_QI",
    "CAPIT_QI",
    "CAPNIT_QI",
    "VA_Q",
    "VAConH",
    "VAConK",
    "VAConTFP",
    "TFPva_I",
    "LAB_AVG",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_path(path_str: str) -> Path:
    return ROOT / path_str


def ensure_source(config: dict) -> Path:
    path = resolve_path(config["raw_path"])
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(config["source_url"], timeout=180)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def year_columns(dataframe: pd.DataFrame, year_start: int, year_end: int) -> list[str]:
    expected = [f"_{year}" for year in range(year_start, year_end + 1)]
    missing = [column for column in expected if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing expected Russia KLEMS year columns: {missing}")
    return expected


def load_russia_klems_long(path: Path, config: dict) -> pd.DataFrame:
    wide = pd.read_excel(path, sheet_name="DATA")
    years = year_columns(wide, config["year_start"], config["year_end"])
    selected = wide.loc[wide["Variable"].isin(config["selected_variables"])].copy()
    long = selected.melt(
        id_vars=["Variable", "desc", "code"],
        value_vars=years,
        var_name="year",
        value_name="value",
    )
    long["year"] = long["year"].str.removeprefix("_").astype(int)
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    return long


def aggregate_sector_variable(rows: pd.DataFrame, variable: str) -> float:
    values = rows["value"].dropna()
    if values.empty:
        return np.nan
    if variable in ABSOLUTE_VARIABLES:
        return float(values.sum())
    if variable in INDEX_VARIABLES:
        return float(values.mean())
    raise ValueError(f"Unknown aggregation rule for variable {variable}.")


def build_sector_panel(long: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, dict]:
    records: list[dict] = []
    map_records: list[dict] = []
    for sector in config["sector_map"]:
        codes = sector["russia_klems_codes"]
        subset = long.loc[long["code"].isin(codes)].copy()
        if subset.empty:
            raise ValueError(f"No Russia KLEMS rows matched sector {sector['sector_id']} with codes {codes}.")
        for (year, variable), rows in subset.groupby(["year", "Variable"]):
            records.append(
                {
                    "year": int(year),
                    "sector_id": sector["sector_id"],
                    "sector_name_ru": sector["sector_name_ru"],
                    "variable": variable,
                    "value": aggregate_sector_variable(rows, variable),
                }
            )
        for _, row in subset[["code", "desc"]].drop_duplicates().iterrows():
            map_records.append(
                {
                    "sector_id": sector["sector_id"],
                    "sector_name_ru": sector["sector_name_ru"],
                    "russia_klems_code": row["code"],
                    "russia_klems_desc": row["desc"],
                    "fit_quality": sector["fit_quality"],
                    "fit_note": sector["fit_note"],
                }
            )

    panel = pd.DataFrame(records)
    panel = panel.pivot_table(
        index=["year", "sector_id", "sector_name_ru"],
        columns="variable",
        values="value",
        aggfunc="first",
    ).reset_index()
    panel.columns.name = None

    sector_meta = pd.DataFrame(config["sector_map"])[
        ["sector_id", "russia_klems_codes", "fit_quality", "fit_note"]
    ].copy()
    sector_meta["russia_klems_codes"] = sector_meta["russia_klems_codes"].str.join("+")
    panel = panel.merge(sector_meta, on="sector_id", how="left")

    panel["labour_share_klems"] = panel["LAB"] / panel["VA"]
    panel["capital_share_klems"] = panel["CAP"] / panel["VA"]
    panel["capital_labour_comp_ratio"] = panel["CAP"] / panel["LAB"]
    panel["ict_to_nonict_capital_services_index"] = panel["CAPIT_QI"] / panel["CAPNIT_QI"]
    panel["va_per_hour_current_rub"] = panel["VA"] / panel["H_EMP"]
    panel["hours_per_person"] = panel["H_EMP"] / panel["EMP"] * 1000.0

    panel = panel.sort_values(["sector_id", "year"]).reset_index(drop=True)
    for column in [
        "VA",
        "LAB",
        "CAP",
        "EMP",
        "H_EMP",
        "LP_I",
        "CAP_QI",
        "LAB_QI",
        "CAPIT_QI",
        "CAPNIT_QI",
        "TFPva_I",
        "labour_share_klems",
        "capital_labour_comp_ratio",
    ]:
        if column in panel.columns:
            panel[f"{column}_growth_pct"] = panel.groupby("sector_id")[column].pct_change() * 100.0

    metadata = {
        "matched_codes": map_records,
        "aggregation_rules": {
            "absolute_variables": sorted(ABSOLUTE_VARIABLES),
            "index_variables": sorted(INDEX_VARIABLES),
            "index_aggregation_note": "Mapped sectors are single-code in this version; mean aggregation is a fallback for future multi-code mappings.",
        },
    }
    return panel, metadata


def cagr(first: float, last: float, years: int) -> float:
    if first is None or last is None or not np.isfinite(first) or not np.isfinite(last):
        return np.nan
    if first <= 0 or last <= 0 or years <= 0:
        return np.nan
    return math.exp(math.log(last / first) / years) - 1.0


def minmax_positive(series: pd.Series) -> pd.Series:
    positive = series.clip(lower=0.0)
    if positive.max(skipna=True) == positive.min(skipna=True):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (positive - positive.min(skipna=True)) / (positive.max(skipna=True) - positive.min(skipna=True))


def first_last(panel: pd.DataFrame, sector_id: str, column: str, year_start: int, year_end: int) -> tuple[float, float]:
    rows = panel.loc[panel["sector_id"].eq(sector_id)]
    first = rows.loc[rows["year"].eq(year_start), column]
    last = rows.loc[rows["year"].eq(year_end), column]
    return (
        float(first.iloc[0]) if not first.empty else np.nan,
        float(last.iloc[0]) if not last.empty else np.nan,
    )


def build_obsolescence_proxy(panel: pd.DataFrame, config: dict) -> pd.DataFrame:
    year_start = config["year_start"]
    year_end = config["year_end"]
    years = year_end - year_start
    records: list[dict] = []
    for sector in config["sector_map"]:
        sector_id = sector["sector_id"]
        record = {
            "sector_id": sector_id,
            "sector_name_ru": sector["sector_name_ru"],
            "period_start": year_start,
            "period_end": year_end,
            "fit_quality": sector["fit_quality"],
        }
        for column in [
            "LP_I",
            "H_EMP",
            "EMP",
            "LAB_QI",
            "CAP_QI",
            "CAPIT_QI",
            "CAPNIT_QI",
            "TFPva_I",
            "labour_share_klems",
            "capital_labour_comp_ratio",
        ]:
            first, last = first_last(panel, sector_id, column, year_start, year_end)
            record[f"{column}_start"] = first
            record[f"{column}_end"] = last
            record[f"{column}_cagr"] = cagr(first, last, years)

        record["labour_share_change_pp"] = (
            record["labour_share_klems_end"] - record["labour_share_klems_start"]
        )
        record["productivity_hours_gap_cagr"] = record["LP_I_cagr"] - record["H_EMP_cagr"]
        record["capital_labour_services_gap_cagr"] = record["CAP_QI_cagr"] - record["LAB_QI_cagr"]
        record["ict_nonict_services_gap_cagr"] = record["CAPIT_QI_cagr"] - record["CAPNIT_QI_cagr"]
        record["employment_contraction_cagr"] = -record["EMP_cagr"]
        records.append(record)

    proxy = pd.DataFrame(records)
    proxy["productivity_hours_gap_score"] = minmax_positive(proxy["productivity_hours_gap_cagr"])
    proxy["capital_labour_services_gap_score"] = minmax_positive(proxy["capital_labour_services_gap_cagr"])
    proxy["ict_nonict_services_gap_score"] = minmax_positive(proxy["ict_nonict_services_gap_cagr"])
    proxy["employment_contraction_score"] = minmax_positive(proxy["employment_contraction_cagr"])
    proxy["managed_obsolescence_pressure_score"] = (
        0.35 * proxy["productivity_hours_gap_score"]
        + 0.30 * proxy["capital_labour_services_gap_score"]
        + 0.20 * proxy["ict_nonict_services_gap_score"]
        + 0.15 * proxy["employment_contraction_score"]
    )
    proxy["managed_obsolescence_pressure_rank"] = proxy["managed_obsolescence_pressure_score"].rank(
        ascending=False,
        method="dense",
    ).astype(int)
    proxy = proxy.sort_values("managed_obsolescence_pressure_rank").reset_index(drop=True)
    return proxy


def main() -> None:
    config = load_json(CONFIG_PATH)
    source_path = ensure_source(config)
    long = load_russia_klems_long(source_path, config)
    panel, metadata = build_sector_panel(long, config)
    proxy = build_obsolescence_proxy(panel, config)

    panel_output = resolve_path(config["sector_panel_output_path"])
    proxy_output = resolve_path(config["obsolescence_proxy_output_path"])
    metadata_output = resolve_path(config["metadata_output_path"])

    panel_output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(panel_output, index=False)
    proxy.to_csv(proxy_output, index=False)

    metadata.update(
        {
            "source_page": config["source_page"],
            "source_url": config["source_url"],
            "raw_path": config["raw_path"],
            "year_start": config["year_start"],
            "year_end": config["year_end"],
            "n_panel_rows": int(len(panel)),
            "n_proxy_rows": int(len(proxy)),
            "outputs": {
                "sector_panel": config["sector_panel_output_path"],
                "obsolescence_proxy": config["obsolescence_proxy_output_path"],
            },
            "proxy_formulas": {
                "productivity_hours_gap_cagr": "CAGR(LP_I) - CAGR(H_EMP)",
                "capital_labour_services_gap_cagr": "CAGR(CAP_QI) - CAGR(LAB_QI)",
                "ict_nonict_services_gap_cagr": "CAGR(CAPIT_QI) - CAGR(CAPNIT_QI)",
                "employment_contraction_cagr": "-CAGR(EMP)",
                "managed_obsolescence_pressure_score": "0.35 productivity-hours + 0.30 capital-labour + 0.20 ICT-nonICT + 0.15 employment-contraction, min-max normalized across project sectors",
            },
            "limitations": [
                "The proxy does not identify deliberate planned obsolescence or collusion.",
                "It measures sectoral pressure under which firms or regulators may prefer staged deployment, compatibility limits, controlled repair/access, or slower capability release.",
                "Russia KLEMS Release 3 uses NACE 1.0 and covers 1995-2016; mapping to current OKVED2 sectors is approximate for J and M.",
                "Russia KLEMS notes that 2015-2016 values are preliminary and labour shares are fixed at the 2014 level in this release.",
                "Special caution is required for oil and gas related industries because of transfer pricing and cross-industry allocation issues noted by Russia KLEMS.",
            ],
        }
    )
    with metadata_output.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)

    print(f"Saved Russia KLEMS panel: {panel_output}")
    print(f"Saved managed obsolescence proxy: {proxy_output}")
    print(f"Saved metadata: {metadata_output}")
    print(proxy[["sector_id", "managed_obsolescence_pressure_score", "managed_obsolescence_pressure_rank"]].to_string(index=False))


if __name__ == "__main__":
    main()

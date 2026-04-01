from __future__ import annotations

import json
import re
from pathlib import Path
from urllib3.exceptions import InsecureRequestWarning

import numpy as np
import pandas as pd
import requests
import urllib3


urllib3.disable_warnings(InsecureRequestWarning)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "russia_official_sources.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).replace("\xa0", " ").replace("\n", " ").strip().lower()
    return re.sub(r"\s+", " ", text)


def parse_year(value: object) -> int | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group(0)) if match else None


def to_float(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).replace("\xa0", " ").strip()
    text = text.replace(",", ".")
    return float(text) if text else np.nan


def resolve_path(path_str: str) -> Path:
    return ROOT / path_str


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=180, verify=False)
    response.raise_for_status()
    destination.write_bytes(response.content)


def ensure_sources(config: dict) -> dict[str, Path]:
    raw_dir = resolve_path(config["raw_dir"])
    paths: dict[str, Path] = {}
    for source_name, source_cfg in config["sources"].items():
        path = raw_dir / source_cfg["filename"]
        if not path.exists():
            download_file(source_cfg["url"], path)
        paths[source_name] = path
    return paths


def load_sector_metadata(config: dict) -> pd.DataFrame:
    targets = load_json(resolve_path(config["benchmark_targets_path"]))
    return pd.DataFrame(targets["sector_map"])[
        [
            "sector_id",
            "sector_name_ru",
            "okved",
            "ai_intensity",
            "is_proxy_mn",
            "staffing_proxy_exact",
        ]
    ]


def build_label_index(series: pd.Series) -> dict[str, int]:
    label_index: dict[str, int] = {}
    for idx, value in series.items():
        normalized = normalize_text(value)
        if normalized and normalized not in label_index:
            label_index[normalized] = int(idx)
    return label_index


def extract_rows(
    dataframe: pd.DataFrame,
    header_row: int,
    label_col: int,
    value_start_col: int,
    sector_rows: dict[str, list[str]],
) -> tuple[pd.DataFrame, dict]:
    year_cols = {
        col_idx: year
        for col_idx in range(value_start_col, dataframe.shape[1])
        if (year := parse_year(dataframe.iloc[header_row, col_idx])) is not None
    }
    label_index = build_label_index(dataframe.iloc[:, label_col])
    records: list[dict] = []
    matches: dict[str, list[dict[str, object]]] = {}

    for sector_id, labels in sector_rows.items():
        matched_rows: list[dict[str, object]] = []
        for component_idx, label in enumerate(labels):
            normalized = normalize_text(label)
            if normalized not in label_index:
                raise ValueError(f"Could not locate row '{label}' for sector {sector_id}.")
            row_idx = label_index[normalized]
            matched_rows.append({"requested_label": label, "row_index": row_idx, "component_idx": component_idx})
            for col_idx, year in year_cols.items():
                records.append(
                    {
                        "sector_id": sector_id,
                        "year": year,
                        "component_idx": component_idx,
                        "row_label": label,
                        "value": to_float(dataframe.iloc[row_idx, col_idx]),
                    }
                )
        matches[sector_id] = matched_rows

    extracted = pd.DataFrame(records)
    return extracted, matches


def aggregate_series(
    dataframe: pd.DataFrame,
    sector_rows: dict[str, list[str]],
    *,
    header_row: int,
    label_col: int,
    value_start_col: int,
    value_name: str,
) -> tuple[pd.DataFrame, dict]:
    extracted, matches = extract_rows(
        dataframe,
        header_row=header_row,
        label_col=label_col,
        value_start_col=value_start_col,
        sector_rows=sector_rows,
    )
    aggregated = (
        extracted.groupby(["sector_id", "year"], as_index=False)
        .agg(**{value_name: ("value", "sum")})
        .sort_values(["sector_id", "year"])
        .reset_index(drop=True)
    )
    return aggregated, matches


def parse_va_block(workbook_path: Path, sheet_name: str, sector_rows: dict[str, list[str]], value_name: str) -> tuple[pd.DataFrame, dict]:
    dataframe = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None)
    return aggregate_series(
        dataframe,
        sector_rows,
        header_row=2,
        label_col=2,
        value_start_col=3,
        value_name=value_name,
    )


def parse_employment_block(workbook_path: Path, sheet_name: str, sector_rows: dict[str, list[str]]) -> tuple[pd.DataFrame, dict]:
    dataframe = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None)
    return aggregate_series(
        dataframe,
        sector_rows,
        header_row=4,
        label_col=0,
        value_start_col=1,
        value_name="employment_thousand_persons",
    )


def weighted_average_wage(
    wage_sector_rows: dict[str, list[str]],
    employment_sector_rows: dict[str, list[str]],
    wage_workbook_path: Path,
    wage_sheet: str,
    employment_workbook_path: Path,
    employment_sheet: str,
) -> tuple[pd.DataFrame, dict]:
    wage_df = pd.read_excel(wage_workbook_path, sheet_name=wage_sheet, header=None)
    emp_df = pd.read_excel(employment_workbook_path, sheet_name=employment_sheet, header=None)

    wage_rows, wage_matches = extract_rows(
        wage_df,
        header_row=4,
        label_col=0,
        value_start_col=1,
        sector_rows=wage_sector_rows,
    )
    emp_rows, emp_matches = extract_rows(
        emp_df,
        header_row=4,
        label_col=0,
        value_start_col=1,
        sector_rows=employment_sector_rows,
    )

    merged = wage_rows.merge(
        emp_rows[["sector_id", "year", "component_idx", "value"]].rename(
            columns={"value": "employment_thousand_persons"}
        ),
        on=["sector_id", "year", "component_idx"],
        how="left",
    )
    merged["annual_fot_component_bn_rub"] = (
        merged["employment_thousand_persons"] * merged["value"] * 12.0 / 1_000_000.0
    )
    weighted = (
        merged.groupby(["sector_id", "year"], as_index=False)
        .agg(
            annual_fot_component_bn_rub=("annual_fot_component_bn_rub", "sum"),
            employment_thousand_persons=("employment_thousand_persons", "sum"),
        )
        .sort_values(["sector_id", "year"])
        .reset_index(drop=True)
    )
    weighted["avg_monthly_wage_rub"] = (
        weighted["annual_fot_component_bn_rub"] * 1_000_000.0 / weighted["employment_thousand_persons"] / 12.0
    )
    weighted = weighted[["sector_id", "year", "avg_monthly_wage_rub"]]
    return weighted, {"wage_rows": wage_matches, "employment_rows": emp_matches}


def build_panel(config: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    source_paths = ensure_sources(config)
    sector_meta = load_sector_metadata(config)
    sector_rows = config["row_labels"]

    va_workbook = config["sources"]["va_workbook"]
    va_current, va_current_matches = parse_va_block(
        source_paths["va_workbook"],
        va_workbook["sheets"]["va_current_bn_rub"],
        {sector_id: rows["va"] for sector_id, rows in sector_rows.items()},
        "va_current_bn_rub",
    )
    va_constant_2016, va_constant_2016_matches = parse_va_block(
        source_paths["va_workbook"],
        va_workbook["sheets"]["va_constant_2016_bn_rub"],
        {sector_id: rows["va"] for sector_id, rows in sector_rows.items()},
        "va_constant_2016_bn_rub",
    )
    va_constant_2021, va_constant_2021_matches = parse_va_block(
        source_paths["va_workbook"],
        va_workbook["sheets"]["va_constant_2021_bn_rub"],
        {sector_id: rows["va"] for sector_id, rows in sector_rows.items()},
        "va_constant_2021_bn_rub",
    )
    va_volume_index_official, va_volume_index_matches = parse_va_block(
        source_paths["va_workbook"],
        va_workbook["sheets"]["va_volume_index_official_prev_year_pct"],
        {sector_id: rows["va"] for sector_id, rows in sector_rows.items()},
        "va_volume_index_official_prev_year_pct",
    )
    va_deflator_index_official, va_deflator_index_matches = parse_va_block(
        source_paths["va_workbook"],
        va_workbook["sheets"]["va_deflator_index_official_prev_year_pct"],
        {sector_id: rows["va"] for sector_id, rows in sector_rows.items()},
        "va_deflator_index_official_prev_year_pct",
    )
    employment, employment_matches = parse_employment_block(
        source_paths["employment_workbook"],
        config["sources"]["employment_workbook"]["sheet"],
        {sector_id: rows["employment"] for sector_id, rows in sector_rows.items()},
    )
    wages, weighted_wage_matches = weighted_average_wage(
        wage_sector_rows={sector_id: rows["wage"] for sector_id, rows in sector_rows.items()},
        employment_sector_rows={sector_id: rows["employment"] for sector_id, rows in sector_rows.items()},
        wage_workbook_path=source_paths["wage_workbook"],
        wage_sheet=config["sources"]["wage_workbook"]["sheet"],
        employment_workbook_path=source_paths["employment_workbook"],
        employment_sheet=config["sources"]["employment_workbook"]["sheet"],
    )

    panel = sector_meta.merge(va_current, on="sector_id", how="left")
    for dataframe in [
        va_constant_2016,
        va_constant_2021,
        va_volume_index_official,
        va_deflator_index_official,
        employment,
        wages,
    ]:
        panel = panel.merge(dataframe, on=["sector_id", "year"], how="left")

    panel = panel.sort_values(["sector_id", "year"]).reset_index(drop=True)
    panel["va_nominal_index_prev_year_pct"] = (
        panel.groupby("sector_id")["va_current_bn_rub"].pct_change().add(1.0) * 100.0
    )
    panel["va_volume_index_prev_year_pct"] = (
        panel.groupby("sector_id")["va_constant_2021_bn_rub"].pct_change().add(1.0) * 100.0
    )
    panel["va_deflator_index_prev_year_pct"] = (
        panel["va_nominal_index_prev_year_pct"] / panel["va_volume_index_prev_year_pct"] * 100.0
    )

    panel["employment_persons"] = panel["employment_thousand_persons"] * 1000.0
    panel["annual_wage_rub"] = panel["avg_monthly_wage_rub"] * 12.0
    panel["fot_proxy_bn_rub"] = panel["employment_thousand_persons"] * panel["avg_monthly_wage_rub"] * 12.0 / 1_000_000.0
    panel["labour_share_proxy"] = panel["fot_proxy_bn_rub"] / panel["va_current_bn_rub"]
    panel["va_real_growth_pct"] = panel["va_volume_index_prev_year_pct"] - 100.0
    panel["va_deflator_growth_pct"] = panel["va_deflator_index_prev_year_pct"] - 100.0
    panel["has_complete_labor_share_inputs"] = panel[
        ["va_current_bn_rub", "employment_thousand_persons", "avg_monthly_wage_rub"]
    ].notna().all(axis=1)
    panel["has_complete_real_va_inputs"] = panel[["va_constant_2021_bn_rub", "va_volume_index_prev_year_pct"]].notna().all(axis=1)
    panel["source_layer"] = np.where(panel["has_complete_labor_share_inputs"], "official_complete", "official_partial")

    ordered_columns = [
        "year",
        "sector_id",
        "sector_name_ru",
        "okved",
        "ai_intensity",
        "is_proxy_mn",
        "staffing_proxy_exact",
        "va_current_bn_rub",
        "va_constant_2016_bn_rub",
        "va_constant_2021_bn_rub",
        "va_nominal_index_prev_year_pct",
        "va_volume_index_prev_year_pct",
        "va_real_growth_pct",
        "va_deflator_index_prev_year_pct",
        "va_deflator_growth_pct",
        "va_volume_index_official_prev_year_pct",
        "va_deflator_index_official_prev_year_pct",
        "employment_thousand_persons",
        "employment_persons",
        "avg_monthly_wage_rub",
        "annual_wage_rub",
        "fot_proxy_bn_rub",
        "labour_share_proxy",
        "has_complete_labor_share_inputs",
        "has_complete_real_va_inputs",
        "source_layer",
    ]
    panel = panel[ordered_columns].sort_values(["year", "sector_id"]).reset_index(drop=True)

    latest_complete_year = config["latest_complete_year"]
    baseline = panel.loc[
        (panel["year"] == latest_complete_year) & panel["has_complete_labor_share_inputs"]
    ].reset_index(drop=True)

    metadata = {
        "latest_complete_year": latest_complete_year,
        "n_panel_rows": int(len(panel)),
        "n_baseline_rows": int(len(baseline)),
        "year_min": int(panel["year"].min()),
        "year_max": int(panel["year"].max()),
        "complete_labor_share_years": sorted(
            int(year) for year in panel.loc[panel["has_complete_labor_share_inputs"], "year"].drop_duplicates().tolist()
        ),
        "complete_real_va_years": sorted(
            int(year) for year in panel.loc[panel["has_complete_real_va_inputs"], "year"].drop_duplicates().tolist()
        ),
        "source_urls": {
            source_name: source_cfg["url"] for source_name, source_cfg in config["sources"].items()
        },
        "matches": {
            "va_current": va_current_matches,
            "va_constant_2016": va_constant_2016_matches,
            "va_constant_2021": va_constant_2021_matches,
            "va_volume_index_official": va_volume_index_matches,
            "va_deflator_index_official": va_deflator_index_matches,
            "employment": employment_matches,
            "weighted_wage": weighted_wage_matches,
        },
        "formulas": {
            "fot_proxy_bn_rub": "employment_thousand_persons * avg_monthly_wage_rub * 12 / 1_000_000",
            "labour_share_proxy": "fot_proxy_bn_rub / va_current_bn_rub",
            "va_nominal_index_prev_year_pct": "(va_current_bn_rub_t / va_current_bn_rub_t-1) * 100",
            "va_volume_index_prev_year_pct": "(va_constant_2021_bn_rub_t / va_constant_2021_bn_rub_t-1) * 100",
            "va_real_growth_pct": "va_volume_index_prev_year_pct - 100",
            "va_deflator_index_prev_year_pct": "(va_nominal_index_prev_year_pct / va_volume_index_prev_year_pct) * 100",
            "va_deflator_growth_pct": "va_deflator_index_prev_year_pct - 100",
        },
        "limitations": [
            "Direct EMISS/Fedstat indicator API returned 403 in this environment, so the pipeline uses official Rosstat XLS/XLSX direct files.",
            "Direct payroll series 57821 is not yet wired from Fedstat; FOT is proxied as employment multiplied by average monthly wage and 12 months.",
            "Employment workbook currently covers 2017-2024, so labour-share complete overlap is 2017-2024.",
            "For aggregated sector D+E, volume and deflator indices are computed from aggregated current and constant-price VA levels; official sheet indices are retained only for audit.",
        ],
    }
    return panel, baseline, metadata


def main() -> None:
    config = load_json(CONFIG_PATH)
    panel, baseline, metadata = build_panel(config)

    panel_output = resolve_path(config["panel_output_path"])
    baseline_output = resolve_path(config["baseline_output_path"])
    metadata_output = resolve_path(config["metadata_output_path"])

    panel.to_csv(panel_output, index=False)
    baseline.to_csv(baseline_output, index=False)
    with metadata_output.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)

    print(f"Saved panel: {panel_output}")
    print(f"Saved baseline: {baseline_output}")
    print(f"Saved metadata: {metadata_output}")
    print(
        f"Panel rows={len(panel)}, baseline rows={len(baseline)}, "
        f"complete years={metadata['complete_labor_share_years'][0]}-{metadata['complete_labor_share_years'][-1]}"
    )


if __name__ == "__main__":
    main()

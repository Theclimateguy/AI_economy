from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "russia_klems_sources.json"
OFFICIAL_PANEL_PATH = ROOT / "data" / "processed" / "russia_sector_panel_official_2011_2025.csv"
ICT_USAGE_RAW_PATH = ROOT / "data" / "raw" / "russia" / "ikt_org.xlsx"
ICT_USAGE_URL = "https://rosstat.gov.ru/storage/mediabank/ikt_org.xlsx"
FIXED_ASSET_RENEWAL_RAW_PATH = ROOT / "data" / "raw" / "russia" / "koef_ved_2017_2021.xlsx"
FIXED_ASSET_RENEWAL_URL = "https://rosstat.gov.ru/free_doc/new_site/business/osnfond/KOEF_ved2.xlsx"

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


def normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).replace("\xa0", " ").replace("\n", " ").strip().lower()
    return re.sub(r"\s+", " ", text)


def parse_year(value: object) -> int:
    match = re.search(r"(19|20)\d{2}", str(value))
    if not match:
        raise ValueError(f"Could not parse year from value: {value!r}")
    return int(match.group(0))


def lookup_row_index(label_index: dict[str, int], label: str) -> int:
    normalized = normalize_text(label)
    if normalized in label_index:
        return label_index[normalized]
    for candidate, idx in label_index.items():
        if normalized in candidate or candidate in normalized:
            return idx
    raise KeyError(normalized)


def ensure_source(config: dict) -> Path:
    path = resolve_path(config["raw_path"])
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(config["source_url"], timeout=180, verify=False)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def ensure_download(url: str, destination: Path) -> Path:
    if destination.exists():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=180, verify=False)
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination


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


def build_klems_proxy(panel: pd.DataFrame, config: dict, year_start: int, year_end: int, prefix: str) -> pd.DataFrame:
    years = year_end - year_start
    records: list[dict] = []
    for sector in config["sector_map"]:
        sector_id = sector["sector_id"]
        record = {
            "sector_id": sector_id,
            "sector_name_ru": sector["sector_name_ru"],
            f"{prefix}_period_start": year_start,
            f"{prefix}_period_end": year_end,
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
            record[f"{prefix}_{column}_start"] = first
            record[f"{prefix}_{column}_end"] = last
            record[f"{prefix}_{column}_cagr"] = cagr(first, last, years)

        record[f"{prefix}_labour_share_change_pp"] = (
            record[f"{prefix}_labour_share_klems_end"] - record[f"{prefix}_labour_share_klems_start"]
        )
        record[f"{prefix}_productivity_hours_gap_cagr"] = (
            record[f"{prefix}_LP_I_cagr"] - record[f"{prefix}_H_EMP_cagr"]
        )
        record[f"{prefix}_capital_labour_services_gap_cagr"] = (
            record[f"{prefix}_CAP_QI_cagr"] - record[f"{prefix}_LAB_QI_cagr"]
        )
        record[f"{prefix}_ict_nonict_services_gap_cagr"] = (
            record[f"{prefix}_CAPIT_QI_cagr"] - record[f"{prefix}_CAPNIT_QI_cagr"]
        )
        record[f"{prefix}_employment_contraction_cagr"] = -record[f"{prefix}_EMP_cagr"]
        records.append(record)

    proxy = pd.DataFrame(records)
    proxy[f"{prefix}_productivity_hours_gap_score"] = minmax_positive(proxy[f"{prefix}_productivity_hours_gap_cagr"])
    proxy[f"{prefix}_capital_labour_services_gap_score"] = minmax_positive(
        proxy[f"{prefix}_capital_labour_services_gap_cagr"]
    )
    proxy[f"{prefix}_ict_nonict_services_gap_score"] = minmax_positive(
        proxy[f"{prefix}_ict_nonict_services_gap_cagr"]
    )
    proxy[f"{prefix}_employment_contraction_score"] = minmax_positive(proxy[f"{prefix}_employment_contraction_cagr"])
    proxy[f"{prefix}_managed_obsolescence_pressure_score"] = (
        0.35 * proxy[f"{prefix}_productivity_hours_gap_score"]
        + 0.30 * proxy[f"{prefix}_capital_labour_services_gap_score"]
        + 0.20 * proxy[f"{prefix}_ict_nonict_services_gap_score"]
        + 0.15 * proxy[f"{prefix}_employment_contraction_score"]
    )
    proxy[f"{prefix}_managed_obsolescence_pressure_rank"] = proxy[f"{prefix}_managed_obsolescence_pressure_score"].rank(
        ascending=False,
        method="dense",
    ).astype(int)
    return proxy.sort_values(f"{prefix}_managed_obsolescence_pressure_rank").reset_index(drop=True)


def load_official_panel() -> pd.DataFrame:
    return pd.read_csv(OFFICIAL_PANEL_PATH)


def load_ict_usage() -> pd.DataFrame:
    path = ensure_download(ICT_USAGE_URL, ICT_USAGE_RAW_PATH)
    raw = pd.read_excel(path, sheet_name="6", header=None)
    rows = {
        "B": "Добыча полезных ископаемых",
        "C": "Обрабатывающие производства",
        "DE_1": "Обеспечение элелектрической электроэнергией, газом и паром; кондиционирование воздуха",
        "DE_2": "Водоснабжение; водоотведение, организация сбора и утилизации отходов, деятельность по ликвидации загрязнений",
        "F": "Строительство",
        "H": "Транспортировка и хранение",
        "J": "Деятельность в области информации и связи",
        "K": "Деятельность финансовая и страховая",
        "M": "Деятельность профессиональная, научная и техническая",
    }
    label_index = {
        normalize_text(raw.iloc[idx, 0]): idx
        for idx in range(len(raw))
        if normalize_text(raw.iloc[idx, 0])
    }
    year_row = 5
    server_cols = list(range(10, 18))
    website_cols = list(range(44, 52))
    records: list[dict] = []
    for key, label in rows.items():
        sector_id = "DE" if key.startswith("DE_") else key
        row_idx = lookup_row_index(label_index, label)
        for offset, col_idx in enumerate(server_cols):
            year = parse_year(raw.iloc[year_row, col_idx])
            website_year = parse_year(raw.iloc[year_row, website_cols[offset]])
            if year != website_year:
                raise ValueError(f"ICT usage year mismatch for sector {sector_id}: {year} vs {website_year}")
            records.append(
                {
                    "sector_id": sector_id,
                    "year": year,
                    "server_share_pct": float(raw.iloc[row_idx, col_idx]),
                    "website_share_pct": float(raw.iloc[row_idx, website_cols[offset]]),
                }
            )
    ict = (
        pd.DataFrame(records)
        .groupby(["sector_id", "year"], as_index=False)
        .agg(
            server_share_pct=("server_share_pct", "mean"),
            website_share_pct=("website_share_pct", "mean"),
        )
        .sort_values(["sector_id", "year"])
        .reset_index(drop=True)
    )
    ict["ict_digital_share_proxy_pct"] = 0.5 * ict["server_share_pct"] + 0.5 * ict["website_share_pct"]
    return ict


def decode_decimal_cell(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = re.sub(r"[^\d,.\-]", "", str(value))
    if not text:
        return np.nan
    if "," in text:
        return float(text.replace(",", "."))
    if "." in text:
        return float(text)
    if len(text) >= 2:
        return float(f"{text[:-1]}.{text[-1]}")
    return float(text)


def load_fixed_asset_renewal() -> pd.DataFrame:
    path = ensure_download(FIXED_ASSET_RENEWAL_URL, FIXED_ASSET_RENEWAL_RAW_PATH)
    raw = pd.read_excel(path, sheet_name="Лист1", header=None, engine="openpyxl")
    rows = {
        "B": "добыча полезеых ископаемых",
        "C": "обрабатывающие производства",
        "DE_1": "обеспечение электрической энергией, газом и паром; кондиционирование воздуха",
        "DE_2": "водоснабжение; водоотведение, организация сбора и утилизации отходов,деятельность по ликвидации загрязнений",
        "F": "строительство",
        "H": "транспортировка и хранение",
        "J": "деятельность в области информации и связи",
        "K": "деятельность финансовая и страховая",
        "M": "деятельность профессиональная, научная и техническая",
    }
    label_index = {
        normalize_text(raw.iloc[idx, 0]): idx
        for idx in range(len(raw))
        if normalize_text(raw.iloc[idx, 0])
    }
    years = [parse_year(raw.iloc[6, col]) for col in range(1, 6)]
    records: list[dict] = []
    for key, label in rows.items():
        sector_id = "DE" if key.startswith("DE_") else key
        row_idx = lookup_row_index(label_index, label)
        for offset, col_idx in enumerate(range(1, 6)):
            records.append(
                {
                    "sector_id": sector_id,
                    "year": years[offset],
                    "fixed_asset_renewal_pct": decode_decimal_cell(raw.iloc[row_idx, col_idx]),
                }
            )
    renewal = (
        pd.DataFrame(records)
        .groupby(["sector_id", "year"], as_index=False)["fixed_asset_renewal_pct"]
        .mean()
        .sort_values(["sector_id", "year"])
        .reset_index(drop=True)
    )
    return renewal


def build_recent_official_proxy(config: dict, year_start: int = 2017, year_end: int = 2024) -> pd.DataFrame:
    years = year_end - year_start
    official = load_official_panel()
    official = official.loc[official["year"].between(year_start, year_end)].copy()
    official["lp_per_worker_proxy"] = official["va_constant_2021_bn_rub"] * 1000.0 / official["employment_persons"]
    official = official.merge(load_ict_usage(), on=["sector_id", "year"], how="left")
    official = official.merge(load_fixed_asset_renewal(), on=["sector_id", "year"], how="left")

    records: list[dict] = []
    for sector in config["sector_map"]:
        sector_id = sector["sector_id"]
        group = official.loc[official["sector_id"].eq(sector_id)].sort_values("year").reset_index(drop=True)
        if group.empty:
            raise ValueError(f"Missing official rows for sector {sector_id}.")
        lp_first, lp_last = first_last(group, sector_id, "lp_per_worker_proxy", year_start, year_end)
        emp_first, emp_last = first_last(group, sector_id, "employment_thousand_persons", year_start, year_end)
        va_first, va_last = first_last(group, sector_id, "va_constant_2021_bn_rub", year_start, year_end)
        fot_first, fot_last = first_last(group, sector_id, "fot_proxy_bn_rub", year_start, year_end)
        ict_first, ict_last = first_last(group, sector_id, "ict_digital_share_proxy_pct", year_start, year_end)
        renew_first, renew_last = first_last(group, sector_id, "fixed_asset_renewal_pct", 2017, 2020)

        record = {
            "sector_id": sector_id,
            "sector_name_ru": sector["sector_name_ru"],
            "official_period_start": year_start,
            "official_period_end": year_end,
            "official_lp_per_worker_proxy_start": lp_first,
            "official_lp_per_worker_proxy_end": lp_last,
            "official_employment_start": emp_first,
            "official_employment_end": emp_last,
            "official_real_va_start": va_first,
            "official_real_va_end": va_last,
            "official_fot_proxy_start": fot_first,
            "official_fot_proxy_end": fot_last,
            "official_ict_digital_share_start": ict_first,
            "official_ict_digital_share_end": ict_last,
            "official_fixed_asset_renewal_2017": renew_first,
            "official_fixed_asset_renewal_2020": renew_last,
            "official_lp_per_worker_proxy_cagr": cagr(lp_first, lp_last, years),
            "official_employment_cagr": cagr(emp_first, emp_last, years),
            "official_real_va_cagr": cagr(va_first, va_last, years),
            "official_fot_proxy_cagr": cagr(fot_first, fot_last, years),
            "official_ict_digital_share_cagr": cagr(ict_first, ict_last, years),
            "official_fixed_asset_renewal_cagr_2017_2020": cagr(renew_first, renew_last, 3),
        }
        record["official_productivity_hours_gap_cagr"] = record["official_lp_per_worker_proxy_cagr"]
        record["official_capital_labour_services_gap_cagr"] = 0.5 * (
            record["official_real_va_cagr"] - record["official_fot_proxy_cagr"]
        ) + 0.5 * record["official_fixed_asset_renewal_cagr_2017_2020"]
        record["official_ict_nonict_services_gap_cagr"] = record["official_ict_digital_share_cagr"]
        record["official_employment_contraction_cagr"] = -record["official_employment_cagr"]
        records.append(record)

    proxy = pd.DataFrame(records)
    proxy["official_productivity_hours_gap_score"] = minmax_positive(proxy["official_productivity_hours_gap_cagr"])
    proxy["official_capital_labour_services_gap_score"] = minmax_positive(
        proxy["official_capital_labour_services_gap_cagr"]
    )
    proxy["official_ict_nonict_services_gap_score"] = minmax_positive(
        proxy["official_ict_nonict_services_gap_cagr"]
    )
    proxy["official_employment_contraction_score"] = minmax_positive(proxy["official_employment_contraction_cagr"])
    proxy["official_managed_obsolescence_pressure_score"] = (
        0.35 * proxy["official_productivity_hours_gap_score"]
        + 0.30 * proxy["official_capital_labour_services_gap_score"]
        + 0.20 * proxy["official_ict_nonict_services_gap_score"]
        + 0.15 * proxy["official_employment_contraction_score"]
    )
    proxy["official_managed_obsolescence_pressure_rank"] = proxy["official_managed_obsolescence_pressure_score"].rank(
        ascending=False,
        method="dense",
    ).astype(int)
    return proxy.sort_values("official_managed_obsolescence_pressure_rank").reset_index(drop=True)


def build_updated_proxy(panel: pd.DataFrame, config: dict) -> pd.DataFrame:
    old_klems = build_klems_proxy(panel, config, year_start=1995, year_end=2016, prefix="klems_1995_2016")
    long_klems = build_klems_proxy(panel, config, year_start=2000, year_end=2016, prefix="klems_2000_2016")
    recent = build_recent_official_proxy(config, year_start=2017, year_end=2024)

    proxy = old_klems.merge(long_klems, on=["sector_id", "sector_name_ru", "fit_quality"], how="left")
    proxy = proxy.merge(recent, on=["sector_id", "sector_name_ru"], how="left")

    historical_years = 2016 - 2000
    recent_years = 2024 - 2017
    total_years = historical_years + recent_years
    for component in [
        "productivity_hours_gap_score",
        "capital_labour_services_gap_score",
        "ict_nonict_services_gap_score",
        "employment_contraction_score",
    ]:
        proxy[f"updated_{component}"] = (
            historical_years * proxy[f"klems_2000_2016_{component}"]
            + recent_years * proxy[f"official_{component}"]
        ) / total_years

    proxy["mos_score_recent_2017_2024"] = proxy["official_managed_obsolescence_pressure_score"]
    proxy["mos_score_updated"] = (
        0.35 * proxy["updated_productivity_hours_gap_score"]
        + 0.30 * proxy["updated_capital_labour_services_gap_score"]
        + 0.20 * proxy["updated_ict_nonict_services_gap_score"]
        + 0.15 * proxy["updated_employment_contraction_score"]
    )
    proxy["mos_rank_updated"] = proxy["mos_score_updated"].rank(ascending=False, method="dense").astype(int)
    proxy["mos_score_klems_1995_2016"] = proxy["klems_1995_2016_managed_obsolescence_pressure_score"]
    proxy["mos_rank_klems_1995_2016"] = proxy["klems_1995_2016_managed_obsolescence_pressure_rank"]
    proxy["mos_score_klems_2000_2016"] = proxy["klems_2000_2016_managed_obsolescence_pressure_score"]
    proxy["mos_rank_klems_2000_2016"] = proxy["klems_2000_2016_managed_obsolescence_pressure_rank"]
    proxy["rank_delta_vs_klems_1995_2016"] = proxy["mos_rank_updated"] - proxy["mos_rank_klems_1995_2016"]

    proxy["managed_obsolescence_pressure_score"] = proxy["mos_score_updated"]
    proxy["managed_obsolescence_pressure_rank"] = proxy["mos_rank_updated"]
    proxy = proxy.sort_values("managed_obsolescence_pressure_rank").reset_index(drop=True)
    return proxy


def main() -> None:
    config = load_json(CONFIG_PATH)
    source_path = ensure_source(config)
    long = load_russia_klems_long(source_path, config)
    panel, metadata = build_sector_panel(long, config)
    proxy = build_updated_proxy(panel, config)

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
                "klems_productivity_hours_gap_cagr": "CAGR(LP_I) - CAGR(H_EMP)",
                "klems_capital_labour_services_gap_cagr": "CAGR(CAP_QI) - CAGR(LAB_QI)",
                "klems_ict_nonict_services_gap_cagr": "CAGR(CAPIT_QI) - CAGR(CAPNIT_QI)",
                "klems_employment_contraction_cagr": "-CAGR(EMP)",
                "official_productivity_hours_gap_cagr": "CAGR(real VA per worker proxy, 2017-2024). Hours-worked series is unavailable in the current repo, so worker productivity is used as the observed labour-saving proxy.",
                "official_capital_labour_services_gap_cagr": "0.5 * (CAGR(real VA, 2017-2024) - CAGR(FOT proxy, 2017-2024)) + 0.5 * CAGR(fixed-asset renewal coefficient, 2017-2020).",
                "official_ict_nonict_services_gap_cagr": "CAGR(0.5 * server_share_pct + 0.5 * website_share_pct, 2017-2024) from Rosstat ICT usage by activity.",
                "official_employment_contraction_cagr": "-CAGR(employment, 2017-2024)",
                "mos_score_updated": "0.35 * updated_productivity + 0.30 * updated_capital_labour + 0.20 * updated_ICT + 0.15 * updated_employment, where updated component score is a year-span-weighted blend of KLEMS 2000-2016 and official 2017-2024 normalized component scores.",
            },
            "limitations": [
                "The proxy does not identify deliberate planned obsolescence or collusion.",
                "It measures sectoral pressure under which firms or regulators may prefer staged deployment, compatibility limits, controlled repair/access, or slower capability release.",
                "Russia KLEMS Release 3 uses NACE 1.0 and covers 1995-2016; mapping to current OKVED2 sectors is approximate for J and M.",
                "Russia KLEMS notes that 2015-2016 values are preliminary and labour shares are fixed at the 2014 level in this release.",
                "Special caution is required for oil and gas related industries because of transfer pricing and cross-industry allocation issues noted by Russia KLEMS.",
                "Rosstat fixed-asset renewal table currently contributes 2017-2020 values; the 2021-2024 tail is not published in the same machine-readable table used here.",
                "Recent official block uses observed VA, employment, wage-bill proxy and ICT-use shares. This is materially better than relying only on 1995-2016 KLEMS, but it remains a proxy layer rather than a direct measure of ICT versus non-ICT capital services.",
            ],
            "supplemental_sources": {
                "official_panel_path": str(OFFICIAL_PANEL_PATH.relative_to(ROOT)),
                "ict_usage_url": ICT_USAGE_URL,
                "ict_usage_raw_path": str(ICT_USAGE_RAW_PATH.relative_to(ROOT)),
                "fixed_asset_renewal_url": FIXED_ASSET_RENEWAL_URL,
                "fixed_asset_renewal_raw_path": str(FIXED_ASSET_RENEWAL_RAW_PATH.relative_to(ROOT)),
            },
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

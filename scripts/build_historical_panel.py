from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from build_staffing_matrix import build_staffing_rti_panel


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "benchmark_targets.json"

RAW_DIR = ROOT / "data" / "raw"
INTERIM_DIR = ROOT / "data" / "interim"
PROCESSED_DIR = ROOT / "data" / "processed"

EU_KLEMS_DIR = RAW_DIR / "eu_klems"
OECD_DIR = RAW_DIR / "oecd"
RTI_DIR = RAW_DIR / "rti"

KLEMS_NA_FILE = EU_KLEMS_DIR / "statistical_national_accounts.csv"
KLEMS_CAPITAL_FILE = EU_KLEMS_DIR / "statistical_capital.csv"
KLEMS_LABOUR_SHARE_FILE = EU_KLEMS_DIR / "shares_labour_income.csv"
KLEMS_ICT_SHARE_FILE = EU_KLEMS_DIR / "shares_ict_nonict.csv"
KLEMS_VARIABLE_DESCRIPTION_FILE = EU_KLEMS_DIR / "variable_description.csv"
STAN_FILE = OECD_DIR / "stan_2025_selected.csv"
RTI_ZIP_FILE = RTI_DIR / "lewandowski_rti_102_countries.zip"

KLEMS_NA_VARS = ["VA", "VA_Q", "COMP", "EMP", "H_EMP"]
KLEMS_CAPITAL_VARS = ["K_GFCF", "Kq_GFCF", "Kq_IT", "Kq_CT", "Kq_Soft_DB"]

STAN_VALUE_FILTERS = {
    ("B1G", "V", "XDC"): "va_nominal_stan",
    ("B1G", "L", "XDC"): "va_real_stan",
    ("B1GFC", "V", "XDC"): "va_factor_cost_stan",
    ("B2A3G", "V", "XDC"): "gross_operating_surplus_stan",
    ("D1", "V", "XDC"): "comp_nominal_stan",
    ("D11", "V", "XDC"): "wages_nominal_stan",
    ("D29X39", "V", "XDC"): "net_taxes_prod_stan",
    ("EMP", "_Z", "PS"): "employment_stan",
    ("SAL", "_Z", "PS"): "employees_stan",
    ("SELF", "_Z", "PS"): "self_employed_stan",
    ("P1", "V", "XDC"): "output_nominal_stan",
    ("P2", "V", "XDC"): "intermediate_nominal_stan",
    ("P51G", "V", "XDC"): "gfcf_total_stan",
    ("P51G_ICT", "V", "XDC"): "gfcf_ict_stan",
    ("N11GA", "L", "XDC"): "gross_capital_stock_stan",
    ("N11GA_ICT", "L", "XDC"): "gross_capital_stock_ict_stan",
    ("N11NA", "L", "XDC"): "net_capital_stock_stan",
    ("N11NA_ICT", "L", "XDC"): "net_capital_stock_ict_stan",
}


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_directories(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def download_file(url: str, destination: Path, overwrite: bool = False) -> Path:
    if destination.exists() and not overwrite:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=180) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if chunk:
                    handle.write(chunk)
    return destination


def build_stan_query_url(config: dict) -> str:
    stan_cfg = config["oecd_stan"]
    start_year = config["requested_window"]["start_year"]
    end_year = config["requested_window"]["end_year"]

    iso3_countries = [config["country_code_map"][code] for code in config["comparator_countries"]]
    activity_codes = [item["stan_code"] for item in config["sector_map"]]
    measure_codes = stan_cfg["measures"]

    key = ".".join(
        [
            "A",
            "+".join(iso3_countries),
            "+".join(activity_codes),
            "+".join(measure_codes),
            "",
            "",
        ]
    )

    return (
        "https://sdmx.oecd.org/public/rest/data/"
        f"{stan_cfg['agency']},{stan_cfg['dataset']},{stan_cfg['version']}/{key}"
        f"?startPeriod={start_year}&endPeriod={end_year}&format=csvfile"
    )


def download_sources(config: dict, overwrite: bool = False) -> dict[str, Path]:
    klems_cfg = config["eu_klems"]
    rti_cfg = config["rti_source"]
    downloaded = {
        "klems_na": download_file(klems_cfg["national_accounts_url"], KLEMS_NA_FILE, overwrite=overwrite),
        "klems_capital": download_file(klems_cfg["capital_url"], KLEMS_CAPITAL_FILE, overwrite=overwrite),
        "klems_labour_share": download_file(klems_cfg["labour_share_url"], KLEMS_LABOUR_SHARE_FILE, overwrite=overwrite),
        "klems_ict_share": download_file(klems_cfg["ict_share_url"], KLEMS_ICT_SHARE_FILE, overwrite=overwrite),
        "klems_variable_description": download_file(
            klems_cfg["variable_description_url"], KLEMS_VARIABLE_DESCRIPTION_FILE, overwrite=overwrite
        ),
        "stan": download_file(build_stan_query_url(config), STAN_FILE, overwrite=overwrite),
        "rti_zip": download_file(rti_cfg["url"], RTI_ZIP_FILE, overwrite=overwrite),
    }
    return downloaded


def melt_wide_panel(data: pd.DataFrame, id_vars: list[str], value_name: str) -> pd.DataFrame:
    year_cols = [column for column in data.columns if str(column).isdigit()]
    panel = data.melt(id_vars=id_vars, value_vars=year_cols, var_name="year", value_name=value_name)
    panel["year"] = panel["year"].astype(int)
    panel[value_name] = pd.to_numeric(panel[value_name], errors="coerce")
    return panel


def read_klems_subset(
    csv_path: Path,
    keep_vars: list[str],
    keep_codes: list[str],
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    header = pd.read_csv(csv_path, nrows=0)
    year_cols = [column for column in header.columns if str(column).isdigit() and start_year <= int(column) <= end_year]
    usecols = [column for column in header.columns if column in {"country", "var", "code"} or column in year_cols]
    data = pd.read_csv(csv_path, usecols=usecols)
    return data.loc[data["var"].isin(keep_vars) & data["code"].isin(keep_codes)].copy()


def build_klems_panel(config: dict) -> pd.DataFrame:
    start_year = config["requested_window"]["start_year"]
    end_year = config["requested_window"]["end_year"]
    country_map = config["country_code_map"]

    sector_lookup = pd.DataFrame(config["sector_map"])[
        ["sector_id", "sector_name_ru", "okved", "ai_intensity", "klems_code", "share_code", "is_proxy_mn"]
    ]
    sector_lookup = sector_lookup.rename(columns={"klems_code": "code"})

    na = read_klems_subset(
        KLEMS_NA_FILE,
        keep_vars=KLEMS_NA_VARS,
        keep_codes=sector_lookup["code"].tolist(),
        start_year=max(start_year, config["eu_klems_first_year"]),
        end_year=end_year,
    )
    capital = read_klems_subset(
        KLEMS_CAPITAL_FILE,
        keep_vars=KLEMS_CAPITAL_VARS,
        keep_codes=sector_lookup["code"].tolist(),
        start_year=max(start_year, config["eu_klems_first_year"]),
        end_year=end_year,
    )

    na_panel = melt_wide_panel(na, ["country", "var", "code"], "value")
    capital_panel = melt_wide_panel(capital, ["country", "var", "code"], "value")

    na_panel = (
        na_panel.merge(sector_lookup, on="code", how="left")
        .assign(country_iso3=lambda df: df["country"].map(country_map))
        .pivot_table(index=["country", "country_iso3", "sector_id", "sector_name_ru", "okved", "ai_intensity", "year"], columns="var", values="value", aggfunc="first")
        .reset_index()
        .rename(
            columns={
                "VA": "va_nominal_klems",
                "VA_Q": "va_real_klems",
                "COMP": "comp_nominal_klems",
                "EMP": "employment_klems",
                "H_EMP": "hours_klems",
            }
        )
    )

    capital_panel = (
        capital_panel.merge(sector_lookup, on="code", how="left")
        .assign(country_iso3=lambda df: df["country"].map(country_map))
        .pivot_table(index=["country", "country_iso3", "sector_id", "sector_name_ru", "okved", "ai_intensity", "year"], columns="var", values="value", aggfunc="first")
        .reset_index()
        .rename(
            columns={
                "K_GFCF": "capital_nominal_klems",
                "Kq_GFCF": "capital_real_klems",
                "Kq_IT": "capital_ict_it_real_klems",
                "Kq_CT": "capital_ict_ct_real_klems",
                "Kq_Soft_DB": "capital_ict_softdb_real_klems",
            }
        )
    )

    labour_share = pd.read_csv(KLEMS_LABOUR_SHARE_FILE)
    labour_share = (
        labour_share.loc[
            labour_share["Country"].isin(config["comparator_countries"])
            & labour_share["NACE_R2"].isin(sector_lookup["share_code"])
            & labour_share["year"].between(config["eu_klems_first_year"], end_year)
        ]
        .merge(sector_lookup, left_on="NACE_R2", right_on="share_code", how="left")
        .assign(
            country=lambda df: df["Country"],
            country_iso3=lambda df: df["Country"].map(country_map),
            year=lambda df: df["year"].astype(int),
            labour_share_klems_official=lambda df: pd.to_numeric(df["sh"], errors="coerce") / 100.0,
        )
        [["country", "country_iso3", "sector_id", "year", "labour_share_klems_official"]]
    )

    ict_share = pd.read_csv(KLEMS_ICT_SHARE_FILE)
    ict_share = (
        ict_share.loc[
            ict_share["Country"].isin(config["comparator_countries"])
            & ict_share["NACE_R2"].isin(sector_lookup["share_code"])
            & (ict_share["VAR"] == "ICT")
            & ict_share["year"].between(config["eu_klems_first_year"], end_year)
        ]
        .merge(sector_lookup, left_on="NACE_R2", right_on="share_code", how="left")
        .assign(
            country=lambda df: df["Country"],
            country_iso3=lambda df: df["Country"].map(country_map),
            year=lambda df: df["year"].astype(int),
            ict_share_klems=lambda df: pd.to_numeric(df["sh"], errors="coerce") / 100.0,
        )
        [["country", "country_iso3", "sector_id", "year", "ict_share_klems"]]
    )

    klems = na_panel.merge(
        capital_panel,
        on=["country", "country_iso3", "sector_id", "sector_name_ru", "okved", "ai_intensity", "year"],
        how="outer",
    )
    klems = klems.merge(labour_share, on=["country", "country_iso3", "sector_id", "year"], how="left")
    klems = klems.merge(ict_share, on=["country", "country_iso3", "sector_id", "year"], how="left")

    klems["labour_share_klems_from_levels"] = klems["comp_nominal_klems"] / klems["va_nominal_klems"]
    klems["capital_ict_real_klems"] = klems[
        ["capital_ict_it_real_klems", "capital_ict_ct_real_klems", "capital_ict_softdb_real_klems"]
    ].sum(axis=1, min_count=1)
    klems["techint_klems"] = klems["capital_ict_real_klems"] / klems["capital_real_klems"]
    klems["k_l_real_klems"] = klems["capital_real_klems"] / klems["employment_klems"]
    klems["hours_per_worker_klems"] = klems["hours_klems"] / klems["employment_klems"]

    klems = klems.sort_values(["country_iso3", "sector_id", "year"]).reset_index(drop=True)
    klems["va_real_growth_klems"] = klems.groupby(["country_iso3", "sector_id"])["va_real_klems"].pct_change()
    klems["employment_growth_klems"] = klems.groupby(["country_iso3", "sector_id"])["employment_klems"].pct_change()
    klems["has_klems"] = True
    return klems


def build_stan_panel(config: dict) -> pd.DataFrame:
    sector_lookup = pd.DataFrame(config["sector_map"])[["sector_id", "sector_name_ru", "okved", "ai_intensity", "stan_code"]]
    sector_lookup = sector_lookup.rename(columns={"stan_code": "ACTIVITY"})

    stan = pd.read_csv(STAN_FILE)
    stan["TIME_PERIOD"] = pd.to_numeric(stan["TIME_PERIOD"], errors="coerce").astype("Int64")
    stan["OBS_VALUE"] = pd.to_numeric(stan["OBS_VALUE"], errors="coerce")

    valid_keys = set(STAN_VALUE_FILTERS)
    stan["series_key"] = list(zip(stan["MEASURE"], stan["PRICE_BASE"], stan["UNIT_MEASURE"]))
    stan = stan.loc[stan["series_key"].isin(valid_keys)].copy()
    stan["series_name"] = stan["series_key"].map(STAN_VALUE_FILTERS)

    panel = (
        stan.merge(sector_lookup, on="ACTIVITY", how="left")
        .pivot_table(
            index=["REF_AREA", "sector_id", "sector_name_ru", "okved", "ai_intensity", "TIME_PERIOD"],
            columns="series_name",
            values="OBS_VALUE",
            aggfunc="first",
        )
        .reset_index()
        .rename(columns={"REF_AREA": "country_iso3", "TIME_PERIOD": "year"})
    )

    for column_name in set(STAN_VALUE_FILTERS.values()):
        if column_name not in panel.columns:
            panel[column_name] = pd.NA

    iso3_to_klems = {iso3: iso2 for iso2, iso3 in config["country_code_map"].items()}
    panel["country"] = panel["country_iso3"].map(iso3_to_klems)

    panel["labour_share_stan"] = panel["comp_nominal_stan"] / panel["va_nominal_stan"]
    panel["margin_share_stan"] = 1.0 - panel["labour_share_stan"] - panel["net_taxes_prod_stan"] / panel["va_nominal_stan"]
    panel["ict_investment_share_stan"] = panel["gfcf_ict_stan"] / panel["gfcf_total_stan"]
    panel["ict_capital_share_stan"] = panel["gross_capital_stock_ict_stan"] / panel["gross_capital_stock_stan"]
    panel["k_l_nominal_stan"] = panel["net_capital_stock_stan"] / panel["employment_stan"]
    panel["hours_klems_gap_flag"] = True

    panel = panel.sort_values(["country_iso3", "sector_id", "year"]).reset_index(drop=True)
    panel["va_real_growth_stan"] = panel.groupby(["country_iso3", "sector_id"])["va_real_stan"].pct_change()
    panel["employment_growth_stan"] = panel.groupby(["country_iso3", "sector_id"])["employment_stan"].pct_change()
    panel["has_stan"] = True
    return panel


def build_final_panel(config: dict, klems: pd.DataFrame, stan: pd.DataFrame, rti_panel: pd.DataFrame) -> pd.DataFrame:
    sector_flags = pd.DataFrame(config["sector_map"])[["sector_id", "is_proxy_mn", "staffing_proxy_exact"]]
    rti_merge = rti_panel.drop(
        columns=[column for column in ["sector_name_ru", "is_proxy_mn", "staffing_proxy_exact"] if column in rti_panel.columns]
    )

    final_panel = stan.merge(
        klems,
        on=["country", "country_iso3", "sector_id", "sector_name_ru", "okved", "ai_intensity", "year"],
        how="outer",
    )
    final_panel = final_panel.merge(sector_flags, on="sector_id", how="left")
    final_panel = final_panel.merge(rti_merge, on=["country_iso3", "sector_id"], how="left")

    final_panel["has_stan"] = final_panel["has_stan"].fillna(False)
    final_panel["has_klems"] = final_panel["has_klems"].fillna(False)
    final_panel["coverage_status"] = "missing"
    final_panel.loc[final_panel["has_stan"] & ~final_panel["has_klems"], "coverage_status"] = "stan_only"
    final_panel.loc[~final_panel["has_stan"] & final_panel["has_klems"], "coverage_status"] = "klems_only"
    final_panel.loc[final_panel["has_stan"] & final_panel["has_klems"], "coverage_status"] = "stan_and_klems"

    final_panel["requested_benchmark_window"] = f"{config['requested_window']['start_year']}-{config['requested_window']['end_year']}"
    final_panel["klems_available_for_requested_window"] = final_panel["year"] >= config["eu_klems_first_year"]
    final_panel["pre_1995_klems_gap"] = final_panel["year"] < config["eu_klems_first_year"]

    final_panel["va_real_growth"] = final_panel["va_real_growth_klems"].combine_first(final_panel["va_real_growth_stan"])
    final_panel["employment_growth"] = final_panel["employment_growth_klems"].combine_first(final_panel["employment_growth_stan"])
    final_panel["labour_share"] = final_panel["labour_share_klems_official"].combine_first(final_panel["labour_share_stan"])
    final_panel["labour_share_structural"] = final_panel["labour_share_klems_official"].combine_first(
        final_panel["labour_share_klems_from_levels"]
    )
    final_panel["employment"] = final_panel["employment_klems"].combine_first(final_panel["employment_stan"])
    final_panel["ict_share_proxy"] = final_panel["ict_share_klems"].combine_first(final_panel["ict_capital_share_stan"])
    final_panel["techint"] = final_panel["techint_klems"].combine_first(final_panel["ict_capital_share_stan"])
    final_panel["margin"] = final_panel["margin_share_stan"]
    final_panel["occ"] = (final_panel["capital_nominal_klems"] - final_panel["comp_nominal_klems"]) / final_panel["comp_nominal_klems"]
    final_panel["emp_per_va"] = final_panel["employment"] / final_panel["va_real_klems"].combine_first(final_panel["va_real_stan"])

    final_panel["benchmark_core_ready"] = (
        final_panel[["va_real_growth", "labour_share_structural", "margin", "employment", "techint", "k_l_real_klems", "rti_staffing_base"]]
        .notna()
        .all(axis=1)
    )

    ordered_columns = [
        "country",
        "country_iso3",
        "sector_id",
        "sector_name_ru",
        "okved",
        "ai_intensity",
        "year",
        "coverage_status",
        "benchmark_core_ready",
        "pre_1995_klems_gap",
        "is_proxy_mn",
        "staffing_proxy_exact",
        "va_real_growth",
        "employment_growth",
        "labour_share",
        "labour_share_structural",
        "margin_share_stan",
        "margin",
        "ict_share_proxy",
        "techint",
        "rti_staffing_base",
        "rti_base_year",
        "rti_base_year_exact",
        "rti_year_distance",
        "rti_year_priority",
        "rti_n_occ_available",
        "rti_weight_coverage",
        "rti_base_source",
        "rti_total_source",
        "k_l_real_klems",
        "emp_per_va",
        "occ",
        "hours_klems",
        "va_real_klems",
        "va_real_stan",
        "va_nominal_klems",
        "va_nominal_stan",
        "comp_nominal_klems",
        "comp_nominal_stan",
        "capital_real_klems",
        "net_capital_stock_stan",
        "employment_klems",
        "employment_stan",
        "ict_share_klems",
        "ict_capital_share_stan",
        "ict_investment_share_stan",
        "requested_benchmark_window",
    ]

    remaining = [column for column in final_panel.columns if column not in ordered_columns]
    final_panel = final_panel[ordered_columns + remaining].sort_values(["country_iso3", "sector_id", "year"]).reset_index(drop=True)
    return final_panel


def build_coverage_table(config: dict, panel: pd.DataFrame) -> pd.DataFrame:
    requested_countries = len(config["comparator_countries"])

    coverage = (
        panel.groupby(["year", "sector_id", "sector_name_ru"], dropna=False)
        .agg(
            n_rows=("country_iso3", "size"),
            n_countries_stan=("has_stan", "sum"),
            n_countries_klems=("has_klems", "sum"),
            n_benchmark_ready=("benchmark_core_ready", "sum"),
        )
        .reset_index()
    )
    coverage["n_requested_countries"] = requested_countries
    coverage["stan_coverage_ratio"] = coverage["n_countries_stan"] / requested_countries
    coverage["klems_coverage_ratio"] = coverage["n_countries_klems"] / requested_countries
    coverage["benchmark_ready_ratio"] = coverage["n_benchmark_ready"] / requested_countries
    return coverage.sort_values(["sector_id", "year"]).reset_index(drop=True)


def write_metadata(config: dict, panel: pd.DataFrame, coverage: pd.DataFrame) -> None:
    metadata = {
        "requested_window": config["requested_window"],
        "eu_klems_first_year": config["eu_klems_first_year"],
        "recommended_joint_window": {
            "start_year": max(config["requested_window"]["start_year"], config["eu_klems_first_year"]),
            "end_year": config["requested_window"]["end_year"],
        },
        "n_rows": int(len(panel)),
        "n_countries": int(panel["country_iso3"].dropna().nunique()),
        "n_sectors": int(panel["sector_id"].dropna().nunique()),
        "n_benchmark_ready_rows": int(panel["benchmark_core_ready"].sum()),
        "sources": {
            "eu_klems_archive": [
                "Statistical_National-Accounts.csv",
                "Statistical_Capital.csv",
                "Shares_LabourIncome.csv",
                "Shares_ICT-NonICT.csv",
            ],
            "oecd_stan": "DSD_STAN@DF_STAN_2025",
            "rti": "Lewandowski RTI x ILOSTAT base-year staffing matrix",
        },
        "notes": [
            "EU KLEMS archive used here starts in 1995, so 1985-1994 remain STAN-only rows in the merged panel.",
            "Benchmark-ready rows require joint availability of growth, labour share, margin share, technology intensity, employment, K/L, and RTI.",
            "Margin share is computed from OECD STAN as 1 - D1/B1G - D29X39/B1G.",
            "Sector M is proxied by M_N in KLEMS and STAN, flagged as is_proxy_mn.",
            "Historical staffing-matrix crosswalk uses ISIC Rev.3 1-digit codes; staffing_proxy_exact marks sectors with exact versus broad historical proxies.",
            "RTI is built from base-year staffing weights (1995 with fallback to nearby years) and country-specific Lewandowski occupation RTI.",
        ],
        "max_klems_coverage_years": {
            "start_year": int(panel.loc[panel["has_klems"], "year"].min()),
            "end_year": int(panel.loc[panel["has_klems"], "year"].max()),
        },
        "coverage_snapshot": coverage.loc[coverage["year"].isin([1985, 1995, 2005])].to_dict(orient="records"),
    }

    metadata_path = PROCESSED_DIR / "panel_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)


def main(overwrite: bool = False) -> None:
    ensure_directories([RAW_DIR, INTERIM_DIR, PROCESSED_DIR, EU_KLEMS_DIR, OECD_DIR, RTI_DIR])
    config = load_config(CONFIG_PATH)

    download_sources(config, overwrite=overwrite)
    klems = build_klems_panel(config)
    stan = build_stan_panel(config)
    rti_panel = build_staffing_rti_panel(config, overwrite=overwrite)
    final_panel = build_final_panel(config, klems, stan, rti_panel)
    coverage = build_coverage_table(config, final_panel)

    panel_path = PROCESSED_DIR / "historical_sector_panel_1985_2005.csv"
    coverage_path = PROCESSED_DIR / "historical_sector_coverage_1985_2005.csv"

    final_panel.to_csv(panel_path, index=False)
    coverage.to_csv(coverage_path, index=False)
    write_metadata(config, final_panel, coverage)

    print(f"Saved panel: {panel_path}")
    print(f"Saved coverage: {coverage_path}")
    print(f"Rows: {len(final_panel):,}")
    print(f"Countries: {final_panel['country_iso3'].dropna().nunique()}")
    print(f"Sectors: {final_panel['sector_id'].dropna().nunique()}")
    print(f"Benchmark-ready rows: {int(final_panel['benchmark_core_ready'].sum())}")
    print(
        "Joint KLEMS+STAN window: "
        f"{max(config['requested_window']['start_year'], config['eu_klems_first_year'])}"
        f"-{config['requested_window']['end_year']}"
    )


if __name__ == "__main__":
    main()

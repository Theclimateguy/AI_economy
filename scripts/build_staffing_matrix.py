from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable
import zipfile

import numpy as np
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "benchmark_targets.json"

RAW_DIR = ROOT / "data" / "raw"
RTI_DIR = RAW_DIR / "rti"
ILOSTAT_DIR = RAW_DIR / "ilostat"
PROCESSED_DIR = ROOT / "data" / "processed"

RTI_ZIP_FILE = RTI_DIR / "lewandowski_rti_102_countries.zip"
ILOSTAT_FILE = ILOSTAT_DIR / "emp_temp_eco_ocu_nb_a.csv.gz"

OUTPUT_RTI = PROCESSED_DIR / "rti_matrix_proxy.csv"
OUTPUT_WEIGHTS = PROCESSED_DIR / "staffing_matrix_base_weights.csv"
OUTPUT_METADATA = PROCESSED_DIR / "staffing_matrix_metadata.json"

MIN_WEIGHT_COVERAGE = 0.95


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_directories(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def download_file(url: str, destination: Path, overwrite: bool = False, headers: dict | None = None) -> Path:
    if destination.exists() and not overwrite:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    request_headers = {"User-Agent": "Mozilla/5.0"}
    if headers:
        request_headers.update(headers)

    with requests.get(url, stream=True, timeout=180, headers=request_headers) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if chunk:
                    handle.write(chunk)
    return destination


def load_rti_long(config: dict, overwrite: bool = False) -> pd.DataFrame:
    rti_cfg = config["rti_source"]
    download_file(rti_cfg["url"], RTI_ZIP_FILE, overwrite=overwrite)

    prefix = rti_cfg["variant_prefix"]
    columns = ["Country_code"] + [f"{prefix}{digit}" for digit in range(1, 10)]
    with zipfile.ZipFile(RTI_ZIP_FILE) as archive:
        with archive.open(rti_cfg["zip_member_csv"]) as handle:
            rti = pd.read_csv(handle, usecols=columns)

    rti = rti.rename(columns={"Country_code": "country_iso3"})
    rti_long = rti.melt(id_vars="country_iso3", var_name="rti_column", value_name="occupation_rti")
    rti_long["occupation_digit"] = rti_long["rti_column"].str.extract(r"(\d+)$").astype(int)
    return rti_long[["country_iso3", "occupation_digit", "occupation_rti"]]


def build_sector_lookup(config: dict) -> pd.DataFrame:
    rows = []
    for sector in config["sector_map"]:
        for staffing_code in sector["staffing_codes"]:
            rows.append(
                {
                    "sector_id": sector["sector_id"],
                    "sector_name_ru": sector["sector_name_ru"],
                    "classif1": staffing_code,
                    "is_proxy_mn": bool(sector["is_proxy_mn"]),
                    "staffing_proxy_exact": bool(sector.get("staffing_proxy_exact", True)),
                }
            )
    return pd.DataFrame(rows)


def load_staffing_records(config: dict, overwrite: bool = False) -> pd.DataFrame:
    staffing_cfg = config["staffing_matrix_source"]
    download_file(staffing_cfg["url"], ILOSTAT_FILE, overwrite=overwrite)

    comparator_iso3 = set(config["country_code_map"].values())
    staffing_codes = {code for sector in config["sector_map"] for code in sector["staffing_codes"]}
    occupation_codes = [staffing_cfg["total_occupation_code"]]
    occupation_codes.extend([f"{staffing_cfg['occupation_prefix']}{digit}" for digit in range(1, 10)])
    candidate_years = [staffing_cfg["base_year_target"], *staffing_cfg["fallback_years"]]

    usecols = ["ref_area", "source", "classif1", "classif2", "time", "obs_value"]
    chunks = []
    reader = pd.read_csv(
        ILOSTAT_FILE,
        compression="gzip",
        usecols=usecols,
        chunksize=250_000,
        low_memory=False,
    )
    for chunk in reader:
        chunk["time"] = pd.to_numeric(chunk["time"], errors="coerce").astype("Int64")
        chunk["obs_value"] = pd.to_numeric(chunk["obs_value"], errors="coerce")
        subset = chunk.loc[
            chunk["ref_area"].isin(comparator_iso3)
            & chunk["classif1"].isin(staffing_codes)
            & chunk["classif2"].isin(occupation_codes)
            & chunk["time"].isin(candidate_years)
        ].copy()
        if not subset.empty:
            chunks.append(subset)

    if not chunks:
        raise ValueError("No staffing-matrix observations found for the configured countries, sectors, and years.")

    staffing = pd.concat(chunks, ignore_index=True)
    staffing = staffing.rename(
        columns={
            "ref_area": "country_iso3",
            "classif2": "occupation_code",
            "time": "year",
            "obs_value": "employment_obs",
        }
    )
    staffing["year"] = staffing["year"].astype(int)
    staffing = staffing.dropna(subset=["employment_obs"]).copy()
    return staffing


def aggregate_staffing_candidates(config: dict, staffing: pd.DataFrame) -> pd.DataFrame:
    sector_lookup = build_sector_lookup(config)

    deduped = (
        staffing.groupby(["country_iso3", "source", "year", "classif1", "occupation_code"], as_index=False)["employment_obs"]
        .mean()
    )
    sector_panel = deduped.merge(sector_lookup, on="classif1", how="inner")
    sector_panel = (
        sector_panel.groupby(
            [
                "country_iso3",
                "sector_id",
                "sector_name_ru",
                "is_proxy_mn",
                "staffing_proxy_exact",
                "source",
                "year",
                "occupation_code",
            ],
            as_index=False,
        )["employment_obs"]
        .sum()
    )
    return sector_panel


def build_candidate_metrics(config: dict, sector_panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    staffing_cfg = config["staffing_matrix_source"]
    total_code = staffing_cfg["total_occupation_code"]
    occupation_prefix = staffing_cfg["occupation_prefix"]

    total_rows = sector_panel.loc[sector_panel["occupation_code"] == total_code].rename(
        columns={"employment_obs": "reported_sector_total"}
    )
    total_rows = total_rows[
        [
            "country_iso3",
            "sector_id",
            "sector_name_ru",
            "is_proxy_mn",
            "staffing_proxy_exact",
            "source",
            "year",
            "reported_sector_total",
        ]
    ]

    digit_rows = sector_panel.loc[sector_panel["occupation_code"] != total_code].copy()
    digit_rows["occupation_digit"] = digit_rows["occupation_code"].str.replace(occupation_prefix, "", regex=False).astype(int)
    digit_rows = digit_rows.rename(columns={"employment_obs": "occupation_employment"})

    classified = (
        digit_rows.groupby(
            ["country_iso3", "sector_id", "sector_name_ru", "is_proxy_mn", "staffing_proxy_exact", "source", "year"],
            as_index=False,
        )[
            "occupation_employment"
        ]
        .sum()
        .rename(columns={"occupation_employment": "classified_employment"})
    )

    candidate_detail = digit_rows.merge(
        total_rows,
        on=["country_iso3", "sector_id", "sector_name_ru", "is_proxy_mn", "staffing_proxy_exact", "source", "year"],
        how="left",
    )
    candidate_detail = candidate_detail.merge(
        classified,
        on=["country_iso3", "sector_id", "sector_name_ru", "is_proxy_mn", "staffing_proxy_exact", "source", "year"],
        how="left",
    )
    candidate_detail["sector_total_employment"] = candidate_detail[
        ["reported_sector_total", "classified_employment"]
    ].max(axis=1)
    candidate_detail["total_source"] = np.where(
        candidate_detail["reported_sector_total"].notna()
        & (candidate_detail["reported_sector_total"] >= candidate_detail["classified_employment"]),
        "reported_total",
        "sum_digits",
    )
    candidate_detail["share_of_total"] = candidate_detail["occupation_employment"] / candidate_detail["sector_total_employment"]

    summary = (
        candidate_detail.groupby(
            [
                "country_iso3",
                "sector_id",
                "sector_name_ru",
                "is_proxy_mn",
                "staffing_proxy_exact",
                "source",
                "year",
                "total_source",
            ],
            as_index=False,
        )
        .agg(
            n_occ_available=("occupation_digit", "nunique"),
            classified_employment=("classified_employment", "first"),
            sector_total_employment=("sector_total_employment", "first"),
            reported_sector_total=("reported_sector_total", "first"),
            weight_coverage=("share_of_total", "sum"),
        )
    )
    summary["has_reported_total"] = summary["reported_sector_total"].notna()
    summary["is_weight_ready"] = (
        (summary["sector_total_employment"] > 0)
        & (summary["classified_employment"] > 0)
        & (summary["weight_coverage"] >= MIN_WEIGHT_COVERAGE)
    )
    return candidate_detail, summary


def select_base_year_candidates(config: dict, candidate_summary: pd.DataFrame) -> pd.DataFrame:
    staffing_cfg = config["staffing_matrix_source"]
    year_priority = {
        year: rank
        for rank, year in enumerate([staffing_cfg["base_year_target"], *staffing_cfg["fallback_years"]], start=1)
    }
    selected = candidate_summary.loc[candidate_summary["is_weight_ready"]].copy()
    selected["year_priority"] = selected["year"].map(year_priority)
    selected["year_distance"] = (selected["year"] - staffing_cfg["base_year_target"]).abs()
    selected["is_exact_base_year"] = selected["year"] == staffing_cfg["base_year_target"]

    selected = selected.sort_values(
        [
            "country_iso3",
            "sector_id",
            "year_priority",
            "year_distance",
            "weight_coverage",
            "n_occ_available",
            "has_reported_total",
            "sector_total_employment",
        ],
        ascending=[True, True, True, True, False, False, False, False],
    )
    selected = selected.drop_duplicates(subset=["country_iso3", "sector_id"], keep="first").reset_index(drop=True)
    return selected


def build_base_weights(
    selected_candidates: pd.DataFrame,
    candidate_detail: pd.DataFrame,
    rti_long: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_keys = selected_candidates[
        ["country_iso3", "sector_id", "source", "year"]
    ].drop_duplicates()
    base_weights = candidate_detail.merge(
        selected_keys,
        on=["country_iso3", "sector_id", "source", "year"],
        how="inner",
    )
    base_weights["observed_weight_sum"] = base_weights.groupby(
        ["country_iso3", "sector_id", "source", "year"]
    )["share_of_total"].transform("sum")
    base_weights["share_within_classified"] = base_weights["share_of_total"] / base_weights["observed_weight_sum"]

    base_weights = base_weights.merge(rti_long, on=["country_iso3", "occupation_digit"], how="left")
    base_weights["rti_contribution"] = base_weights["share_within_classified"] * base_weights["occupation_rti"]

    rti_panel = (
        base_weights.groupby(["country_iso3", "sector_id"], as_index=False)
        .agg(
            sector_name_ru=("sector_name_ru", "first"),
            rti_staffing_base=("rti_contribution", "sum"),
            rti_base_year=("year", "first"),
            rti_base_source=("source", "first"),
            rti_n_occ_available=("occupation_digit", "nunique"),
            rti_weight_coverage=("observed_weight_sum", "first"),
            rti_sector_total_employment=("sector_total_employment", "first"),
            rti_classified_employment=("classified_employment", "first"),
            rti_total_source=("total_source", "first"),
            is_proxy_mn=("is_proxy_mn", "first"),
            staffing_proxy_exact=("staffing_proxy_exact", "first"),
        )
    )
    rti_panel["rti_proxy_source"] = "Lewandowski RTI x ILOSTAT base-year staffing matrix"

    weights_output = base_weights[
        [
            "country_iso3",
            "sector_id",
            "sector_name_ru",
            "is_proxy_mn",
            "staffing_proxy_exact",
            "year",
            "source",
            "occupation_digit",
            "occupation_employment",
            "sector_total_employment",
            "classified_employment",
            "share_of_total",
            "share_within_classified",
            "occupation_rti",
            "rti_contribution",
            "total_source",
        ]
    ].rename(columns={"source": "staffing_source", "year": "base_year"})

    return rti_panel, weights_output


def write_metadata(config: dict, candidate_summary: pd.DataFrame, selected_candidates: pd.DataFrame, rti_panel: pd.DataFrame) -> None:
    distribution = (
        selected_candidates["year"].value_counts().sort_index().rename_axis("year").reset_index(name="n_country_sector_pairs")
    )
    metadata = {
        "base_year_target": config["staffing_matrix_source"]["base_year_target"],
        "fallback_years": config["staffing_matrix_source"]["fallback_years"],
        "min_weight_coverage": MIN_WEIGHT_COVERAGE,
        "n_candidate_country_sector_year_source": int(len(candidate_summary)),
        "n_selected_country_sector_pairs": int(len(selected_candidates)),
        "n_countries": int(rti_panel["country_iso3"].nunique()),
        "n_sectors": int(rti_panel["sector_id"].nunique()),
        "n_exact_base_year_pairs": int(selected_candidates["is_exact_base_year"].sum()),
        "selected_year_distribution": distribution.to_dict(orient="records"),
        "coverage_by_sector": (
            rti_panel.groupby("sector_id", as_index=False)
            .agg(
                n_country_pairs=("country_iso3", "size"),
                mean_weight_coverage=("rti_weight_coverage", "mean"),
                min_weight_coverage=("rti_weight_coverage", "min"),
            )
            .to_dict(orient="records")
        ),
    }
    with OUTPUT_METADATA.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)


def build_staffing_rti_panel(config: dict, overwrite: bool = False) -> pd.DataFrame:
    ensure_directories([RAW_DIR, RTI_DIR, ILOSTAT_DIR, PROCESSED_DIR])
    staffing = load_staffing_records(config, overwrite=overwrite)
    sector_panel = aggregate_staffing_candidates(config, staffing)
    candidate_detail, candidate_summary = build_candidate_metrics(config, sector_panel)
    selected_candidates = select_base_year_candidates(config, candidate_summary)
    if selected_candidates.empty:
        raise ValueError(
            "No staffing-matrix base-year candidates passed the minimum coverage threshold. "
            "Inspect ILOSTAT availability or lower MIN_WEIGHT_COVERAGE explicitly."
        )
    rti_long = load_rti_long(config, overwrite=overwrite)
    rti_panel, weights_output = build_base_weights(selected_candidates, candidate_detail, rti_long)

    selected_meta = selected_candidates[
        [
            "country_iso3",
            "sector_id",
            "year_priority",
            "year_distance",
        ]
    ].rename(columns={"year_priority": "rti_year_priority", "year_distance": "rti_year_distance"})
    rti_panel = rti_panel.merge(selected_meta, on=["country_iso3", "sector_id"], how="left")
    rti_panel["rti_base_year_exact"] = rti_panel["rti_base_year"] == config["staffing_matrix_source"]["base_year_target"]
    rti_panel = rti_panel.sort_values(["country_iso3", "sector_id"]).reset_index(drop=True)
    weights_output = weights_output.sort_values(["country_iso3", "sector_id", "occupation_digit"]).reset_index(drop=True)

    rti_panel.to_csv(OUTPUT_RTI, index=False)
    weights_output.to_csv(OUTPUT_WEIGHTS, index=False)
    write_metadata(config, candidate_summary, selected_candidates, rti_panel)
    return rti_panel


def main(overwrite: bool = False) -> None:
    config = load_config(CONFIG_PATH)
    rti_panel = build_staffing_rti_panel(config, overwrite=overwrite)
    print(f"Saved RTI panel: {OUTPUT_RTI}")
    print(f"Saved base weights: {OUTPUT_WEIGHTS}")
    print(f"Country-sector pairs: {len(rti_panel):,}")
    print(f"Countries: {rti_panel['country_iso3'].nunique()}")
    print(f"Sectors: {rti_panel['sector_id'].nunique()}")
    print(f"Exact 1995 weights: {int(rti_panel['rti_base_year_exact'].sum())}")


if __name__ == "__main__":
    main()

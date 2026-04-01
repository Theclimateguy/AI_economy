from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = ROOT / "data" / "processed" / "historical_sector_panel_1985_2005.csv"

OUTPUT_ANNUAL = ROOT / "data" / "processed" / "task_content_annual_changes_1995_2005.csv"
OUTPUT_LONG = ROOT / "data" / "processed" / "task_content_longdiff_1995_2005.csv"
OUTPUT_SECTOR = ROOT / "data" / "processed" / "task_content_sector_benchmarks_1995_2005.csv"
OUTPUT_METADATA = ROOT / "data" / "processed" / "task_content_metadata_1995_2005.json"

START_YEAR = 1995
END_YEAR = 2005


def load_panel(path: Path) -> pd.DataFrame:
    panel = pd.read_csv(path)
    panel["year"] = pd.to_numeric(panel["year"], errors="coerce").astype("Int64")
    panel["labour_share_structural"] = pd.to_numeric(panel["labour_share_structural"], errors="coerce")
    return panel


def quantile_stat(series: pd.Series, q: float) -> float:
    clean = series.dropna()
    if clean.empty:
        return np.nan
    return float(clean.quantile(q))


def classify_shift(value: float) -> str:
    if pd.isna(value):
        return "unknown"
    if value < 0:
        return "task_displacing"
    if value > 0:
        return "task_creating"
    return "neutral"


def prepare_task_content_panel(panel: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "country_iso3",
        "sector_id",
        "sector_name_ru",
        "ai_intensity",
        "is_proxy_mn",
        "staffing_proxy_exact",
        "year",
        "labour_share_structural",
        "benchmark_core_ready",
    ]
    tc = panel.loc[panel["year"].between(START_YEAR, END_YEAR), columns].copy()
    tc = tc.dropna(subset=["country_iso3", "sector_id", "year", "labour_share_structural"]).copy()
    tc = tc.sort_values(["country_iso3", "sector_id", "year"]).reset_index(drop=True)
    grouped = tc.groupby(["country_iso3", "sector_id"], sort=False)
    tc["lag_labour_share"] = grouped["labour_share_structural"].shift(1)
    tc["delta_tc_annual"] = tc["labour_share_structural"] - tc["lag_labour_share"]
    return tc


def build_annual_changes(tc: pd.DataFrame) -> pd.DataFrame:
    annual = tc.loc[tc["delta_tc_annual"].notna()].copy()
    annual["task_shift_direction"] = annual["delta_tc_annual"].apply(classify_shift)
    annual["window"] = f"{START_YEAR}-{END_YEAR}"
    return annual


def build_long_differences(tc: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "country_iso3",
        "sector_id",
        "sector_name_ru",
        "ai_intensity",
        "is_proxy_mn",
        "staffing_proxy_exact",
    ]
    start = tc.loc[tc["year"] == START_YEAR, keys + ["labour_share_structural", "benchmark_core_ready"]].rename(
        columns={
            "labour_share_structural": "labour_share_start",
            "benchmark_core_ready": "benchmark_core_ready_start",
        }
    )
    end = tc.loc[tc["year"] == END_YEAR, keys + ["labour_share_structural", "benchmark_core_ready"]].rename(
        columns={
            "labour_share_structural": "labour_share_end",
            "benchmark_core_ready": "benchmark_core_ready_end",
        }
    )

    coverage = (
        tc.groupby(keys, as_index=False)
        .agg(
            n_years_with_labour_share=("year", "nunique"),
            first_available_year=("year", "min"),
            last_available_year=("year", "max"),
        )
    )

    longdiff = start.merge(end, on=keys, how="inner")
    longdiff = longdiff.merge(coverage, on=keys, how="left")
    longdiff["delta_tc_long"] = longdiff["labour_share_end"] - longdiff["labour_share_start"]
    longdiff["delta_tc_annualized"] = longdiff["delta_tc_long"] / float(END_YEAR - START_YEAR)
    longdiff["task_shift_direction"] = longdiff["delta_tc_long"].apply(classify_shift)
    longdiff["is_full_window"] = (
        (longdiff["first_available_year"] == START_YEAR)
        & (longdiff["last_available_year"] == END_YEAR)
        & (longdiff["n_years_with_labour_share"] == (END_YEAR - START_YEAR + 1))
    )
    longdiff["benchmark_core_pair"] = (
        longdiff["benchmark_core_ready_start"].fillna(False) & longdiff["benchmark_core_ready_end"].fillna(False)
    )
    longdiff["window"] = f"{START_YEAR}-{END_YEAR}"
    return longdiff.sort_values(["sector_id", "country_iso3"]).reset_index(drop=True)


def build_sector_benchmarks(longdiff: pd.DataFrame, annual: pd.DataFrame) -> pd.DataFrame:
    grouped = longdiff.groupby(
        ["sector_id", "sector_name_ru", "ai_intensity", "is_proxy_mn", "staffing_proxy_exact"], as_index=False
    )
    sector = grouped.agg(
        n_country_pairs=("country_iso3", "size"),
        n_countries=("country_iso3", "nunique"),
        n_full_window_pairs=("is_full_window", "sum"),
        n_benchmark_core_pairs=("benchmark_core_pair", "sum"),
        mean_delta_tc_long=("delta_tc_long", "mean"),
        std_delta_tc_long=("delta_tc_long", "std"),
        median_delta_tc_long=("delta_tc_long", "median"),
        min_delta_tc_long=("delta_tc_long", "min"),
        max_delta_tc_long=("delta_tc_long", "max"),
        share_negative_long=("delta_tc_long", lambda s: float((s < 0).mean())),
        share_positive_long=("delta_tc_long", lambda s: float((s > 0).mean())),
    )

    quantiles = longdiff.groupby(
        ["sector_id", "sector_name_ru", "ai_intensity", "is_proxy_mn", "staffing_proxy_exact"], as_index=False
    ).agg(
        q10_delta_tc_long=("delta_tc_long", lambda s: quantile_stat(s, 0.10)),
        q25_delta_tc_long=("delta_tc_long", lambda s: quantile_stat(s, 0.25)),
        q75_delta_tc_long=("delta_tc_long", lambda s: quantile_stat(s, 0.75)),
        q90_delta_tc_long=("delta_tc_long", lambda s: quantile_stat(s, 0.90)),
    )
    sector = sector.merge(
        quantiles,
        on=["sector_id", "sector_name_ru", "ai_intensity", "is_proxy_mn", "staffing_proxy_exact"],
        how="left",
    )

    annual_summary = (
        annual.groupby(
            ["sector_id", "sector_name_ru", "ai_intensity", "is_proxy_mn", "staffing_proxy_exact"], as_index=False
        )
        .agg(
            n_annual_changes=("delta_tc_annual", "size"),
            mean_delta_tc_annual=("delta_tc_annual", "mean"),
            std_delta_tc_annual=("delta_tc_annual", "std"),
            median_delta_tc_annual=("delta_tc_annual", "median"),
        )
    )
    sector = sector.merge(
        annual_summary,
        on=["sector_id", "sector_name_ru", "ai_intensity", "is_proxy_mn", "staffing_proxy_exact"],
        how="left",
    )

    sector["dominant_task_shift"] = sector["median_delta_tc_long"].apply(classify_shift)
    sector["shock_neg_1sd_from_mean"] = sector["mean_delta_tc_long"] - sector["std_delta_tc_long"]
    sector["shock_neg_2sd_from_mean"] = sector["mean_delta_tc_long"] - 2.0 * sector["std_delta_tc_long"]
    sector["shock_pos_1sd_from_mean"] = sector["mean_delta_tc_long"] + sector["std_delta_tc_long"]
    sector["shock_pos_2sd_from_mean"] = sector["mean_delta_tc_long"] + 2.0 * sector["std_delta_tc_long"]
    sector["window"] = f"{START_YEAR}-{END_YEAR}"
    sector["task_content_measure"] = "delta_labour_share_structural"
    return sector.sort_values(["ai_intensity", "sector_id"]).reset_index(drop=True)


def write_metadata(panel: pd.DataFrame, annual: pd.DataFrame, longdiff: pd.DataFrame, sector: pd.DataFrame) -> None:
    metadata = {
        "window": {"start_year": START_YEAR, "end_year": END_YEAR},
        "task_content_definition": "Delta TC = Delta(labour_share_structural) = Delta(wL/VA)",
        "variant": "naive_sigma_1",
        "price_clean_variant_available": False,
        "price_clean_variant_note": (
            "Relative-price-cleaned task-content decomposition is not computed in this pipeline because no "
            "sector-consistent price decomposition for wL/VA is attached to the merged historical panel."
        ),
        "n_panel_rows_in_window": int(len(panel)),
        "n_annual_changes": int(len(annual)),
        "n_longdiff_country_sector_pairs": int(len(longdiff)),
        "n_sectors": int(sector["sector_id"].nunique()),
        "n_countries_longdiff": int(longdiff["country_iso3"].nunique()),
        "dominant_task_shift_counts": sector["dominant_task_shift"].value_counts().to_dict(),
    }
    with OUTPUT_METADATA.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)


def main() -> None:
    panel = load_panel(PANEL_PATH)
    tc = prepare_task_content_panel(panel)
    annual = build_annual_changes(tc)
    longdiff = build_long_differences(tc)
    sector = build_sector_benchmarks(longdiff, annual)

    annual.to_csv(OUTPUT_ANNUAL, index=False)
    longdiff.to_csv(OUTPUT_LONG, index=False)
    sector.to_csv(OUTPUT_SECTOR, index=False)
    write_metadata(tc, annual, longdiff, sector)

    print(f"Saved annual changes: {OUTPUT_ANNUAL}")
    print(f"Saved long differences: {OUTPUT_LONG}")
    print(f"Saved sector benchmarks: {OUTPUT_SECTOR}")
    print(f"Annual changes: {len(annual):,}")
    print(f"Long-diff country-sector pairs: {len(longdiff):,}")
    print(f"Sectors: {sector['sector_id'].nunique()}")


if __name__ == "__main__":
    main()

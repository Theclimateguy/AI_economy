from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "russia_ai_scenario_rules.json"
OUTPUT_SCENARIOS = ROOT / "data" / "processed" / "russia_ai_sector_scenarios.csv"
OUTPUT_METADATA = ROOT / "data" / "processed" / "russia_ai_sector_scenarios_metadata.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_path(config: dict, key: str) -> Path:
    return ROOT / config[key]


def classify_rti_bucket(value: float, low_cutoff: float, high_cutoff: float) -> str:
    if value <= low_cutoff:
        return "low"
    if value <= high_cutoff:
        return "medium"
    return "high"


def load_sector_metadata(config: dict) -> pd.DataFrame:
    targets = load_json(resolve_path(config, "benchmark_targets_path"))
    return pd.DataFrame(targets["sector_map"])[
        ["sector_id", "sector_name_ru", "okved", "ai_intensity", "is_proxy_mn", "staffing_proxy_exact"]
    ]


def build_rti_summary(config: dict) -> tuple[pd.DataFrame, dict]:
    rti = pd.read_csv(resolve_path(config, "rti_matrix_path"))
    summary = (
        rti.groupby(["sector_id", "sector_name_ru"], as_index=False)
        .agg(
            rti_country_pairs=("country_iso3", "size"),
            rti_mean_hist=("rti_staffing_base", "mean"),
            rti_median_hist=("rti_staffing_base", "median"),
            rti_std_hist=("rti_staffing_base", "std"),
            rti_min_hist=("rti_staffing_base", "min"),
            rti_max_hist=("rti_staffing_base", "max"),
        )
        .sort_values("sector_id")
        .reset_index(drop=True)
    )

    low_cutoff = float(summary["rti_median_hist"].quantile(1.0 / 3.0))
    high_cutoff = float(summary["rti_median_hist"].quantile(2.0 / 3.0))
    summary["rti_bucket"] = summary["rti_median_hist"].apply(
        lambda value: classify_rti_bucket(value, low_cutoff=low_cutoff, high_cutoff=high_cutoff)
    )
    return summary, {"low_cutoff": low_cutoff, "high_cutoff": high_cutoff}


def extract_margin_lambda(config: dict) -> dict:
    lambda_cfg = config["lambda_source"]
    terms = pd.read_csv(resolve_path(config, "screen_terms_path"))
    row = terms.loc[(terms["test_id"] == lambda_cfg["test_id"]) & (terms["term"] == lambda_cfg["term"])]
    if row.empty:
        raise ValueError("Could not find the requested margin erosion term in historical_benchmark_screen_terms.csv.")

    record = row.iloc[0]
    return {
        "margin_erosion_coef": float(record["baseline_coef"]),
        "margin_erosion_speed": float(abs(record["baseline_coef"])),
        "margin_erosion_pvalue": float(record["baseline_pvalue"]),
        "margin_erosion_qvalue": float(record["q_value"]),
        "margin_erosion_survives": bool(record["survives_screen"]),
    }


def apply_sigma_rule(ai_intensity: str, rti_bucket: str, config: dict) -> tuple[float, float]:
    ai_rule = config["ai_sigma_multipliers"][ai_intensity]
    rti_weight = config["rti_sigma_weights"][rti_bucket]
    return float(ai_rule["core"] * rti_weight), float(ai_rule["stress"] * rti_weight)


def build_scenarios(config: dict) -> tuple[pd.DataFrame, dict]:
    sector_meta = load_sector_metadata(config)
    task_content = pd.read_csv(resolve_path(config, "task_content_benchmarks_path"))
    rti_summary, rti_cutoffs = build_rti_summary(config)
    margin_lambda = extract_margin_lambda(config)

    scenarios = sector_meta.merge(
        task_content,
        on=["sector_id", "sector_name_ru", "ai_intensity", "is_proxy_mn", "staffing_proxy_exact"],
        how="left",
    )
    scenarios = scenarios.merge(rti_summary, on=["sector_id", "sector_name_ru"], how="left")

    sigma_multipliers = scenarios.apply(
        lambda row: apply_sigma_rule(row["ai_intensity"], row["rti_bucket"], config),
        axis=1,
        result_type="expand",
    )
    sigma_multipliers.columns = ["sigma_multiplier_core", "sigma_multiplier_stress"]
    scenarios = pd.concat([scenarios, sigma_multipliers], axis=1)

    scenarios["delta_sL_baseline_mean"] = scenarios["mean_delta_tc_long"]
    scenarios["delta_sL_baseline_median"] = scenarios["median_delta_tc_long"]
    scenarios["delta_sL_core"] = scenarios["mean_delta_tc_long"] - (
        scenarios["sigma_multiplier_core"] * scenarios["std_delta_tc_long"]
    )
    scenarios["delta_sL_stress"] = scenarios["mean_delta_tc_long"] - (
        scenarios["sigma_multiplier_stress"] * scenarios["std_delta_tc_long"]
    )
    scenarios["delta_sL_tail_q25"] = scenarios["q25_delta_tc_long"]
    scenarios["delta_sL_tail_q10"] = scenarios["q10_delta_tc_long"]

    scenarios["margin_erosion_coef"] = margin_lambda["margin_erosion_coef"]
    scenarios["margin_erosion_speed"] = margin_lambda["margin_erosion_speed"]
    scenarios["margin_erosion_pvalue"] = margin_lambda["margin_erosion_pvalue"]
    scenarios["margin_erosion_qvalue"] = margin_lambda["margin_erosion_qvalue"]
    scenarios["margin_erosion_survives"] = margin_lambda["margin_erosion_survives"]

    scenarios["scenario_rule"] = scenarios.apply(
        lambda row: (
            f"core={row['sigma_multiplier_core']:.2f}σ, "
            f"stress={row['sigma_multiplier_stress']:.2f}σ "
            f"from historical mean ΔTC"
        ),
        axis=1,
    )
    scenarios["baseline_anchor"] = "historical_mean_and_median"
    scenarios["task_shock_measure"] = "delta_labour_share_structural"

    ordered_columns = [
        "sector_id",
        "sector_name_ru",
        "okved",
        "ai_intensity",
        "rti_bucket",
        "rti_median_hist",
        "rti_mean_hist",
        "rti_std_hist",
        "staffing_proxy_exact",
        "is_proxy_mn",
        "dominant_task_shift",
        "n_country_pairs",
        "n_benchmark_core_pairs",
        "delta_sL_baseline_mean",
        "delta_sL_baseline_median",
        "delta_sL_core",
        "delta_sL_stress",
        "delta_sL_tail_q25",
        "delta_sL_tail_q10",
        "std_delta_tc_long",
        "q25_delta_tc_long",
        "q10_delta_tc_long",
        "sigma_multiplier_core",
        "sigma_multiplier_stress",
        "scenario_rule",
        "margin_erosion_coef",
        "margin_erosion_speed",
        "margin_erosion_pvalue",
        "margin_erosion_qvalue",
        "margin_erosion_survives",
        "baseline_anchor",
        "task_shock_measure",
    ]
    scenarios = scenarios[ordered_columns].sort_values(["ai_intensity", "sector_id"]).reset_index(drop=True)

    metadata = {
        "rti_bucket_method": config["rti_bucket_method"],
        "rti_bucket_cutoffs": rti_cutoffs,
        "ai_sigma_multipliers": config["ai_sigma_multipliers"],
        "rti_sigma_weights": config["rti_sigma_weights"],
        "margin_lambda": margin_lambda,
        "n_sectors": int(len(scenarios)),
    }
    return scenarios, metadata


def main() -> None:
    config = load_json(CONFIG_PATH)
    scenarios, metadata = build_scenarios(config)

    scenarios.to_csv(OUTPUT_SCENARIOS, index=False)
    with OUTPUT_METADATA.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)

    print(f"Saved scenarios: {OUTPUT_SCENARIOS}")
    print(f"Saved metadata: {OUTPUT_METADATA}")
    print(f"Sectors: {len(scenarios)}")
    print(
        "RTI buckets: "
        + ", ".join(
            f"{bucket}={count}"
            for bucket, count in scenarios["rti_bucket"].value_counts().sort_index().items()
        )
    )


if __name__ == "__main__":
    main()

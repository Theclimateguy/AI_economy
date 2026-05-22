from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_managed_obsolescence_layer import load_fixed_asset_renewal, load_ict_usage


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "data" / "processed" / "russia_sector_baseline_2024.csv"
SECTOR_IMPACT_PATH = ROOT / "data" / "processed" / "russia_ai_sector_impact_summary_2024.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "import_dependency_sector.csv"
DOC_PATH = ROOT / "docs" / "managed_obsolescence_layer.md"
CONFIG_PATH = ROOT / "config" / "russia_economy_structure_layer.json"

AI_INTENSITY_WEIGHT = {
    "high": 1.0,
    "medium": 0.75,
    "low_medium": 0.5,
    "low": 0.3,
}

SECTOR_PRIORS = {
    "B": {
        "equipment_import_dependency": 0.85,
        "software_cloud_dependency": 0.25,
        "gpu_dependency": 0.35,
        "market_concentration_prior": 0.80,
        "strategic_sector_flag": 1.0,
    },
    "C": {
        "equipment_import_dependency": 0.75,
        "software_cloud_dependency": 0.35,
        "gpu_dependency": 0.45,
        "market_concentration_prior": 0.55,
        "strategic_sector_flag": 0.60,
    },
    "C_mach": {
        "equipment_import_dependency": 0.82,
        "software_cloud_dependency": 0.42,
        "gpu_dependency": 0.50,
        "market_concentration_prior": 0.60,
        "strategic_sector_flag": 0.75,
    },
    "DE": {
        "equipment_import_dependency": 0.55,
        "software_cloud_dependency": 0.30,
        "gpu_dependency": 0.20,
        "market_concentration_prior": 0.85,
        "strategic_sector_flag": 1.0,
    },
    "F": {
        "equipment_import_dependency": 0.70,
        "software_cloud_dependency": 0.20,
        "gpu_dependency": 0.25,
        "market_concentration_prior": 0.35,
        "strategic_sector_flag": 0.40,
    },
    "G": {
        "equipment_import_dependency": 0.35,
        "software_cloud_dependency": 0.50,
        "gpu_dependency": 0.35,
        "market_concentration_prior": 0.45,
        "strategic_sector_flag": 0.25,
    },
    "H": {
        "equipment_import_dependency": 0.60,
        "software_cloud_dependency": 0.30,
        "gpu_dependency": 0.30,
        "market_concentration_prior": 0.70,
        "strategic_sector_flag": 0.80,
    },
    "J": {
        "equipment_import_dependency": 0.35,
        "software_cloud_dependency": 0.75,
        "gpu_dependency": 0.65,
        "market_concentration_prior": 0.50,
        "strategic_sector_flag": 0.30,
    },
    "K": {
        "equipment_import_dependency": 0.20,
        "software_cloud_dependency": 0.70,
        "gpu_dependency": 0.50,
        "market_concentration_prior": 0.90,
        "strategic_sector_flag": 0.80,
    },
    "M": {
        "equipment_import_dependency": 0.25,
        "software_cloud_dependency": 0.65,
        "gpu_dependency": 0.45,
        "market_concentration_prior": 0.35,
        "strategic_sector_flag": 0.20,
    },
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def minmax(series: pd.Series) -> pd.Series:
    if series.max(skipna=True) == series.min(skipna=True):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - series.min(skipna=True)) / (series.max(skipna=True) - series.min(skipna=True))


def build_dataset() -> pd.DataFrame:
    baseline = pd.read_csv(BASELINE_PATH)[["sector_id", "sector_name_ru", "ai_intensity"]]
    sector_impact = pd.read_csv(SECTOR_IMPACT_PATH)[["sector_id", "employment_share_2024"]]
    ict_2024 = load_ict_usage().loc[lambda df: df["year"].eq(2024), ["sector_id", "ict_digital_share_proxy_pct"]]
    renewal_2020 = load_fixed_asset_renewal().loc[
        lambda df: df["year"].eq(2020), ["sector_id", "fixed_asset_renewal_pct"]
    ]

    df = baseline.merge(sector_impact, on="sector_id", how="left")
    df = df.merge(ict_2024, on="sector_id", how="left")
    df = df.merge(renewal_2020, on="sector_id", how="left")

    priors = pd.DataFrame.from_dict(SECTOR_PRIORS, orient="index").reset_index().rename(columns={"index": "sector_id"})
    df = df.merge(priors, on="sector_id", how="left")
    df["ai_intensity_weight"] = df["ai_intensity"].map(AI_INTENSITY_WEIGHT).fillna(0.5)

    df["ict_digital_share_norm"] = minmax(df["ict_digital_share_proxy_pct"])
    df["fixed_asset_renewal_norm"] = minmax(df["fixed_asset_renewal_pct"])
    df["employment_share_norm"] = minmax(df["employment_share_2024"])

    # First-pass sanctions proxy: imported hardware, imported software/cloud, and GPU dependence.
    df["import_dependency_score"] = (
        0.45 * df["equipment_import_dependency"] * df["fixed_asset_renewal_norm"]
        + 0.35 * df["software_cloud_dependency"] * df["ict_digital_share_norm"]
        + 0.20 * df["gpu_dependency"] * df["ai_intensity_weight"]
    ).clip(0.0, 1.0)

    df["market_concentration_score"] = (
        0.60 * df["market_concentration_prior"]
        + 0.25 * df["strategic_sector_flag"]
        + 0.15 * df["employment_share_norm"]
    ).clip(0.0, 1.0)
    return df


def apply_sanction_scenarios(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    alpha_4 = float(config["import_friction"]["alpha_4"])
    alpha_5 = float(config["import_friction"]["alpha_5"])
    df["sanction_wedge_base"] = alpha_4 * df["import_dependency_score"] + alpha_5 * df["market_concentration_score"]
    df["sanction_wedge_relief"] = (
        alpha_4 * 0.55 * df["import_dependency_score"] + alpha_5 * 0.90 * df["market_concentration_score"]
    )
    return df


def update_docs() -> None:
    path = DOC_PATH
    text = path.read_text(encoding="utf-8")
    old = """$$
\\tau_{s,t} =
\\alpha_1 MOS_s
+ \\alpha_2 \\text{employment\\_share}_{s,t}
+ \\alpha_3 \\text{strategic\\_sector}_s
+ \\alpha_4 \\text{import\\_dependency}_{s,t}
+ \\alpha_5 \\text{market\\_concentration}_{s,t}
$$
"""
    new = """$$
\\tau_{s,t} =
\\rho MOS_s
+ \\alpha_4 \\text{import\\_dependency}_{s}
+ \\alpha_5 \\text{market\\_concentration}_{s}
$$

где в текущей first-pass реализации

- `import_dependency_s` собирается как proxy из `equipment-import prior`, `software/cloud prior`, `GPU dependence`, `ICT digital share` и `fixed-asset renewal`;
- `market_concentration_s` собирается как proxy из sector concentration prior, strategic flag и `employment_share_2024`;
- сценарии `SanctionBase` и `SanctionRelief` отличаются по силе import wedge при одном и том же `BaseThrottle` уровне для `MOS`.
"""
    if old in text:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    config = load_json(CONFIG_PATH)
    df = build_dataset()
    df = apply_sanction_scenarios(df, config)
    df["notes"] = [
        "First-pass sanctions proxy: literature-anchored priors plus current Rosstat ICT/fixed-assets/employment indicators."
        for _ in range(len(df))
    ]
    df = df.sort_values("sanction_wedge_base", ascending=False).reset_index(drop=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    update_docs()
    print(f"Saved import friction layer: {OUTPUT_PATH}")
    print(df[["sector_id", "import_dependency_score", "market_concentration_score", "sanction_wedge_base", "sanction_wedge_relief"]].to_string(index=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = ROOT / "data" / "processed" / "historical_sector_panel_1985_2005.csv"
CONFIG_PATH = ROOT / "config" / "benchmark_screening.json"
OUTPUT_SUMMARY = ROOT / "data" / "processed" / "historical_benchmark_screen_summary.csv"
OUTPUT_TERMS = ROOT / "data" / "processed" / "historical_benchmark_screen_terms.csv"
OUTPUT_SPECS = ROOT / "data" / "processed" / "historical_benchmark_screen_specs.csv"
OUTPUT_LOO = ROOT / "data" / "processed" / "historical_benchmark_screen_loo.csv"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def benjamini_hochberg(pvalues: pd.Series) -> pd.Series:
    ranked = pvalues.astype(float).sort_values()
    m = len(ranked)
    adjusted = pd.Series(index=ranked.index, dtype=float)
    running_min = 1.0
    for rank, (idx, value) in enumerate(reversed(list(ranked.items())), start=1):
        candidate = value * m / (m - rank + 1)
        running_min = min(running_min, candidate)
        adjusted[idx] = min(running_min, 1.0)
    return adjusted.reindex(pvalues.index)


def prepare_features(panel: pd.DataFrame, config: dict) -> pd.DataFrame:
    window = config["analysis_window"]
    df = panel.copy()
    df = df.loc[df["year"].between(window["start_year"], window["end_year"])].copy()
    df = df.sort_values(["country_iso3", "sector_id", "year"]).reset_index(drop=True)

    grouped = df.groupby(["country_iso3", "sector_id"], sort=False)

    def safe_log(series: pd.Series) -> pd.Series:
        return np.where(series > 0, np.log(series), np.nan)

    df["labour_share_source"] = df["labour_share_structural"]
    df["margin_source"] = df["margin"]
    df["techint_source"] = df["techint"]
    if "rti_staffing_base" in df.columns:
        df["rti"] = df["rti_staffing_base"]
    else:
        df["rti"] = df["rti_onet17_sector_proxy"]
    df["occ_source"] = df["occ"]
    df["emp_per_va_source"] = df["emp_per_va"]

    df["log_occ_plus_one"] = safe_log(1.0 + df["occ_source"])
    df["log_emp_per_va"] = safe_log(df["emp_per_va_source"])

    for source_name, target_name in [
        ("labour_share_source", "labour_share"),
        ("margin_source", "margin"),
        ("techint_source", "techint"),
        ("occ_source", "occ"),
        ("emp_per_va_source", "emp_per_va"),
    ]:
        df[f"lag_{target_name}"] = grouped[source_name].shift(1)
        df[f"d_{target_name}"] = df[source_name] - df[f"lag_{target_name}"]

    df["lag_d_techint"] = grouped["d_techint"].shift(1)
    df["lead_d_techint"] = grouped["d_techint"].shift(-1)
    df["lag_margin"] = grouped["margin_source"].shift(1)
    df["year_centered"] = df["year"] - df["year"].mean()
    df["country_sector"] = df["country_iso3"] + "__" + df["sector_id"]
    return df


def add_country_trend(formula: str) -> str:
    return formula + " + year_centered:C(country_iso3)"


def fit_formula(df: pd.DataFrame, formula: str, covariance: str) -> tuple[object, pd.DataFrame]:
    model = smf.ols(formula=formula, data=df, missing="drop")
    used_index = pd.Index(model.data.row_labels)
    sample = df.loc[used_index].copy()
    if sample.empty:
        raise ValueError("Empty estimation sample.")

    if covariance == "country_cluster":
        result = model.fit(cov_type="cluster", cov_kwds={"groups": sample["country_iso3"]})
    elif covariance == "country_sector_cluster":
        result = model.fit(cov_type="cluster", cov_kwds={"groups": sample["country_sector"]})
    elif covariance == "hc3":
        result = model.fit(cov_type="HC3")
    else:
        raise ValueError(f"Unknown covariance {covariance}")
    return result, sample


def term_sign_ok(coef: float, expected_sign: int) -> bool:
    if pd.isna(coef) or coef == 0:
        return False
    return np.sign(coef) == np.sign(expected_sign)


def fit_spec(df: pd.DataFrame, test: dict, spec_name: str, formula: str, covariance: str) -> list[dict]:
    result, sample = fit_formula(df, formula, covariance)
    rows = []
    for focal in test["focal_terms"]:
        term = focal["term"]
        rows.append(
            {
                "test_id": test["test_id"],
                "label": test["label"],
                "spec_name": spec_name,
                "formula": formula,
                "term": term,
                "expected_sign": int(focal["expected_sign"]),
                "coef": float(result.params.get(term, np.nan)),
                "se": float(result.bse.get(term, np.nan)),
                "pvalue": float(result.pvalues.get(term, np.nan)),
                "r2": float(result.rsquared),
                "nobs": int(result.nobs),
                "n_countries": int(sample["country_iso3"].nunique()),
                "n_sectors": int(sample["sector_id"].nunique()),
            }
        )
    return rows


def run_placebo(df: pd.DataFrame, test: dict, covariance: str) -> list[dict]:
    placebo_rows = []
    placebo_terms = [focal for focal in test["focal_terms"] if "placebo_term" in focal]
    if not placebo_terms:
        return placebo_rows

    placebo_formula = test["formula"].replace("lag_d_techint", "lead_d_techint")
    result, sample = fit_formula(df, placebo_formula, covariance)
    for focal in placebo_terms:
        placebo_rows.append(
            {
                "test_id": test["test_id"],
                "label": test["label"],
                "spec_name": "placebo_lead",
                "formula": placebo_formula,
                "term": focal["term"],
                "placebo_term": focal["placebo_term"],
                "coef": float(result.params.get(focal["placebo_term"], np.nan)),
                "se": float(result.bse.get(focal["placebo_term"], np.nan)),
                "pvalue": float(result.pvalues.get(focal["placebo_term"], np.nan)),
                "r2": float(result.rsquared),
                "nobs": int(result.nobs),
                "n_countries": int(sample["country_iso3"].nunique()),
                "n_sectors": int(sample["sector_id"].nunique()),
            }
        )
    return placebo_rows


def standardized_beta(df: pd.DataFrame, formula: str, term: str) -> float:
    lhs, rhs = formula.split("~", 1)
    lhs = lhs.strip()
    sample = df.copy()
    for column in [lhs, "lag_d_techint", "rti", "lag_margin"]:
        if column in sample.columns:
            std = sample[column].std(ddof=0)
            if pd.notna(std) and std > 0:
                sample[column] = (sample[column] - sample[column].mean()) / std
    try:
        result, _ = fit_formula(sample, formula, "country_cluster")
    except Exception:
        return np.nan
    return float(result.params.get(term, np.nan))


def run_leave_one_country_out(df: pd.DataFrame, test: dict) -> pd.DataFrame:
    rows = []
    countries = sorted(df["country_iso3"].dropna().unique().tolist())
    for country in countries:
        sample = df.loc[df["country_iso3"] != country].copy()
        try:
            spec_rows = fit_spec(sample, test, "baseline", test["formula"], "country_cluster")
        except Exception:
            continue
        for row in spec_rows:
            row["excluded_country"] = country
            rows.append(row)
    return pd.DataFrame(rows)


def build_term_summary(df_features: pd.DataFrame, term_rows: pd.DataFrame, placebo_rows: pd.DataFrame, loo_rows: pd.DataFrame, config: dict) -> pd.DataFrame:
    thresholds = config["thresholds"]
    baseline = term_rows.loc[term_rows["spec_name"] == "baseline"].copy()

    standardized = []
    for _, row in baseline.iterrows():
        standardized.append(standardized_beta(df_features, row["formula"], row["term"]))
    baseline["standardized_beta"] = standardized

    summary_rows = []
    for _, row in baseline.iterrows():
        key = (row["test_id"], row["term"])
        spec_subset = term_rows.loc[(term_rows["test_id"] == key[0]) & (term_rows["term"] == key[1])]
        placebo_subset = placebo_rows.loc[(placebo_rows["test_id"] == key[0]) & (placebo_rows["term"] == key[1])]
        loo_subset = loo_rows.loc[(loo_rows["test_id"] == key[0]) & (loo_rows["term"] == key[1])]

        sign_stability_share = float(
            spec_subset.loc[spec_subset["spec_name"] != "placebo_lead", "coef"]
            .apply(lambda coef: term_sign_ok(coef, int(row["expected_sign"])))
            .mean()
        )
        loo_sign_share = float(
            loo_subset["coef"].apply(lambda coef: term_sign_ok(coef, int(row["expected_sign"]))).mean()
        )
        placebo_pvalue = float(placebo_subset["pvalue"].iloc[0]) if not placebo_subset.empty else np.nan

        summary_rows.append(
            {
                "test_id": row["test_id"],
                "label": row["label"],
                "term": row["term"],
                "expected_sign": int(row["expected_sign"]),
                "baseline_coef": row["coef"],
                "baseline_se": row["se"],
                "baseline_pvalue": row["pvalue"],
                "baseline_r2": row["r2"],
                "standardized_beta": row["standardized_beta"],
                "nobs": row["nobs"],
                "n_countries": row["n_countries"],
                "n_sectors": row["n_sectors"],
                "placebo_pvalue": placebo_pvalue,
                "sign_stability_share": sign_stability_share,
                "loo_sign_share": loo_sign_share,
                "baseline_sign_pass": term_sign_ok(row["coef"], int(row["expected_sign"])),
                "baseline_p_pass": bool(row["pvalue"] <= thresholds["p_value"]),
                "placebo_pass": bool(placebo_pvalue > thresholds["placebo_p_value"]) if pd.notna(placebo_pvalue) else True,
                "sign_stability_pass": bool(sign_stability_share >= thresholds["min_sign_stability_share"]),
                "loo_sign_pass": bool(loo_sign_share >= thresholds["min_loo_sign_share"]),
                "sample_pass": bool(
                    row["nobs"] >= thresholds["min_observations"] and row["n_countries"] >= thresholds["min_country_count"]
                ),
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary["q_value"] = benjamini_hochberg(summary["baseline_pvalue"])
    summary["q_value_pass"] = summary["q_value"] <= thresholds["q_value"]
    summary["survives_screen"] = (
        summary["sample_pass"]
        & summary["baseline_sign_pass"]
        & summary["baseline_p_pass"]
        & summary["q_value_pass"]
        & summary["placebo_pass"]
        & summary["sign_stability_pass"]
        & summary["loo_sign_pass"]
    )
    return summary


def build_test_summary(term_summary: pd.DataFrame, tests: list[dict]) -> pd.DataFrame:
    descriptions = {test["test_id"]: test["description"] for test in tests}
    grouped = term_summary.groupby(["test_id", "label"], as_index=False).agg(
        n_terms=("term", "size"),
        n_terms_surviving=("survives_screen", "sum"),
        n_terms_baseline_sign=("baseline_sign_pass", "sum"),
        min_q_value=("q_value", "min"),
        max_baseline_pvalue=("baseline_pvalue", "max"),
        min_placebo_pvalue=("placebo_pvalue", "min"),
        min_sign_stability_share=("sign_stability_share", "min"),
        min_loo_sign_share=("loo_sign_share", "min"),
        min_n_countries=("n_countries", "min"),
        min_nobs=("nobs", "min"),
    )
    grouped["description"] = grouped["test_id"].map(descriptions)
    grouped["survives_screen"] = grouped["n_terms_surviving"] == grouped["n_terms"]
    grouped["decision"] = np.where(grouped["survives_screen"], "survive", "reject")
    return grouped.sort_values(["survives_screen", "min_q_value"], ascending=[False, True]).reset_index(drop=True)


def main() -> None:
    config = load_json(CONFIG_PATH)
    panel = pd.read_csv(PANEL_PATH)
    df = prepare_features(panel, config)

    robustness_specs = {
        "baseline": {"covariance": "country_cluster", "formula_transform": lambda f: f, "exclude_countries": []},
        "country_sector_cluster": {
            "covariance": "country_sector_cluster",
            "formula_transform": lambda f: f,
            "exclude_countries": [],
        },
        "hc3": {"covariance": "hc3", "formula_transform": lambda f: f, "exclude_countries": []},
        "no_us_jp": {
            "covariance": "country_cluster",
            "formula_transform": lambda f: f,
            "exclude_countries": config["robustness"].get("exclude_countries", []),
        },
        "country_trend": {
            "covariance": "country_cluster",
            "formula_transform": add_country_trend,
            "exclude_countries": [],
        },
    }

    spec_rows = []
    placebo_rows = []
    loo_rows = []
    for test in config["tests"]:
        for spec_name, spec in robustness_specs.items():
            sample = df.copy()
            if spec["exclude_countries"]:
                sample = sample.loc[~sample["country_iso3"].isin(spec["exclude_countries"])].copy()
            formula = spec["formula_transform"](test["formula"])
            spec_rows.extend(fit_spec(sample, test, spec_name, formula, spec["covariance"]))
        placebo_rows.extend(run_placebo(df, test, "country_cluster"))
        loo_rows.append(run_leave_one_country_out(df, test))

    term_rows = pd.DataFrame(spec_rows)
    placebo_df = pd.DataFrame(placebo_rows)
    loo_df = pd.concat(loo_rows, ignore_index=True).sort_values(["test_id", "term", "excluded_country"]).reset_index(drop=True)

    term_summary = build_term_summary(df, term_rows, placebo_df, loo_df, config).sort_values(
        ["survives_screen", "q_value", "baseline_pvalue"], ascending=[False, True, True]
    )
    test_summary = build_test_summary(term_summary, config["tests"])

    term_summary.to_csv(OUTPUT_TERMS, index=False)
    test_summary.to_csv(OUTPUT_SUMMARY, index=False)
    pd.concat([term_rows, placebo_df], ignore_index=True).sort_values(["test_id", "term", "spec_name"]).to_csv(
        OUTPUT_SPECS, index=False
    )
    loo_df.to_csv(OUTPUT_LOO, index=False)

    print(f"Saved test summary: {OUTPUT_SUMMARY}")
    print(f"Saved term summary: {OUTPUT_TERMS}")
    print(f"Saved robustness specs: {OUTPUT_SPECS}")
    print(f"Saved leave-one-country-out: {OUTPUT_LOO}")
    print(f"Tests run: {len(test_summary)}")
    print(f"Surviving tests: {int(test_summary['survives_screen'].sum())}")
    if int(test_summary["survives_screen"].sum()):
        print(test_summary.loc[test_summary["survives_screen"], ["test_id", "n_terms_surviving", "min_q_value"]].to_string(index=False))
    else:
        print("No structural invariant survives the full conservative screen.")


if __name__ == "__main__":
    main()

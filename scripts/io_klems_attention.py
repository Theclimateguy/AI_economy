from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "expert_assumptions_attention_monopoly.yaml"
BASELINE_PATH = ROOT / "data" / "processed" / "russia_sector_baseline_2024.csv"
RETURNS_PATH = ROOT / "data" / "processed" / "ai_capital_return_sector_summary.csv"
STRUCTURE_PATH = ROOT / "data" / "processed" / "russia_economy_structure_sector_summary.csv"

BENCHMARKS_PATH = ROOT / "data" / "benchmarks_attention_monopoly.csv"
SUMMARY_PATH = ROOT / "data" / "processed" / "attention_monopoly_sector_summary.csv"
ABM_PATH = ROOT / "data" / "processed" / "attention_monopoly_abm_paths.csv"
DWL_PATH = ROOT / "data" / "processed" / "attention_monopoly_deadweight_loss.csv"
REPORT_PATH = ROOT / "docs" / "attention_monopoly_scenario.md"

FIG_DIR = ROOT / "output"
RISK_FIG = FIG_DIR / "attention_monopoly_risk_gradient.png"
GVA_FIG = FIG_DIR / "attention_monopoly_gva_shift.png"
ABM_FIG = FIG_DIR / "attention_abm_dynamics.png"
DWL_FIG = FIG_DIR / "attention_deadweight_loss.png"


SECTOR_LABELS = {
    "B": "Mining",
    "C": "Manufact.",
    "C_mach": "Machinery",
    "DE": "Energy",
    "F": "Constr.",
    "G": "Trade",
    "H": "Transport",
    "J": "IT",
    "K": "Finance",
    "M": "Prof.Svcs",
}


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def normalize(series: pd.Series) -> pd.Series:
    lower = float(series.min())
    upper = float(series.max())
    if np.isclose(lower, upper):
        return pd.Series(0.0, index=series.index)
    return (series - lower) / (upper - lower)


def load_model_inputs(config: dict) -> pd.DataFrame:
    scenario = config["scenario"]["main_scenario"]
    baseline = pd.read_csv(BASELINE_PATH)
    returns = pd.read_csv(RETURNS_PATH)
    structure = pd.read_csv(STRUCTURE_PATH)

    returns = returns.loc[returns["scenario"].eq(scenario), ["sector_id", "class_id", "A_2035", "net_return_cf_2035"]]
    structure = structure.loc[
        structure["scenario"].eq(scenario) & structure["throttle_scenario"].eq("BaseThrottle"),
        ["sector_id", "delta_va_share_pp_2035", "incremental_va_2035_bn_rub"],
    ]
    cols = ["sector_id", "sector_name_ru", "ai_intensity", "va_current_bn_rub", "employment_thousand_persons"]
    return baseline[cols].merge(returns, on="sector_id", how="left").merge(structure, on="sector_id", how="left")


def build_benchmarks(config: dict, inputs: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for sector_id, priors in config["sector_priors"].items():
        row = {"sector_id": sector_id, **priors}
        row["source"] = "Issue #7 expert ranges + team first-pass sector priors"
        row["year"] = config["scenario"]["baseline_year"]
        row["confidence"] = "M" if sector_id in {"G", "J", "K", "M"} else "L"
        row["assumption_tag"] = "[EXPERT_ASSUMPTION]"
        rows.append(row)

    benchmarks = pd.DataFrame(rows)
    return inputs[["sector_id", "sector_name_ru", "ai_intensity"]].merge(benchmarks, on="sector_id", how="left")


def bass_path(config: dict) -> pd.DataFrame:
    diff = config["diffusion"]
    years = range(config["scenario"]["start_year"], config["scenario"]["end_year"] + 1)
    records: list[dict] = []

    for saturation_name, saturation in diff["saturation_share"].items():
        share = float(diff["initial_share"])
        for year in years:
            adoption_increment = (diff["p"] + diff["q"] * share) * (float(saturation) - share)
            share = float(np.clip(share + adoption_increment, 0.0, saturation))
            locked_share = share * float(config["abm"]["cognitive_lock_in"])
            open_web_share = max(0.0, 1.0 - share)
            platform_hhi = share**2 / float(config["abm"]["platform_count"]) + open_web_share**2
            records.append(
                {
                    "scenario": saturation_name,
                    "year": year,
                    "assistant_attention_share": share,
                    "locked_attention_share": locked_share,
                    "open_web_attention_share": open_web_share,
                    "attention_hhi": platform_hhi,
                    "sme_outside_platform_index": config["abm"]["n_sme_index"] * open_web_share,
                }
            )
    return pd.DataFrame(records)


def build_attention_sector_summary(inputs: pd.DataFrame, benchmarks: pd.DataFrame, config: dict) -> pd.DataFrame:
    df = inputs.merge(
        benchmarks.drop(columns=["sector_name_ru", "ai_intensity"]),
        on="sector_id",
        how="left",
    )
    weights = config["risk_weights"]
    max_markup = max(prior["platform_markup_mid"] for prior in config["sector_priors"].values())
    df["integration_deficit"] = 1.0 - df["integration_capacity"]
    df["markup_intensity"] = df["platform_markup_mid"] / max_markup
    df["attention_risk_score"] = 100.0 * (
        weights["attention_dependency"] * df["attention_dependency"]
        + weights["integration_deficit"] * df["integration_deficit"]
        + weights["markup_intensity"] * df["markup_intensity"]
        + weights["sme_vulnerability"] * df["vulnerable_sme_share"]
        + weights["ai_adoption"] * df["A_2035"].fillna(df["A_2035"].median())
    )

    assistant_share = float(config["diffusion"]["saturation_share"]["base"])
    access_fee_base = (
        df["va_current_bn_rub"]
        * assistant_share
        * df["attention_dependency"]
        * df["platform_markup_mid"]
        * (0.5 + 0.5 * df["vulnerable_sme_share"])
    )
    integration_loss_factor = df["integration_deficit"].clip(0.0, 1.0)
    df["platform_access_fee_bn_rub"] = access_fee_base * integration_loss_factor

    retained_savings = float(config["capital_reallocation"]["cac_saving_retention"])
    df["cac_saving_va_gain_bn_rub"] = (
        df["va_current_bn_rub"]
        * assistant_share
        * df["attention_dependency"]
        * df["integration_capacity"]
        * df["cac_saving_mid"]
        * retained_savings
    )
    df["attention_gva_shift_bn_rub"] = df["cac_saving_va_gain_bn_rub"] - df["platform_access_fee_bn_rub"]

    rent_pool = float(df["platform_access_fee_bn_rub"].sum() * config["capital_reallocation"]["platform_rent_capture_share"])
    rent_receivers = df["platform_rent_receiver"].fillna(False)
    if rent_receivers.any():
        receiver_weights = df.loc[rent_receivers, "integration_capacity"] * df.loc[rent_receivers, "va_current_bn_rub"]
        df.loc[rent_receivers, "attention_gva_shift_bn_rub"] += rent_pool * receiver_weights / receiver_weights.sum()

    df["capital_reallocation_pressure_bn_rub"] = (
        df["platform_access_fee_bn_rub"].clip(lower=0.0) + df["cac_saving_va_gain_bn_rub"].clip(lower=0.0)
    )
    df["risk_bucket"] = pd.cut(
        df["attention_risk_score"],
        bins=[-np.inf, 45.0, 60.0, np.inf],
        labels=["low", "medium", "high"],
    )
    return df.sort_values("attention_risk_score", ascending=False).reset_index(drop=True)


def build_deadweight_loss(summary: pd.DataFrame, config: dict) -> pd.DataFrame:
    elasticity = float(config["deadweight_loss"]["demand_elasticity_abs"])
    competitive_markup = float(config["deadweight_loss"]["competitive_markup"])
    df = summary.copy()
    excess_markup = (df["platform_markup_mid"] - competitive_markup).clip(lower=0.0)
    addressable_market = df["va_current_bn_rub"] * df["attention_dependency"] * float(
        config["diffusion"]["saturation_share"]["base"]
    )
    df["deadweight_loss_bn_rub"] = 0.5 * elasticity * excess_markup.pow(2) * addressable_market
    return df[["sector_id", "sector_name_ru", "deadweight_loss_bn_rub", "platform_markup_mid", "attention_dependency"]]


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.sans-serif": ["DejaVu Sans", "sans-serif"],
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def save_fig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path.relative_to(ROOT)}")


def plot_risk_gradient(summary: pd.DataFrame, config: dict) -> None:
    weights = config["risk_weights"]
    max_markup = max(prior["platform_markup_mid"] for prior in config["sector_priors"].values())
    x = np.linspace(0.0, 1.0, 150)
    y = np.linspace(0.0, 1.0, 150)
    xx, yy = np.meshgrid(x, y)
    mean_markup = float(summary["platform_markup_mid"].mean() / max_markup)
    mean_sme = float(summary["vulnerable_sme_share"].mean())
    mean_adoption = float(summary["A_2035"].mean())
    zz = 100.0 * (
        weights["attention_dependency"] * yy
        + weights["integration_deficit"] * xx
        + weights["markup_intensity"] * mean_markup
        + weights["sme_vulnerability"] * mean_sme
        + weights["ai_adoption"] * mean_adoption
    )

    fig, ax = plt.subplots(figsize=(11, 8))
    contour = ax.contourf(xx, yy, zz, levels=16, cmap="RdYlGn_r", alpha=0.82)
    ax.scatter(
        summary["integration_deficit"],
        summary["attention_dependency"],
        s=120 + 780 * normalize(summary["va_current_bn_rub"]),
        c=summary["attention_risk_score"],
        cmap="RdYlGn_r",
        edgecolor="#111827",
        linewidth=0.8,
        zorder=3,
    )
    for row in summary.itertuples(index=False):
        ax.text(row.integration_deficit + 0.015, row.attention_dependency + 0.012, SECTOR_LABELS[row.sector_id], fontsize=9)

    ax.set_title("Attention monopoly risk gradient by sector")
    ax.set_xlabel("Integration deficit: 1 - AI/platform integration capacity")
    ax.set_ylabel("Dependence on user attention / discovery channel")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(color="#E5E7EB", linewidth=0.6)
    cbar = fig.colorbar(contour, ax=ax, pad=0.015)
    cbar.set_label("Composite risk score, 0-100")
    save_fig(fig, RISK_FIG)


def plot_gva_shift(summary: pd.DataFrame) -> None:
    df = summary.sort_values("attention_gva_shift_bn_rub")
    colors = np.where(df["attention_gva_shift_bn_rub"] >= 0, "#059669", "#DC2626")
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.barh(df["sector_id"], df["attention_gva_shift_bn_rub"], color=colors)
    ax.axvline(0.0, color="#111827", linewidth=1.0)
    ax.set_title("Attention-monopoly sector GVA shift, base 2035 saturation")
    ax.set_xlabel("Net sector GVA / capital-attraction shift, bn RUB")
    ax.set_ylabel("Sector")
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.7)
    save_fig(fig, GVA_FIG)


def plot_abm(abm: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for scenario, group in abm.groupby("scenario"):
        axes[0].plot(group["year"], group["assistant_attention_share"], linewidth=2.2, label=scenario)
        axes[0].plot(group["year"], group["locked_attention_share"], linewidth=1.6, linestyle="--")
        axes[1].plot(group["year"], group["attention_hhi"], linewidth=2.2, label=scenario)
    axes[0].set_title("Assistant-mediated attention share")
    axes[0].set_ylabel("Share of active digital attention")
    axes[0].set_xlabel("Year")
    axes[1].set_title("Attention concentration index")
    axes[1].set_ylabel("HHI proxy")
    axes[1].set_xlabel("Year")
    for ax in axes:
        ax.grid(color="#E5E7EB", linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].legend(title="Saturation")
    save_fig(fig, ABM_FIG)


def plot_deadweight_loss(dwl: pd.DataFrame) -> None:
    df = dwl.sort_values("deadweight_loss_bn_rub", ascending=True)
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(df["sector_id"], df["deadweight_loss_bn_rub"], color="#7C2D12")
    ax.set_title("Deadweight loss from monopoly access to intentions")
    ax.set_xlabel("DWL, bn RUB")
    ax.set_ylabel("Sector")
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.7)
    save_fig(fig, DWL_FIG)


def markdown_table(df: pd.DataFrame, cols: list[str], n: int = 10) -> str:
    table = df[cols].head(n).copy()
    for col in table.select_dtypes(include=[float]).columns:
        table[col] = table[col].map(lambda value: f"{value:.3f}")
    lines = ["| " + " | ".join(table.columns) + " |", "| " + " | ".join(["---"] * len(table.columns)) + " |"]
    for row in table.itertuples(index=False):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def build_report(summary: pd.DataFrame, dwl: pd.DataFrame) -> str:
    high_risk = summary.sort_values("attention_risk_score", ascending=False)
    gva = summary.sort_values("attention_gva_shift_bn_rub")
    content = rf"""# Attention Monopoly Scenario

Сценарий описывает перераспределение капитала и ВДС, когда единый AI-ассистент становится основной поверхностью доступа к пользователю.

## 1. Формализация

Для отрасли \(s\):

\[
D_s \\in [0,1] \\quad \\text{{attention dependency}},
\\qquad
I_s \\in [0,1] \\quad \\text{{platform integration capacity}},
\\qquad
m_s \\quad \\text{{platform markup}}.
\]

Композитный риск:

\[
R_s = 100\\left(
w_D D_s + w_I(1-I_s) + w_m \\frac{{m_s}}{{\\max_j m_j}} + w_E E_s + w_A A_s(2035)
\\right).
\]

Сдвиг ВДС:

\[
\\Delta VA_s^{{att}} =
VA_s \\bar A D_s I_s c_s \\rho
- VA_s \\bar A D_s m_s (1-I_s) \\frac{{1+E_s}}{{2}}
+ \\mathbf{{1}}_{{s \\in platform}}\\Omega,
\]

где \(E_s\) — vulnerable SME share, \(c_s\) — CAC saving midpoint, \(\bar A=0.4\) — base saturation доля AI-интерфейса, \(\rho=0.5\) — retained CAC saving, \(\Omega\) — доля платформенной ренты, направленная в IT/platform sector.

## 2. Highest Risk Sectors

{markdown_table(
    high_risk,
    [
        "sector_id",
        "sector_name_ru",
        "attention_dependency",
        "integration_capacity",
        "platform_markup_mid",
        "vulnerable_sme_share",
        "attention_risk_score",
    ],
)}

## 3. Net GVA Shift

{markdown_table(
    gva,
    [
        "sector_id",
        "sector_name_ru",
        "platform_access_fee_bn_rub",
        "cac_saving_va_gain_bn_rub",
        "attention_gva_shift_bn_rub",
        "capital_reallocation_pressure_bn_rub",
    ],
)}

## 4. Deadweight Loss

{markdown_table(
    dwl.sort_values("deadweight_loss_bn_rub", ascending=False),
    ["sector_id", "sector_name_ru", "platform_markup_mid", "attention_dependency", "deadweight_loss_bn_rub"],
)}

## 5. Artifacts

- `output/attention_monopoly_risk_gradient.png`
- `output/attention_monopoly_gva_shift.png`
- `output/attention_abm_dynamics.png`
- `output/attention_deadweight_loss.png`
- `data/benchmarks_attention_monopoly.csv`
- `data/processed/attention_monopoly_sector_summary.csv`
"""
    return content.replace("\\\\", "\\")


def main() -> None:
    configure_style()
    config = load_config()
    inputs = load_model_inputs(config)
    benchmarks = build_benchmarks(config, inputs)
    summary = build_attention_sector_summary(inputs, benchmarks, config)
    abm = bass_path(config)
    dwl = build_deadweight_loss(summary, config)

    BENCHMARKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    benchmarks.to_csv(BENCHMARKS_PATH, index=False)
    summary.to_csv(SUMMARY_PATH, index=False)
    abm.to_csv(ABM_PATH, index=False)
    dwl.to_csv(DWL_PATH, index=False)
    REPORT_PATH.write_text(build_report(summary, dwl), encoding="utf-8")

    plot_risk_gradient(summary, config)
    plot_gva_shift(summary)
    plot_abm(abm)
    plot_deadweight_loss(dwl)

    print(f"Saved: {BENCHMARKS_PATH.relative_to(ROOT)}")
    print(f"Saved: {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Saved: {ABM_PATH.relative_to(ROOT)}")
    print(f"Saved: {DWL_PATH.relative_to(ROOT)}")
    print(f"Saved: {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

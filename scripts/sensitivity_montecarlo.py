from __future__ import annotations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from build_ai_diffusion_model import CONFIG_PATH as DIFFUSION_CONFIG_PATH
from build_ai_diffusion_model import load_json as load_diffusion_json
from build_russia_economy_structure import CONFIG_PATH as STRUCTURE_CONFIG_PATH
from build_russia_economy_structure import build_structure_paths
from build_russia_economy_structure import load_json as load_structure_json
from build_russia_economy_structure import prepare_base


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "processed" / "sensitivity_fan_outputs.csv"
OUTPUT_FIGURE = ROOT / "output" / "figures" / "russia_economy_structure" / "sensitivity_fan_charts.png"
OUTPUT_REPORT = ROOT / "docs" / "russia_economy_structure_report.md"
N_DRAWS = 5000
SEED = 20260430
BASE_SCENARIO = "Base"
BASE_THROTTLE = "BaseThrottle"


PRIOR_SPEC = {
    "eta": {
        "software": {
            "va_log_boost_per_adoption": {"mean": 0.14, "sd": 0.03, "lower": 0.08, "upper": 0.22},
            "lp_log_boost_per_adoption": {"mean": 0.22, "sd": 0.05, "lower": 0.12, "upper": 0.35},
        },
        "hybrid": {
            "va_log_boost_per_adoption": {"mean": 0.08, "sd": 0.02, "lower": 0.03, "upper": 0.15},
            "lp_log_boost_per_adoption": {"mean": 0.14, "sd": 0.03, "lower": 0.06, "upper": 0.24},
        },
        "hardware": {
            "va_log_boost_per_adoption": {"mean": 0.04, "sd": 0.015, "lower": 0.00, "upper": 0.09},
            "lp_log_boost_per_adoption": {"mean": 0.09, "sd": 0.025, "lower": 0.02, "upper": 0.18},
        },
    },
    "rho": {"alpha": 6.0, "beta": 14.0},
    "pq_logn_sd": {"p": 0.35, "q": 0.25},
    "pq_bounds_multiplier": {
        "p": {"lower": 0.25, "upper": 2.50},
        "q": {"lower": 0.50, "upper": 2.00},
    },
}


def truncated_normal(rng: np.random.Generator, mean: float, sd: float, lower: float, upper: float) -> float:
    draw = rng.normal(mean, sd)
    return float(np.clip(draw, lower, upper))


def draw_eta_parameters(rng: np.random.Generator) -> dict:
    eta_params: dict[str, dict[str, float]] = {}
    for class_id, class_spec in PRIOR_SPEC["eta"].items():
        eta_params[class_id] = {}
        for name, spec in class_spec.items():
            eta_params[class_id][name] = truncated_normal(rng, spec["mean"], spec["sd"], spec["lower"], spec["upper"])
    return eta_params


def aggregate_paths(paths: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        paths.groupby(["scenario", "throttle_scenario", "year"], as_index=False)
        .agg(
            total_va_cf_bn_rub=("va_cf_bn_rub", "sum"),
            total_va_ai_bn_rub=("va_ai_bn_rub", "sum"),
            total_profit_pool_cf_bn_rub=("profit_pool_cf_bn_rub", "sum"),
            total_profit_pool_ai_bn_rub=("profit_pool_ai_bn_rub", "sum"),
            total_employment_cf_thousand=("employment_cf_thousand", "sum"),
            total_employment_ai_thousand=("employment_ai_thousand", "sum"),
        )
        .sort_values(["scenario", "throttle_scenario", "year"])
        .reset_index(drop=True)
    )
    grouped["total_va_gain_pct"] = (grouped["total_va_ai_bn_rub"] / grouped["total_va_cf_bn_rub"] - 1.0) * 100.0
    grouped["total_profit_pool_gain_pct"] = (
        grouped["total_profit_pool_ai_bn_rub"] / grouped["total_profit_pool_cf_bn_rub"] - 1.0
    ) * 100.0
    grouped["total_employment_delta_thousand"] = (
        grouped["total_employment_ai_thousand"] - grouped["total_employment_cf_thousand"]
    )
    return grouped


def deterministic_baseline(structure_config: dict) -> pd.DataFrame:
    paths = build_structure_paths(structure_config)
    aggregate = aggregate_paths(paths)
    return aggregate.loc[
        aggregate["scenario"].eq(BASE_SCENARIO) & aggregate["throttle_scenario"].eq(BASE_THROTTLE)
    ].reset_index(drop=True)


def prepare_simulation_inputs(structure_config: dict, diffusion_config: dict) -> dict:
    base = prepare_base(structure_config)
    base = base.loc[base["scenario"].eq(BASE_SCENARIO)].copy()
    years = np.arange(structure_config["projection_start_year"], structure_config["projection_end_year"] + 1)
    sector_meta = (
        base.sort_values(["sector_id", "year"])
        .groupby("sector_id", as_index=False)
        .first()[
            [
                "sector_id",
                "class_id",
                "va_current_bn_rub",
                "employment_thousand_persons",
                "va_cf_growth_rate_annual",
                "employment_cf_growth_rate_annual",
                "managed_obsolescence_pressure_score",
                "delta_sL_potential",
                "pi0_proxy",
                "gamma_margin",
                "lambda_speed",
            ]
        ]
    )

    class_to_idx = {class_id: idx for idx, class_id in enumerate(["software", "hybrid", "hardware"])}
    class_index = sector_meta["class_id"].map(class_to_idx).to_numpy(dtype=int)
    years_from_base = years - int(structure_config["baseline_year"])

    va_cf = sector_meta["va_current_bn_rub"].to_numpy()[:, None] * np.power(
        1.0 + sector_meta["va_cf_growth_rate_annual"].to_numpy()[:, None],
        years_from_base[None, :],
    )
    employment_cf = sector_meta["employment_thousand_persons"].to_numpy()[:, None] * np.power(
        1.0 + sector_meta["employment_cf_growth_rate_annual"].to_numpy()[:, None],
        years_from_base[None, :],
    )
    lp_cf = va_cf * 1000.0 / employment_cf

    class_params = diffusion_config["class_parameters"]
    p_anchor = sector_meta["class_id"].map(lambda class_id: class_params[class_id]["p"]).to_numpy(dtype=float)
    q_anchor = sector_meta["class_id"].map(lambda class_id: class_params[class_id]["q"]).to_numpy(dtype=float)

    return {
        "years": years,
        "class_index": class_index,
        "sector_meta": sector_meta,
        "va_cf": va_cf,
        "employment_cf": employment_cf,
        "lp_cf": lp_cf,
        "p_anchor": p_anchor,
        "q_anchor": q_anchor,
        "mos": sector_meta["managed_obsolescence_pressure_score"].fillna(0.0).to_numpy(dtype=float),
        "pi0_proxy": sector_meta["pi0_proxy"].to_numpy(dtype=float),
        "gamma_margin": sector_meta["gamma_margin"].to_numpy(dtype=float),
        "delta_sL_potential": sector_meta["delta_sL_potential"].to_numpy(dtype=float),
        "va_current": sector_meta["va_current_bn_rub"].to_numpy(dtype=float),
        "lambda_speed": sector_meta["lambda_speed"].to_numpy(dtype=float),
    }


def run_monte_carlo(n_draws: int = N_DRAWS, seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    diffusion_config = load_diffusion_json(DIFFUSION_CONFIG_PATH)
    structure_config = load_structure_json(STRUCTURE_CONFIG_PATH)
    deterministic = deterministic_baseline(structure_config)
    sim = prepare_simulation_inputs(structure_config, diffusion_config)

    n_sectors = len(sim["sector_meta"])
    n_years = len(sim["years"])
    p_mult_bounds = PRIOR_SPEC["pq_bounds_multiplier"]["p"]
    q_mult_bounds = PRIOR_SPEC["pq_bounds_multiplier"]["q"]
    p_sigma = float(PRIOR_SPEC["pq_logn_sd"]["p"])
    q_sigma = float(PRIOR_SPEC["pq_logn_sd"]["q"])

    metric_store = {
        "aggregate_va_ai_bn_rub": np.empty((n_draws, n_years), dtype=float),
        "aggregate_profit_pool_ai_bn_rub": np.empty((n_draws, n_years), dtype=float),
        "aggregate_employment_delta_thousand": np.empty((n_draws, n_years), dtype=float),
        "aggregate_va_gain_pct": np.empty((n_draws, n_years), dtype=float),
        "aggregate_profit_pool_gain_pct": np.empty((n_draws, n_years), dtype=float),
    }
    rho_draws = np.empty(n_draws, dtype=float)

    total_va_cf = sim["va_cf"].sum(axis=0)
    total_profit_cf = np.empty(n_years, dtype=float)
    total_employment_cf = sim["employment_cf"].sum(axis=0)

    margin_cf_prev = sim["pi0_proxy"].copy()
    for year_idx in range(n_years):
        margin_cf_t = sim["pi0_proxy"] - sim["lambda_speed"] * margin_cf_prev
        total_profit_cf[year_idx] = np.sum(margin_cf_t * sim["va_cf"][:, year_idx])
        margin_cf_prev = margin_cf_t

    for draw_id in range(n_draws):
        eta_draw = draw_eta_parameters(rng)
        eta_va_by_class = np.array(
            [
                eta_draw["software"]["va_log_boost_per_adoption"],
                eta_draw["hybrid"]["va_log_boost_per_adoption"],
                eta_draw["hardware"]["va_log_boost_per_adoption"],
            ],
            dtype=float,
        )
        eta_lp_by_class = np.array(
            [
                eta_draw["software"]["lp_log_boost_per_adoption"],
                eta_draw["hybrid"]["lp_log_boost_per_adoption"],
                eta_draw["hardware"]["lp_log_boost_per_adoption"],
            ],
            dtype=float,
        )
        eta_va = eta_va_by_class[sim["class_index"]]
        eta_lp = eta_lp_by_class[sim["class_index"]]
        rho_draw = float(rng.beta(PRIOR_SPEC["rho"]["alpha"], PRIOR_SPEC["rho"]["beta"]))
        rho_draws[draw_id] = rho_draw

        p_mult = np.clip(rng.lognormal(mean=0.0, sigma=p_sigma, size=n_sectors), p_mult_bounds["lower"], p_mult_bounds["upper"])
        q_mult = np.clip(rng.lognormal(mean=0.0, sigma=q_sigma, size=n_sectors), q_mult_bounds["lower"], q_mult_bounds["upper"])
        p_draw = sim["p_anchor"] * p_mult
        q_draw = sim["q_anchor"] * q_mult

        adaptation_prev = np.zeros(n_sectors, dtype=float)
        margin_prev = sim["pi0_proxy"].copy()
        cumulative_log_va = np.zeros(n_sectors, dtype=float)
        cumulative_log_lp = np.zeros(n_sectors, dtype=float)
        managed_factor = np.clip(1.0 - rho_draw * sim["mos"], 0.0, 1.0)

        for year_idx in range(n_years):
            diffusion_speed = (p_draw + q_draw * adaptation_prev) * (1.0 - adaptation_prev)
            adaptation = np.clip(adaptation_prev + diffusion_speed, 0.0, 1.0)
            adaptation_managed = adaptation * managed_factor
            diffusion_speed_managed = diffusion_speed * managed_factor
            margin_ai = np.clip(sim["pi0_proxy"] + sim["gamma_margin"] * adaptation_managed - sim["lambda_speed"] * margin_prev, 0.0, 1.0)

            cumulative_log_va += diffusion_speed_managed * eta_va
            cumulative_log_lp += diffusion_speed_managed * eta_lp

            va_ai = sim["va_cf"][:, year_idx] * np.exp(cumulative_log_va)
            lp_ai = sim["lp_cf"][:, year_idx] * np.exp(cumulative_log_lp)
            employment_ai = va_ai * 1000.0 / lp_ai
            profit_ai = margin_ai * va_ai

            metric_store["aggregate_va_ai_bn_rub"][draw_id, year_idx] = np.sum(va_ai)
            metric_store["aggregate_profit_pool_ai_bn_rub"][draw_id, year_idx] = np.sum(profit_ai)
            metric_store["aggregate_employment_delta_thousand"][draw_id, year_idx] = np.sum(employment_ai) - total_employment_cf[year_idx]
            metric_store["aggregate_va_gain_pct"][draw_id, year_idx] = (
                metric_store["aggregate_va_ai_bn_rub"][draw_id, year_idx] / total_va_cf[year_idx] - 1.0
            ) * 100.0
            metric_store["aggregate_profit_pool_gain_pct"][draw_id, year_idx] = (
                metric_store["aggregate_profit_pool_ai_bn_rub"][draw_id, year_idx] / total_profit_cf[year_idx] - 1.0
            ) * 100.0

            adaptation_prev = adaptation
            margin_prev = margin_ai

    rows: list[dict] = []
    for metric, values in metric_store.items():
        base_column = {
            "aggregate_va_ai_bn_rub": "total_va_ai_bn_rub",
            "aggregate_profit_pool_ai_bn_rub": "total_profit_pool_ai_bn_rub",
            "aggregate_employment_delta_thousand": "total_employment_delta_thousand",
            "aggregate_va_gain_pct": "total_va_gain_pct",
            "aggregate_profit_pool_gain_pct": "total_profit_pool_gain_pct",
        }[metric]
        for year_idx, year in enumerate(sim["years"]):
            det_year = deterministic.loc[deterministic["year"].eq(year)].iloc[0]
            year_values = values[:, year_idx]
            rows.append(
                {
                    "metric": metric,
                    "year": int(year),
                    "p10": float(np.quantile(year_values, 0.10)),
                    "p50": float(np.quantile(year_values, 0.50)),
                    "p90": float(np.quantile(year_values, 0.90)),
                    "mean": float(np.mean(year_values)),
                    "base": float(det_year[base_column]),
                    "n_draws": int(n_draws),
                }
            )

    fan = pd.DataFrame(rows).sort_values(["metric", "year"]).reset_index(drop=True)
    rho_frame = pd.DataFrame({"draw_id": np.arange(1, n_draws + 1), "rho_draw": rho_draws})
    return fan, rho_frame


def plot_fan(fan: pd.DataFrame) -> None:
    OUTPUT_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    plot_specs = [
        ("aggregate_va_ai_bn_rub", "Aggregate VA, bn RUB (2024 basis)", "#1D4ED8"),
        ("aggregate_profit_pool_ai_bn_rub", "Profit pool, bn RUB (2024 basis)", "#B45309"),
        ("aggregate_employment_delta_thousand", "Employment delta, thousand persons", "#047857"),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(9.5, 10.5), sharex=True)
    years = None
    for ax, (metric, title, color) in zip(axes, plot_specs):
        subset = fan.loc[fan["metric"].eq(metric)].sort_values("year")
        years = subset["year"].to_numpy()
        ax.fill_between(years, subset["p10"], subset["p90"], color=color, alpha=0.18, label="p10-p90")
        ax.plot(years, subset["p50"], color=color, linewidth=2.2, label="p50")
        ax.plot(years, subset["base"], color="#111827", linewidth=1.4, linestyle="--", label="deterministic base")
        ax.set_title(title, fontsize=11)
        ax.grid(alpha=0.25, linewidth=0.6)
        ax.legend(frameon=False, fontsize=8, loc="best")

    axes[-1].set_xlabel("Year")
    fig.suptitle("Sensitivity fan charts: Base diffusion with uncertain eta, rho, p, q", fontsize=13, y=0.995)
    fig.tight_layout()
    fig.savefig(OUTPUT_FIGURE, dpi=180, bbox_inches="tight")
    plt.close(fig)


def prior_table_markdown() -> str:
    rows = [
        {
            "parameter": r"$\eta^{VA}_{software}$",
            "distribution": "trunc. normal",
            "hyperparameters": "mean=0.14, sd=0.03, [0.08, 0.22]",
        },
        {
            "parameter": r"$\eta^{LP}_{software}$",
            "distribution": "trunc. normal",
            "hyperparameters": "mean=0.22, sd=0.05, [0.12, 0.35]",
        },
        {
            "parameter": r"$\eta^{VA}_{hybrid}$",
            "distribution": "trunc. normal",
            "hyperparameters": "mean=0.08, sd=0.02, [0.03, 0.15]",
        },
        {
            "parameter": r"$\eta^{LP}_{hybrid}$",
            "distribution": "trunc. normal",
            "hyperparameters": "mean=0.14, sd=0.03, [0.06, 0.24]",
        },
        {
            "parameter": r"$\eta^{VA}_{hardware}$",
            "distribution": "trunc. normal",
            "hyperparameters": "mean=0.04, sd=0.015, [0.00, 0.09]",
        },
        {
            "parameter": r"$\eta^{LP}_{hardware}$",
            "distribution": "trunc. normal",
            "hyperparameters": "mean=0.09, sd=0.025, [0.02, 0.18]",
        },
        {
            "parameter": r"$\rho$",
            "distribution": "beta",
            "hyperparameters": "alpha=6, beta=14, mean=0.30",
        },
        {
            "parameter": r"$p_s$",
            "distribution": "lognormal multiplier on class anchor",
            "hyperparameters": "sigma=0.35, clip=[0.25x, 2.50x]",
        },
        {
            "parameter": r"$q_s$",
            "distribution": "lognormal multiplier on class anchor",
            "hyperparameters": "sigma=0.25, clip=[0.50x, 2.00x]",
        },
    ]
    header = "| parameter | distribution | hyperparameters |\n| --- | --- | --- |"
    body = "\n".join(f"| {row['parameter']} | {row['distribution']} | {row['hyperparameters']} |" for row in rows)
    return f"{header}\n{body}"


def percentile_table_markdown(fan: pd.DataFrame) -> str:
    metrics = [
        ("aggregate_va_gain_pct", "VA gain, %"),
        ("aggregate_profit_pool_gain_pct", "Profit pool gain, %"),
        ("aggregate_employment_delta_thousand", "Employment delta, thousand"),
    ]
    header = "| metric | p10 | p50 | p90 | deterministic base |\n| --- | --- | --- | --- | --- |"
    rows: list[str] = []
    for metric, label in metrics:
        row = fan.loc[(fan["metric"].eq(metric)) & (fan["year"].eq(2035))].iloc[0]
        rows.append(
            f"| {label} | {row['p10']:.3f} | {row['p50']:.3f} | {row['p90']:.3f} | {row['base']:.3f} |"
        )
    return f"{header}\n" + "\n".join(rows)


def build_sensitivity_section(fan: pd.DataFrame) -> str:
    va_2035 = fan.loc[(fan["metric"].eq("aggregate_va_gain_pct")) & (fan["year"].eq(2035))].iloc[0]
    profit_2035 = fan.loc[(fan["metric"].eq("aggregate_profit_pool_gain_pct")) & (fan["year"].eq(2035))].iloc[0]
    employment_2035 = fan.loc[
        (fan["metric"].eq("aggregate_employment_delta_thousand")) & (fan["year"].eq(2035))
    ].iloc[0]

    return f"""

## 9. Sensitivity

Формально считаем неопределенность по вектору параметров

$$
\\theta = \\left(\\{{\\eta^{{VA}}_c, \\eta^{{LP}}_c\\}}_{{c \\in \\{{software, hybrid, hardware\\}}}}, \\rho, \\{{p_s, q_s\\}}_s\\right),
$$

и оцениваем распределение агрегированных исходов

$$
Y_t(\\theta) = \\left(VA^{{AI}}_t, \\Pi^{{AI}}_t, L^{{AI}}_t - L^{{cf}}_t\\right)
$$

через Monte Carlo с `N={N_DRAWS}` draws и `seed={SEED}`.

### Priors

{prior_table_markdown()}

### 2035 percentile outcomes

{percentile_table_markdown(fan)}

Медианный исход к `2035` близок к deterministic base, но интервалы уже заметно шире headline-чисел: `VA gain` лежит в диапазоне `[{va_2035["p10"]:.2f}; {va_2035["p90"]:.2f}]%`, `profit pool gain` — `[{profit_2035["p10"]:.2f}; {profit_2035["p90"]:.2f}]%`, а `employment delta` — `[{employment_2035["p10"]:.0f}; {employment_2035["p90"]:.0f}]` тыс. человек.

### Fan charts

![Sensitivity fan charts]({OUTPUT_FIGURE})
"""


def update_report(fan: pd.DataFrame) -> None:
    report = OUTPUT_REPORT.read_text(encoding="utf-8")
    marker = "\n## 9. Sensitivity\n"
    if marker in report:
        report = report.split(marker, 1)[0].rstrip() + "\n"
    report = report.rstrip() + build_sensitivity_section(fan)
    OUTPUT_REPORT.write_text(report.rstrip() + "\n", encoding="utf-8")


def write_outputs(fan: pd.DataFrame) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fan.to_csv(OUTPUT_PATH, index=False)
    plot_fan(fan)
    update_report(fan)


def main() -> None:
    fan, _ = run_monte_carlo()
    write_outputs(fan)
    print(f"Saved sensitivity outputs: {OUTPUT_PATH}")
    print(f"Saved sensitivity figure: {OUTPUT_FIGURE}")
    print(f"Updated report: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STAGE_MAP = {
    "stage1": [
        "build_staffing_matrix.py",
        "build_historical_panel.py",
        "screen_historical_benchmarks.py",
        "calculate_task_content.py",
    ],
    "stage2": [
        "build_russia_ai_scenarios.py",
        "build_russia_sector_panel.py",
        "build_cmach_share_proxy.py",
        "build_russia_ai_summary_report.py",
        "build_ai_diffusion_model.py",
        "build_ai_capital_returns.py",
    ],
    "managed_obsolescence": [
        "build_managed_obsolescence_layer.py",
        "import_friction_layer.py",
        "generate_managed_obsolescence_figures.py",
    ],
    "structure": [
        "import_friction_layer.py",
        "build_russia_economy_structure.py",
        "sensitivity_montecarlo.py",
        "io_leontief_propagation.py",
        "welfare_distributional.py",
    ],
    "attention_monopoly": [
        "scenario_runner.py --scenario attention_monopoly",
    ],
}
STAGE_MAP["all"] = (
    STAGE_MAP["stage1"]
    + STAGE_MAP["stage2"]
    + STAGE_MAP["managed_obsolescence"]
    + STAGE_MAP["structure"]
    + STAGE_MAP["attention_monopoly"]
)


def run_script(script_name: str) -> None:
    parts = script_name.split()
    script_path = ROOT / "scripts" / parts[0]
    print(f"[run_pipeline] running {script_name}", flush=True)
    subprocess.run([sys.executable, str(script_path), *parts[1:]], check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI vs economy pipeline.")
    parser.add_argument("--stage", choices=sorted(STAGE_MAP.keys()), default="all")
    args = parser.parse_args()

    for script_name in STAGE_MAP[args.stage]:
        run_script(script_name)


if __name__ == "__main__":
    main()

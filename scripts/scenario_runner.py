from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCENARIOS = {
    "attention_monopoly": ["io_klems_attention.py"],
}


def run_script(script_name: str) -> None:
    script_path = ROOT / "scripts" / script_name
    print(f"[scenario_runner] running {script_name}", flush=True)
    subprocess.run([sys.executable, str(script_path)], check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scenario-specific model blocks.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    args = parser.parse_args()

    for script_name in SCENARIOS[args.scenario]:
        run_script(script_name)


if __name__ == "__main__":
    main()

from __future__ import annotations

from io_klems_attention import (
    CONFIG_PATH,
    DWL_PATH,
    SUMMARY_PATH,
    build_deadweight_loss,
    load_config,
)

import pandas as pd


def main() -> None:
    config = load_config(CONFIG_PATH)
    summary = pd.read_csv(SUMMARY_PATH)
    dwl = build_deadweight_loss(summary, config)
    dwl.to_csv(DWL_PATH, index=False)
    print(f"Saved intention-market DWL: {DWL_PATH}")


if __name__ == "__main__":
    main()

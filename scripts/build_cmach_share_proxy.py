from __future__ import annotations

from pathlib import Path

import pandas as pd

from build_russia_sector_panel import CONFIG_PATH, build_panel, load_json


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "processed" / "cmach_share_proxy.csv"


def build_cmach_share_proxy() -> pd.DataFrame:
    """Compute the OKVED 26-30 share in aggregate manufacturing VA."""
    config = load_json(CONFIG_PATH)
    panel, _, _ = build_panel(config)
    c = panel.loc[panel["sector_id"].eq("C"), ["year", "va_current_bn_rub"]].rename(
        columns={"va_current_bn_rub": "c_residual_va_bln_rub"}
    )
    cmach = panel.loc[panel["sector_id"].eq("C_mach"), ["year", "va_current_bn_rub"]].rename(
        columns={"va_current_bn_rub": "cmach_va_bln_rub"}
    )
    proxy = cmach.merge(c, on="year", how="inner")
    proxy["manufacturing_total_va_bln_rub"] = proxy["cmach_va_bln_rub"] + proxy["c_residual_va_bln_rub"]
    proxy["cmach_share"] = proxy["cmach_va_bln_rub"] / proxy["manufacturing_total_va_bln_rub"]
    proxy["source"] = "Rosstat_VDS_OKVED2_26_30_share"
    return proxy[
        [
            "year",
            "cmach_share",
            "cmach_va_bln_rub",
            "manufacturing_total_va_bln_rub",
            "source",
        ]
    ].sort_values("year").reset_index(drop=True)


def main() -> None:
    proxy = build_cmach_share_proxy()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    proxy.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved C_mach share proxy: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

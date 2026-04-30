# Reproducibility Guide

## Environment

- Python `3.13`
- packages from `requirements.txt`

## Quick start

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_pipeline.py --stage all
```

## Stage-by-stage

### Stage 1

```bash
python3 scripts/run_pipeline.py --stage stage1
```

### Stage 2

```bash
python3 scripts/run_pipeline.py --stage stage2
```

### Managed obsolescence

```bash
python3 scripts/run_pipeline.py --stage managed_obsolescence
```

### Economy structure

```bash
python3 scripts/run_pipeline.py --stage structure
```

## Manual script order

```bash
python3 scripts/build_staffing_matrix.py
python3 scripts/build_historical_panel.py
python3 scripts/screen_historical_benchmarks.py
python3 scripts/calculate_task_content.py
python3 scripts/build_russia_ai_scenarios.py
python3 scripts/build_russia_sector_panel.py
python3 scripts/build_russia_ai_summary_report.py
python3 scripts/build_ai_diffusion_model.py
python3 scripts/build_ai_capital_returns.py
python3 scripts/build_managed_obsolescence_layer.py
python3 scripts/generate_managed_obsolescence_figures.py
python3 scripts/build_russia_economy_structure.py
```

## Notes

- Raw sources already лежат в `data/raw/`, поэтому повторный запуск не должен зависеть от повторной загрузки нестабильных источников.
- `data/interim/` не версионируется.
- Основные результаты и итоговые таблицы лежат в `data/processed/`.

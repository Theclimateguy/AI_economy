# Data Catalog

## Источники

### Historical comparator data

| Source | Folder | What it provides |
|---|---|---|
| `EU KLEMS` | `data/raw/eu_klems/` | `VA`, labour share, capital, ICT-capital shares, `K/L` |
| `OECD STAN` | `data/raw/oecd/` | output, `VA`, compensation, taxes, operating surplus, capital stocks |
| `ILOSTAT` | `data/raw/ilostat/` | historical staffing matrix for `industry × occupation` |
| `Lewandowski RTI` | `data/raw/rti/` | occupation-level routine task intensity |

### Russia data

| Source | Folder | What it provides |
|---|---|---|
| `Rosstat official XLS/XLSX` | `data/raw/russia/` | `VA`, real indices, employment, wages |

## Processed outputs by experiment

## Stage 1

- Historical panel:
  - `data/processed/historical_sector_panel_1985_2005.csv`
  - `data/processed/historical_sector_coverage_1985_2005.csv`
  - `data/processed/panel_metadata.json`
- Econometric screening:
  - `data/processed/historical_benchmark_screen_summary.csv`
  - `data/processed/historical_benchmark_screen_specs.csv`
  - `data/processed/historical_benchmark_screen_terms.csv`
  - `data/processed/historical_benchmark_screen_loo.csv`
- Task content:
  - `data/processed/task_content_annual_changes_1995_2005.csv`
  - `data/processed/task_content_longdiff_1995_2005.csv`
  - `data/processed/task_content_sector_benchmarks_1995_2005.csv`

## Stage 2

- Russia baseline:
  - `data/processed/russia_sector_panel_official_2011_2025.csv`
  - `data/processed/russia_sector_baseline_2024.csv`
- Scenario layer:
  - `data/processed/russia_ai_sector_scenarios.csv`
  - `data/processed/russia_ai_sector_impact_summary_2024.csv`
- Diffusion:
  - `data/processed/ai_diffusion_paths_2025_2035.csv`
  - `data/processed/ai_diffusion_sector_summary.csv`
  - `data/processed/ai_diffusion_class_summary.csv`
  - `data/processed/ai_diffusion_calibration_diagnostics.csv`
- Capital returns:
  - `data/processed/ai_capital_return_paths_2025_2035.csv`
  - `data/processed/ai_capital_return_sector_summary.csv`
  - `data/processed/ai_capital_return_class_summary.csv`

## Смысл разделения raw / processed

- `raw` хранит конкретные скачанные файлы источников;
- `processed` хранит аналитические таблицы, на которых строятся отчеты;
- `interim` используется только для промежуточных шагов и не версионируется.

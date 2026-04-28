# Data Layout

Весь data-layer вынесен в папку `data/`.

## Структура

- `data/raw/`
  Скачанные исходные файлы из `EU KLEMS`, `OECD STAN`, `ILOSTAT`, `Lewandowski RTI`, `Rosstat`.
- `data/interim/`
  Временные промежуточные артефакты. Эта папка не версионируется.
- `data/processed/`
  Воспроизводимые итоговые таблицы, на которых строятся отчеты и сценарии.

## Raw

Основные подкаталоги:

- `data/raw/eu_klems/`
- `data/raw/oecd/`
- `data/raw/ilostat/`
- `data/raw/rti/`
- `data/raw/russia/`
- `data/raw/russia_klems/`
- `data/raw/world_tech/`

## Processed

Ключевые группы файлов:

- Historical panel and screening:
  - `historical_sector_panel_1985_2005.csv`
  - `historical_sector_coverage_1985_2005.csv`
  - `historical_benchmark_screen_*.csv`
- Task-content benchmarks:
  - `task_content_annual_changes_1995_2005.csv`
  - `task_content_longdiff_1995_2005.csv`
  - `task_content_sector_benchmarks_1995_2005.csv`
- Russia baseline and scenarios:
  - `russia_sector_panel_official_2011_2025.csv`
  - `russia_sector_baseline_2024.csv`
  - `russia_ai_sector_scenarios.csv`
  - `russia_ai_sector_impact_summary_2024.csv`
- Diffusion and capital returns:
  - `ai_diffusion_paths_2025_2035.csv`
  - `ai_diffusion_sector_summary.csv`
  - `ai_capital_return_paths_2025_2035.csv`
  - `ai_capital_return_sector_summary.csv`
- Managed obsolescence:
  - `russia_klems_sector_panel_1995_2016.csv`
  - `managed_obsolescence_sector_proxy.csv`
  - `russia_klems_metadata.json`
  - `world_technology_diffusion_benchmarks.csv`

## Принцип воспроизводимости

В repo лежат не только скрипты, но и raw/processed артефакты. Это нужно, чтобы:

- можно было сразу воспроизвести все отчеты;
- можно было проверить результаты без повторной загрузки нестабильных источников;
- можно было отследить точный state данных, на котором считались выводы.

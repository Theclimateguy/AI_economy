# AI Economy

Эмпирический research repo по анализу влияния ИИ на отрасли экономики РФ.

## Что внутри

Репозиторий собран как воспроизводимый пакет из двух этапов.

### Этап 1. Проверка гипотез инвариантов

- historical comparator panel на `EU KLEMS + OECD STAN`
- staffing-matrix RTI
- строгий screening инвариантов
- переход от невыживших regression betas к historical `ΔTC`

### Этап 2. Диффузия, адаптация и капитальная отдача

- официальный baseline РФ по секторам
- sector-level AI shocks
- Bass-type diffusion by adoption class
- margin dynamics
- capital need и capital-return functions

## Структура

```text
.
├── config/     # параметры моделей и источников
├── data/       # raw / interim / processed
├── docs/       # постановка, методология, эксперименты, результаты
├── scripts/    # reproducible pipeline
└── README.md
```

Подробный индекс документов: [docs/index.md](docs/index.md)

## Быстрый запуск

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_pipeline.py --stage all
```

Поэтапный запуск:

```bash
python3 scripts/run_pipeline.py --stage stage1
python3 scripts/run_pipeline.py --stage stage2
```

## Ключевые документы

- [Research Pack](docs/research_pack.md)
- [Problem Statement](docs/problem_statement.md)
- [Data Catalog](docs/data_catalog.md)
- [Stage 1: Invariants Screening](docs/stage1_invariants.md)
- [Stage 2: Diffusion, Adaptation, Capital Returns](docs/stage2_diffusion_and_returns.md)
- [Reproducibility Guide](docs/reproducibility.md)

## Ключевые результаты

### Stage 1

- строгий screening не дал surviving full invariants;
- выжил только механизм эрозии маржи;
- поэтому forecasting layer был переведен на scenario calibration через historical `ΔTC`.

### Stage 2

- `software`-класс показывает режим `high adoption / low capex / high return`;
- `hardware`-класс показывает режим `low adoption / high capex / late or absent payback`;
- `hybrid`-класс занимает промежуточное положение.

## Основные артефакты

- Historical panel:
  - `data/processed/historical_sector_panel_1985_2005.csv`
- Russia baseline:
  - `data/processed/russia_sector_baseline_2024.csv`
- Diffusion:
  - `data/processed/ai_diffusion_paths_2025_2035.csv`
- Capital returns:
  - `data/processed/ai_capital_return_sector_summary.csv`

## Notes

- `data/raw/` и `data/processed/` сохранены в repo для полной воспроизводимости текущего состояния анализа.
- `data/interim/` не версионируется.

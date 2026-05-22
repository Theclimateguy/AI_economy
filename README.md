# AI Economy

Эмпирический research repo по анализу влияния ИИ на отрасли экономики РФ.

## Итоговая аналитическая записка

Финальная аналитическая записка по проекту доступна в корне репозитория в двух форматах: [Markdown](./ai-economy-analytical-note.md) и [PDF](./ai-economy-analytical-note.pdf). В ней консолидированы ключевые результаты, графики, таблицы, выводы и допущения по всем этапам анализа — от исторической проверки инвариантов и диффузии ИИ до межотраслевого закрытия и распределительного слоя.

## Что внутри

Репозиторий собран как воспроизводимый пакет из пяти этапов.

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

### Этап 3. Managed obsolescence / throttling

- Russia KLEMS ВШЭ как исторический мост для РФ, 1995-2016
- proxy давления на staged deployment: productivity-hours gap, capital-labour gap, ICT vs non-ICT capital services, employment contraction
- формализация разрыва между frontier AI capability и deployed capability

### Этап 4. Economy structure accounting

- перевод diffusion / margin / capital-return paths в `VA`, отраслевые доли, profit pool, labour income, занятость и `VA/L`
- managed adoption через `A_managed = A * (1 - rho * MOS)`
- sector winners/losers по доле экономики, прибыли и производительности труда

### Этап 5. AI-монополия внимания

- сценарный слой, где единый AI-ассистент концентрирует пользовательское внимание и намерения
- reduced-form KLEMS/I-O метрики `D`, `I`, `R`: зависимость от внимания, готовность к интеграции и композитный риск
- split торговли на `Торговля (еда)` и `Торговля (не еда)` внутри attention-layer
- PDF-отчет по сценарию с risk gradient, GVA shift, ABM dynamics и deadweight loss

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
python3 scripts/run_pipeline.py --stage managed_obsolescence
python3 scripts/run_pipeline.py --stage structure
python3 scripts/run_pipeline.py --stage attention_monopoly
```

## Ключевые документы

- [Research Pack](docs/research_pack.md)
- [Problem Statement](docs/problem_statement.md)
- [Data Catalog](docs/data_catalog.md)
- [Stage 1: Invariants Screening](docs/stage1_invariants.md)
- [Stage 2: Diffusion, Adaptation, Capital Returns](docs/stage2_diffusion_and_returns.md)
- [Managed Obsolescence Layer](docs/managed_obsolescence_layer.md)
- [Managed Obsolescence Figures](docs/managed_obsolescence_figures.md)
- [Russia Economy Structure Report](docs/russia_economy_structure_report.md)
- [Attention Monopoly Scenario](docs/attention_monopoly_scenario.md)
- [Attention Monopoly PDF](output/reports/attention_monopoly_scenario_report_ru.pdf)
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

### Stage 3

- `Russia KLEMS` добавлен как слой исторической калибровки для РФ;
- самый высокий proxy-score у `J`, но это weak proxy из-за NACE 1.0;
- среди чисто сопоставимых отраслей главный managed-obsolescence pressure показывает `C`.

### Stage 4

- в `Base / BaseThrottle` aggregate `VA` к 2035 выше контрфакта на `4.4%`;
- profit pool выше на `12.2%`, aggregate `VA/L` выше на `6.5%`;
- основные winners по доле экономики: `K`, `M`, `J`; главные relative share losers: `B`, `C`, `H`.

### Stage 5

- `Торговля (не еда)`, `Профессиональные услуги`, `ИТ и связь` и `Финансы` дают верхний кластер риска AI-монополии внимания;
- `Торговля (еда)` отделена от непродовольственной торговли как более низкая по discretionary search / comparison-shopping exposure;
- `Добыча`, `Обработка` и `Энергия и ЖКХ` сдвинуты вправо по оси digital-readiness deficit, но остаются ниже consumer-facing отраслей по attention dependency.

## Основные артефакты

- Historical panel:
  - `data/processed/historical_sector_panel_1985_2005.csv`
- Russia baseline:
  - `data/processed/russia_sector_baseline_2024.csv`
- Diffusion:
  - `data/processed/ai_diffusion_paths_2025_2035.csv`
- Capital returns:
  - `data/processed/ai_capital_return_sector_summary.csv`
- Managed obsolescence:
  - `data/processed/managed_obsolescence_sector_proxy.csv`
- Economy structure:
  - `data/processed/russia_economy_structure_sector_summary.csv`
- Attention monopoly:
  - `data/processed/attention_monopoly_sector_summary.csv`
  - `output/reports/attention_monopoly_scenario_report_ru.pdf`

## Notes

- `data/raw/` и `data/processed/` сохранены в repo для полной воспроизводимости текущего состояния анализа.
- `data/interim/` не версионируется.

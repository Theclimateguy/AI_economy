# Research Pack

## Что это

Этот репозиторий оформлен как воспроизводимый research pack по анализу влияния ИИ на отрасли экономики РФ. Логика работы разбита на четыре этапа:

1. строгая историческая проверка гипотез об инвариантах технологических революций;
2. структурная модель диффузии, адаптации и капитальной отдачи для РФ после отказа от неустойчивых универсальных бет;
3. политэкономический слой managed obsolescence, который переводит исторические механизмы controlled replacement / compatibility / repair restrictions в секторный throttling proxy для РФ.
4. итоговый accounting layer, который переводит прогнозы в `VA`, отраслевые доли, profit pool, labour income, занятость и производительность труда.

## Постановка задачи

Цель исследования:

- проверить, существуют ли переносимые между технологическими революциями отраслевые инварианты;
- если таких инвариантов нет, построить более честную сценарную рамку для РФ;
- получить воспроизводимые sector-level trajectories по labour share, марже, адаптации и капитальным затратам.
- получить финальную карту winners / losers по структуре экономики.

Объект анализа: 8 секторов `B`, `C`, `DE`, `F`, `H`, `J`, `K`, `M`.

Ядро второй стадии задается системой:

$$
\frac{dA_s}{dt} = (p_s + q_s A_s)(1 - A_s)
$$

$$
\Delta s^L_{s,t} = \Delta s^{L,potential}_s \cdot A_s(t)
$$

$$
\pi_{s,t} = \pi_{s,0} + \gamma_s A_s(t) - \lambda \pi_{s,t-1}
$$

где $\lambda = 0.04195$ взят из survived historical screening.

См. также: [problem_statement.md](problem_statement.md).

## Данные

В pack сохранены и raw, и processed данные.

### Historical block

- `EU KLEMS`: labour share, capital, ICT-capital, `K/L`
- `OECD STAN`: `VA`, output, compensation, taxes, surplus
- `ILOSTAT`: staffing matrix `industry × occupation`
- `Lewandowski RTI`: occupation-level routine task intensity

### Russia block

- official `Rosstat` files по `VA`, индексу физического объема, занятости, зарплатам
- `Russia KLEMS` ВШЭ по выпуску, труду, капиталу, производительности и TFP за 1995-2016

### Где лежат данные

- raw sources: [../data/raw/](../data/raw/)
- processed outputs: [../data/processed/](../data/processed/)
- каталог источников и файлов: [data_catalog.md](data_catalog.md)

## Этап 1. Проверка гипотез инвариантов

### Что тестировалось

- comparator panel `EU KLEMS + OECD STAN` по 8 секторам;
- RTI через staffing-matrix aggregation с base-year weights;
- FE-спецификации с жестким screening:
  - multiple specs;
  - BH-correction;
  - placebo lead;
  - leave-one-country-out stability.

### Главный результат

Полный screening дал честный результат:

- `0 surviving full invariants`;
- выжил только отдельный механизм эрозии маржи `lag_margin < 0`.

То есть данные не поддерживают идею универсальной исторической tech-beta, которую можно механически перенести на ИИ.

### Что было сделано после этого

После провала регрессионной стратегии модель была переопределена через исторические распределения смещения task content:

$$
\Delta TC_{c,s} = \Delta(wL/VA)_{c,s}
$$

Это стало источником scenario anchors для `Δs^L`.

### Основные артефакты этапа 1

- panel: [../data/processed/historical_sector_panel_1985_2005.csv](../data/processed/historical_sector_panel_1985_2005.csv)
- screening summary: [../data/processed/historical_benchmark_screen_summary.csv](../data/processed/historical_benchmark_screen_summary.csv)
- screening terms: [../data/processed/historical_benchmark_screen_terms.csv](../data/processed/historical_benchmark_screen_terms.csv)
- task-content benchmarks: [../data/processed/task_content_sector_benchmarks_1995_2005.csv](../data/processed/task_content_sector_benchmarks_1995_2005.csv)

Детально: [stage1_invariants.md](stage1_invariants.md).

## Этап 2. Диффузия, адаптация, капитальная отдача

### Что построено

- официальный sector baseline РФ;
- sector-level potential labour-share shocks на базе historical `ΔTC`;
- три adoption classes:
  - `software` = `J`, `K`, `M`
  - `hardware` = `B`, `F`, `H`
  - `hybrid` = `C`, `DE`
- Bass-type diffusion paths `2025–2035`;
- margin dynamics с adoption premium и historical erosion;
- capital need и capital return относительно контрфактической маржи без AI-premium.

### Ключевые результаты

#### Diffusion

В `Base` к `2035`:

- `software`: `A ≈ 0.876`
- `hybrid`: `A ≈ 0.330`
- `hardware`: `A ≈ 0.113`

То есть классы расходятся не marginally, а структурно.

#### Capital returns

В `Base` к `2035` class-level `net_return_cf`:

- `software ≈ 37.7`
- `hybrid ≈ 3.94`
- `hardware ≈ 1.36`

Во `Friction` hardware-class в целом не окупается до конца горизонта.

#### Sector ranking

Лучшие сектора по `Base net_return_cf_2035`:

- `M = 66.3`
- `K = 43.0`
- `J = 19.6`

Главные bottlenecks во `Friction`:

- `B`
- `DE`
- `H`

### Интерпретация

Итоговая секторная карта имеет три устойчивых режима:

- `software`: high adoption / low capex / high return;
- `hardware`: low adoption / high capex / late or absent payback;
- `hybrid`: medium adoption / medium capex / medium but uncertain return.

Это и есть итоговая прикладная рамка для подачи экзогенных shock paths в балансовую или CGE-модель.

### Основные артефакты этапа 2

- Russia baseline: [../data/processed/russia_sector_baseline_2024.csv](../data/processed/russia_sector_baseline_2024.csv)
- scenario layer: [../data/processed/russia_ai_sector_scenarios.csv](../data/processed/russia_ai_sector_scenarios.csv)
- diffusion paths: [../data/processed/ai_diffusion_paths_2025_2035.csv](../data/processed/ai_diffusion_paths_2025_2035.csv)
- diffusion summary: [../data/processed/ai_diffusion_sector_summary.csv](../data/processed/ai_diffusion_sector_summary.csv)
- capital returns: [../data/processed/ai_capital_return_sector_summary.csv](../data/processed/ai_capital_return_sector_summary.csv)

Детально: [stage2_diffusion_and_returns.md](stage2_diffusion_and_returns.md).

## Этап 3. Managed obsolescence and throttling

### Что добавлено

Новый слой формализует риск, что frontier AI capability будет внедряться не полностью:

$$
a_{s,t} = q_t A_{s,t}(1-\tau_{s,t})
$$

где $\tau_{s,t}$ отражает не только regulation, но и экономику replacement cycles, compatibility lock-in, repair/access restrictions и controlled release.

### Новый источник данных

Добавлен `Russia KLEMS` ВШЭ:

- raw: [../data/raw/russia_klems/RUS_december_2019_0.xlsx](../data/raw/russia_klems/RUS_december_2019_0.xlsx)
- panel: [../data/processed/russia_klems_sector_panel_1995_2016.csv](../data/processed/russia_klems_sector_panel_1995_2016.csv)
- proxy: [../data/processed/managed_obsolescence_sector_proxy.csv](../data/processed/managed_obsolescence_sector_proxy.csv)

### Первый результат

Рейтинг sector pressure score:

- `J`: 0.888, но weak proxy из-за старой NACE 1.0 telecom/post mapping;
- `C`: 0.543, чистый маппинг и центральный сектор для РФ;
- `M`: 0.431, высокий AI exposure, но broad proxy;
- `B`: 0.375, чистый маппинг, но нефтегазовая статистика требует caution.

Детально: [managed_obsolescence_layer.md](managed_obsolescence_layer.md).

Графический набор: [managed_obsolescence_figures.md](managed_obsolescence_figures.md).

## Этап 4. Economy structure accounting

### Что добавлено

Финальный слой замыкает предыдущие блоки в секторную accounting-модель:

$$
VA^{AI}_{s,t} = VA^{cf}_{s,t}
\exp\left(\sum_{\tau=2025}^{t}\eta^{VA}_{s}\Delta A^m_{s,\tau}\right)
$$

$$
LP^{AI}_{s,t} = LP^{cf}_{s,t}
\exp\left(\sum_{\tau=2025}^{t}\eta^{LP}_{s}\Delta A^m_{s,\tau}\right)
$$

$$
L^{AI}_{s,t}=\frac{VA^{AI}_{s,t}}{LP^{AI}_{s,t}},
\qquad
\Pi^{AI}_{s,t}=\pi^{AI}_{s,t}VA^{AI}_{s,t}.
$$

Managed adoption:

$$
A^m_{s,t}=A_{s,t}(1-\rho MOS_s)
$$

### Первый результат

В `Base / BaseThrottle` к `2035`:

- aggregate `VA` выше контрфакта на `4.4%`;
- aggregate profit pool выше на `12.2%`;
- aggregate labour productivity выше на `6.5%`;
- занятость ниже контрфакта примерно на `692` тыс. человек в восьми секторах;
- winners по доле экономики: `K`, `M`, `J`;
- relative share losers: `B`, `C`, `H`.

Основные артефакты:

- paths: [../data/processed/russia_economy_structure_paths_2025_2035.csv](../data/processed/russia_economy_structure_paths_2025_2035.csv)
- sector summary: [../data/processed/russia_economy_structure_sector_summary.csv](../data/processed/russia_economy_structure_sector_summary.csv)
- aggregate summary: [../data/processed/russia_economy_structure_aggregate_summary.csv](../data/processed/russia_economy_structure_aggregate_summary.csv)

Детально: [russia_economy_structure_report.md](russia_economy_structure_report.md).

## Воспроизводимость

Полный pipeline запускается так:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_pipeline.py --stage all
```

Пошаговый порядок, структура папок и замечания по данным описаны в:

- [reproducibility.md](reproducibility.md)
- [../data/README.md](../data/README.md)

## Вывод

Главный научный результат этого пакета не в том, что он "нашел красивую бету", а в том, что он честно отверг слабые инварианты и заменил их более устойчивой структурной рамкой. На текущих данных переносимой universal beta нет, но есть воспроизводимая схема: historical task-content calibration плюс class-based diffusion, capital-return analysis, throttling proxy и финальный accounting layer для структуры экономики РФ.

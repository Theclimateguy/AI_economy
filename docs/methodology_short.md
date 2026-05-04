# Короткая методология проекта

Документ описывает только методологию: какие данные были взяты, как они были преобразованы и какие аналитические артефакты получены. Интерпретации и выводы намеренно не включены.

## 1. Историческая база для проверки переносимых закономерностей

- Данные `EU KLEMS` по национальным счетам, капиталу, доле труда и ICT/non-ICT капиталу были взяты из открытых bulk-файлов EU KLEMS ([National Accounts](https://euklems.eu/bulk/Statistical_National-Accounts.csv), [Capital](https://euklems.eu/bulk/Statistical_Capital.csv), [Labour income shares](https://euklems.eu/bulk/Shares_LabourIncome.csv), [ICT/non-ICT shares](https://euklems.eu/bulk/Shares_ICT-NonICT.csv)) и приведены к восьми проектным секторам `B, C, DE, F, H, J, K, M`; получена историческая sector-country панель с выпуском, добавленной стоимостью, капиталом, долей труда и капиталовооруженностью.

- Данные `OECD STAN 2025` были взяты из набора `OECD.STI.PIE/DSD_STAN@DF_STAN_2025` и приведены к тем же восьми секторам; получены дополнительные отраслевые показатели выпуска, добавленной стоимости, компенсации работников, налогов, операционного излишка и запасов капитала.

- Данные `ILOSTAT` по занятости `industry × occupation` ([EMP_TEMP_ECO_OCU_NB_A](https://rplumber.ilo.org/data/indicator/?id=EMP_TEMP_ECO_OCU_NB_A&lang=en&type=code&format=.csv.gz&channel=ilostat)) были объединены с occupation-level RTI из базы Lewandowski ([RTI for 102 countries](https://piotr-lewandowski.pl/wp-content/uploads/2023/08/Country-specific-routine-task-intensity-of-occupations-for-102-countries.zip)); получена матрица отраслевой рутинности `RTI_s` как средневзвешенное значение RTI профессий внутри отрасли.

- Исторические отраслевые данные `EU KLEMS + OECD STAN + ILOSTAT + RTI` были объединены методом panel merge по `country × sector × year`; получен файл [`historical_sector_panel_1985_2005.csv`](../data/processed/historical_sector_panel_1985_2005.csv) и audit-файлы покрытия.

## 2. Эконометрический screening исторических инвариантов

- Историческая панель была преобразована в набор регрессионных спецификаций с фиксированными эффектами: проверялось, объясняют ли лаги технологических и структурных переменных изменения отраслевых исходов. Практически это означало сравнение динамики отраслей внутри стран с учетом постоянных различий между странами, секторами и годами.

- Для каждого кандидата на "инвариант" были применены несколько фильтров: разные спецификации, поправка Benjamini-Hochberg на множественные проверки, placebo lead и leave-one-country-out устойчивость; получены файлы [`historical_benchmark_screen_summary.csv`](../data/processed/historical_benchmark_screen_summary.csv), [`historical_benchmark_screen_specs.csv`](../data/processed/historical_benchmark_screen_specs.csv), [`historical_benchmark_screen_terms.csv`](../data/processed/historical_benchmark_screen_terms.csv) и [`historical_benchmark_screen_loo.csv`](../data/processed/historical_benchmark_screen_loo.csv).

- Доля труда `wL/VA` была преобразована в long-difference показатель task content: из значения 2005 года вычиталось значение 1995 года внутри каждой пары `country × sector`; получены распределения исторического смещения task content по секторам в [`task_content_sector_benchmarks_1995_2005.csv`](../data/processed/task_content_sector_benchmarks_1995_2005.csv), годовые изменения в [`task_content_annual_changes_1995_2005.csv`](../data/processed/task_content_annual_changes_1995_2005.csv) и long-diff таблица [`task_content_longdiff_1995_2005.csv`](../data/processed/task_content_longdiff_1995_2005.csv).

## 3. Официальный baseline РФ

- Файлы Росстата по ВДС, занятости и зарплатам были взяты из официальных XLS/XLSX: [ВДС по ОКВЭД2 2011-2025](https://rosstat.gov.ru/storage/mediabank/VDS_god_OKVED2_s_2011-2025.xlsx), [занятость 2017-2024](https://rosstat.gov.ru/storage/mediabank/05-05_2017-2024.xls), [зарплаты 2017-2025](https://rosstat.gov.ru/storage/mediabank/tab3-zpl_2025.xlsx). Строки ОКВЭД2 были явно сопоставлены с секторами `B, C, DE, F, H, J, K, M`; для `DE` отрасли `D` и `E` сначала агрегировались, а затем считались производные показатели.

- Номинальная ВДС, ВДС в постоянных ценах, занятость и среднемесячная зарплата были преобразованы в панель `sector × year`; получен файл [`russia_sector_panel_official_2011_2025.csv`](../data/processed/russia_sector_panel_official_2011_2025.csv).

- Занятость и зарплата были преобразованы в proxy фонда оплаты труда по формуле "занятые × зарплата × 12"; этот proxy был разделен на номинальную ВДС, получена proxy-доля труда `sL`; срез последнего полного года сохранен как [`russia_sector_baseline_2024.csv`](../data/processed/russia_sector_baseline_2024.csv).

- Номинальные и реальные уровни ВДС были преобразованы в level-consistent индексы роста и дефляторы после отраслевой агрегации; получены диагностические real-side переменные для дальнейшей калибровки.

## 4. Сценарные AI-шоки по секторам РФ

- Исторические распределения `ΔTC` из comparator panel были преобразованы в sector-level anchors для потенциального изменения доли труда в РФ: среднее, медиана, стандартное отклонение и нижние квантили стали базовыми ориентирами для сценариев.

- Historical sector RTI был преобразован в три режима рутинности `low / medium / high` через tertiles; вместе с экспертной AI-интенсивностью сектора он задал силу сценарного сдвига в доле труда.

- Для каждого сектора были рассчитаны три labour-share shocks: baseline, core и stress. Простыми словами: историческое среднее смещение доли труда было усилено или ослаблено в зависимости от AI-интенсивности и рутинности сектора; получен файл [`russia_ai_sector_scenarios.csv`](../data/processed/russia_ai_sector_scenarios.csv).

- Из econometric screening была взята только скорость затухания маржи, а не полный набор регрессионных коэффициентов; этот параметр был сохранен в сценарной таблице как механизм постепенной эрозии начального profit pulse.

## 5. Диффузия ИИ и капитальная отдача

- Сектора были разделены на классы внедрения: `software`, `hybrid`, `hardware`; каждому классу были заданы параметры скорости раннего внедрения, имитационного распространения, премии к марже и капитального барьера.

- Сценарные параметры были преобразованы в годовые траектории adoption `2025-2035` через Bass-type кривую: внедрение сначала идет медленно, затем ускоряется за счет распространения внутри отрасли, затем приближается к насыщению; получен файл [`ai_diffusion_paths_2025_2035.csv`](../data/processed/ai_diffusion_paths_2025_2035.csv).

- Потенциальный shock доли труда был умножен на степень adoption каждого года; получены годовые траектории фактически реализованного labour-share shock и отраслевые summary-таблицы [`ai_diffusion_sector_summary.csv`](../data/processed/ai_diffusion_sector_summary.csv) и [`ai_diffusion_class_summary.csv`](../data/processed/ai_diffusion_class_summary.csv).

- Adoption paths, премия к марже и капитальные барьеры были преобразованы в capital-need и capital-return траектории; маржа без AI-premium использовалась как контрфакт, чтобы отделить эффект внедрения от обычной динамики маржи. Получены [`ai_capital_return_paths_2025_2035.csv`](../data/processed/ai_capital_return_paths_2025_2035.csv), [`ai_capital_return_sector_summary.csv`](../data/processed/ai_capital_return_sector_summary.csv) и [`ai_capital_return_class_summary.csv`](../data/processed/ai_capital_return_class_summary.csv).

## 6. Managed obsolescence / throttling layer

- Данные `Russia KLEMS` ВШЭ ([страница источника](https://cps.hse.ru/en/data/), [raw workbook](https://www.hse.ru/mirror/pubs/share/322620037)) были приведены из NACE 1.0 к восьми проектным секторам; получена панель [`russia_klems_sector_panel_1995_2016.csv`](../data/processed/russia_klems_sector_panel_1995_2016.csv).

- Исторические индексы Russia KLEMS были преобразованы в четыре компонента pressure score: разрыв "производительность минус часы", разрыв "капитальные услуги минус трудовые услуги", разрыв "ICT-капитал минус non-ICT капитал" и сокращение занятости. Каждый компонент был взят только в положительной части и нормирован от 0 до 1 по секторам.

- Официальные российские данные 2017-2024 были преобразованы в recent-block: real VA per worker proxy, employment, wage-bill proxy, ICT-use proxy из [`ikt_org.xlsx`](../data/raw/russia/ikt_org.xlsx) и fixed-asset renewal из [`koef_ved_2017_2021.xlsx`](../data/raw/russia/koef_ved_2017_2021.xlsx).

- Исторический KLEMS-блок и recent-block были объединены взвешиванием по длине периодов; получен обновленный sector-level proxy `MOS_s` в [`managed_obsolescence_sector_proxy.csv`](../data/processed/managed_obsolescence_sector_proxy.csv). Этот показатель трактуется как склонность сектора к замедлению внедрения, а не как доказательство намеренного ограничения технологии.

- Sector-level priors по импортной зависимости, облакам/ПО, GPU, концентрации и стратегичности были объединены с официальными ICT/renewal/employment indicators; получен sanction/import friction proxy в [`import_dependency_sector.csv`](../data/processed/import_dependency_sector.csv).

## 7. Accounting layer структуры экономики

- Baseline РФ 2024 был продлен до 2035 контрфактическим ростом: для каждого сектора использовался clipped median реального роста из официальной панели 2017-2024; получена контрфактическая траектория ВДС без AI-шока.

- Adoption paths были преобразованы в managed adoption: базовая adoption умножалась на секторный тормоз `1 - rho × MOS_s`; получены траектории внедрения с учетом throttling.

- Managed adoption была преобразована в прирост ВДС и производительности труда через class-specific elasticities: чем больше изменение adoption за год, тем больше добавочный эффект на выпуск и `VA/L`; получены годовые траектории [`russia_economy_structure_paths_2025_2035.csv`](../data/processed/russia_economy_structure_paths_2025_2035.csv).

- ВДС и производительность труда были преобразованы в занятость делением `VA` на `VA/L`; маржа была умножена на ВДС, получен profit pool; доля труда была умножена на ВДС, получен labour income. Итоговые sector и aggregate таблицы сохранены в [`russia_economy_structure_sector_summary.csv`](../data/processed/russia_economy_structure_sector_summary.csv) и [`russia_economy_structure_aggregate_summary.csv`](../data/processed/russia_economy_structure_aggregate_summary.csv).

## 8. Monte Carlo sensitivity

- Параметры elasticities, throttling strength и Bass diffusion были преобразованы в распределения неопределенности: нормальные распределения с отсечением для эффектов ВДС и производительности, beta-распределение для `rho`, lognormal-множители для `p` и `q`.

- Из этих распределений было сделано 5000 прогонов с фиксированным seed; для каждого прогона пересчитаны aggregate trajectories `VA`, profit pool и занятость. Получен файл [`sensitivity_fan_outputs.csv`](../data/processed/sensitivity_fan_outputs.csv) и график [`sensitivity_fan_charts.png`](../output/figures/russia_economy_structure/sensitivity_fan_charts.png).

## 9. Input-output partial closure

- Таблицы Росстата input-output были взяты из официальных файлов: [базовая ТЗВ 2016](https://rosstat.gov.ru/storage/mediabank/baz-tzv-2016(1).xlsx) и [TRI 2019](https://rosstat.gov.ru/storage/mediabank/tri-2019.xlsx). Они были агрегированы к восьми проектным секторам.

- Межотраслевая матрица промежуточного потребления была преобразована в матрицу прямых затрат: каждый столбец intermediate-use был поделен на выпуск соответствующего сектора. Затем была посчитана матрица Леонтьева, которая показывает, сколько совокупного выпуска требуется по цепочкам поставок для единицы финального спроса.

- Direct AI-shock из accounting layer был преобразован в output-equivalent impulse через коэффициент `VA/output`; этот impulse был пропущен через матрицу Леонтьева. Получены прямые и косвенные эффекты по ВДС, занятости и импортной компоненте в [`io_multiplier_sector_summary.csv`](../data/processed/io_multiplier_sector_summary.csv).

## 10. Welfare / distributional proxy

- Российская матрица `occupation × industry` из ILOSTAT для `RUS, 2024, ISCO-08, ISIC4` была объединена с AI exposure по профессиям из OECD figure data ([stat.link/2q5i1s](https://stat.link/2q5i1s)); получена occupation-level exposure-weighted структура риска.

- Sector employment delta из accounting layer был распределен по профессиям пропорционально занятости профессии в секторе и ее AI exposure; получены occupation-level изменения занятости.

- Sector wage из Росстата был умножен на occupation wage multiplier proxy; получен baseline labour income по ячейкам `sector × occupation`. Затем occupation cells были разложены по income-quintile proxy, а прирост profit pool распределен по capital-income weights `0, 0, 0.05, 0.20, 0.75`; получен файл [`welfare_occupation_quintile_summary.csv`](../data/processed/welfare_occupation_quintile_summary.csv).

## 11. Графики и итоговые артефакты

- Таблицы diffusion, capital returns, managed obsolescence, economy structure, IO и welfare были преобразованы в набор PNG-графиков для аналитической записки; получены файлы [`ai-economy-diffusion-return.png`](../ai-economy-diffusion-return.png), [`ai-economy-sector-shift.png`](../ai-economy-sector-shift.png), [`ai-economy-macro-bridge.png`](../ai-economy-macro-bridge.png), [`ai-economy-monte-carlo.png`](../ai-economy-monte-carlo.png), [`ai-economy-welfare-quintiles.png`](../ai-economy-welfare-quintiles.png) и пакет [`output/figures/managed_obsolescence/`](../output/figures/managed_obsolescence/).

- Все processed-таблицы и графики были собраны в итоговую аналитическую записку [`ai-economy-analytical-note.md`](../ai-economy-analytical-note.md) и PDF-версию [`ai-economy-analytical-note.pdf`](../ai-economy-analytical-note.pdf).

## 12. Воспроизводимый порядок запуска

Полный pipeline запускается командой:

```bash
python3 scripts/run_pipeline.py --stage all
```

Фактический порядок преобразований:

1. `build_staffing_matrix.py`: ILOSTAT + Lewandowski RTI → sector RTI.
2. `build_historical_panel.py`: EU KLEMS + OECD STAN + RTI → historical comparator panel.
3. `screen_historical_benchmarks.py`: historical panel → econometric screening tables.
4. `calculate_task_content.py`: labour-share panel → historical `ΔTC` benchmarks.
5. `build_russia_ai_scenarios.py`: `ΔTC` benchmarks + RTI buckets → Russia AI scenario shocks.
6. `build_russia_sector_panel.py`: Rosstat XLS/XLSX → official Russia sector baseline.
7. `build_ai_diffusion_model.py`: scenario classes → AI adoption paths.
8. `build_ai_capital_returns.py`: adoption + margin + capex assumptions → capital-return paths.
9. `build_managed_obsolescence_layer.py`: Russia KLEMS + recent official block → `MOS_s`.
10. `import_friction_layer.py`: sector priors + official indicators → import/sanction wedge.
11. `build_russia_economy_structure.py`: adoption + baseline + MOS → economy-structure paths.
12. `sensitivity_montecarlo.py`: parameter distributions → uncertainty fan outputs.
13. `io_leontief_propagation.py`: IO tables + direct shocks → partial IO closure.
14. `welfare_distributional.py`: occupation matrix + exposure + sector shocks → welfare proxy.

# Stage 1: Invariants Screening

## Задача

Проверить, существуют ли исторически устойчивые инварианты технологических революций, которые можно перенести на ИИ в отраслевом разрезе РФ.

## Что было сделано

1. Собрана comparator panel по 8 секторам на `EU KLEMS + OECD STAN`.
2. RTI построен через staffing-matrix aggregation, а не через грубый sector proxy.
3. Прогнан строгий econometric screening:
   - baseline FE
   - BH-correction
   - placebo lead
   - robustness across specs
   - leave-one-country-out

## Формула этапа

Изначально тестировались структурные спецификации вида:

$$
\Delta y_{c,s,t} = f(\Delta Tech_{c,s,t-1}, RTI_{c,s}, K/L_{c,s,t-1}) + FE + \varepsilon_{c,s,t}.
$$

## Главный результат

Честный результат screening:

- `0 surviving full invariants`
- выжил только отдельный механизм эрозии маржи: `lag_margin < 0`

Это означает:

- переносимых linear tech betas не найдено;
- принудительный перенос regression coefficients на РФ был бы научно слабым;
- переход к scenario calibration через historical distributions of `ΔTC` был необходим, а не optional.

## Следующий ход

После провала universal betas модель была переопределена:

$$
\Delta TC_{c,s} = \Delta(wL/VA)_{c,s}
$$

и именно empirical distribution `ΔTC` стала источником sector-level shocks.

## Ключевые артефакты

- panel: `data/processed/historical_sector_panel_1985_2005.csv`
- screening summary: `data/processed/historical_benchmark_screen_summary.csv`
- screening terms: `data/processed/historical_benchmark_screen_terms.csv`
- task-content benchmarks: `data/processed/task_content_sector_benchmarks_1995_2005.csv`

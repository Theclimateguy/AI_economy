# Методичка: CRITIC-модель устойчивости отраслей по ОКВЭД

## Цель

Построить воспроизводимый интегральный индекс устойчивости отраслей по ОКВЭД на базе метода CRITIC. Индекс нужен для ранжирования отраслей по сочетанию адаптивности, кредитного потенциала, доходности для банка, финансовой устойчивости и стратегической конвергенции до 2030 года.

## Обозначения

- $i$ - отрасль ОКВЭД.
- $j$ - показатель внутри блока.
- $b$ - блок модели.
- $x_{ij}$ - исходное значение показателя.
- $z_{ij}$ - нормированное значение, где больше значит лучше.
- $w_j$ - CRITIC-вес показателя.
- $W_b$ - CRITIC-вес блока.
- $B_{ib}$ - score отрасли $i$ по блоку $b$.
- $R_i$ - итоговый индекс устойчивости.

## Блоки модели

1. **Адаптивный потенциал**: управляемая адаптация, скорость диффузии ИИ, рост ВДС, прирост производительности.
2. **Кредитный потенциал**: доля ВДС, годовая и накопленная потребность в капитале, отношение капитальной потребности к ВДС.
3. **Доходность для банка**: margin proxy, прирост profit pool, profit uplift, net value after capex.
4. **Финансовая устойчивость**: margin proxy, импортная зависимость, концентрация рынка, давление устаревания, transition risk.
5. **Стратегическая конвергенция**: адаптация, производительность, strategy capacity, diversification upside, net transformation score.

## Нормировка

Для каждого показателя применяется winsorized min-max нормировка:

$$
z_{ij} = \frac{\operatorname{clip}(x_{ij}, q_{0.05,j}, q_{0.95,j}) - q_{0.05,j}}{q_{0.95,j} - q_{0.05,j}}.
$$

Для негативных показателей, где меньше значит лучше:

$$
z_{ij}^{-} = 1 - z_{ij}.
$$

После нормировки значения ограничиваются интервалом:

$$
z_{ij} \in [0.01, 1].
$$

Это нужно, чтобы геометрическая агрегация не обнуляла индекс из-за одного нулевого значения.

## CRITIC-веса

Метод CRITIC повышает вес показателя, если он:

- сильно различает отрасли;
- слабо дублирует другие показатели.

Информационная значимость показателя:

$$
C_j = \sigma_j \sum_{k=1}^{m}(1-r_{jk}),
$$

где $\sigma_j$ - стандартное отклонение нормированного показателя, $r_{jk}$ - корреляция между показателями $j$ и $k$.

Вес:

$$
w_j = \frac{C_j}{\sum_j C_j}.
$$

CRITIC считается иерархически:

1. веса показателей внутри каждого блока;
2. score каждого блока;
3. веса самих блоков;
4. итоговый индекс.

## Агрегация

Блоковый score:

$$
B_{ib} = \prod_{j \in b} z_{ij}^{w_j}.
$$

Базовый индекс:

$$
R_i^{base} = \prod_b B_{ib}^{W_b}.
$$

Добавлен мягкий risk-gate по финансовой устойчивости:

$$
R_i = R_i^{base}\exp\{-\lambda \max(0, \delta - B_{i,financial})^2\}.
$$

В текущей версии:

$$
\delta = 0.35,\quad \lambda = 3.0.
$$

## Расчёт до 2030

Для графиков до 2030 используется annual-panel 2025-2030. CRITIC-веса калибруются на срезе 2030, затем применяются ко всем годам 2025-2030. Это даёт сопоставимые траектории индекса и рангов.

Базовый сценарий:

- `scenario = Base`
- `throttle_scenario = BaseThrottle`
- `complex_scenario = OrderlyTransition`

## Проверки

Минимальный набор проверок:

1. **Bootstrap по секторам**: устойчивость рангов к пересчёту CRITIC-весов.
2. **Leave-one-block**: проверка, не держится ли рейтинг на одном блоке.
3. **Leave-one-indicator**: чувствительность к отдельным показателям.
4. **Альтернативная нормировка**: сравнение winsorized min-max, обычной min-max и rank-нормировки.
5. **Альтернативная агрегация**: сравнение геометрической и аддитивной схем.
6. **Historical rolling-origin backtest**: проверка, воспроизводится ли сигнал на исторических данных.

Критерий для робастности рангов:

- `pass`: median Spearman >= 0.80 и p10 Spearman >= 0.60;
- `tentative`: median Spearman >= 0.60 и p10 Spearman >= 0.40;
- `fail`: ниже этих порогов.

## Команды

Базовая модель и проверки:

```bash
python scripts/build_okved_resilience_model.py --bootstrap 500 --seed 42
```

Графики CRITIC-устойчивости до 2030:

```bash
python scripts/plot_okved_resilience_2030.py \
  --scenario Base \
  --throttle BaseThrottle \
  --climate-scenario OrderlyTransition
```

## Основные outputs

- `data/processed/okved_resilience_ranking_2024.csv`
- `data/processed/okved_resilience_weights_2024.csv`
- `data/processed/okved_resilience_robustness_summary.csv`
- `data/processed/okved_resilience_historical_backtest_summary.csv`
- `data/processed/okved_resilience_forward_paths_2025_2030.csv`
- `data/processed/okved_resilience_forward_summary_2030.csv`
- `output/figures/okved_resilience/critic_resilience_index_paths_top5_2025_2030.png`
- `output/figures/okved_resilience/critic_resilience_index_2030.png`
- `output/figures/okved_resilience/critic_resilience_block_heatmap_2030.png`

## Ограничения

Текущая версия использует отраслевые прокси для банковских блоков. Для production-модели нужны фактические банковские данные по ОКВЭД: RAROC, cost of risk, NPL, выдачи, портфель, лимиты, LGD/PD и залоговое покрытие.


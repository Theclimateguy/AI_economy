# Russia Economy Structure Report

Этот слой переводит `AI diffusion / margin / capital return` в структуру экономики РФ: `VA`, отраслевые доли, profit pool, labour income, занятость и производительность труда.

## 1. Формализация

Контрфактический выпуск:

\[
VA^{cf}_{s,t} = VA_{s,2024} \prod_{\tau=2025}^t (1 + g^{cf}_s)
\]

Managed adoption:

\[
A^{m}_{s,t} = A_{s,t}(1 - \rho MOS_s)
\]

AI output and labour-productivity boosts:

\[
VA^{AI}_{s,t} = VA^{cf}_{s,t} \exp\left(\sum_{\tau=2025}^t \eta^{VA}_s \Delta A^m_{s,\tau}\right)
\]

\[
LP^{AI}_{s,t} = LP^{cf}_{s,t} \exp\left(\sum_{\tau=2025}^t \eta^{LP}_s \Delta A^m_{s,\tau}\right)
\]

\[
L^{AI}_{s,t} = \frac{VA^{AI}_{s,t}}{LP^{AI}_{s,t}},
\qquad
\Pi^{AI}_{s,t} = \pi^{AI}_{s,t} VA^{AI}_{s,t}
\]

Контрфактический рост `VA` — clipped median official real growth за `2017-2024`. Денежные величины интерпретируются как рубли baseline 2024, а не номинальный прогноз инфляции.

## 2. Aggregate Base / BaseThrottle

| scenario | throttle_scenario | total_va_gain_2035_pct | total_profit_pool_gain_2035_pct | total_labour_income_gain_2035_pct | aggregate_lp_gain_vs_cf_2035_pct | total_employment_delta_2035_thousand | cumulative_net_value_after_capex_2035_bn_rub |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Base | BaseThrottle | 4.267 | 11.980 | -7.249 | 6.381 | -978.392 | 46591.450 |

## 2a. Операционный горизонт 2030

| sector_id | sector_name_ru | class_id | adaptation_managed_2030 | incremental_va_2030_bn_rub | incremental_profit_pool_2030_bn_rub | employment_delta_2030_thousand |
| --- | --- | --- | --- | --- | --- | --- |
| K | Финансы и страхование | software | 0.342 | 717.788 | 1245.610 | -31.422 |
| M | Профессиональные и научные услуги | software | 0.365 | 600.804 | 809.123 | -86.354 |
| J | ИТ и связь | software | 0.311 | 423.930 | 495.899 | -58.303 |
| G | Оптовая и розничная торговля | hybrid | 0.103 | 197.447 | 237.439 | -81.506 |
| C | Обрабатывающая промышленность без машиностроения | hybrid | 0.094 | 196.829 | 317.803 | -47.290 |
| C_mach | Машиностроение (ОКВЭД 26–30) | hybrid | 0.093 | 62.888 | 101.528 | -13.859 |
| B | Добыча полезных ископаемых | hardware | 0.040 | 38.592 | 99.532 | -2.642 |
| DE | Энергетика и ЖКХ | hybrid | 0.096 | 37.198 | 57.498 | -11.629 |
| H | Транспорт и логистика | hardware | 0.040 | 22.985 | 32.263 | -12.991 |
| F | Строительство | hardware | 0.040 | 18.868 | 13.510 | -14.566 |

## 3. Sector Share Winners

| sector_id | sector_name_ru | class_id | delta_va_share_pp_2035 | va_share_ai_2035 | incremental_va_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| K | Финансы и страхование | software | 0.845 | 0.130 | 2479.988 |
| M | Профессиональные и научные услуги | software | 0.611 | 0.085 | 1727.892 |
| J | ИТ и связь | software | 0.429 | 0.077 | 1342.801 |
| DE | Энергетика и ЖКХ | hybrid | -0.049 | 0.027 | 115.959 |
| C_mach | Машиностроение (ОКВЭД 26–30) | hybrid | -0.124 | 0.065 | 275.312 |

## 4. Sector Share Losers

| sector_id | sector_name_ru | class_id | delta_va_share_pp_2035 | va_share_ai_2035 | incremental_va_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| B | Добыча полезных ископаемых | hardware | -0.535 | 0.140 | 108.620 |
| H | Транспорт и логистика | hardware | -0.335 | 0.088 | 68.353 |
| C | Обрабатывающая промышленность без машиностроения | hybrid | -0.317 | 0.171 | 730.958 |
| F | Строительство | hardware | -0.293 | 0.077 | 60.223 |
| G | Оптовая и розничная торговля | hybrid | -0.233 | 0.142 | 659.975 |

## 5. Profit Pool Winners

| sector_id | sector_name_ru | class_id | incremental_profit_pool_2035_bn_rub | profit_pool_ai_2035_bn_rub | cumulative_net_value_after_capex_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| K | Финансы и страхование | software | 4367.448 | 17449.852 | 18256.006 |
| M | Профессиональные и научные услуги | software | 2364.543 | 8974.872 | 10820.278 |
| J | ИТ и связь | software | 1591.170 | 6885.519 | 6860.656 |
| C | Обрабатывающая промышленность без машиностроения | hybrid | 1183.678 | 18372.926 | 4465.201 |
| G | Оптовая и розничная торговля | hybrid | 796.349 | 11386.743 | 3247.349 |

## 6. Labour Productivity Winners

| sector_id | sector_name_ru | class_id | adaptation_managed_2035 | lp_gain_vs_cf_2035_pct | employment_delta_2035_thousand |
| --- | --- | --- | --- | --- | --- |
| M | Профессиональные и научные услуги | software | 0.831 | 20.073 | -194.577 |
| K | Финансы и страхование | software | 0.781 | 18.736 | -65.131 |
| J | ИТ и связь | software | 0.709 | 16.871 | -158.123 |
| G | Оптовая и розничная торговля | hybrid | 0.319 | 4.562 | -248.195 |
| DE | Энергетика и ЖКХ | hybrid | 0.297 | 4.242 | -33.730 |

## 7. Employment Delta

| sector_id | sector_name_ru | class_id | employment_delta_2035_thousand | incremental_labour_income_2035_bn_rub | labour_income_ai_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| G | Оптовая и розничная торговля | hybrid | -248.195 | -1218.628 | 13638.402 |
| M | Профессиональные и научные услуги | software | -194.577 | 95.592 | 7419.846 |
| J | ИТ и связь | software | -158.123 | -148.182 | 7375.206 |
| C | Обрабатывающая промышленность без машиностроения | hybrid | -146.590 | -931.753 | 12635.947 |
| K | Финансы и страхование | software | -65.131 | -1074.115 | 6830.166 |

## 8. Ограничения

- Это accounting layer, а не general equilibrium: цены, межотраслевые связи и спрос не замыкаются.
- `VA` строится в baseline-ruble units через real growth и AI boosts; номинальная инфляция не моделируется.
- Параметры `η` заданы сценарно по adoption class и должны идти в sensitivity block.
- `MOS_s` — pressure proxy, а не доказательство намеренного ограничения внедрения.

## 8. Ограничения

- Базовые headline-цифры выше остаются direct accounting layer; partial IO-closure вынесен в `docs/io_macro_closure.md`.
- По `2019` Rosstat `TRI` тот же `Base / BaseThrottle` shock vector даёт `IO-adjusted VA gain = 7.200%` против accounting `4.549%`, то есть ещё `+5203.245` млрд руб. через межотраслевые связи.
- Direct employment effect в accounting layer равен `-978.392` тыс., но Leontief demand-support добавляет `1260.024` тыс.; net partial-closure outcome становится `281.632` тыс. Это не GE-оценка и не учитывает wages/prices crowding-out.
- `VA` строится в baseline-ruble units через real growth и AI boosts; номинальная инфляция не моделируется.
- Параметры `η` заданы сценарно по adoption class и должны идти в sensitivity block.
- `MOS_s` — pressure proxy, а не доказательство намеренного ограничения внедрения.

## 9. Sensitivity

Формально считаем неопределенность по вектору параметров

\[
\theta = \left(\{\eta^{VA}_c, \eta^{LP}_c\}_{c \in \{software, hybrid, hardware\}}, \rho, \{p_s, q_s\}_s\right),
\]

и оцениваем распределение агрегированных исходов

\[
Y_t(\theta) = \left(VA^{AI}_t, \Pi^{AI}_t, L^{AI}_t - L^{cf}_t\right)
\]

через Monte Carlo с `N=5000` draws и `seed=20260430`.

### Priors

| parameter | distribution | hyperparameters |
| --- | --- | --- |
| $\eta^{VA}_{software}$ | trunc. normal | mean=0.14, sd=0.03, [0.08, 0.22] |
| $\eta^{LP}_{software}$ | trunc. normal | mean=0.22, sd=0.05, [0.12, 0.35] |
| $\eta^{VA}_{hybrid}$ | trunc. normal | mean=0.08, sd=0.02, [0.03, 0.15] |
| $\eta^{LP}_{hybrid}$ | trunc. normal | mean=0.14, sd=0.03, [0.06, 0.24] |
| $\eta^{VA}_{hardware}$ | trunc. normal | mean=0.04, sd=0.015, [0.00, 0.09] |
| $\eta^{LP}_{hardware}$ | trunc. normal | mean=0.09, sd=0.025, [0.02, 0.18] |
| $\rho$ | beta | alpha=6, beta=14, mean=0.30 |
| $p_s$ | lognormal multiplier on class anchor | sigma=0.35, clip=[0.25x, 2.50x] |
| $q_s$ | lognormal multiplier on class anchor | sigma=0.25, clip=[0.50x, 2.00x] |

### 2035 percentile outcomes

| metric | p10 | p50 | p90 | deterministic base |
| --- | --- | --- | --- | --- |
| VA gain, % | 3.242 | 4.261 | 5.420 | 4.267 |
| Profit pool gain, % | 10.208 | 12.013 | 13.937 | 11.980 |
| Employment delta, thousand | -1550.486 | -972.331 | -450.053 | -978.392 |

Медианный исход к `2035` близок к deterministic base, но интервалы уже заметно шире headline-чисел: `VA gain` лежит в диапазоне `[3.24; 5.42]%`, `profit pool gain` — `[10.21; 13.94]%`, а `employment delta` — `[-1550; -450]` тыс. человек.

### Fan charts

![Sensitivity fan charts](/home/user/workspace/AI_economy-317066fb/output/figures/russia_economy_structure/sensitivity_fan_charts.png)

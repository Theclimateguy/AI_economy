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
| Base | BaseThrottle | 4.549 | 12.535 | -6.777 | 6.698 | -726.342 | 43206.409 |

## 3. Sector Share Winners

| sector_id | sector_name_ru | class_id | delta_va_share_pp_2035 | va_share_ai_2035 | incremental_va_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| K | Финансы и страхование | software | 0.951 | 0.152 | 2480.001 |
| M | Профессиональные и научные услуги | software | 0.690 | 0.099 | 1727.897 |
| J | ИТ и связь | software | 0.475 | 0.090 | 1336.458 |
| DE | Энергетика и ЖКХ | hybrid | -0.066 | 0.031 | 115.931 |
| F | Строительство | hardware | -0.368 | 0.090 | 60.223 |

## 4. Sector Share Losers

| sector_id | sector_name_ru | class_id | delta_va_share_pp_2035 | va_share_ai_2035 | incremental_va_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| B | Добыча полезных ископаемых | hardware | -0.671 | 0.163 | 108.622 |
| C | Обрабатывающая промышленность | hybrid | -0.590 | 0.272 | 981.344 |
| H | Транспорт и логистика | hardware | -0.421 | 0.103 | 68.353 |
| F | Строительство | hardware | -0.368 | 0.090 | 60.223 |
| DE | Энергетика и ЖКХ | hybrid | -0.066 | 0.031 | 115.931 |

## 5. Profit Pool Winners

| sector_id | sector_name_ru | class_id | incremental_profit_pool_2035_bn_rub | profit_pool_ai_2035_bn_rub | cumulative_net_value_after_capex_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| K | Финансы и страхование | software | 4367.471 | 17449.875 | 18256.102 |
| M | Профессиональные и научные услуги | software | 2364.550 | 8974.879 | 10820.309 |
| C | Обрабатывающая промышленность | hybrid | 1588.966 | 25003.859 | 5920.953 |
| J | ИТ и связь | software | 1583.426 | 6877.775 | 6827.874 |
| B | Добыча полезных ископаемых | hardware | 279.862 | 22246.486 | 681.102 |

## 6. Labour Productivity Winners

| sector_id | sector_name_ru | class_id | adaptation_managed_2035 | lp_gain_vs_cf_2035_pct | employment_delta_2035_thousand |
| --- | --- | --- | --- | --- | --- |
| M | Профессиональные и научные услуги | software | 0.831 | 20.073 | -194.578 |
| K | Финансы и страхование | software | 0.781 | 18.736 | -65.131 |
| J | ИТ и связь | software | 0.705 | 16.789 | -157.432 |
| DE | Энергетика и ЖКХ | hybrid | 0.297 | 4.241 | -33.722 |
| C | Обрабатывающая промышленность | hybrid | 0.288 | 4.117 | -190.567 |

## 7. Employment Delta

| sector_id | sector_name_ru | class_id | employment_delta_2035_thousand | incremental_labour_income_2035_bn_rub | labour_income_ai_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| M | Профессиональные и научные услуги | software | -194.578 | 95.593 | 7419.847 |
| C | Обрабатывающая промышленность | hybrid | -190.567 | -1264.968 | 17216.717 |
| J | ИТ и связь | software | -157.432 | -148.381 | 7375.007 |
| K | Финансы и страхование | software | -65.131 | -1074.118 | 6830.163 |
| F | Строительство | hardware | -40.420 | -197.498 | 10519.383 |

## 8. Ограничения

- Базовые headline-цифры выше остаются direct accounting layer; partial IO-closure вынесен в `docs/io_macro_closure.md`.
- По `2019` Rosstat `TRI` тот же `Base / BaseThrottle` shock vector даёт `IO-adjusted VA gain = 7.347%` против accounting `4.549%`, то есть ещё `+4232.693` млрд руб. через межотраслевые связи.
- Direct employment effect в accounting layer равен `-726.342` тыс., но Leontief demand-support добавляет `874.704` тыс.; net partial-closure outcome становится `148.363` тыс. Это не GE-оценка и не учитывает wages/prices crowding-out.
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
| VA gain, % | 3.345 | 4.505 | 5.791 | 4.549 |
| Profit pool gain, % | 10.447 | 12.467 | 14.626 | 12.535 |
| Employment delta, thousand | -1169.812 | -723.030 | -308.325 | -726.342 |

Медианный исход к `2035` близок к deterministic base, но интервалы уже заметно шире headline-чисел: `VA gain` лежит в диапазоне `[3.35; 5.79]%`, `profit pool gain` — `[10.45; 14.63]%`, а `employment delta` — `[-1170; -308]` тыс. человек.

### Fan charts

![Sensitivity fan charts](/Users/theclimateguy/Documents/science/AI vs economy/output/figures/russia_economy_structure/sensitivity_fan_charts.png)

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
| Base | BaseThrottle | 4.409 | 12.245 | -6.828 | 6.453 | -692.466 | 42124.181 |

## 3. Sector Share Winners

| sector_id | sector_name_ru | class_id | delta_va_share_pp_2035 | va_share_ai_2035 | incremental_va_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| K | Финансы и страхование | software | 1.037 | 0.152 | 2583.879 |
| M | Профессиональные и научные услуги | software | 0.608 | 0.099 | 1577.282 |
| J | ИТ и связь | software | 0.408 | 0.089 | 1211.997 |
| DE | Энергетика и ЖКХ | hybrid | -0.056 | 0.031 | 123.606 |
| F | Строительство | hardware | -0.357 | 0.090 | 58.883 |

## 4. Sector Share Losers

| sector_id | sector_name_ru | class_id | delta_va_share_pp_2035 | va_share_ai_2035 | incremental_va_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| B | Добыча полезных ископаемых | hardware | -0.653 | 0.164 | 103.611 |
| C | Обрабатывающая промышленность | hybrid | -0.579 | 0.272 | 941.204 |
| H | Транспорт и логистика | hardware | -0.408 | 0.103 | 67.596 |
| F | Строительство | hardware | -0.357 | 0.090 | 58.883 |
| DE | Энергетика и ЖКХ | hybrid | -0.056 | 0.031 | 123.606 |

## 5. Profit Pool Winners

| sector_id | sector_name_ru | class_id | incremental_profit_pool_2035_bn_rub | profit_pool_ai_2035_bn_rub | cumulative_net_value_after_capex_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| K | Финансы и страхование | software | 4556.735 | 17639.139 | 19030.924 |
| M | Профессиональные и научные услуги | software | 2151.781 | 8762.110 | 9867.145 |
| C | Обрабатывающая промышленность | hybrid | 1523.509 | 24938.401 | 5678.323 |
| J | ИТ и связь | software | 1431.916 | 6726.265 | 6185.342 |
| B | Добыча полезных ископаемых | hardware | 266.935 | 22233.560 | 649.616 |

## 6. Labour Productivity Winners

| sector_id | sector_name_ru | class_id | adaptation_managed_2035 | lp_gain_vs_cf_2035_pct | employment_delta_2035_thousand |
| --- | --- | --- | --- | --- | --- |
| K | Финансы и страхование | software | 0.812 | 19.547 | -67.627 |
| M | Профессиональные и научные услуги | software | 0.763 | 18.270 | -178.976 |
| J | ИТ и связь | software | 0.643 | 15.186 | -143.767 |
| DE | Энергетика и ЖКХ | hybrid | 0.316 | 4.525 | -35.906 |
| C | Обрабатывающая промышленность | hybrid | 0.277 | 3.947 | -182.922 |

## 7. Employment Delta

| sector_id | sector_name_ru | class_id | employment_delta_2035_thousand | incremental_labour_income_2035_bn_rub | labour_income_ai_2035_bn_rub |
| --- | --- | --- | --- | --- | --- |
| C | Обрабатывающая промышленность | hybrid | -182.922 | -1253.100 | 17228.584 |
| M | Профессиональные и научные услуги | software | -178.976 | 65.224 | 7389.478 |
| J | ИТ и связь | software | -143.767 | -152.567 | 7370.820 |
| K | Финансы и страхование | software | -67.627 | -1099.164 | 6805.117 |
| F | Строительство | hardware | -39.525 | -196.224 | 10520.658 |

## 8. Ограничения

- Это accounting layer, а не general equilibrium: цены, межотраслевые связи и спрос не замыкаются.
- `VA` строится в baseline-ruble units через real growth и AI boosts; номинальная инфляция не моделируется.
- Параметры `η` заданы сценарно по adoption class и должны идти в sensitivity block.
- `MOS_s` — pressure proxy, а не доказательство намеренного ограничения внедрения.

# Russia AI Capital Return Report

Этот слой переводит диффузионную модель в функцию капитальной отдачи по классам и секторам.

Используем две величины:

\[
R^{K,gross}_{s,t} = \frac{\gamma_s A_s(t) \cdot VA_{s,0}}{\Delta K_{s,t}},
\qquad
R^{K,net}_{s,t} = \frac{\left(\pi_{s,t} - \pi^{cf}_{s,t}\right) \cdot VA_{s,0}}{\Delta K_{s,t}},
\]

где контрфактуал маржи задан как

\[
\pi^{cf}_{s,t} = \pi_{s,0} - \lambda \pi^{cf}_{s,t-1},
\]

то есть сравнение идет не со статическим `π0`, а с той же траекторией historical erosion без AI-premium.

## 1. Class Return Function

Base-scenario:

| class_id | A_2035 | net_return_cf_2035 | net_payback_year_cf | cum_capex_2035_bn_rub | cum_net_gain_cf_2035_bn_rub | techint_delta_median |
| --- | --- | --- | --- | --- | --- | --- |
| software | 0.876 | 37.700 | 2025.0 | 387.493 | 14608.380 | 0.109 |
| hybrid | 0.330 | 3.942 | 2026.0 | 979.003 | 3859.625 | 0.019 |
| hardware | 0.113 | 1.361 | 2032.0 | 875.367 | 1191.058 | 0.015 |

Здесь видно три разных режима:

- `software`: very high net return, payback внутри горизонта практически сразу, низкий capex.
- `hybrid`: положительная, но сильно более низкая капитальная отдача; payback зависит от сценария.
- `hardware`: самая слабая отдача и максимальная зависимость от frictions.

## 2. Sector Leaders in Base

| sector_id | sector_name_ru | class_id | net_return_cf_2035 | net_payback_year_cf | cumulative_delta_k_need_bn_rub |
| --- | --- | --- | --- | --- | --- |
| M | Профессиональные и научные услуги | software | 66.300 | 2025.0 | 74.525 |
| K | Финансы и страхование | software | 43.030 | 2025.0 | 151.102 |
| J | ИТ и связь | software | 19.555 | 2025.0 | 161.866 |
| C | Обрабатывающая промышленность | hybrid | 7.905 | 2025.0 | 416.023 |
| F | Строительство | hardware | 3.635 | 2026.0 | 26.700 |

## 3. Fast Winners

| sector_id | sector_name_ru | class_id | net_return_cf_2035 | gross_payback_year |
| --- | --- | --- | --- | --- |
| M | Профессиональные и научные услуги | software | 104.435 | 2025.0 |
| K | Финансы и страхование | software | 67.781 | 2025.0 |
| J | ИТ и связь | software | 30.803 | 2025.0 |

## 4. Friction Bottlenecks

| sector_id | sector_name_ru | class_id | cumulative_delta_k_need_bn_rub | net_return_cf_2035 | net_payback_year_cf |
| --- | --- | --- | --- | --- | --- |
| B | Добыча полезных ископаемых | hardware | 685.043 | 0.626 |  |
| DE | Энергетика и ЖКХ | hybrid | 317.782 | 0.966 |  |
| C | Обрабатывающая промышленность | hybrid | 234.830 | 7.523 | 2025.0 |

## 5. Главный вывод

1. `software` действительно реализует режим `high adoption / low capex / high return`. В `Base` net return к `2035` уже очень высок, а в `Fast` еще сильнее.
2. `hardware` реализует режим `low adoption / high capex / late or absent payback`. Во `Friction` часть hardware-секторов не достигает net payback к `2035`.
3. `hybrid` это transition regime: положительная отдача есть, но она зависит от длины горизонта и стоимости капитала намного сильнее, чем в software.

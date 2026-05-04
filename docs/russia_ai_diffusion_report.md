# Russia AI Diffusion Report

Этот слой превращает sector-level AI shocks в годовые траектории `2025–2035` через Bass-диффузию, margin adaptation и capital-need block.

## 1. Что реально удалось калибровать из данных

Для диагностики использован `EU KLEMS` ICT capital intensity `techint_klems` по comparators за `1995–2017`. Исторические данные дают чистую иерархию уровней диффузии, но не дают статистически чистой идентификации `p,q` на class-level, поэтому expert anchors retained.

| class_id | start_year | end_year | techint_start_median | techint_end_median | techint_delta_median | positive_dA_share | p_hat_disc | q_hat_disc | fit_is_structurally_clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hardware | 1995 | 2017 | 0.010 | 0.025 | 0.015 | 0.633 | 0.033 | -0.063 | False |
| hybrid | 1995 | 2017 | 0.020 | 0.040 | 0.020 | 0.722 | 0.046 | -0.099 | False |
| software | 1995 | 2017 | 0.066 | 0.175 | 0.109 | 0.714 | 0.195 | -0.675 | False |

Вывод по калибровке:

- `software` имеет самый высокий historical techint и самый большой прирост.
- `hybrid` и особенно `hardware` растут заметно медленнее.
- Class-level discrete Bass fits не дают устойчивого положительного `q`; поэтому модель использует ваши class anchors как priors, а data block служит validation layer, а не source of false precision.

## 2. Class Dynamics 2025–2035

Base-scenario class trajectories:

| class_id | A_2030 | A_2035 | year_A50 | peak_speed_year | peak_speed | cumulative_delta_k_need_bn_rub |
| --- | --- | --- | --- | --- | --- | --- |
| hardware | 0.043 | 0.113 |  | 2035 | 0.018 | 875.367 |
| hybrid | 0.106 | 0.330 |  | 2035 | 0.057 | 1131.272 |
| software | 0.384 | 0.876 | 2032 | 2032 | 0.115 | 387.493 |

Главный рисунок здесь простой:

- `software` выходит на `A≈0.88` к 2035 и пересекает `A=0.5` уже в `2032`; в `Fast` это происходит в `2030`.
- `hybrid` в `Base` к 2035 доходит только до `A≈0.33`; до `0.5` он добирается лишь в `Fast`.
- `hardware` не достигает `A=0.5` даже в `Fast` к 2035, что и создает длинную investment phase.

## 3. Sector Implications

Сектора с самым глубоким снижением labour share к 2035 в `Base`:

| sector_id | sector_name_ru | class_id | A_2035 | delta_sL_2035 | labour_share_2035 |
| --- | --- | --- | --- | --- | --- |
| K | Финансы и страхование | software | 0.876 | -0.064 | 0.278 |
| J | ИТ и связь | software | 0.876 | -0.060 | 0.507 |
| G | Оптовая и розничная торговля | hybrid | 0.330 | -0.045 | 0.519 |

Сектора с наибольшим margin peak в `Fast`:

| sector_id | sector_name_ru | class_id | margin_peak_year | margin_peak |
| --- | --- | --- | --- | --- |
| B | Добыча полезных ископаемых | hardware | 2035 | 0.867 |
| K | Финансы и страхование | software | 2035 | 0.758 |
| C_mach | Машиностроение (ОКВЭД 26–30) | hybrid | 2035 | 0.601 |

Сектора с наибольшей cumulative capital need в `Friction`:

| sector_id | sector_name_ru | class_id | cumulative_delta_k_need_bn_rub |
| --- | --- | --- | --- |
| B | Добыча полезных ископаемых | hardware | 685.043 |
| DE | Энергетика и ЖКХ | hybrid | 317.782 |
| H | Транспорт и логистика | hardware | 194.468 |

## 4. Интерпретация

1. Первые winners по марже действительно относятся к `software`-классу: `K`, `J`, `M`. Это следует не из «красивой гипотезы», а из комбинации высокого `p,q`, умеренного capital barrier и положительного adoption premium на уже существующую margin base.
2. Самая длинная transition zone у `hardware`: `B`, `F`, `H`. Там adaptation к 2035 остаётся низкой, но capital need на единицу внедрения высокой, особенно в `Friction`.
3. `hybrid` (`C`, `DE`) оказывается промежуточным режимом: заметный labour squeeze и существенная capital need, но без software-speed diffusion.

## 5. Ограничения

- `Δs^L_potential` взят из текущего central anchor `delta_sL_core`, а не из новой causal AI-regression.
- `γ_s` не идентифицирован историей; он задан как class-ordered structural parameter на базе baseline margin.
- `ΔK` — это modelled capital requirement, а не наблюдаемый CAPEX forecast.
- Для России по-прежнему отсутствует современный прямой `K/L`; используется historical comparator anchor.

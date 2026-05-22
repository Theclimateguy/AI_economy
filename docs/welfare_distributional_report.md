# Welfare Distributional Report

Этот блок раскладывает `Stage 4` direct labour/capital reallocation по occupation-major groups и по income-quintile proxy.

## 1. Формализация

Пусть `l_{s,o}` — занятость occupation group `o` в секторе `s`, `e_o` — occupation AI exposure, `\Delta L_s` — sector employment delta из `Stage 4`.

Секторный employment shock распределяется по occupations как exposure-weighted allocation:

$$
\omega_{s,o} =
\frac{l_{s,o} e_o}{\sum_{o'} l_{s,o'} e_{o'}},
\qquad
\Delta L_{s,o} = \omega_{s,o} \Delta L_s
$$

Базовый labour income по ячейке:

$$
Y^L_{s,o} = L_{s,o} \cdot w_s \cdot \mu_o
$$

где `w_s` — официальный sector wage за `2024`, а `\mu_o` — occupation wage multiplier proxy по ISCO08 major groups.

Incremental profit pool распределяется по quintile proxy через capital-income weights
`(0, 0, 0.05, 0.20, 0.75)` для `Q1..Q5`.

## 2. Источники

- Russian `occupation × industry` matrix: `data/raw/ilostat/emp_temp_eco_ocu_nb_a.csv.gz` (`RUS`, `2024`, `ISCO-08`, `ISIC4`)
- OECD figure data for AI exposure: [stat.link/2q5i1s](https://stat.link/2q5i1s)
- Rosstat sector wages: `data/raw/russia/tab3-zpl_2025.xlsx`
- Stage 4 sector outcomes: `data/processed/russia_economy_structure_sector_summary.csv`

Ключевая оговорка: в repo нет RLMS/LFS microdata по индивидуальным доходам. Поэтому quintile block ниже — это transparent proxy через `ISCO08` wage multipliers и sector wages, а не household micro-estimation.

## 3. Highest Exposure Occupations

| occupation_digit | occupation_name_isco08 | ai_exposure_score | baseline_employment_thousand | employment_delta_2035_thousand |
| --- | --- | --- | --- | --- |
| 1.0 | Managers | 0.816 | 1519.595 | -48.013 |
| 2.0 | Professionals | 0.806 | 8696.048 | -401.101 |
| 4.0 | Clerical support workers | 0.746 | 1341.068 | -37.029 |
| 3.0 | Technicians and associate professionals | 0.742 | 3975.567 | -110.279 |
| 5.0 | Services and sales workers | 0.624 | 799.712 | -12.868 |

## 4. Largest Employment Losses

| occupation_digit | occupation_name_isco08 | baseline_employment_thousand | employment_delta_2035_thousand | loss_per_baseline_pct |
| --- | --- | --- | --- | --- |
| 2.0 | Professionals | 8696.048 | -401.101 | -4.612 |
| 3.0 | Technicians and associate professionals | 3975.567 | -110.279 | -2.774 |
| 7.0 | Craft and related trades workers | 7773.117 | -76.967 | -0.990 |
| 1.0 | Managers | 1519.595 | -48.013 | -3.160 |
| 8.0 | Plant and machine operators, assemblers | 6701.619 | -37.090 | -0.553 |

## 5. Quintile Proxy

| quintile | baseline_employment_thousand | employment_delta_2035_thousand | labour_income_delta_2035_bn_rub | profit_gain_allocated_bn_rub | total_income_delta_bn_rub |
| --- | --- | --- | --- | --- | --- |
| Q1 | 6574.700 | -40.308 | -381.436 | 0.000 | -381.436 |
| Q2 | 6574.700 | -36.473 | -372.719 | 0.000 | -372.719 |
| Q3 | 6574.700 | -102.775 | -605.557 | 525.147 | -80.410 |
| Q4 | 6574.700 | -156.039 | -1248.387 | 2100.588 | 852.201 |
| Q5 | 6574.700 | -390.748 | -1883.771 | 7877.204 | 5993.433 |

Baseline grouped-labour Gini proxy равен `0.290`. После AI reallocation и top-quintile-heavy profit capture он сдвигается до `0.380`, то есть `ΔGini = 0.090`.

## 6. Интерпретация

- Профессиональный риск концентрируется в white-collar major groups `1-4`, где OECD/Felten-derived exposure highest.
- Абсолютные employment losses всё равно велики и в крупных middle-skill группах, потому что они сидят внутри `C`, `J`, `M` и `K`.
- Quintile proxy показывает типичный pattern: labour losses and weak labour-income growth давят `Q1-Q4`, а profit-pool expansion концентрируется в `Q5`.
- Это welfare accounting, а не causal micro-simulation: без RLMS/LFS невозможно честно отделить within-occupation wage dispersion, secondary earners и regional heterogeneity.

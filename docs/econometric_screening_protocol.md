# Econometric Screening Protocol

Цель не подтвердить заранее придуманные инварианты, а отфильтровать только те регулярности, которые выдерживают строгую панельную проверку.

## Принцип

Для каждого кандидата $I_j$ заранее фиксируется:

$$
y_{cst} = \beta_j \Delta ICT_{cst} + \theta_j \log(K/L)_{cs,t-1} + \alpha_c + \gamma_s + \tau_t + \varepsilon_{cst},
$$

где:

- $c$ — страна,
- $s$ — сектор,
- $t$ — год,
- $\alpha_c$, $\gamma_s$, $\tau_t$ — country, sector и year fixed effects.

Важно: это screening на историческую устойчивость, а не сильное каузальное утверждение.

## Текущий набор проверяемых структурных инвариантов

- `I2`: `d_labour_share ~ lag_d_techint + rti + lag_d_techint:rti + country_fe + year_fe`
- `I3`: `d_emp_per_va ~ lag_d_techint + rti + lag_d_techint:rti + country_fe + year_fe`
- `I6`: `d_margin ~ lag_d_techint + lag_margin + country_fe + year_fe`
- `I8`: `d_occ ~ lag_d_techint + country_fe + year_fe`

Здесь:

- `techint = K_ICT / K_total`,
- `rti` — статический sector RTI из base-year staffing matrix (`ILOSTAT x Lewandowski`),
- `margin = 1 - D1/B1G - D29X39/B1G`,
- `occ = (K - wL)/wL`,
- `emp_per_va = L / VA_real`.

## Критерии прохождения

Кандидат проходит только если одновременно выполнено всё:

1. В baseline FE-спецификации знак совпадает с заранее зафиксированным.
2. `p < 0.05` в baseline со стандартными ошибками, кластеризованными по стране.
3. После Benjamini-Hochberg поправки по семейству тестов `q < 0.10`.
4. Placebo lead-тест незначим: будущая $\Delta TechInt_{c,s,t+1}$ не должна “объяснять” текущий $y_{cst}$, то есть `p_placebo > 0.10`.
5. Доля спецификаций с тем же знаком не ниже `0.8`.
6. Доля leave-one-country-out оценок с тем же знаком не ниже `0.8`.
7. В выборке не меньше `100` наблюдений и `12` стран.

Если какой-то пункт не проходит, кандидат не считается устойчивым инвариантом. Это намеренно строгий фильтр.

## Робастные спецификации

- baseline: FE + кластер по стране
- cluster sensitivity: FE + кластер по паре `country-sector`
- heteroskedasticity sensitivity: `HC3`
- sample sensitivity: исключаем `USA` и `JPN`
- trend sensitivity: добавляем country-specific linear trends
- leave-one-country-out: исключаем по одной стране

## Интерпретация результата

- `survive`: можно переносить как исторически устойчивый benchmark-кандидат
- `tentative`: есть сигнал, но он недостаточно чистый для калибровки инварианта
- `reject`: переносить в модель нельзя

Если survives останется 2–3 из 8, это нормальный результат. Хуже было бы протащить в балансную модель ложные “инварианты”.

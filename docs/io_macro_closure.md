# IO Macro Closure

Этот блок добавляет partial input-output closure поверх `Stage 4` direct accounting layer и считает backward-linkage propagation для проектных секторов `B, C, DE, F, H, J, K, M`.

## 1. Формализация

Для агрегированного `8 x 8` use matrix:

\[
A_{ij} = \frac{Z_{ij}}{x_j},
\qquad
L = (I - A)^{-1}
\]

где `Z` — промежуточное потребление, `x` — выпуск сектора, `A` — матрица прямых затрат.

Direct `Stage 4` shock переводится в output-equivalent impulse через value-added coefficient:

\[
v_s = \frac{VA_s}{x_s},
\qquad
\Delta f_s = \frac{\Delta VA^{direct}_s}{v_s}
\]

Тогда total output response:

\[
\Delta x = L \Delta f,
\qquad
\Delta x^{indirect} = (L - I) \Delta f
\]

А IO-adjusted value added и занятость считаются через fixed coefficients:

\[
\Delta VA^{IO} = \operatorname{diag}(v) \Delta x,
\qquad
\Delta EMP^{indirect} = \operatorname{diag}(n) \Delta x^{indirect}
\]

где `n_s = EMP_s / x_s` калибруется на `2035` counterfactual из `Stage 4`.

Import content:

\[
m_s = \frac{M_s}{x_s},
\qquad
IC = \sum_s m_s \Delta x_s
\]

Для санкционного import substitution считаем first-pass haircut:

\[
m^{sanction}_s = m_s (1 - \omega_s)
\]

где `\omega_s` — sector sanction wedge из `import_friction_layer.py`.

## 2. Источники

- Rosstat accounts page: [rosstat.gov.ru/accounts](https://rosstat.gov.ru/accounts)
- 2016 base IO table: [baz-tzv-2016(1).xlsx](https://rosstat.gov.ru/storage/mediabank/baz-tzv-2016(1).xlsx)
- 2019 supply-use tables: [tri-2019.xlsx](https://rosstat.gov.ru/storage/mediabank/tri-2019.xlsx)
- WIOD reference for methodology: [rug.nl/ggdc/valuechain/wiod](https://www.rug.nl/ggdc/valuechain/wiod/)

Важная оговорка на `30 апреля 2026`: на странице Rosstat есть базовая `ТЗВ 2016` и `TRI 2019`, но не опубликована отдельная базовая `ТЗВ 2019`. Поэтому `2019` блок строится из `ТИоц` и `М-имп` после агрегации к проектным восьми секторам; `2016` используется как structural cross-check.

## 3. Aggregate Comparison

| table_year | accounting_total_va_gain_2035_pct | io_total_va_gain_2035_pct_of_cf | direct_va_gain_2035_bn_rub | io_indirect_va_gain_2035_bn_rub | io_total_va_gain_2035_bn_rub | direct_employment_delta_2035_thousand | io_indirect_employment_support_2035_thousand | io_net_employment_delta_2035_thousand | import_content_base_2035_bn_rub |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | 4.549 | 7.281 | 6878.828 | 4132.745 | 11011.573 | -726.342 | 902.758 | 176.416 | 1417.953 |
| 2019 | 4.549 | 7.347 | 6878.828 | 4232.693 | 11111.521 | -726.342 | 874.704 | 148.363 | 1381.742 |

Базовый вывод устойчив: direct accounting headline `4.55%` для `VA` заметно недооценивает total production-chain effect. На `2019` таблице `BaseThrottle` даёт `7.35%` к `2035` counterfactual `VA`, из которых `4.23 трлн руб.` — это косвенный supply-chain effect сверх прямого sector-level gain.

При этом занятость меняет знак: direct accounting даёт `-726 тыс.`, но IO-блок возвращает `+875 тыс.` косвенного спроса на upstream/downstream цепочки, так что net partial-closure effect становится `+148 тыс.`. Это не означает full-equilibrium занятость; это именно Leontief demand-support effect без цен, wages и crowding-out.

## 4. Backward Linkages

| sector_id | sector_name_ru | backward_linkage_multiplier | own_sector_output_multiplier | io_indirect_va_gain_2035_bn_rub |
| --- | --- | --- | --- | --- |
| C | Обрабатывающая промышленность | 2.105 | 1.567 | 1590.786 |
| J | ИТ и связь | 1.685 | 1.333 | 831.087 |
| M | Профессиональные и научные услуги | 1.589 | 1.172 | 797.713 |
| K | Финансы и страхование | 1.340 | 1.180 | 712.935 |
| DE | Энергетика и ЖКХ | 2.158 | 1.566 | 172.935 |
| F | Строительство | 1.911 | 1.037 | 49.210 |
| H | Транспорт и логистика | 1.777 | 1.241 | 48.045 |
| B | Добыча полезных ископаемых | 1.440 | 1.091 | 29.981 |

Самые сильные backward linkages у `DE`, `C` и `F`; именно поэтому даже умеренный direct AI-shock в utilities даёт disproportionate indirect effect, а manufacturing остаётся главным multiplier channel в абсолютных рублях.

## 5. Import Content Under Sanctions

| sector_id | sector_name_ru | import_content_base_2035_bn_rub | import_content_sanction_base_2035_bn_rub | import_content_sanction_saving_base_2035_bn_rub |
| --- | --- | --- | --- | --- |
| C | Обрабатывающая промышленность | 601.548 | 539.119 | 62.428 |
| J | ИТ и связь | 301.993 | 271.282 | 30.711 |
| M | Профессиональные и научные услуги | 292.176 | 272.246 | 19.930 |
| K | Финансы и страхование | 122.341 | 107.240 | 15.101 |
| DE | Энергетика и ЖКХ | 25.192 | 22.757 | 2.436 |

Для агрегированного `2019 BaseThrottle` shock vector import content оценивается в `1381.742 млрд руб.`. First-pass sanction substitution haircut снижает его до `1247.596 млрд руб.` в `SanctionBase` equivalent accounting, то есть экономит `134.146 млрд руб.` внешней компонентной зависимости.

## 6. Ограничения

- `2019` строится из supply-use, а не из опубликованной симметричной `ТЗВ`; это корректно на уровне `8` агрегатов, но слабее full product-technology reconstruction.
- Используется открытая quantity-side Leontief closure без цен, substitution, bottleneck capacity и monetary policy.
- Employment response трактуется как fixed-coefficient demand support поверх direct labour-saving из `Stage 4`; это upper bound для short-run chain re-absorption.
- Import substitution задана через sanction wedges из previous issue, а не через отдельную dynamic trade model.

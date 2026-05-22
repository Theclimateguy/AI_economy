# RTI Proxy Method

Текущий `RTI` в панели строится через historical staffing matrix с фиксированными base-year weights:

$$
RTI_{c,s,t_0} = \sum_{o=1}^{9} \omega_{c,s,o,t_0}\,RTI^{\text{Lewandowski}}_{c,o},
$$

где:

- $c$ — страна,
- $s$ — сектор,
- $o$ — 1-digit occupation group (`ISCO-88`),
- $t_0$ — base year окна (`1995`, fallback: `1994`, `1996`, `1993`, `1997`),
- $\omega_{c,s,o,t_0} = Emp_{c,s,o,t_0} / Emp_{c,s,t_0}$ — доля профессии в секторе на старте окна.

## Staffing Matrix Aggregation

Источник отраслево-профессиональной матрицы:

- `ILOSTAT EMP_TEMP_ECO_OCU_NB_A`
- коды отраслей: исторически доступны только `ECO_ISIC3_*` на 1-digit уровне для окна `1995–1997`
- коды занятий: `OCU_ISCO88_1 ... OCU_ISCO88_9`, `OCU_ISCO88_TOTAL`

Источник occupational RTI:

- Lewandowski country-specific RTI for `ISCO-88` 1-digit groups.

Алгоритм в pipeline:

1. Для каждой пары `(country, sector)` выбирается base-year staffing matrix с приоритетом `1995 -> 1994 -> 1996 -> 1993 -> 1997`.
2. Внутри выбранного года сохраняется один `ILOSTAT source`, чтобы не смешивать разные обследования в одной матрице.
3. Исторический crosswalk строится на `ISIC Rev.3 1-digit`:
   `B -> C`, `C -> D`, `D+E -> E`, `F -> F`, `H -> I`, `K -> J`, `J -> K`, `M -> K`.
4. Поле `staffing_proxy_exact` отделяет exact historical crosswalk от broad proxy:
   `H`, `J`, `M` в `ISIC3` наблюдаются только через более широкие сервисные агрегаты.
5. Если reported total меньше суммы occupation cells, total заменяется на сумму occupation cells.
6. Sector RTI считается только если coverage occupation weights не ниже `0.95`.
7. Внутри наблюдаемой occupation mass веса нормируются:

$$
\tilde{\omega}_{c,s,o,t_0} =
\frac{\omega_{c,s,o,t_0}}{\sum_{o \in \mathcal{O}_{obs}} \omega_{c,s,o,t_0}}.
$$

Итоговый секторный индекс:

$$
RTI_{c,s,t_0} = \sum_{o \in \mathcal{O}_{obs}} \tilde{\omega}_{c,s,o,t_0}\,RTI_{c,o}.
$$

## Почему именно base-year weights

Если использовать contemporaneous weights, возникает эндогенность:

$$
\text{technology shock} \rightarrow \text{сжатие рутинных профессий} \rightarrow \text{падение их веса} \rightarrow RTI_{c,s,t} \downarrow
$$

тогда сам индекс рутинности частично становится следствием технологического шока. Base-year aggregation устраняет этот канал.

## Выходные файлы

- `data/processed/rti_matrix_proxy.csv`
- `data/processed/staffing_matrix_base_weights.csv`
- `data/processed/staffing_matrix_metadata.json`

## Ограничения

- Это всё ещё статический `RTI_{c,s,t_0}`, а не time-varying task composition.
- Для части стран и секторов base year может быть заменён ближайшим fallback year.
- Для `H`, `J`, `M` историческая staffing matrix остаётся broad proxy из-за ограничений `ISIC3 1-digit`.
- Coverage threshold `0.95` намеренно строгий: лучше потерять часть country-sector пар, чем втащить шумную задачно-профессиональную структуру в screening.

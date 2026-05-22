# Russia AI Scenario Mechanics

Цель этого слоя не оценить ещё одну регрессию, а превратить исторические `ΔTC` из ИКТ-эпохи в воспроизводимые sector-level shocks для российской балансовой / CGE-модели.

## 1. Исторический benchmark

Для каждого сектора $s$ используется long-difference распределение:

$$
\Delta TC_{c,s}^{1995\rightarrow 2005} = \left(\frac{wL}{VA}\right)_{c,s,2005} - \left(\frac{wL}{VA}\right)_{c,s,1995}.
$$

Из него уже рассчитаны:

- $\mu_s = \mathbb{E}[\Delta TC_s]$
- $\tilde{\mu}_s = \text{median}(\Delta TC_s)$
- $\sigma_s = \text{sd}(\Delta TC_s)$
- tail anchors $q10_s, q25_s$

Источник: [task_content_sector_benchmarks_1995_2005.csv](../data/processed/task_content_sector_benchmarks_1995_2005.csv).

## 2. RTI regime

Так как российская staffing matrix ещё не построена из ОРС/ОКЗ, текущий `RTI` для сценариев берётся как historical sector median из comparator panel:

$$
RTI_s^{hist} = \text{median}_c(RTI_{c,s}).
$$

Дальше сектора раскладываются на `low / medium / high` по tertiles этого historical sector RTI.

Текущие cutoffs, полученные из [russia_ai_sector_scenarios_metadata.json](../data/processed/russia_ai_sector_scenarios_metadata.json):

- `low`: $RTI_s^{hist} \le 0.0571$
- `medium`: $0.0571 < RTI_s^{hist} \le 0.4207$
- `high`: $RTI_s^{hist} > 0.4207$

Это временный proxy. Когда будет построен российский `RTI_s^{RU}`, bucketization нужно будет просто заменить без изменения downstream formulas.

## 3. Сценарий шока по доле труда

Для сектора $s$ задаются три anchors:

$$
\Delta s^{L,\text{baseline}}_s = \mu_s,
$$

$$
\Delta s^{L,\text{core}}_s = \mu_s - m^{AI}_{core}(s)\,w^{RTI}(s)\,\sigma_s,
$$

$$
\Delta s^{L,\text{stress}}_s = \mu_s - m^{AI}_{stress}(s)\,w^{RTI}(s)\,\sigma_s.
$$

Где:

- $m^{AI}_{core}, m^{AI}_{stress}$ — множители по `AI_intensity`
- $w^{RTI}$ — вес по RTI bucket

### AI multipliers

| AI intensity | Core | Stress |
|---|---:|---:|
| `high` | `1.00` | `2.00` |
| `medium` | `0.75` | `1.50` |
| `low_medium` | `0.50` | `1.00` |
| `low` | `0.25` | `0.50` |

### RTI weights

| RTI bucket | Weight |
|---|---:|
| `high` | `1.00` |
| `medium` | `0.75` |
| `low` | `0.50` |

Таким образом, требование "high AI + high RTI = 1–2σ downside shock" выполняется буквально, а для остальных секторов shock intensity затухает плавно.

## 4. Маржа

Из screening переносится не tech beta, а только скорость эрозии маржи:

$$
\Delta margin_{s,t} = -\lambda\,margin_{s,t-1} + \varepsilon_{s,t},
$$

где $\lambda = |\hat{\beta}_{I6,\;lag\_margin}|$.

Практически это означает:

- initial profit pulse в модели можно задать экзогенно;
- дальше маржа затухает со скоростью $\lambda$, не требуя спорной оценки прямого AI-effect на margins.

Текущая оценка из screening:

- `margin_erosion_coef = -0.04195`
- `margin_erosion_speed = 0.04195`
- `p = 0.00073`, `q = 0.00363`

## 5. Выходной файл

Скрипт [build_russia_ai_scenarios.py](../scripts/build_russia_ai_scenarios.py) сохраняет:

- `data/processed/russia_ai_sector_scenarios.csv`
- `data/processed/russia_ai_sector_scenarios_metadata.json`

Ключевые поля:

- `delta_sL_baseline_mean`
- `delta_sL_baseline_median`
- `delta_sL_core`
- `delta_sL_stress`
- `delta_sL_tail_q25`
- `delta_sL_tail_q10`
- `margin_erosion_coef`
- `margin_erosion_speed`

## 6. Ограничения

- `H/J/M` всё ещё несут historical staffing proxy, потому что в ILOSTAT для этого окна есть только `ISIC Rev.3 1-digit`.
- `M` остаётся вне margin-based benchmark sample, но task-content benchmark для него считается, потому что для `ΔTC` нужна только labour share.
- Сценарная таблица для РФ пока использует historical RTI buckets, а не российскую occupation matrix. Это надо заменить, когда будет собрана ОРС `ОКВЭД × ОКЗ`.

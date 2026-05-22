# Problem Statement

## Цель

Построить воспроизводимую эмпирическую рамку для анализа влияния ИИ на отрасли экономики РФ на базе:

- исторических аналогий технологических революций;
- строгого screening гипотез инвариантов;
- перехода от невыживших линейных бет к сценарным task-content shocks;
- динамической модели диффузии, маржи и капитальных затрат;
- политэкономического слоя managed obsolescence, где frontier capability может развертываться не полностью из-за replacement cycles, compatibility lock-in, repair/access restrictions, regulation и риска трудового backlash.

## Объект анализа

8 секторов, покрывающих полюса российской экономики:

- `B` добыча полезных ископаемых
- `C` обрабатывающая промышленность
- `DE` энергетика и ЖКХ
- `F` строительство
- `H` транспорт и логистика
- `J` ИТ и связь
- `K` финансы и страхование
- `M` профессиональные и научные услуги

## Целевые переменные

- выпуск
- доля труда / labour share
- маржинальность
- капиталовооруженность и органическое строение капитала
- трудовые ресурсы

## Двухэтапная логика

### Этап 1. Проверка инвариантов

Гипотеза: существуют исторически устойчивые структурные инварианты, которые можно оценить на ИКТ-эпохе и перенести на ИИ.

Практически это означает:

- сбор comparator panel;
- screening уравнений с жесткой защитой от ложноположительных результатов;
- отказ от невыживших betas;
- переход к historical distributions of `ΔTC`.

### Этап 2. Диффузия и адаптация

Если универсальной beta нет, то прогноз строится через:

- sector-level potential shocks `Δs^L`;
- Bass-type diffusion by adoption class;
- margin dynamics с surviving erosion parameter `λ`;
- capital need и capital return functions.

## Формализация ядра

$$
\frac{dA_s}{dt} = (p_s + q_s A_s)(1 - A_s)
$$

$$
\Delta s^L_{s,t} = \Delta s^{L,potential}_s \cdot A_s(t)
$$

$$
\pi_{s,t} = \pi_{s,0} + \gamma_s A_s(t) - \lambda \pi_{s,t-1}
$$

$$
a_{s,t} = q_t A_s(t)(1-\tau_{s,t})
$$

где:

- $A_s(t)$ — накопленная адаптация;
- $p_s, q_s$ — параметры диффузии;
- $\Delta s^{L,potential}_s$ — потенциальный шок доли труда;
- $\gamma_s$ — adoption premium;
- $\lambda$ — исторически выжившая скорость эрозии маржи;
- $q_t$ — frontier capability ИИ;
- $a_{s,t}$ — deployed capability в секторе;
- $\tau_{s,t}$ — managed-obsolescence / throttling wedge.

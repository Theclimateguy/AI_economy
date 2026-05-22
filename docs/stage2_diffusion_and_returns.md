# Stage 2: Diffusion, Adaptation, Capital Returns

## Задача

После отказа от неустойчивых regression betas построить структурную модель sector dynamics в РФ через:

- historical task-content shocks,
- официальную baseline-картину РФ,
- class-based diffusion,
- margin dynamics,
- capital need и capital return.

## Шаги

1. Собран официальный baseline РФ по `VA`, employment, wage и proxy labour share.
2. Historical `ΔTC` превращены в sector-level `Δs^L_potential`.
3. Сектора разбиты на три adoption classes:
   - `software`
   - `hardware`
   - `hybrid`
4. Для каждого класса заданы `p,q`, margin premium и capital barrier.
5. Построены annual paths `2025–2035`.
6. Отдельно посчитана capital-return функция с контрфактической маржей без AI-premium.

## Формализация

$$
\frac{dA_s}{dt} = (p_s + q_s A_s)(1 - A_s)
$$

$$
\Delta s^L_{s,t} = \Delta s^{L,potential}_s \cdot A_s(t)
$$

$$
\pi_{s,t} = \pi_{s,0} + \gamma_s A_s(t) - \lambda \pi_{s,t-1}
$$

## Ключевой вывод по классам

- `software`: high adoption, low capex, high margin growth, very high capital return
- `hardware`: low adoption, high capex, late or absent payback under frictions
- `hybrid`: medium adoption, medium capex, intermediate but uncertain return

## Эмпирический итог

### Diffusion

- `software` достигает `A≈0.88` к `2035` в `Base`
- `hybrid` достигает только `A≈0.33`
- `hardware` достигает только `A≈0.11`

### Capital returns

В `Base` к `2035` class-level `net return`:

- `software ≈ 37.7`
- `hybrid ≈ 3.94`
- `hardware ≈ 1.36`

Во `Friction` hardware-class в целом не окупается к `2035`.

## Ключевые артефакты

- scenarios: `data/processed/russia_ai_sector_scenarios.csv`
- Russia baseline: `data/processed/russia_sector_baseline_2024.csv`
- diffusion: `data/processed/ai_diffusion_paths_2025_2035.csv`
- capital returns: `data/processed/ai_capital_return_sector_summary.csv`
- reports:
  - `docs/russia_ai_sector_report.md`
  - `docs/russia_ai_diffusion_report.md`
  - `docs/russia_ai_capital_return_report.md`

# CRITIC OKVED Resilience Model

Короткий слой для расчёта интегральной устойчивости отраслей по ОКВЭД методом CRITIC.

## Что внутри

- `scripts/build_okved_resilience_model.py` - базовая CRITIC-модель, веса, рейтинг 2024, робастность и historical backtest.
- `scripts/plot_okved_resilience_2030.py` - графики CRITIC-устойчивости до 2030.
- `docs/okved_resilience_critic_method_short.md` - краткая методичка.
- `docs/okved_resilience_model.md` - отчёт по базовой модели и проверкам.
- `docs/okved_resilience_2030_figures.md` - отчёт по графикам до 2030.
- `data/processed/okved_resilience_*.csv|json` - расчётные таблицы и метаданные.
- `output/figures/okved_resilience/*.png` - графики индекса, рангов, блоков и весов.

## Запуск

```bash
python scripts/build_okved_resilience_model.py --bootstrap 500 --seed 42

python scripts/plot_okved_resilience_2030.py \
  --scenario Base \
  --throttle BaseThrottle \
  --climate-scenario OrderlyTransition
```

## Главный результат

Базовая модель проходит проверки робастности рангов, но historical rolling-origin backtest пока даёт статус `tentative`, а не `pass`.

Топ forward-рейтинга CRITIC на 2030:

1. `M` - профессиональные и научные услуги
2. `K` - финансы и страхование
3. `J` - ИТ и связь
4. `G` - торговля
5. `C_mach` - машиностроение

## Ограничение

Банковские блоки пока построены на отраслевых прокси. Для production-модели нужны фактические данные по ОКВЭД: RAROC, cost of risk, NPL, портфель, выдачи, лимиты, PD/LGD и залоговое покрытие.


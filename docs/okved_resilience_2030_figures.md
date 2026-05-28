# Графики CRITIC-устойчивости ОКВЭД до 2030

Построены только графики по самой модели устойчивости CRITIC: итоговый индекс, ранги, блоковые scores и CRITIC-веса. Экономические scatter/opportunity-графики не включены.

## Веса блоков 2030

| criterion | label | weight |
| --- | --- | --- |
| credit_potential | Кредитный потенциал | 0.255 |
| strategic_convergence | Стратегическая конвергенция | 0.215 |
| adaptive_potential | Адаптивность | 0.199 |
| financial_stability | Финансовая устойчивость | 0.186 |
| bank_profitability | Доходность для банка | 0.146 |

## Forward-рейтинг 2030

| forward_rank | sector_id | sector_name_ru | forward_resilience_index | adaptive_potential | credit_potential | bank_profitability | financial_stability | strategic_convergence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | M | Профессиональные и научные услуги | 0.591 | 0.809 | 0.215 | 0.75 | 0.756 | 1.0 |
| 2 | K | Финансы и страхование | 0.442 | 1.0 | 0.362 | 0.874 | 0.144 | 0.787 |
| 3 | J | ИТ и связь | 0.391 | 0.929 | 0.276 | 0.642 | 0.127 | 1.0 |
| 4 | G | Оптовая и розничная торговля | 0.314 | 0.223 | 0.325 | 0.323 | 0.546 | 0.252 |
| 5 | C_mach | Машиностроение (ОКВЭД 26–30) | 0.302 | 0.426 | 0.165 | 0.268 | 0.356 | 0.423 |
| 6 | C | Обрабатывающая промышленность без машиностроения | 0.288 | 0.318 | 0.575 | 0.431 | 0.212 | 0.151 |
| 7 | B | Добыча полезных ископаемых | 0.185 | 0.09 | 0.786 | 0.178 | 0.198 | 0.087 |
| 8 | H | Транспорт и логистика | 0.15 | 0.122 | 0.349 | 0.087 | 0.214 | 0.094 |
| 9 | DE | Энергетика и ЖКХ | 0.138 | 0.059 | 0.115 | 0.139 | 0.188 | 0.404 |
| 10 | F | Строительство | 0.109 | 0.152 | 0.065 | 0.019 | 0.265 | 0.245 |

## Файлы графиков

- `output/figures/okved_resilience/critic_resilience_index_paths_top5_2025_2030.png`
- `output/figures/okved_resilience/critic_resilience_rank_paths_2025_2030.png`
- `output/figures/okved_resilience/critic_resilience_rank_shift_2024_2030.png`
- `output/figures/okved_resilience/critic_resilience_index_2030.png`
- `output/figures/okved_resilience/critic_resilience_block_heatmap_2030.png`
- `output/figures/okved_resilience/critic_resilience_block_weights_2030.png`

## Воспроизводимость

- Скрипт: `python scripts/plot_okved_resilience_2030.py --scenario Base --throttle BaseThrottle --climate-scenario OrderlyTransition`
- Панель: `data/processed/okved_resilience_forward_paths_2025_2030.csv`
- Summary 2030: `data/processed/okved_resilience_forward_summary_2030.csv`
- Веса: `data/processed/okved_resilience_forward_weights_2030.csv`

## Интерпретационное ограничение

Это не новая банковская production-модель, а визуализация CRITIC-устойчивости на имеющихся сценарных прокси. Фактические RAROC, выдачи, NPL и cost of risk по ОКВЭД всё ещё нужны для калибровки банковских блоков.

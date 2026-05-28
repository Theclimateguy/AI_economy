# CRITIC-модель устойчивости отраслей по ОКВЭД

## Постановка

Индекс строится как иерархический CRITIC: сначала CRITIC-веса внутри пяти блоков, затем CRITIC-веса самих блоков. Агрегация базово геометрическая, чтобы слабый блок не полностью компенсировался сильным. Для банковской логики добавлен мягкий risk-gate по финансовой устойчивости:

$$R_i=\left(\prod_b B_{ib}^{W_b}\right)\exp\{-\lambda\max(0,\delta-B_{i,financial})^2\},$$

где $\delta=0.35$, $\lambda=3.0$. Данные банковской доходности и кредитного портфеля в папке отсутствуют, поэтому эти блоки собраны как явно помеченные отраслевые прокси.

## Топ-уровневые веса

| criterion | label | weight |
| --- | --- | --- |
| adaptive_potential | Adaptive potential | 0.204 |
| credit_potential | Credit potential | 0.166 |
| bank_profitability | Bank profitability proxy | 0.261 |
| financial_stability | Financial stability | 0.173 |
| strategic_convergence | Strategic convergence | 0.197 |

## Рейтинг 2024

| rank | sector_id | sector_name_ru | okved | resilience_index | adaptive_potential | credit_potential | bank_profitability | financial_stability | strategic_convergence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | M | Профессиональные и научные услуги | M | 0.487 | 0.605 | 0.187 | 0.629 | 0.682 | 0.463 |
| 2 | C | Обрабатывающая промышленность без машиностроения | C excl. 26-30 | 0.415 | 0.543 | 0.494 | 0.267 | 0.572 | 0.367 |
| 3 | K | Финансы и страхование | K | 0.395 | 0.65 | 0.124 | 0.81 | 0.211 | 0.561 |
| 4 | J | ИТ и связь | J | 0.329 | 0.63 | 0.201 | 0.323 | 0.303 | 0.292 |
| 5 | G | Оптовая и розничная торговля | G | 0.193 | 0.251 | 0.327 | 0.215 | 0.225 | 0.091 |
| 6 | C_mach | Машиностроение (ОКВЭД 26–30) | C 26-30 | 0.189 | 0.111 | 0.183 | 0.172 | 0.227 | 0.405 |
| 7 | DE | Энергетика и ЖКХ | D+E | 0.165 | 0.228 | 0.098 | 0.063 | 0.357 | 0.339 |
| 8 | H | Транспорт и логистика | H | 0.136 | 0.254 | 0.204 | 0.045 | 0.39 | 0.087 |
| 9 | F | Строительство | F | 0.097 | 0.558 | 0.224 | 0.015 | 0.35 | 0.032 |
| 10 | B | Добыча полезных ископаемых | B | 0.088 | 0.076 | 0.12 | 0.103 | 0.176 | 0.056 |

## Робастность рангов

| check_type | n | median_spearman | p10_spearman | min_spearman | median_kendall | min_top3_overlap | decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| aggregation | 1 | 0.806 | 0.806 | 0.806 | 0.6 | 1.0 | pass |
| bootstrap_sector_weights | 500 | 0.976 | 0.939 | 0.855 | 0.911 | 0.667 | pass |
| leave_one_block | 5 | 0.952 | 0.91 | 0.891 | 0.867 | 0.667 | pass |
| leave_one_indicator | 31 | 1.0 | 0.976 | 0.952 | 1.0 | 0.667 | pass |
| leave_one_sector_weight_fit | 10 | 0.994 | 0.976 | 0.976 | 0.978 | 1.0 | pass |
| normalization | 2 | 0.964 | 0.944 | 0.939 | 0.889 | 1.0 | pass |
| risk_gate | 1 | 0.988 | 0.988 | 0.988 | 0.956 | 1.0 | pass |
| weights | 1 | 0.988 | 0.988 | 0.988 | 0.956 | 1.0 | pass |

Правило: `pass`, если медианная Spearman-корреляция с базовым рейтингом >= 0.80 и 10-й перцентиль >= 0.60; `tentative`, если >= 0.60 и >= 0.40; иначе `fail`.

## Исторический rolling-origin backtest

Историческая версия использует только официальные метрики, доступные в панели 2011-2025: рост ВДС, волатильность, доли ВДС/занятости, зарплаты, proxy margin и класс AI-интенсивности. Целевая переменная:

$$Y_{i,t,h}=\bar g_{i,t+1:t+h}-0.5\sigma(g_{i,t+1:t+h})+0.25\min(g_{i,t+1:t+h}).$$

| horizon_years | n_origins | median_spearman | mean_spearman | share_positive_spearman | median_kendall | mean_top_bottom_spread_pp | share_positive_top_bottom_spread | median_ols_slope | share_positive_ols_slope | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 5 | 0.188 | 0.316 | 1.0 | 0.156 | 3.803 | 0.6 | 12.662 | 0.6 | tentative |
| 2 | 5 | 0.261 | 0.253 | 1.0 | 0.2 | 2.84 | 0.8 | 8.813 | 1.0 | tentative |
| 3 | 5 | 0.212 | 0.285 | 1.0 | 0.2 | 3.046 | 0.8 | 9.756 | 1.0 | tentative |

Правило: `pass`, если median Spearman >= 0.30 и top-bottom spread положителен минимум в 70% origin-years; `tentative`, если median Spearman > 0 и spread положителен минимум в 60%; иначе `fail`.

## Воспроизводимость

- Скрипт: `python scripts/build_okved_resilience_model.py --bootstrap 500 --seed 42`
- Матрица признаков: `data/processed/okved_resilience_feature_matrix_2024.csv`
- Рейтинг: `data/processed/okved_resilience_ranking_2024.csv`
- Веса: `data/processed/okved_resilience_weights_2024.csv`
- Робастность: `data/processed/okved_resilience_robustness_checks.csv`
- Backtest: `data/processed/okved_resilience_historical_backtest.csv`

## Ограничения

- Наблюдений всего 10 секторов, поэтому CRITIC-веса чувствительны к составу отраслей; bootstrap/leave-one-sector это прямо проверяют.
- Банковские метрики заменены прокси; для production-версии нужны фактические RAROC, cost of risk, NPL, лимиты, портфель и выдачи по ОКВЭД.
- Исторический backtest проверяет не тот же полный forward-рейтинг, а его официальную историческую проекцию без AI/климат/капиталоотдачи будущих сценариев.

# Managed Obsolescence Layer

## Зачем этот слой

Новый слой добавляет к сценарию ИИ политэкономический тормоз: frontier capability может существовать, но deployed capability ограничивается через срок полезности, совместимость, доступ, ремонт, обновления, лицензирование или регуляторные gates.

Базовая формализация:

\[
q_t = \text{frontier capability}, \qquad a_{s,t} = \text{deployed capability in sector } s
\]

\[
a_{s,t} = q_t A_{s,t}(1-\tau_{s,t})
\]

где \(A_{s,t}\) — технологическая адаптация из Stage 2, а \(\tau_{s,t}\) — managed-obsolescence / throttling wedge. В этом исследовании \(\tau_{s,t}\) трактуется не как доказательство сговора, а как измеряемая склонность сектора к управляемому замедлению внедрения при высоких социальных и отраслевых издержках.

## Исторические механизмы

| Механизм | Исторический пример | Что переносится на ИИ |
|---|---|---|
| Physical durability limits | Phoebus cartel and lamp lifetime standards | Умышленное или институциональное ограничение срока полезности продукта |
| Dynamic obsolescence | GM annual model changes and styling cycles | Частые версии, refresh cycles, paid upgrades |
| Compatibility obsolescence | Software, devices, standards, proprietary parts | API deprecation, model retirement, closed weights, data-format lock-in |
| Repair/access restrictions | Repair restrictions documented by FTC | Compute access, diagnostics, fine-tuning, tool access, audit logs |
| Counter-policy | EU right-to-repair and ecodesign rules | Durability mandates, interoperability, open standards, auditability |

Главная аналитическая оговорка: historical planned obsolescence редко наблюдается как чистая переменная. Лучше измерять не "заговор", а каналы: replacement intensity, forced upgrade, repair restriction, compatibility lock-in, product-cycle compression, capability throttling.

## Связь с рынком труда

Технологический стресс для труда удобно задавать как разрыв между ростом производительности и динамикой часов:

\[
LS_s =
\Delta \ln LP_s - \Delta \ln H_s
\]

Если \(LS_s > 0\), производительность растет быстрее часов. Это не доказывает вытеснение труда, но показывает сектор, где быстрая автоматизация потенциально создает более сильный социальный и политический backlash.

Managed obsolescence может смягчать шок через более медленное внедрение:

\[
A^{managed}_{s,t} = A_{s,t}(1-\theta_s)
\]

где \(\theta_s\) — sector pressure score. Экономический смысл: часть эффективности откладывается, чтобы сохранить replacement cycles, занятость в смежных сервисах, rent extraction и предсказуемую адаптацию отраслей. Издержки: ниже welfare, больше капитальных и материальных потерь, слабее TFP.

## Данные

Добавлен источник `Russia KLEMS` ВШЭ:

- source page: https://cps.hse.ru/en/data/
- raw file: `data/raw/russia_klems/RUS_december_2019_0.xlsx`
- processed panel: `data/processed/russia_klems_sector_panel_1995_2016.csv`
- proxy output: `data/processed/managed_obsolescence_sector_proxy.csv`
- metadata: `data/processed/russia_klems_metadata.json`

Russia KLEMS Release 3 покрывает 1995-2016 и 34 отрасли в классификации NACE 1.0. Важные ограничения источника: 2015-2016 предварительные, labour shares зафиксированы на уровне 2014, для нефтегазовых отраслей есть проблема transfer pricing и распределения активности между mining, trade, fuel and transport.

Для актуализации добавлен официальный recent-block Росстата:

- `data/processed/russia_sector_panel_official_2011_2025.csv` для `VA`, занятости и wage-bill proxy;
- `data/raw/russia/ikt_org.xlsx` для отраслевого использования цифровых технологий;
- `data/raw/russia/koef_ved_2017_2021.xlsx` для коэффициента обновления основных фондов.

## Маппинг на отрасли проекта

| Project sector | Russia KLEMS code | Качество | Комментарий |
|---|---:|---|---|
| `B` добыча | `C` | exact old NACE | mining and quarrying |
| `C` обрабатывающая | `D` | exact old NACE | manufacturing |
| `DE` энергетика и ЖКХ | `E` | partial old NACE | electricity, gas and water supply |
| `F` строительство | `F` | exact old NACE | construction |
| `H` транспорт | `60t63` | partial old NACE | transport and storage |
| `J` ИТ и связь | `64` | weak proxy | post and telecommunications, not full OKVED2 J |
| `K` финансы | `J` | exact old NACE | financial intermediation |
| `M` проф. и научные услуги | `71t74` | weak proxy | renting, computer-related, R&D and business services |

## Proxy score

Исторический KLEMS score сохраняется для backward comparability:

\[
MOS_s =
0.35 N^+(g^{LP}_s - g^{H}_s)
+ 0.30 N^+(g^{CAP}_s - g^{LAB}_s)
+ 0.20 N^+(g^{CAPIT}_s - g^{CAPNIT}_s)
+ 0.15 N^+(-g^{EMP}_s)
\]

где \(g\) — CAGR за 1995-2016, \(N^+(\cdot)\) — min-max нормировка положительной части по восьми секторам.

Обновленный long-base score строится в два шага.

Сначала recent-block `2017–2024`:

\[
MOS^{recent}_s =
0.35 N^+(g^{LP,off}_s)
+ 0.30 N^+\left(0.5(g^{VA,real}_s - g^{FOT}_s) + 0.5 g^{renewal}_s\right)
+ 0.20 N^+(g^{ICTshare}_s)
+ 0.15 N^+(-g^{EMP,off}_s)
\]

Затем long-base blend `2000–2024` по component scores:

\[
S^{long}_{s,j} =
\frac{16}{23} S^{KLEMS(2000-2016)}_{s,j}
+ \frac{7}{23} S^{OFF(2017-2024)}_{s,j},
\qquad
MOS^{updated}_s = 0.35 S^{long}_{s,1} + 0.30 S^{long}_{s,2} + 0.20 S^{long}_{s,3} + 0.15 S^{long}_{s,4}
\]

Здесь:

- \(g^{LP,off}\) — CAGR real `VA per worker` proxy, так как часов по секторам в текущем repo нет;
- \(g^{FOT}\) — CAGR `employment * wage * 12`;
- \(g^{renewal}\) — CAGR коэффициента обновления основных фондов за `2017–2020`;
- \(g^{ICTshare}\) — CAGR proxy `0.5 * server_share + 0.5 * website_share` из `ikt_org.xlsx`.

Интерпретация компонентов:

- \(g^{LP} - g^{H}\): производительность растет быстрее отработанных часов;
- \(g^{CAP} - g^{LAB}\): capital services растут быстрее labour services;
- \(g^{CAPIT} - g^{CAPNIT}\): ICT capital services растут быстрее non-ICT capital services;
- \(-g^{EMP}\): сжатие занятости.

Этот score не идентифицирует намеренность. Он помечает отрасли, где быстрый ИИ-шок с большей вероятностью будет политически или организационно throttled.

## Первый результат для РФ

Ниже уже не legacy KLEMS rank, а обновленный `mos_score_updated`:

| Rank | Sector | Score | Read |
|---:|---|---:|---|
| 1 | `J` ИТ и связь | 0.649 | лидер сохраняется, но теперь score опирается не только на legacy telecom proxy, а и на recent digital block |
| 2 | `C` обрабатывающая | 0.426 | устойчиво высокий throttling-pressure: сочетание capital renewal, ICT use и large employment base |
| 3 | `K` финансы | 0.363 | главный upward re-rank: recent digitalization и productivity growth поднимают сектор с `7` на `3` место |
| 4 | `DE` энергетика и ЖКХ | 0.340 | второй крупный upward re-rank: strategic infrastructure больше не выглядит “низким stress” сектором |
| 5 | `B` добыча | 0.233 | historical pressure был выше, но recent official block делает картину более умеренной |
| 6 | `H` транспорт | 0.224 | средний, но устойчивый throttling-risk через infra/safety constraints |
| 7 | `F` строительство | 0.201 | recent block повышает цифровизацию меньше, чем капитальный цикл, поэтому сектор опускается ниже baseline intuition |
| 8 | `M` проф. и научные услуги | 0.169 | strongest downward re-rank: historical broad KLEMS proxy переоценивал текущий throttling-pressure сектора |

Главный прикладной вывод изменился: recent official block поднимает `K` и `DE`, а `M` больше не выглядит естественным top-3 bottleneck. Для downstream `Stage 2/4` это важно, потому что institutional throttling теперь сильнее смещается в сторону финансовой инфраструктуры и regulated utility systems, а не только в legacy `J/C`.

## Как встроить в Stage 2

Быстрый вариант:

\[
A^{managed}_{s,t} = A_{s,t}(1-\rho MOS_s)
\]

где \(\rho \in [0, 1]\) — сила институционального тормоза. Для first-pass сценария можно взять:

- `low`: \(\rho = 0.15\)
- `base`: \(\rho = 0.30\)
- `stress`: \(\rho = 0.50\)

Надежный вариант:

\[
\tau_{s,t} =
\rho MOS_s
+ \alpha_4 \text{import\_dependency}_{s}
+ \alpha_5 \text{market\_concentration}_{s}
\]

где в текущей first-pass реализации

- `import_dependency_s` собирается как proxy из `equipment-import prior`, `software/cloud prior`, `GPU dependence`, `ICT digital share` и `fixed-asset renewal`;
- `market_concentration_s` собирается как proxy из sector concentration prior, strategic flag и `employment_share_2024`;
- сценарии `SanctionBase` и `SanctionRelief` отличаются по силе import wedge при одном и том же `BaseThrottle` уровне для `MOS`.

Тогда managed obsolescence становится не отдельной исторической аналогией, а слоем policy friction поверх Bass diffusion.

## Какие данные добавить дальше

1. `Rosstat fixed assets`: износ, коэффициент обновления, возраст основных фондов по ОКВЭД.
2. `Rosstat employment/wages`: уже есть в `data/raw/russia/`, использовать для актуализации 2017-2024.
3. `Import dependence / input-output`: импортная доля оборудования, ПО, компонентов, сервисов.
4. `Market structure`: концентрация, доля крупных компаний, госучастие, regulated tariffs.
5. `Repair and maintenance`: оборот ремонта, техобслуживания, сервисных контрактов.
6. `AI adoption`: расходы на ПО, облака, центры обработки данных, вакансии AI/ML, закупки ИИ-систем.
7. `Regulatory events`: отраслевые запреты, требования сертификации, персональные данные, критическая инфраструктура.

## Запуск

```bash
python3 scripts/run_pipeline.py --stage managed_obsolescence
```

или полный pipeline:

```bash
python3 scripts/run_pipeline.py --stage all
```

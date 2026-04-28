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

Для каждого сектора построен score:

\[
MOS_s =
0.35 N^+(g^{LP}_s - g^{H}_s)
+ 0.30 N^+(g^{CAP}_s - g^{LAB}_s)
+ 0.20 N^+(g^{CAPIT}_s - g^{CAPNIT}_s)
+ 0.15 N^+(-g^{EMP}_s)
\]

где \(g\) — CAGR за 1995-2016, \(N^+(\cdot)\) — min-max нормировка положительной части по восьми секторам.

Интерпретация компонентов:

- \(g^{LP} - g^{H}\): производительность растет быстрее отработанных часов;
- \(g^{CAP} - g^{LAB}\): capital services растут быстрее labour services;
- \(g^{CAPIT} - g^{CAPNIT}\): ICT capital services растут быстрее non-ICT capital services;
- \(-g^{EMP}\): сжатие занятости.

Этот score не идентифицирует намеренность. Он помечает отрасли, где быстрый ИИ-шок с большей вероятностью будет политически или организационно throttled.

## Первый результат для РФ

| Rank | Sector | Score | Read |
|---:|---|---:|---|
| 1 | `J` ИТ и связь | 0.888 | высокий сигнал, но слабый legacy proxy: telecom/post вместо полной OKVED2 J |
| 2 | `C` обрабатывающая | 0.543 | чистый маппинг; центральный сектор для managed deployment |
| 3 | `M` проф. и научные услуги | 0.431 | высокий AI exposure, но KLEMS proxy широк и смешивает виды деятельности |
| 4 | `B` добыча | 0.375 | чистый маппинг, но нефтегазовая статистика требует осторожности |
| 5 | `F` строительство | 0.271 | умеренный стресс, вероятнее через материалы, оборудование и проектирование |
| 6 | `H` транспорт | 0.258 | умеренный стресс; логистика чувствительна к regulation and safety gates |
| 7 | `K` финансы | 0.245 | исторически занятость росла, но текущий AI exposure остается высоким |
| 8 | `DE` энергетика и ЖКХ | 0.144 | низкий KLEMS-score, но strategic throttling может идти через надежность и безопасность |

Главный прикладной вывод: для РФ слой надо использовать асимметрично. В `C` и частично `B/F/H` он отражает материально-капитальные constraints. В `J/K/M` он должен связываться с Stage 2 AI exposure, но исторический KLEMS-мэппинг сам по себе недостаточен.

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
\alpha_1 MOS_s
+ \alpha_2 \text{employment\_share}_{s,t}
+ \alpha_3 \text{strategic\_sector}_s
+ \alpha_4 \text{import\_dependency}_{s,t}
+ \alpha_5 \text{market\_concentration}_{s,t}
\]

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

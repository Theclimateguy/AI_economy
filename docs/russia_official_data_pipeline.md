# Russia Official Data Pipeline

Этот слой нужен для инициализации российской балансовой / CGE-модели не прокси-оценками, а прямыми официальными рядами Росстата по 8 секторам.

## 1. Источники

Pipeline использует прямые XLS/XLSX-файлы Rosstat:

- `VDS_god_OKVED2_s_2011-2025.xlsx`: ВДС по ОКВЭД2, текущие цены, постоянные цены, индексы физического объема и дефляторы.
- `05-05_2017-2024.xls`: среднегодовая численность занятых по ОКВЭД2.
- `tab3-zpl_2025.xlsx`: среднемесячная номинальная начисленная заработная плата по ОКВЭД2.

Ссылка на конфиг источников: [russia_official_sources.json](../config/russia_official_sources.json).

## 2. Мэппинг на 8 секторов

Используется явный row-level mapping из официальных таблиц:

- `B`: добыча полезных ископаемых
- `C`: обрабатывающие производства
- `DE`: сумма `D + E`
- `F`: строительство
- `H`: транспортировка и хранение
- `J`: информация и связь
- `K`: финансы и страхование
- `M`: профессиональная, научная и техническая деятельность

Для `DE` агрегирование делается до расчета derived variables.

## 3. Переменные

Из официальных файлов строятся:

$$
VA^{cur}_{s,t},
\quad
VA^{2016}_{s,t},
\quad
VA^{2021}_{s,t},
\quad
L_{s,t},
\quad
w_{s,t}.
$$

Где:

- $VA^{cur}$ — ВДС в текущих ценах, млрд руб.
- $VA^{2016}$, $VA^{2021}$ — ВДС в постоянных ценах, млрд руб.
- $L$ — среднегодовая занятость, тыс. человек.
- $w$ — среднемесячная номинальная зарплата, руб./мес.

Official sheet-level `volume/deflator` indices тоже сохраняются, но для аналитики используются level-consistent индексы, пересчитанные после агрегирования.

## 4. Производные расчеты

Так как прямой `ФОТ` из ЕМИСС `57821` пока не подцеплен в reproducible mode, используется официальный proxy:

$$
FOT^{proxy}_{s,t} = L_{s,t} \times 1000 \times w_{s,t} \times 12.
$$

В выходной таблице он хранится в млрд руб.:

$$
FOT^{proxy,bn}_{s,t} = \frac{L_{s,t} \times w_{s,t} \times 12}{10^6}.
$$

Дальше прокси доли труда:

$$
s^L_{s,t} = \frac{FOT^{proxy,bn}_{s,t}}{VA^{cur}_{s,t}}.
$$

Для real-side diagnostics сначала считаются level-consistent индексы:

$$
I^{nom}_{s,t} = \frac{VA^{cur}_{s,t}}{VA^{cur}_{s,t-1}} \times 100,
\qquad
I^{vol}_{s,t} = \frac{VA^{2021}_{s,t}}{VA^{2021}_{s,t-1}} \times 100,
$$

$$
I^{defl}_{s,t} = \frac{I^{nom}_{s,t}}{I^{vol}_{s,t}} \times 100.
$$

Только после этого:

$$
\Delta VA^{real}_{s,t} = I^{vol}_{s,t} - 100,
\qquad
\Delta P^{VA}_{s,t} = I^{defl}_{s,t} - 100.
$$

## 5. Выходные артефакты

Скрипт [build_russia_sector_panel.py](../scripts/build_russia_sector_panel.py) сохраняет:

- `data/processed/russia_sector_panel_official_2011_2025.csv`
- `data/processed/russia_sector_baseline_2024.csv`
- `data/processed/russia_sector_panel_metadata.json`

`russia_sector_baseline_2024.csv` — это latest complete slice, где одновременно доступны `VA`, `employment`, `wage` и, значит, `s^L`.

## 6. Ограничения

- В текущем окружении прямой доступ к `fedstat.ru/indicator/...` возвращал `403`, поэтому pipeline не завязан на нестабильный ЕМИСС frontend.
- Из-за этого прямой `ФОТ` пока не тянется из показателя `57821`; используется прозрачный proxy через официальные `employment × wage`.
- Полное пересечение `VA + employment + wage` сейчас равно `2017–2024`.
- `2025` есть для `VA` и `wage`, но пока нет в official employment workbook, поэтому для labour-share calibration этот год помечается как partial.
- Для агрегата `DE` официальные индексы листов `4/5` нельзя суммировать напрямую; поэтому в panel сохраняются audit-columns из workbook и рабочие level-consistent индексы, пересчитанные из агрегированных уровней `VA`.

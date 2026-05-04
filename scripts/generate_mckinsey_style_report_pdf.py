from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import qrcode
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
FIG_DIR = ROOT / "output" / "figures" / "managed_obsolescence"
REPORT_DIR = ROOT / "output" / "reports"
REPORT_PATH = REPORT_DIR / "ai_economy_managed_obsolescence_report_ru.pdf"
QR_PATH = REPORT_DIR / "repo_qr.png"
REPO_URL = "https://github.com/Theclimateguy/AI_economy"

PAGE_SIZE = (11.69, 8.27)  # A4 landscape in inches.
BLUE = "#1F4E79"
INK = "#111827"
MUTED = "#4B5563"
LIGHT = "#EEF2F7"
GREEN = "#0F766E"
ORANGE = "#B45309"
RED = "#B91C1C"

SECTOR_LABELS_RU = {
    "B": "Добыча",
    "C": "Обработка*",
    "C_mach": "Машиностр.",
    "DE": "Энерг./ЖКХ",
    "F": "Стройка",
    "G": "Торговля",
    "H": "Транспорт",
    "J": "ИТ/связь",
    "K": "Финансы",
    "M": "Проф. услуги",
}

KLEMS_SECTIONS = [
    ("A", "Сельское, лесное и рыбное хозяйство"),
    ("B", "Добыча полезных ископаемых"),
    ("C", "Обрабатывающие производства"),
    ("D", "Электроэнергия, газ, пар, кондиционирование"),
    ("E", "Водоснабжение, отходы, очистка"),
    ("F", "Строительство"),
    ("G", "Торговля; ремонт автотранспорта"),
    ("H", "Транспортировка и хранение"),
    ("I", "Гостиницы и общественное питание"),
    ("J", "Информация и связь"),
    ("K", "Финансовая и страховая деятельность"),
    ("L", "Операции с недвижимостью"),
    ("M", "Профессиональная, научная и техническая деятельность"),
    ("N", "Административная и сопутствующая деятельность"),
    ("O", "Госуправление, оборона, соцстрахование"),
    ("P", "Образование"),
    ("Q", "Здравоохранение и социальная помощь"),
    ("R", "Искусство, развлечения и отдых"),
    ("S", "Прочие услуги; ремонт"),
    ("T", "Домашние хозяйства как работодатели"),
    ("U", "Экстерриториальные организации"),
]


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.sans-serif": ["DejaVu Sans", "Arial", "sans-serif"],
            "mathtext.fontset": "dejavusans",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def fitted_title_size(title: str, requested: float) -> float:
    if len(title) <= 54:
        return requested
    if len(title) <= 72:
        return min(requested, 20.0)
    if len(title) <= 88:
        return min(requested, 18.6)
    return min(requested, 17.2)


def create_page(title: str, subtitle: str | None = None, title_size: float = 22) -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=PAGE_SIZE, dpi=220)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.add_patch(Rectangle((0.04, 0.945), 0.92, 0.035, color=BLUE, transform=ax.transAxes))
    ax.text(0.055, 0.963, "AI economy | managed obsolescence scenario", color="white", fontsize=9, va="center")
    ax.text(0.04, 0.905, title, color=INK, fontsize=fitted_title_size(title, title_size), fontweight="bold", va="top")
    if subtitle:
        ax.text(0.04, 0.862, subtitle, color=MUTED, fontsize=10.5, va="top")
    ax.text(0.96, 0.035, "Theclimateguy / AI_economy", color="#6B7280", fontsize=8, ha="right")
    return fig, ax


def wrapped_text(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    *,
    width: int = 74,
    fontsize: float = 10,
    color: str = INK,
    line_height: float = 0.030,
    weight: str = "normal",
) -> float:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, width=width, break_long_words=False))
    for idx, line in enumerate(lines):
        ax.text(x, y - idx * line_height, line, fontsize=fontsize, color=color, va="top", fontweight=weight)
    return y - max(len(lines), 1) * line_height


def section_label(ax: plt.Axes, x: float, y: float, label: str, color: str = BLUE) -> None:
    ax.add_patch(Rectangle((x, y - 0.025), 0.012, 0.032, color=color, transform=ax.transAxes))
    ax.text(x + 0.018, y, label, fontsize=12, fontweight="bold", color=INK, va="top")


def add_image(ax: plt.Axes, path: Path, bbox: list[float], *, aspect: str = "equal") -> None:
    image_ax = ax.figure.add_axes(bbox)
    image_ax.set_axis_off()
    image = Image.open(path)
    image_ax.imshow(image, aspect=aspect)


def add_card(ax: plt.Axes, x: float, y: float, w: float, h: float, title: str, body: str, color: str = BLUE) -> None:
    ax.add_patch(Rectangle((x, y - h), w, h, facecolor="#F8FAFC", edgecolor="#D1D5DB", linewidth=0.8, transform=ax.transAxes))
    ax.text(x + 0.018, y - 0.030, title, color=color, fontsize=11, fontweight="bold", va="top")
    wrap_width = max(26, int(w * 118))
    wrapped_text(ax, x + 0.018, y - 0.070, body, width=wrap_width, fontsize=8.7, color=INK, line_height=0.023)


def add_table(
    ax: plt.Axes,
    df: pd.DataFrame,
    bbox: list[float],
    fontsize: float = 8.5,
    col_widths: list[float] | None = None,
) -> None:
    table_kwargs = {}
    if col_widths is not None:
        total = sum(col_widths)
        table_kwargs["colWidths"] = [bbox[2] * width / total for width in col_widths]
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        colLoc="center",
        bbox=bbox,
        **table_kwargs,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#D1D5DB")
        cell.set_linewidth(0.55)
        if row == 0:
            cell.set_facecolor(BLUE)
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#FFFFFF" if row % 2 else "#F8FAFC")


def make_qr() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(REPO_URL)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    image.save(QR_PATH)


def load_russia_table() -> pd.DataFrame:
    diffusion = pd.read_csv(DATA_DIR / "ai_diffusion_sector_summary.csv")
    proxy = pd.read_csv(DATA_DIR / "managed_obsolescence_sector_proxy.csv")
    base = diffusion.loc[diffusion["scenario"].eq("Base"), ["sector_id", "A_2035", "class_id"]].merge(
        proxy[["sector_id", "managed_obsolescence_pressure_score", "fit_quality"]],
        on="sector_id",
        how="left",
    )
    base["A_managed_030"] = base["A_2035"] * (1.0 - 0.30 * base["managed_obsolescence_pressure_score"])
    base["loss_pp"] = (base["A_2035"] - base["A_managed_030"]) * 100
    base = base.sort_values("managed_obsolescence_pressure_score", ascending=False)
    return pd.DataFrame(
        {
            "Сектор": base["sector_id"].map(SECTOR_LABELS_RU),
            "Класс": base["class_id"].map({"software": "software", "hybrid": "hybrid", "hardware": "hardware"}),
            "A2035": base["A_2035"].map(lambda x: f"{x:.2f}"),
            "MOS": base["managed_obsolescence_pressure_score"].map(lambda x: f"{x:.2f}"),
            "A managed": base["A_managed_030"].map(lambda x: f"{x:.2f}"),
            "Loss, п.п.": base["loss_pp"].map(lambda x: f"{x:.1f}"),
        }
    )


def page_executive_summary(pdf: PdfPages) -> None:
    fig, ax = create_page(
        "Executive summary: управляемое устаревание как wedge",
        "Отчет оценивает не технический предел ИИ, а институциональный разрыв между frontier capability и реально внедренной capability.",
        title_size=19.5,
    )
    section_label(ax, 0.04, 0.80, "Тезис")
    narrative = (
        "Базовая идея: экономика может ограничивать эффективность надежных технологий, если быстрая диффузия разрушает привычные циклы замены, сервисные ренты, занятость и отраслевую адаптацию. "
        "Поэтому ИИ моделируется не как мгновенный перенос frontier-возможности в выпуск, а как частичное развертывание с wedge tau(s,t). "
        "Такой подход позволяет сравнивать технологический потенциал с политэкономическими ограничениями без сильного утверждения о сговоре."
    )
    wrapped_text(ax, 0.055, 0.755, narrative, width=112, fontsize=9.7, line_height=0.028)

    section_label(ax, 0.04, 0.615, "Почему разные сценарии")
    scenarios = (
        "Fast — низкие институциональные трения и быстрый перенос frontier capability в производство. "
        "Base — умеренная диффузия с отраслевыми различиями по software / hardware / hybrid. "
        "Friction — высокая цена адаптации, regulatory gates, дефицит оборудования и более сильный managed-obsolescence wedge. "
        "Разделение сценариев нужно, потому что одна и та же frontier-модель дает разные траектории выпуска при разных ограничениях доступа, капитала, ремонта, данных и регулирования."
    )
    wrapped_text(ax, 0.055, 0.572, scenarios, width=112, fontsize=9.4, line_height=0.027)

    section_label(ax, 0.04, 0.405, "Почему три класса adoption")
    classes = pd.DataFrame(
        [
            ["Software", "J, K, M", "модели, данные,\nAPI, compliance", "быстрая диффузия,\nнизкий capex"],
            ["Hardware / robots", "B, F, H", "оборудование, сенсоры,\nроботы, безопасность", "медленная диффузия,\nвысокий capex"],
            ["Hybrid", "C, DE", "софт + физические активы\nи инфраструктура", "средняя скорость,\nсильные bottlenecks"],
        ],
        columns=["Класс", "Сектора", "Механизм внедрения", "Почему отличается"],
    )
    add_table(ax, classes, [0.04, 0.075, 0.92, 0.255], fontsize=7.9, col_widths=[0.13, 0.10, 0.40, 0.37])
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_methodology(pdf: PdfPages) -> None:
    fig, ax = create_page(
        "Методология: frontier capability ≠ deployed capability",
        "Сценарий управляемого устаревания описывает разрыв между технологической границей ИИ и фактически развернутой производственной возможностью.",
        title_size=21,
    )
    section_label(ax, 0.04, 0.79, "Математическое ядро")
    formulas = [
        r"$\frac{dA_s}{dt}=(p_s+q_sA_s)(1-A_s)$",
        r"$a_{s,t}=q_t A_{s,t}(1-\tau_{s,t})$",
        r"$A^{managed}_{s,2035}=A^{base}_{s,2035}(1-\rho MOS_s)$",
        r"$MOS_s=0.35N^+(g^{LP}-g^H)+0.30N^+(g^{CAP}-g^{LAB})$",
        r"$\qquad\quad +0.20N^+(g^{ICT}-g^{NICT})+0.15N^+(-g^{EMP})$",
    ]
    for idx, formula in enumerate(formulas):
        ax.text(0.055, 0.735 - idx * 0.044, formula, fontsize=11.4, color=INK, va="top")

    section_label(ax, 0.04, 0.49, "Проверяемые гипотезы")
    hypotheses = (
        "H1. Универсальная историческая beta технологических революций неустойчива; перенос на ИИ должен быть сценарным.\n"
        "H2. Запланированное устаревание действует прежде всего на effective service flow: срок службы, совместимость, доступ, ремонт и программные ограничения.\n"
        "H3. Давление на staged deployment выше там, где производительность и капитал растут быстрее труда или занятость сжимается.\n"
        "H4. Для РФ эффект должен быть отраслевым: software-сектора получают высокий AI upside, а материальные сектора ограничены капиталом, инфраструктурой и регуляторикой."
    )
    wrapped_text(ax, 0.055, 0.445, hypotheses, width=66, fontsize=10.1, line_height=0.032)

    section_label(ax, 0.60, 0.79, "Данные")
    data_rows = pd.DataFrame(
        [
            ["EU KLEMS/OECD", "1985-2005", "сравнительная панель ICT-эпохи"],
            ["ILOSTAT + RTI", "1995+", "профиль задач и рутинизация"],
            ["Russia KLEMS ВШЭ", "1995-2016", "труд, капитал, TFP, productivity"],
            ["Rosstat", "2011-2025", "VA, занятость, зарплаты по ОКВЭД"],
            ["OWID/Comin-Hobijn", "1908-2019", "benchmark S-кривых диффузии"],
            ["Case evidence", "1924-2024", "Phoebus, GM, Apple, repair restrictions"],
        ],
        columns=["Источник", "Окно", "Назначение"],
    )
    add_table(ax, data_rows, [0.56, 0.37, 0.40, 0.37], fontsize=7.45, col_widths=[0.25, 0.15, 0.60])
    add_card(
        ax,
        0.60,
        0.31,
        0.36,
        0.18,
        "Важная оговорка",
        "MOS не доказывает сговор или намеренность. Это измеримый proxy давления, при котором рынки и регуляторы могут рационально замедлять внедрение эффективной технологии.",
        color=RED,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_world(pdf: PdfPages) -> None:
    fig, ax = create_page(
        "Историческая рамка: нормальная диффузия и каналы управляемого устаревания",
        "Технологии обычно распространяются S-кривыми; managed obsolescence меняет не только долю пользователей, но и качество получаемого сервиса.",
        title_size=19.8,
    )
    add_image(ax, FIG_DIR / "fig6_world_technology_s_curves.png", [0.035, 0.40, 0.43, 0.39])
    add_image(ax, FIG_DIR / "fig8_historical_obsolescence_mechanisms.png", [0.475, 0.43, 0.485, 0.33], aspect="auto")
    section_label(ax, 0.05, 0.31, "Интерпретация")
    world_text = (
        "Digital/network technologies сжимают окно адаптации: smartphone usage дошел от 10% до 80% примерно за 8 лет, social media usage — за 11 лет. "
        "Это повышает вероятность политического и отраслевого throttling, потому что рынок труда и смежные сервисы не успевают перестроиться. "
        "Исторические кейсы показывают четыре канала: физический срок службы, дизайн/модельный цикл, software throttling и ограничения ремонта/доступа."
    )
    wrapped_text(ax, 0.065, 0.265, world_text, width=78, fontsize=10.1, line_height=0.031)
    speed = pd.read_csv(DATA_DIR / "world_technology_diffusion_benchmarks.csv")
    speed = speed.loc[speed["technology"].isin(["Automobile", "Electric power", "Radio", "Internet", "Social media usage", "Smartphone usage"])]
    speed = speed[["technology", "years_10_to_80"]].sort_values("years_10_to_80")
    speed["years_10_to_80"] = speed["years_10_to_80"].map(lambda x: f"{x:.0f}")
    speed.columns = ["Технология", "10→80%, лет"]
    add_table(ax, speed, [0.66, 0.07, 0.27, 0.22], fontsize=8.4)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_russia(pdf: PdfPages) -> None:
    fig, ax = create_page(
        "РФ: отраслевой риск staged AI deployment",
        "Russia KLEMS дает исторический proxy давления; Stage 2 показывает, где ИИ быстрее всего входит в производственную функцию.",
    )
    add_image(ax, FIG_DIR / "fig10_russia_managed_obsolescence_pressure.png", [0.035, 0.42, 0.44, 0.39])
    add_image(ax, FIG_DIR / "fig12_russia_ai_throttling_quadrants.png", [0.51, 0.42, 0.45, 0.39])
    section_label(ax, 0.05, 0.34, "Ключевые выводы по секторам")
    text_left = (
        "C_mach выделяет машинно-оборудовательный агрегат ОКВЭД 26–30, а C теперь читается как остаточная обработка без машиностроения. "
        "Торговля G добавляет крупный hybrid-сектор с frontend AI exposure и умеренными материальными ограничениями. "
        "J и M находятся в зоне высокого AI upside и высокого pressure, но трактуются осторожно из-за legacy NACE proxy. "
        "B, H и DE требуют отдельного слоя надежности, безопасности и инфраструктурной регуляторики."
    )
    wrapped_text(ax, 0.065, 0.295, text_left, width=63, fontsize=10.1, line_height=0.031)
    table = load_russia_table().head(6)
    add_table(ax, table, [0.59, 0.075, 0.36, 0.27], fontsize=7.0)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_forecast_and_qr(pdf: PdfPages) -> None:
    fig, ax = create_page(
        "Прогноз: managed obsolescence снижает deployed capability, но не отменяет ИИ",
        "Сценарий не утверждает невозможность AGI. Он описывает экономико-политический режим частичного развертывания эффективной технологии.",
        title_size=19.5,
    )
    add_image(ax, FIG_DIR / "fig11_russia_base_vs_managed_ai_2035.png", [0.04, 0.35, 0.55, 0.46])
    section_label(ax, 0.63, 0.76, "Итоговая рамка")
    final_text = (
        "Основной риск для прогноза — не техническая невозможность ИИ, а разрыв между frontier capability и deployed capability. "
        "В software-секторах wedge действует через доступ, лицензирование, данные и compliance; в материальных секторах — через оборудование, ремонт, импортозависимость и safety gates."
    )
    wrapped_text(ax, 0.645, 0.715, final_text, width=54, fontsize=8.5, line_height=0.023)
    ax.text(0.64, 0.505, "Выводы", fontsize=12.2, fontweight="bold", color=GREEN)
    conclusions = (
        "1. AI adoption и deployed capability не тождественны.\n"
        "2. Software-сектора дают быстрый upside, но наиболее чувствительны к доступу, данным и compliance.\n"
        "3. Материальные сектора ограничены capex, ремонтом, импортом оборудования и надежностью.\n"
        "4. Manufacturing split: C_mach — отдельный инвестиционно-емкий hybrid-агрегат; C — остаточная обработка."
    )
    wrapped_text(ax, 0.64, 0.472, conclusions, width=60, fontsize=8.0, color=INK, line_height=0.020)
    ax.text(0.64, 0.245, "Репозиторий и pipeline", fontsize=10.0, fontweight="bold", color=INK)
    ax.text(0.64, 0.218, "GitHub: Theclimateguy/AI_economy", fontsize=8.0, color=BLUE)
    wrapped_text(
        ax,
        0.64,
        0.188,
        "QR: данные, скрипты, графики и документация.",
        width=30,
        fontsize=7.8,
        color=MUTED,
        line_height=0.019,
    )
    add_image(ax, QR_PATH, [0.852, 0.090, 0.078, 0.110])
    foot = (
        "Ограничения: historical case evidence не является causal panel; Russia KLEMS использует NACE 1.0 и имеет слабые proxy для J/M; "
        "2015-2016 в Russia KLEMS предварительные. Поэтому результаты следует читать как scenario layer, а не точечный прогноз."
    )
    wrapped_text(ax, 0.04, 0.19, foot, width=95, fontsize=8.8, color=MUTED, line_height=0.026)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def klems_table() -> pd.DataFrame:
    left = KLEMS_SECTIONS[:11]
    right = KLEMS_SECTIONS[11:]
    rows = []
    max_len = max(len(left), len(right))
    for idx in range(max_len):
        l_code, l_name = left[idx] if idx < len(left) else ("", "")
        r_code, r_name = right[idx] if idx < len(right) else ("", "")
        rows.append([l_code, l_name, r_code, r_name])
    return pd.DataFrame(rows, columns=["Код", "Секция", "Код", "Секция"])


def page_appendix_klems(pdf: PdfPages) -> None:
    fig, ax = create_page(
        "Приложение: соответствие буквенных секций KLEMS / NACE / ОКВЭД",
        "Таблица нужна для чтения отраслевых кодов в KLEMS, национальных таблицах и сценарной карте РФ.",
        title_size=20.0,
    )
    add_table(ax, klems_table(), [0.05, 0.17, 0.83, 0.62], fontsize=7.8, col_widths=[0.08, 0.42, 0.08, 0.42])
    section_label(ax, 0.05, 0.115, "Примечание")
    note = (
        "В проекте используется агрегированная карта: B — добыча, C — обработка без C_mach, C_mach — машиностроение ОКВЭД 26–30, DE — энергетика и ЖКХ, F — строительство, G — торговля, H — транспорт, J — ИТ и связь, K — финансы, M — профессиональные и научные услуги. "
        "Для Russia KLEMS часть соответствий построена через старую NACE 1.0, поэтому J и M отмечены как weak proxy."
    )
    wrapped_text(ax, 0.065, 0.078, note, width=100, fontsize=8.8, color=MUTED, line_height=0.024)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    configure_style()
    make_qr()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with PdfPages(REPORT_PATH) as pdf:
        page_executive_summary(pdf)
        page_methodology(pdf)
        page_world(pdf)
        page_russia(pdf)
        page_forecast_and_qr(pdf)
        page_appendix_klems(pdf)
    print(f"Saved report: {REPORT_PATH.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()

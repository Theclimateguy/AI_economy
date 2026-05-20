from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output"
REPORT_DIR = OUTPUT_DIR / "reports"

SUMMARY_PATH = DATA_DIR / "attention_monopoly_sector_summary.csv"
ABM_PATH = DATA_DIR / "attention_monopoly_abm_paths.csv"
DWL_PATH = DATA_DIR / "attention_monopoly_deadweight_loss.csv"

RISK_FIG = OUTPUT_DIR / "attention_monopoly_risk_gradient.png"
GVA_FIG = OUTPUT_DIR / "attention_monopoly_gva_shift.png"
ABM_FIG = OUTPUT_DIR / "attention_abm_dynamics.png"
DWL_FIG = OUTPUT_DIR / "attention_deadweight_loss.png"

REPORT_PATH = REPORT_DIR / "attention_monopoly_scenario_report_ru.pdf"

PAGE_SIZE = (11.69, 8.27)
BLUE = "#1F4E79"
INK = "#111827"
MUTED = "#4B5563"
LIGHT = "#EEF2F7"
GREEN = "#047857"
RED = "#B91C1C"
ORANGE = "#B45309"


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


def create_page(title: str, subtitle: str | None = None, title_size: float = 21) -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=PAGE_SIZE, dpi=220)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.add_patch(Rectangle((0.04, 0.945), 0.92, 0.035, color=BLUE, transform=ax.transAxes))
    ax.text(0.055, 0.963, "AI economy | attention monopoly scenario", color="white", fontsize=9, va="center")
    ax.text(0.04, 0.905, title, color=INK, fontsize=title_size, fontweight="bold", va="top")
    if subtitle:
        ax.text(0.04, 0.860, subtitle, color=MUTED, fontsize=10.2, va="top")
    ax.text(0.96, 0.035, "Theclimateguy / AI_economy", color="#6B7280", fontsize=8, ha="right")
    return fig, ax


def wrapped_text(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    *,
    width: int = 92,
    fontsize: float = 9.5,
    color: str = INK,
    line_height: float = 0.027,
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
    ax.text(x + 0.018, y, label, fontsize=11.5, fontweight="bold", color=INK, va="top")


def add_card(ax: plt.Axes, x: float, y: float, w: float, h: float, title: str, body: str, color: str = BLUE) -> None:
    ax.add_patch(Rectangle((x, y - h), w, h, facecolor="#F8FAFC", edgecolor="#D1D5DB", linewidth=0.8, transform=ax.transAxes))
    ax.text(x + 0.016, y - 0.028, title, color=color, fontsize=10.6, fontweight="bold", va="top")
    wrapped_text(ax, x + 0.016, y - 0.066, body, width=max(24, int(w * 120)), fontsize=8.6, line_height=0.022)


def add_image(ax: plt.Axes, path: Path, bbox: list[float], *, aspect: str = "equal") -> None:
    image_ax = ax.figure.add_axes(bbox)
    image_ax.set_axis_off()
    image = Image.open(path)
    image_ax.imshow(image, aspect=aspect)


def add_table(ax: plt.Axes, df: pd.DataFrame, bbox: list[float], fontsize: float = 7.7) -> None:
    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc="center", colLoc="center", bbox=bbox)
    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    for (row, _), cell in table.get_celld().items():
        cell.set_edgecolor("#D1D5DB")
        cell.set_linewidth(0.5)
        if row == 0:
            cell.set_facecolor(BLUE)
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#FFFFFF" if row % 2 else "#F8FAFC")


def load_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return pd.read_csv(SUMMARY_PATH), pd.read_csv(ABM_PATH), pd.read_csv(DWL_PATH)


def fmt_bn(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def page_problem(pdf: PdfPages, summary: pd.DataFrame, abm: pd.DataFrame) -> None:
    final_base = abm.loc[abm["scenario"].eq("base")].sort_values("year").iloc[-1]
    fig, ax = create_page(
        "Сценарий: AI-монополия внимания",
        "Единый ИИ-ассистент становится основной поверхностью доступа к поиску, покупкам, финансам, сервисам и контенту.",
        title_size=21,
    )
    section_label(ax, 0.04, 0.79, "Постановка")
    text = (
        "Гипотеза: пользовательские намерения концентрируются в 1-2 интерфейсах. Для отраслей это меняет цену доступа к спросу: "
        "часть компаний получает более дешёвое привлечение клиента через intent-based targeting, а уязвимые фирмы платят платформенную ренту "
        "или теряют прямой канал к пользователю. В терминах KLEMS это сценарий перераспределения S и K: расходы на маркетинг, медиа и "
        "customer access перетекают в ИТ-экосистемы и капитальные активы платформ."
    )
    wrapped_text(ax, 0.055, 0.750, text, width=120, fontsize=9.5)

    add_card(
        ax,
        0.05,
        0.565,
        0.28,
        0.16,
        "Ось X",
        "Integration deficit: x_s = 1 - I_s. Чем правее отрасль, тем слабее её способность встроиться в AI/platform stack.",
    )
    add_card(
        ax,
        0.36,
        0.565,
        0.28,
        0.16,
        "Ось Y",
        "Attention dependency: D_s. Чем выше отрасль, тем сильнее она зависит от discovery channel и пользовательского внимания.",
    )
    add_card(
        ax,
        0.67,
        0.565,
        0.28,
        0.16,
        "Цвет",
        "Composite risk R_s от 0 до 100: зависимость от внимания, дефицит интеграции, markup, доля уязвимых МСП и AI adoption.",
    )

    section_label(ax, 0.04, 0.345, "Ключевые числа базовой калибровки")
    metrics = pd.DataFrame(
        [
            ["AI-interface saturation 2035", f"{final_base['assistant_attention_share']:.1%}"],
            ["Locked attention share 2035", f"{final_base['locked_attention_share']:.1%}"],
            ["Platform access fees", f"{fmt_bn(summary['platform_access_fee_bn_rub'].sum())} млрд руб."],
            ["CAC saving VA gain", f"{fmt_bn(summary['cac_saving_va_gain_bn_rub'].sum())} млрд руб."],
            ["Net GVA/capital shift", f"{fmt_bn(summary['attention_gva_shift_bn_rub'].sum())} млрд руб."],
        ],
        columns=["Метрика", "Значение"],
    )
    add_table(ax, metrics, [0.05, 0.090, 0.48, 0.220], fontsize=8.5)
    wrapped_text(
        ax,
        0.58,
        0.300,
        "Все величины являются сценарными first-pass оценками в ценах baseline 2024. Параметры, по которым нет публичной статистики РФ, вынесены в конфиг expert assumptions и помечены как экспертные допущения.",
        width=50,
        fontsize=9.0,
        color=MUTED,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_model(pdf: PdfPages) -> None:
    fig, ax = create_page(
        "Формализация: риск и сдвиг ВДС",
        "Сценарий строится как reduced-form слой поверх текущих sector baseline, AI adoption и capital-return outputs.",
        title_size=21,
    )
    section_label(ax, 0.04, 0.79, "Индексы")
    formulas = [
        r"$D_s \in [0,1]$ — зависимость отрасли от пользовательского внимания",
        r"$I_s \in [0,1]$ — способность встроиться в AI/platform stack",
        r"$m_s$ — platform markup за доступ к пользователю",
        r"$E_s$ — доля уязвимых МСП / игроков без собственного API-канала",
        r"$A_s(2035)$ — adoption из существующего diffusion/capital-return слоя",
    ]
    y = 0.740
    for formula in formulas:
        ax.text(0.065, y, formula, fontsize=12.0, color=INK, va="top")
        y -= 0.055

    section_label(ax, 0.04, 0.430, "Composite risk")
    ax.text(
        0.060,
        0.360,
        r"$R_s = 100\left(w_DD_s+w_I(1-I_s)+w_m\frac{m_s}{\max_j m_j}+w_EE_s+w_AA_s(2035)\right)$",
        fontsize=15.0,
        color=INK,
    )

    section_label(ax, 0.04, 0.245, "Net GVA / capital-attraction shift")
    ax.text(
        0.060,
        0.170,
        r"$\Delta VA_s^{att}=VA_s\bar{A}D_sI_sc_s\rho - VA_s\bar{A}D_sm_s(1-I_s)\frac{1+E_s}{2} + 1_{s\in platform}\Omega$",
        fontsize=13.0,
        color=INK,
    )
    wrapped_text(
        ax,
        0.060,
        0.110,
        "Первое слагаемое — сохранённая выгода от снижения CAC. Второе — платформа забирает часть маржи за доступ к намерениям. Третье — рента, аккумулируемая AI/platform sector.",
        width=115,
        fontsize=8.8,
        color=MUTED,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_risk_gradient(pdf: PdfPages, summary: pd.DataFrame) -> None:
    fig, ax = create_page(
        "Карта риска: зависимость от внимания × дефицит интеграции",
        "Точки — отрасли; размер точки пропорционален текущей ВДС; цвет — composite risk score.",
        title_size=19.5,
    )
    add_image(ax, RISK_FIG, [0.04, 0.080, 0.62, 0.740], aspect="equal")
    top = summary.sort_values("attention_risk_score", ascending=False).head(5).copy()
    top_table = pd.DataFrame(
        {
            "Сектор": top["sector_id"],
            "D": top["attention_dependency"].map(lambda x: f"{x:.2f}"),
            "I": top["integration_capacity"].map(lambda x: f"{x:.2f}"),
            "R": top["attention_risk_score"].map(lambda x: f"{x:.1f}"),
        }
    )
    section_label(ax, 0.70, 0.780, "High-risk cluster")
    add_table(ax, top_table, [0.70, 0.535, 0.25, 0.205], fontsize=8.6)
    wrapped_text(
        ax,
        0.70,
        0.485,
        "M и F находятся в зоне высокого риска из-за высокой зависимости от discovery/intermediation и слабой интеграции. G и J тоже высоко по attention, но интеграция снижает риск и превращает часть шока в upside.",
        width=39,
        fontsize=8.9,
        color=MUTED,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_gva_results(pdf: PdfPages, summary: pd.DataFrame) -> None:
    fig, ax = create_page(
        "Результат: перераспределение ВДС и капитала",
        "Net shift показывает баланс CAC-saving upside и платформенной ренты за доступ к пользователю.",
        title_size=20.5,
    )
    add_image(ax, GVA_FIG, [0.04, 0.125, 0.58, 0.660], aspect="equal")
    losers = summary.sort_values("attention_gva_shift_bn_rub").head(4)
    winners = summary.sort_values("attention_gva_shift_bn_rub", ascending=False).head(4)
    table = pd.DataFrame(
        {
            "Losers": losers["sector_id"].to_list(),
            "ΔVA, млрд": losers["attention_gva_shift_bn_rub"].map(lambda x: f"{x:.0f}").to_list(),
            "Winners": winners["sector_id"].to_list(),
            "ΔVA, млрд ": winners["attention_gva_shift_bn_rub"].map(lambda x: f"{x:.0f}").to_list(),
        }
    )
    section_label(ax, 0.66, 0.765, "Секторный баланс")
    add_table(ax, table, [0.66, 0.555, 0.30, 0.170], fontsize=8.2)
    wrapped_text(
        ax,
        0.66,
        0.495,
        "Сценарий не является чисто негативным: aggregate net shift положителен, но распределение асимметрично. J получает платформенную ренту, G и K выигрывают от конверсии и CAC savings. F, M, H и часть C теряют из-за доступа через посредника.",
        width=42,
        fontsize=8.8,
        color=MUTED,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_abm_dwl(pdf: PdfPages, summary: pd.DataFrame, dwl: pd.DataFrame) -> None:
    fig, ax = create_page(
        "Динамика внимания и welfare cost",
        "ABM-блок пока reduced-form: пользователи и МСП перетекают из открытого web/discovery в AI-interface.",
        title_size=20.5,
    )
    add_image(ax, ABM_FIG, [0.04, 0.470, 0.52, 0.325], aspect="equal")
    add_image(ax, DWL_FIG, [0.04, 0.070, 0.52, 0.325], aspect="equal")
    section_label(ax, 0.61, 0.765, "Интерпретация")
    wrapped_text(
        ax,
        0.61,
        0.725,
        "В base-сценарии AI-интерфейс достигает 40% saturation к 2035, а cognitive lock-in удерживает значимую долю внимания внутри одной поверхности. Это повышает HHI внимания и создаёт market power для доступа к intentions.",
        width=49,
        fontsize=8.9,
        color=MUTED,
    )
    top_dwl = dwl.sort_values("deadweight_loss_bn_rub", ascending=False).head(5)
    dwl_table = pd.DataFrame(
        {
            "Сектор": top_dwl["sector_id"],
            "DWL, млрд": top_dwl["deadweight_loss_bn_rub"].map(lambda x: f"{x:.1f}"),
            "markup": top_dwl["platform_markup_mid"].map(lambda x: f"{x:.2f}"),
        }
    )
    section_label(ax, 0.61, 0.450, "Top welfare losses")
    add_table(ax, dwl_table, [0.61, 0.225, 0.31, 0.185], fontsize=8.4)
    total_dwl = float(dwl["deadweight_loss_bn_rub"].sum())
    wrapped_text(
        ax,
        0.61,
        0.170,
        f"Суммарный reduced-form deadweight loss: {total_dwl:.1f} млрд руб. Наибольший вклад дают M, F и J/G: высокая attention exposure плюс ненулевая платформа-комиссия.",
        width=48,
        fontsize=8.8,
        color=MUTED,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_assumptions(pdf: PdfPages, summary: pd.DataFrame) -> None:
    fig, ax = create_page(
        "Вводные и ограничения",
        "Текущая версия — first-pass сценарная калибровка; параметры должны быть обновлены после экспертной сессии и внешних бенчмарков.",
        title_size=20.5,
    )
    section_label(ax, 0.04, 0.790, "Главные допущения")
    assumptions = pd.DataFrame(
        [
            ["AI-interface saturation", "base 40%; range 20-60%", "Issue #7"],
            ["Cognitive lock-in", "0.75", "expert assumption"],
            ["Platform markup", "3-22% midpoint by sector", "marketplace/API proxy"],
            ["CAC saving", "4-30% midpoint by sector", "intent targeting proxy"],
            ["SME vulnerability", "20-70% by sector", "expert assumption"],
        ],
        columns=["Параметр", "Значение", "Источник"],
    )
    add_table(ax, assumptions, [0.05, 0.525, 0.90, 0.215], fontsize=8.5)
    section_label(ax, 0.04, 0.440, "Диагностическая таблица")
    table = summary.sort_values("attention_risk_score", ascending=False).copy()
    diagnostic = pd.DataFrame(
        {
            "Сектор": table["sector_id"],
            "R": table["attention_risk_score"].map(lambda x: f"{x:.1f}"),
            "Fee": table["platform_access_fee_bn_rub"].map(lambda x: f"{x:.0f}"),
            "CAC gain": table["cac_saving_va_gain_bn_rub"].map(lambda x: f"{x:.0f}"),
            "Net shift": table["attention_gva_shift_bn_rub"].map(lambda x: f"{x:.0f}"),
        }
    )
    add_table(ax, diagnostic, [0.05, 0.090, 0.90, 0.305], fontsize=7.9)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    configure_style()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary, abm, dwl = load_outputs()
    with PdfPages(REPORT_PATH) as pdf:
        page_problem(pdf, summary, abm)
        page_model(pdf)
        page_risk_gradient(pdf, summary)
        page_gva_results(pdf, summary)
        page_abm_dwl(pdf, summary, dwl)
        page_assumptions(pdf, summary)
    print(f"Saved report: {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

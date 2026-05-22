from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
REPORT_DIR = OUTPUT_DIR / "reports"
RISK_FIG = OUTPUT_DIR / "attention_monopoly_risk_gradient.png"
REPORT_PATH = REPORT_DIR / "attention_monopoly_gradient_step_brief_ru.pdf"

PAGE_SIZE = (8.27, 11.69)
BLUE = "#1F4E79"
INK = "#111827"
MUTED = "#4B5563"
LIGHT = "#F3F6FA"


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


def wrapped_text(ax: plt.Axes, x: float, y: float, text: str, width: int, fontsize: float, line_height: float) -> float:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, width=width, break_long_words=False))
    for i, line in enumerate(lines):
        ax.text(x, y - i * line_height, line, fontsize=fontsize, color=INK, va="top")
    return y - max(len(lines), 1) * line_height


def section(ax: plt.Axes, x: float, y: float, title: str) -> None:
    ax.add_patch(Rectangle((x, y - 0.022), 0.011, 0.026, transform=ax.transAxes, facecolor=BLUE, edgecolor="none"))
    ax.text(x + 0.018, y, title, fontsize=10.4, fontweight="bold", color=INK, va="top")


def add_risk_image(fig: plt.Figure, bbox: list[float]) -> None:
    image_ax = fig.add_axes(bbox)
    image_ax.set_axis_off()
    image = Image.open(RISK_FIG)
    image_ax.imshow(image)


def build_report() -> None:
    configure_style()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with PdfPages(REPORT_PATH) as pdf:
        fig = plt.figure(figsize=PAGE_SIZE, dpi=220)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()

        ax.add_patch(Rectangle((0.04, 0.925), 0.92, 0.040, transform=ax.transAxes, facecolor=BLUE, edgecolor="none"))
        ax.text(0.055, 0.945, "AI economy | scenario step note", fontsize=8.3, color="white", va="center")
        ax.text(0.04, 0.885, "Монополия внимания: корректировка риск-градиента", fontsize=16.5, fontweight="bold", color=INK, va="top")
        ax.text(
            0.04,
            0.838,
            "Короткая фиксация изменения: риск теперь растет при высокой зависимости от поиска и высокой подключаемости к платформе.",
            fontsize=8.9,
            color=MUTED,
            va="top",
        )

        section(ax, 0.04, 0.785, "Математика")
        y = 0.745
        formulas = [
            r"$D_s \in [0,1]$ — зависимость отрасли от поиска, рекомендаций и discovery channel.",
            r"$I_s \in [0,1]$ — способность быстро встроиться в AI/platform stack.",
            r"$R_s=100\left(w_DD_s+w_II_s+w_m\frac{m_s}{\max_j m_j}+w_EE_s+w_GG_s+w_AA_s(2035)\right)$.",
        ]
        for formula in formulas:
            ax.text(0.06, y, formula, fontsize=10.0, color=INK, va="top")
            y -= 0.044

        section(ax, 0.04, 0.615, "Смысл изменения")
        body = (
            "Ось X теперь трактуется как прямая интеграционная емкость $I_s$, а не дефицит $1-I_s$. "
            "Поэтому опасная зона графика — правый верхний угол: отрасли, где пользовательский выбор сильно "
            "зависит от поиска, и где подключение к AI-платформе технически и организационно простое. "
            "Это не отменяет отдельный loss-factor $1-I_s$ в формуле чистого сдвига ВДС: там он описывает потери "
            "игроков, не встроившихся в платформу."
        )
        wrapped_text(ax, 0.06, 0.575, body, width=86, fontsize=8.7, line_height=0.021)

        section(ax, 0.04, 0.448, "Калибровочные допущения")
        assumptions = (
            "Торговля и ИТ сдвинуты вправо-вверх: поиск, маркетплейсы, delivery, карты, API и рекомендации "
            "делают их одновременно attention-sensitive и platform-connectable. Добыча и строительство "
            "сдвинуты влево-вниз: спрос там более B2B/project-based, менее discovery-driven и хуже стандартизуется "
            "под единый AI-интерфейс."
        )
        wrapped_text(ax, 0.06, 0.408, assumptions, width=86, fontsize=8.7, line_height=0.021)

        ax.add_patch(Rectangle((0.100, 0.105), 0.800, 0.180, transform=ax.transAxes, facecolor=LIGHT, edgecolor="#D1D5DB", linewidth=0.6))
        add_risk_image(fig, [0.120, 0.121, 0.760, 0.150])
        ax.text(0.100, 0.086, "Фрагмент обновленного риск-градиента", fontsize=8.2, color=MUTED, va="top")

        ax.text(0.04, 0.045, "Output: attention_monopoly_gradient_step_brief_ru.pdf", fontsize=7.4, color="#6B7280")
        ax.text(0.96, 0.045, "Theclimateguy / AI_economy", fontsize=7.4, color="#6B7280", ha="right")
        pdf.savefig(fig)
        plt.close(fig)
    print(f"Saved report: {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    build_report()

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ARTIFACT_TOOL =
  process.env.ARTIFACT_TOOL_PATH ||
  path.join(
    os.homedir(),
    ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs",
  );

const { Presentation, PresentationFile } = await import(ARTIFACT_TOOL);

const OUT_DIR = path.join(ROOT, "output", "reports");
const RISK_FIG = path.join(ROOT, "output", "attention_monopoly_risk_gradient.png");
const PPTX_PATH = path.join(OUT_DIR, "attention_monopoly_gradient_comments_ru.pptx");

const W = 1280;
const H = 720;
const C = {
  ink: "#111827",
  muted: "#4B5563",
  blue: "#1F4E79",
  blue2: "#D8E6F3",
  green: "#047857",
  red: "#B91C1C",
  amber: "#B45309",
  paper: "#F8FAFC",
  line: "#CBD5E1",
  white: "#FFFFFF",
};

function addText(slide, text, left, top, width, height, style = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
  });
  box.text.set(text);
  box.text.style = {
    fontSize: style.fontSize ?? 24,
    color: style.color ?? C.ink,
    bold: style.bold ?? false,
    alignment: style.alignment ?? "left",
    lineSpacing: style.lineSpacing ?? 1.15,
  };
  if (style.verticalAlignment) box.text.verticalAlignment = style.verticalAlignment;
  return box;
}

function addRect(slide, left, top, width, height, fill, line = "none") {
  return slide.shapes.add({
    geometry: "rect",
    position: { left, top, width, height },
    fill,
    line: line === "none" ? { style: "solid", width: 0, fill } : line,
  });
}

function addHeader(slide, kicker, title) {
  addRect(slide, 0, 0, W, 20, C.blue);
  addText(slide, kicker, 56, 36, 520, 22, { fontSize: 13, color: C.blue, bold: true });
  addText(slide, title, 56, 64, 820, 80, { fontSize: 36, bold: true, lineSpacing: 1.05 });
}

function addFooter(slide, n) {
  addText(slide, "AI economy | attention monopoly scenario", 56, 684, 480, 18, { fontSize: 10, color: C.muted });
  addText(slide, String(n), 1192, 684, 32, 18, { fontSize: 10, color: C.muted, alignment: "right" });
}

function addRiskImage(slide, left, top, width, height) {
  slide.images.add({
    data: fs.readFileSync(RISK_FIG),
    contentType: "image/png",
    position: { left, top, width, height },
  });
}

function addCallout(slide, label, body, left, top, width, color) {
  addRect(slide, left, top, 5, 86, color);
  addText(slide, label, left + 18, top + 2, width - 18, 24, { fontSize: 16, bold: true, color });
  addText(slide, body, left + 18, top + 30, width - 18, 52, { fontSize: 15, color: C.ink, lineSpacing: 1.18 });
}

function slide01(p) {
  const s = p.slides.add();
  s.background.fill = C.white;
  addHeader(s, "ГРАДИЕНТ РИСКА", "Монополия внимания: риск перехвата клиентского канала");
  addRiskImage(s, 58, 176, 760, 452);

  addRect(s, 880, 176, 320, 452, C.paper, { style: "solid", width: 1, fill: C.line });
  addText(s, "Как читать график", 910, 204, 250, 34, { fontSize: 24, bold: true });
  addText(
    s,
    "X: способность встроиться в AI/platform stack\nY: зависимость от поиска, рекомендаций и discovery channel\nЦвет: композитный риск 0-100\nРазмер точки: масштаб ВДС отрасли",
    910,
    254,
    248,
    160,
    { fontSize: 17, lineSpacing: 1.25 },
  );
  addText(
    s,
    "Красная зона справа-вверху: отрасли, которым важен поиск и которые легко подключить к платформе.",
    910,
    438,
    248,
    110,
    { fontSize: 20, bold: true, color: C.red, lineSpacing: 1.15 },
  );
  addFooter(s, 1);
}

function slide02(p) {
  const s = p.slides.add();
  s.background.fill = C.white;
  addHeader(s, "ЛОГИКА ОСЕЙ", "Риск теперь растет при высокой зависимости от внимания и высокой подключаемости");

  addRect(s, 70, 170, 320, 300, "#EEF6FF", { style: "solid", width: 1, fill: C.blue2 });
  addText(s, "D: attention dependency", 95, 195, 270, 34, { fontSize: 24, bold: true, color: C.blue });
  addText(
    s,
    "Высокий D означает, что клиентский выбор начинается с поиска, рекомендаций, сравнения, маркетплейса или карты.",
    95,
    255,
    250,
    130,
    { fontSize: 19, lineSpacing: 1.22 },
  );

  addRect(s, 480, 170, 320, 300, "#F0FDF4", { style: "solid", width: 1, fill: "#BBF7D0" });
  addText(s, "I: integration capacity", 505, 195, 270, 34, { fontSize: 24, bold: true, color: C.green });
  addText(
    s,
    "Высокий I означает, что отрасль можно быстро завести в AI-интерфейс через API, каталоги, delivery, booking или lead flow.",
    505,
    255,
    250,
    145,
    { fontSize: 19, lineSpacing: 1.22 },
  );

  addRect(s, 890, 170, 320, 300, "#FEF2F2", { style: "solid", width: 1, fill: "#FECACA" });
  addText(s, "Risk score", 915, 195, 270, 34, { fontSize: 24, bold: true, color: C.red });
  addText(
    s,
    "Минимальная математика: риск это взвешенная сумма D, I, markup, SME vulnerability, gatekeeping и adoption к 2035.",
    915,
    255,
    250,
    145,
    { fontSize: 19, lineSpacing: 1.22 },
  );

  addText(
    s,
    "Главная смена знака: в риск-градиенте используется I, а не 1-I. Поэтому самый опасный сектор не тот, кто плохо готов к цифре, а тот, кого AI-платформа может быстро встроить и отранжировать.",
    90,
    535,
    1080,
    90,
    { fontSize: 24, bold: true, color: C.ink, lineSpacing: 1.14 },
  );
  addFooter(s, 2);
}

function slide03(p) {
  const s = p.slides.add();
  s.background.fill = C.white;
  addHeader(s, "КАЛИБРОВКА", "После правки торговля и ИТ уходят вправо-вверх, добыча и стройка влево-вниз");

  addRiskImage(s, 64, 155, 610, 385);

  addCallout(
    s,
    "Правый верхний кластер",
    "ИТ и связь, торговля не едой и торговля едой: высокий поиск/discovery плюс высокая platform-connectability.",
    730,
    165,
    420,
    C.red,
  );
  addCallout(
    s,
    "Средний слой",
    "Финансы и проф. услуги: высокий risk score из-за gatekeeping, lead allocation и роли default recommendations.",
    730,
    275,
    420,
    C.amber,
  );
  addCallout(
    s,
    "Левый нижний кластер",
    "Добыча и строительство: B2B/project-based спрос, низкая зависимость от consumer search и слабая стандартизация под единый AI-интерфейс.",
    730,
    385,
    420,
    C.green,
  );

  addText(
    s,
    "Итог: график теперь показывает не цифровую готовность сама по себе, а риск перехвата клиентского канала платформой.",
    82,
    590,
    1060,
    52,
    { fontSize: 24, bold: true, color: C.ink, lineSpacing: 1.1 },
  );
  addFooter(s, 3);
}

function slide04(p) {
  const s = p.slides.add();
  s.background.fill = C.white;
  addHeader(s, "ДОПУЩЕНИЯ", "Что именно заложено в этот сценарный слой");

  const items = [
    ["Единая поверхность доступа", "AI-ассистент становится default interface для поиска поставщиков, товаров и услуг."],
    ["Платформенное ранжирование", "Риск связан не только с комиссией, но и с тем, кто получает выдачу, lead flow и рекомендацию по умолчанию."],
    ["Торговля и ИТ", "Сектора одновременно зависят от discovery и хорошо подключаются через каталоги, API, delivery, marketplace rails."],
    ["Добыча и стройка", "Спрос менее consumer-search-driven, больше B2B/project based, поэтому они должны лежать левее и ниже."],
  ];
  items.forEach((it, idx) => {
    const y = 160 + idx * 112;
    addRect(s, 84, y, 46, 46, idx < 2 ? C.blue : idx === 2 ? C.red : C.green);
    addText(s, String(idx + 1), 84, y + 7, 46, 24, { fontSize: 20, bold: true, color: C.white, alignment: "center" });
    addText(s, it[0], 155, y - 2, 360, 30, { fontSize: 23, bold: true });
    addText(s, it[1], 155, y + 35, 930, 44, { fontSize: 18, color: C.muted, lineSpacing: 1.18 });
  });

  addText(
    s,
    "Формула оставлена как компактный weighted score: R = f(D, I, markup, SME, gatekeeping, adoption). Детальная параметризация хранится в YAML и CSV слоя attention_monopoly.",
    84,
    620,
    1070,
    44,
    { fontSize: 18, color: C.ink, lineSpacing: 1.12 },
  );
  addFooter(s, 4);
}

fs.mkdirSync(OUT_DIR, { recursive: true });
const presentation = Presentation.create({ slideSize: { width: W, height: H } });
slide01(presentation);
slide02(presentation);
slide03(presentation);
slide04(presentation);

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(PPTX_PATH);
console.log(`Saved: ${path.relative(ROOT, PPTX_PATH)}`);

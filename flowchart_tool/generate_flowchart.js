// Genera un flujograma .pptx VERTICAL (formas nativas editables) a partir de un JSON
// de pasos exportado desde la planilla de relevamiento. Las fases se agrupan en
// bloques apilados de arriba hacia abajo, con borde punteado y etiqueta, similar
// al estilo de flujograma de Visio de referencia.
//
// Uso: node generate_flowchart.js pasos.json "Título del proceso" salida.pptx

const fs = require("fs");
const pptxgen = require("pptxgenjs");

const [, , jsonPath, title, outPath] = process.argv;
if (!jsonPath || !title || !outPath) {
  console.error("Uso: node generate_flowchart.js pasos.json \"Título\" salida.pptx");
  process.exit(1);
}

const steps = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
const byId = {};
steps.forEach((s, idx) => (byId[s.id] = { ...s, idx }));

// ---------- 0. Detectar arcos de retroceso (loops) con DFS ----------
// Un proceso real suele tener vueltas ("si no cumple, vuelve al paso X").
// Esos arcos no deben usarse para calcular el orden de filas (crean ciclos);
// se dibujan aparte, siempre como "vuelve hacia atrás".
const WHITE = 0, GRAY = 1, BLACK = 2;
const dfsColor = {};
steps.forEach((s) => (dfsColor[s.id] = WHITE));
const backEdges = new Set(); // `${from}->${to}`
function dfsVisit(id) {
  dfsColor[id] = GRAY;
  const node = byId[id];
  (node.siguientes || []).forEach((t) => {
    if (!byId[t]) return;
    if (dfsColor[t] === WHITE) dfsVisit(t);
    else if (dfsColor[t] === GRAY) backEdges.add(id + "->" + t);
  });
  dfsColor[id] = BLACK;
}
steps.forEach((s) => {
  if (dfsColor[s.id] === WHITE) dfsVisit(s.id);
});

// ---------- 1. Filas (orden topológico = eje vertical), ignorando arcos de retroceso ----------
const indegree = {};
steps.forEach((s) => (indegree[s.id] = 0));
steps.forEach((s) =>
  s.siguientes.forEach((t) => {
    if (byId[t] && !backEdges.has(s.id + "->" + t)) indegree[t] = (indegree[t] || 0) + 1;
  })
);

const row = {};
const preds = {}; // id -> [ids predecesores] (sin arcos de retroceso)
steps.forEach((s) => (preds[s.id] = []));
steps.forEach((s) =>
  s.siguientes.forEach((t) => {
    if (byId[t] && !backEdges.has(s.id + "->" + t)) (preds[t] = preds[t] || []).push(s.id);
  })
);

let start = steps.filter((s) => indegree[s.id] === 0).map((s) => s.id);
start.forEach((id) => (row[id] = 0));
const indegreeLeft = { ...indegree };
const queue = [...start];
let qi = 0;
while (qi < queue.length) {
  const id = queue[qi++];
  const node = byId[id];
  node.siguientes.forEach((t) => {
    if (!byId[t] || backEdges.has(id + "->" + t)) return;
    row[t] = Math.max(row[t] ?? 0, row[id] + 1);
    indegreeLeft[t] -= 1;
    if (indegreeLeft[t] === 0) queue.push(t);
  });
}
steps.forEach((s) => {
  if (row[s.id] === undefined) row[s.id] = 0;
});
const maxRow = Math.max(...steps.map((s) => row[s.id]));

// ---------- 2. Columnas (ramas en paralelo, eje horizontal) ----------
// Agrupa por fila y asigna columna intentando heredar la del/de los predecesor(es)
// para mantener el flujo recto; si está ocupada busca la más cercana libre.
const rowsList = [];
for (let r = 0; r <= maxRow; r++) rowsList.push([]);
steps.forEach((s) => rowsList[row[s.id]].push(s));
rowsList.forEach((list) => list.sort((a, b) => a.idx - b.idx));

const col = {};
rowsList.forEach((list) => {
  const used = new Set();
  list.forEach((s) => {
    const ps = preds[s.id] || [];
    let preferred;
    if (ps.length) {
      preferred = Math.round(ps.reduce((sum, p) => sum + (col[p] ?? 0), 0) / ps.length);
    } else {
      preferred = 0;
    }
    let c = preferred;
    let step = 0;
    while (used.has(c)) {
      step += 1;
      c = preferred + (step % 2 === 1 ? Math.ceil(step / 2) : -Math.ceil(step / 2));
    }
    if (c < 0) c = Math.max(...used, -1) + 1; // fallback simple
    used.add(c);
    col[s.id] = c;
  });
});
const minCol = Math.min(...steps.map((s) => col[s.id]));
steps.forEach((s) => (col[s.id] -= minCol)); // normalizar a >= 0
const maxCol = Math.max(...steps.map((s) => col[s.id]));

// ---------- 3. Fases: agrupar filas consecutivas por fase dominante ----------
const faseOfRow = [];
for (let r = 0; r <= maxRow; r++) {
  const list = rowsList[r];
  if (!list.length) {
    faseOfRow.push(faseOfRow[r - 1] || "");
    continue;
  }
  const counts = {};
  list.forEach((s) => (counts[s.fase] = (counts[s.fase] || 0) + 1));
  const dominant = Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
  faseOfRow.push(dominant);
}
const faseBlocks = []; // {fase, rowStart, rowEnd}
faseOfRow.forEach((fase, r) => {
  const last = faseBlocks[faseBlocks.length - 1];
  if (last && last.fase === fase) {
    last.rowEnd = r;
  } else {
    faseBlocks.push({ fase, rowStart: r, rowEnd: r });
  }
});

// ---------- 4. Geometría ----------
const NODE_W = 2.3;
const NODE_H = 0.6;
const DECISION_W = 1.9;
const DECISION_H = 0.85;
const COL_W = 2.6;
const ROW_H = 1.05;
const PHASE_GAP = 0.34; // espacio extra entre bloques de fase
const PHASE_LABEL_H = 0.28;
const MARGIN_TOP = 1.05;
const MARGIN_LEFT = 0.4;
const MARGIN_RIGHT = 0.4;
const MARGIN_BOTTOM = 0.4;

// Y de cada fila, agregando el gap de fase al iniciar un bloque nuevo
const rowY = [];
{
  let y = MARGIN_TOP;
  let prevFase = null;
  for (let r = 0; r <= maxRow; r++) {
    const fase = faseOfRow[r];
    const blockStart = faseBlocks.some((b) => b.fase === fase && b.rowStart === r);
    if (blockStart) {
      y += PHASE_GAP + PHASE_LABEL_H;
    }
    rowY.push(y);
    y += ROW_H;
    prevFase = fase;
  }
}
const slideH = (rowY[maxRow] || MARGIN_TOP) + ROW_H - (ROW_H - NODE_H) + MARGIN_BOTTOM;
const GUTTER_W = 0.9; // carril lateral para enrutar saltos de fila sin cruzar cajas
const gutterX = MARGIN_LEFT + (maxCol + 1) * COL_W + GUTTER_W / 2;
const slideW = MARGIN_LEFT + (maxCol + 1) * COL_W + GUTTER_W + MARGIN_RIGHT;

function nodeXY(step) {
  const r = row[step.id];
  const c = col[step.id];
  const isDecision = step.tipo === "Decisión";
  const w = isDecision ? DECISION_W : NODE_W;
  const h = isDecision ? DECISION_H : NODE_H;
  const cx = MARGIN_LEFT + c * COL_W + COL_W / 2;
  const x = cx - w / 2;
  const y = rowY[r] + (ROW_H - h) / 2;
  return { x, y, w, h };
}

// ---------- 5. Paleta por Fase ----------
const PALETTE = [
  { fill: "CADCFC", line: "1E2761" },
  { fill: "D7EFD9", line: "2C5F2D" },
  { fill: "F9E0C6", line: "B85042" },
  { fill: "E6D9F2", line: "5B2C6F" },
  { fill: "FDE9E9", line: "990011" },
  { fill: "DDEFEF", line: "028090" },
];
const fasesOrdered = [];
faseBlocks.forEach((b) => {
  if (!fasesOrdered.includes(b.fase)) fasesOrdered.push(b.fase);
});
const faseColor = {};
fasesOrdered.forEach((f, i) => (faseColor[f] = PALETTE[i % PALETTE.length]));

// ---------- 6. Construcción del PPTX ----------
const pres = new pptxgen();
pres.defineLayout({ name: "FLOW", width: slideW, height: slideH });
pres.layout = "FLOW";

const slide = pres.addSlide();
slide.background = { color: "FFFFFF" };

slide.addText(title, {
  x: 0.3,
  y: 0.15,
  w: slideW - 0.6,
  h: 0.4,
  fontFace: "Calibri",
  fontSize: 20,
  bold: true,
  color: "1E2761",
});

// ---------- 7. Bloques de fase (borde punteado + etiqueta) ----------
faseBlocks.forEach((b) => {
  const yTop = rowY[b.rowStart] - PHASE_GAP - PHASE_LABEL_H;
  const lastRowBottomY = rowY[b.rowEnd] + ROW_H - (ROW_H - NODE_H) / 2;
  const yBottom = lastRowBottomY + 0.08;
  const c = faseColor[b.fase] || { fill: "EFEFEF", line: "888888" };

  slide.addShape("rect", {
    x: MARGIN_LEFT - 0.15,
    y: yTop,
    w: slideW - MARGIN_LEFT - MARGIN_RIGHT + 0.3,
    h: yBottom - yTop,
    fill: { color: c.fill, transparency: 88 },
    line: { color: c.line, width: 1, dashType: "dash" },
  });
  slide.addText(b.fase, {
    x: MARGIN_LEFT - 0.1,
    y: yTop + 0.02,
    w: 3,
    h: PHASE_LABEL_H,
    fontFace: "Calibri",
    fontSize: 11,
    bold: true,
    color: c.line,
  });
});

// ---------- 8. Conectores ----------
function edgePoint(box, side) {
  switch (side) {
    case "right":
      return { x: box.x + box.w, y: box.y + box.h / 2 };
    case "left":
      return { x: box.x, y: box.y + box.h / 2 };
    case "top":
      return { x: box.x + box.w / 2, y: box.y };
    case "bottom":
      return { x: box.x + box.w / 2, y: box.y + box.h };
  }
}

function drawSegment(p1, p2) {
  const x = Math.min(p1.x, p2.x);
  const y = Math.min(p1.y, p2.y);
  const w = Math.max(Math.abs(p2.x - p1.x), 0.01);
  const h = Math.max(Math.abs(p2.y - p1.y), 0.01);
  const flipH = p2.x < p1.x;
  const flipV = p2.y < p1.y;
  slide.addShape("line", {
    x,
    y,
    w,
    h,
    flipH,
    flipV,
    line: { color: "6B7280", width: 1.5 },
  });
}

function drawArrowSegment(p1, p2) {
  const x = Math.min(p1.x, p2.x);
  const y = Math.min(p1.y, p2.y);
  const w = Math.max(Math.abs(p2.x - p1.x), 0.01);
  const h = Math.max(Math.abs(p2.y - p1.y), 0.01);
  const flipH = p2.x < p1.x;
  const flipV = p2.y < p1.y;
  slide.addShape("line", {
    x,
    y,
    w,
    h,
    flipH,
    flipV,
    line: { color: "6B7280", width: 1.5, endArrowType: "triangle" },
  });
}

function addLabel(x, y, label) {
  slide.addText(label, {
    x: x - 0.35,
    y: y - 0.14,
    w: 0.7,
    h: 0.26,
    fontFace: "Calibri",
    fontSize: 9,
    bold: true,
    color: "1E2761",
    align: "center",
    valign: "middle",
    fill: { color: "FFFFFF" },
  });
}

steps.forEach((s) => {
  const from = nodeXY(s);
  s.siguientes.forEach((tid, i) => {
    const t = byId[tid];
    if (!t) return;
    const to = nodeXY(t);
    const label = s.etiquetas_rama && s.etiquetas_rama[i];
    const isBack = backEdges.has(s.id + "->" + tid);
    const rowGap = isBack ? -1 : row[tid] - row[s.id];

    if (rowGap === 1) {
      // fila siguiente inmediata: línea directa (recta o diagonal si cambia de columna)
      const p1 = edgePoint(from, "bottom");
      const p2 = edgePoint(to, "top");
      drawArrowSegment(p1, p2);
      if (label) addLabel((p1.x + p2.x) / 2, (p1.y + p2.y) / 2, label);
    } else if (rowGap === 0) {
      // misma fila: conecta por el costado
      const p1 = edgePoint(from, to.x > from.x ? "right" : "left");
      const p2 = edgePoint(to, to.x > from.x ? "left" : "right");
      drawArrowSegment(p1, p2);
      if (label) addLabel((p1.x + p2.x) / 2, (p1.y + p2.y) / 2, label);
    } else {
      // salto de fila (>1) o vuelve hacia atrás: rodea por el carril lateral derecho
      // para no cruzar cajas intermedias.
      const p1 = edgePoint(from, "right");
      const p3 = edgePoint(to, "right");
      const p2 = { x: gutterX, y: p1.y };
      const p4 = { x: gutterX, y: p3.y };
      drawSegment(p1, p2);
      drawSegment(p2, p4);
      drawArrowSegment(p4, p3);
      if (label) addLabel(gutterX, (p2.y + p4.y) / 2, label);
    }
  });
});

// ---------- 9. Formas de los pasos ----------
const SHAPE_BY_TYPE = {
  "Inicio/Fin": "ellipse",
  "Proceso": "roundRect",
  "Decisión": "diamond",
  "Documento": "flowChartDocument",
  "Conector": "ellipse",
};

steps.forEach((s) => {
  const box = nodeXY(s);
  const shapeType = SHAPE_BY_TYPE[s.tipo] || "roundRect";
  const colorSet = faseColor[s.fase] || { fill: "EDEDED", line: "555555" };

  const opts = {
    x: box.x,
    y: box.y,
    w: box.w,
    h: box.h,
    fill: { color: colorSet.fill },
    line: { color: colorSet.line, width: 1.25 },
    shadow: { type: "outer", color: "888888", opacity: 0.25, blur: 3, offset: 1, angle: 90 },
  };
  if (shapeType === "roundRect") opts.rectRadius = 0.1;

  slide.addShape(shapeType, opts);
  slide.addText(s.nombre, {
    x: box.x + 0.08,
    y: box.y,
    w: box.w - 0.16,
    h: box.h,
    fontFace: "Calibri",
    fontSize: s.tipo === "Decisión" ? 9.5 : 10,
    color: "1F2430",
    align: "center",
    valign: "middle",
    fit: "shrink",
  });

  if (s.notas) {
    slide.addText(`ⓘ ${s.notas}`, {
      x: box.x,
      y: box.y + box.h + 0.02,
      w: box.w,
      h: 0.2,
      fontFace: "Calibri",
      fontSize: 7,
      italic: true,
      color: "8A8F98",
      align: "center",
    });
  }
});

pres.writeFile({ fileName: outPath }).then(() => {
  console.log("OK ->", outPath);
});

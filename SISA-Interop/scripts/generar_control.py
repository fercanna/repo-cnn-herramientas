#!/usr/bin/env python3
"""
generar_control.py — Planilla de control de interoperabilidad SISA
==================================================================
Lee un log JSON generado por main.py y produce un Excel que replica
la lógica de la hoja de trabajo de bacteriología: una fila por paciente,
columnas por determinación, semáforo de estado.

Uso:
    python scripts/generar_control.py <log.json>
    python scripts/generar_control.py logs/main_20260605_100500.json
    python scripts/generar_control.py logs/main_20260605_100500.json --out mi_control.xlsx

Integración con la UI:
    Se puede llamar desde ui.py pasando el path del último log generado.
"""

import json
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("ERROR: openpyxl no instalado. Ejecutar: pip install openpyxl")
    sys.exit(1)

# ── Paleta de colores ─────────────────────────────────────────────────────────
C_HEADER    = PatternFill("solid", fgColor="1F3864")  # azul oscuro — encabezados
C_SUBHEAD   = PatternFill("solid", fgColor="2E75B6")  # azul medio — sub-encabezados
C_GREEN     = PatternFill("solid", fgColor="C6EFCE")  # verde — NUEVO OK
C_LGREEN    = PatternFill("solid", fgColor="E2EFDA")  # verde claro — REUSE OK
C_GRAY      = PatternFill("solid", fgColor="D9D9D9")  # gris — SKIP / no aplica
C_RED       = PatternFill("solid", fgColor="FFC7CE")  # rojo — ERROR
C_YELLOW    = PatternFill("solid", fgColor="FFEB9C")  # amarillo — advertencia
C_SUMMARY_G = PatternFill("solid", fgColor="A9D18E")  # verde resumen
C_SUMMARY_R = PatternFill("solid", fgColor="FF7676")  # rojo resumen

FONT_WHITE  = Font(bold=True, color="FFFFFF", size=11)
FONT_BOLD   = Font(bold=True)
ALIGN_C     = Alignment(horizontal="center", vertical="center")
ALIGN_L     = Alignment(horizontal="left",   vertical="center")

# ── Mapeo de estudios LIS → columnas del control ──────────────────────────────
# Clave: substring del campo "estudio" en el log
# Valor: (columna_display, grupo_evento)
ESTUDIO_MAP = {
    "7101":  ("SIFI (Treponémica)",       "Sífilis"),
    "14 SIF": ("SIFI (Banco Sangre)",      "Sífilis"),
    "201":   ("Test Rápido (TP)",          "Sífilis"),
    "72 SIF": ("VDRL",                     "Sífilis"),
    "VIH":   ("Anti-VIH Combo",           "VIH"),
    "VHC":   ("Anti-VHC",                 "Hepatitis C"),
    "CRUZI": ("Chagas (ELISA)",           "Chagas crónico"),
    "INFLUE":("Influenza A",              "Respiratorio"),
    "SINCIT":("VRS",                      "Respiratorio"),
}

# Columnas fijas en la planilla pivoteada de sífilis
SIFILIS_COLS = [
    "SIFI (Treponémica)",
    "SIFI (Banco Sangre)",
    "Test Rápido (TP)",
    "VDRL",
]


def get_det_col(estudio: str) -> tuple[str, str]:
    """Devuelve (columna_display, grupo_evento) para un estudio del log."""
    est_upper = estudio.upper()
    for key, val in ESTUDIO_MAP.items():
        if key.upper() in est_upper:
            return val
    return (estudio, "Otros")


def get_id_evento_label(caso: dict) -> str:
    """Deriva la sub-clasificación (General / Gestante) desde el log."""
    try:
        id_ev = caso["ws400"]["payload"]["eventoCasoNominal"]["idEvento"]
        return {115: "Gestante", 193: "General"}.get(id_ev, str(id_ev))
    except (KeyError, TypeError):
        pob = caso.get("poblacion", "")
        return "Gestante" if pob == "GESTANTE" else "General"


def caso_fill(caso: dict) -> PatternFill:
    modo = caso.get("modo") or ""
    ok   = caso.get("ok")
    if modo in ("SKIP", "SKIP_VDRL"):
        return C_GRAY
    if ok is False or caso.get("error"):
        return C_RED
    if ok is True:
        return C_GREEN if modo == "NUEVO" else C_LGREEN
    return C_YELLOW


def caso_notif_label(caso: dict) -> str:
    modo = caso.get("modo") or ""
    ok   = caso.get("ok")
    if modo == "SKIP":
        return "SKIP"
    if modo == "SKIP_VDRL":
        return "SIN TREPO"
    if ok is True:
        return "OK ✓"
    if ok is False:
        return "ERROR ✗"
    return "?"


def caso_error(caso: dict) -> str:
    err = caso.get("error") or ""
    if not err and not caso.get("ok"):
        # Intentar sacar mensaje de api76 o ws400
        for api_key in ("api76", "api75", "ws400"):
            api = caso.get(api_key) or {}
            resp = api.get("response") or {}
            if isinstance(resp, dict):
                desc = resp.get("description") or resp.get("error") or ""
                if desc:
                    return str(desc)[:120]
    return str(err)[:120] if err else ""


# ── Helpers de formato ─────────────────────────────────────────────────────────
def set_header(cell, text, fill=None, font=None, align=None):
    cell.value = text
    cell.fill  = fill  or C_HEADER
    cell.font  = font  or FONT_WHITE
    cell.alignment = align or ALIGN_C


def autofit(ws, col_letter, width):
    ws.column_dimensions[col_letter].width = width


def add_border(cell):
    thin = Side(style="thin")
    cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)


# ── Construcción del Excel ────────────────────────────────────────────────────
def build_excel(data: dict, out_path: str):
    casos = data.get("casos", [])

    # Agrupar casos por (dni, orden) — un paciente puede tener varias filas
    # Para sífilis pivoteamos; para otros hacemos flat.
    sifilis_pacientes: dict[tuple, dict] = {}  # (dni, orden) → {col: caso}
    otros_casos: list[dict] = []

    for caso in casos:
        det_col, grupo = get_det_col(caso.get("estudio", ""))
        dni   = caso.get("dni", "")
        orden = caso.get("orden", "")
        key   = (dni, orden)

        if grupo == "Sífilis":
            if key not in sifilis_pacientes:
                sifilis_pacientes[key] = {
                    "dni": dni,
                    "orden": orden,
                    "sucursal": caso.get("sucursal", ""),
                    "sub": get_id_evento_label(caso),
                    "cols": {},
                }
            sifilis_pacientes[key]["cols"][det_col] = caso
        else:
            otros_casos.append({**caso, "_det_col": det_col, "_grupo": grupo})

    wb = openpyxl.Workbook()

    # ── Sheet 1: Resumen ──────────────────────────────────────────────────────
    ws_sum = wb.active
    ws_sum.title = "Resumen"
    _build_resumen(ws_sum, data, sifilis_pacientes, otros_casos)

    # ── Sheet 2: Sífilis (pivot) ──────────────────────────────────────────────
    if sifilis_pacientes:
        ws_sif = wb.create_sheet("Sífilis")
        _build_sifilis(ws_sif, sifilis_pacientes)

    # ── Sheet 3+: Un sheet por grupo de otros eventos ─────────────────────────
    grupos_otros: dict[str, list] = defaultdict(list)
    for c in otros_casos:
        grupos_otros[c["_grupo"]].append(c)

    for grupo, casos_grupo in sorted(grupos_otros.items()):
        ws_g = wb.create_sheet(grupo[:31])
        _build_otros(ws_g, grupo, casos_grupo)

    wb.save(out_path)
    print(f"Excel guardado en: {out_path}")


def _build_resumen(ws, data: dict, sifilis_pacs: dict, otros: list):
    """Sheet de resumen ejecutivo."""
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 45
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14

    r = 1
    # Título
    ws.merge_cells(f"A{r}:F{r}")
    set_header(ws[f"A{r}"], "CONTROL DE INTEROPERABILIDAD SISA — LABORATORIO CENTRAL")
    ws.row_dimensions[r].height = 28
    r += 1

    # Metadata del run
    meta = [
        ("Archivo TXT procesado", data.get("archivo", "—")),
        ("Fecha de corrida",       data.get("timestamp", "—")),
        ("Entorno",                data.get("entorno",   "—")),
        ("Generado el",            datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]
    for label, val in meta:
        ws[f"A{r}"] = label
        ws[f"B{r}"] = val
        ws[f"A{r}"].font = FONT_BOLD
        r += 1

    r += 1  # espacio

    # Totales globales
    ws.merge_cells(f"A{r}:F{r}")
    set_header(ws[f"A{r}"], "TOTALES DE LA CORRIDA", fill=C_SUBHEAD)
    ws.row_dimensions[r].height = 22
    r += 1

    totales = [
        ("Total casos procesados", data.get("total",         0)),
        ("NUEVO (caso nuevo)",     data.get("nuevo",         0)),
        ("REUSE (reutiliza muestra)", data.get("reuse",      0)),
        ("SKIP (ya existía en SISA)", data.get("skip_unicidad", 0)),
        ("SKIP_VDRL (sin treponémica)", data.get("skip_vdrl", 0)),
        ("Errores",                data.get("errores",       0)),
    ]
    for label, val in totales:
        ws[f"A{r}"] = label
        ws[f"B{r}"] = val
        ws[f"A{r}"].font = FONT_BOLD
        if label == "Errores" and val > 0:
            ws[f"B{r}"].fill = C_RED
        elif "NUEVO" in label and val > 0:
            ws[f"B{r}"].fill = C_GREEN
        r += 1

    r += 1

    # Por sub-evento
    ws.merge_cells(f"A{r}:F{r}")
    set_header(ws[f"A{r}"], "DETALLE POR SUB-EVENTO", fill=C_SUBHEAD)
    ws.row_dimensions[r].height = 22
    r += 1

    headers_se = ["Sub-evento / Grupo", "Determinación", "Total", "OK ✓", "SKIP", "ERROR ✗"]
    for ci, h in enumerate(headers_se, 1):
        cell = ws.cell(row=r, column=ci, value=h)
        cell.fill  = PatternFill("solid", fgColor="BDD7EE")
        cell.font  = FONT_BOLD
        cell.alignment = ALIGN_C
    r += 1

    # Calcular stats por (grupo, det_col)
    stats: dict[tuple, dict] = defaultdict(lambda: {"total": 0, "ok": 0, "skip": 0, "error": 0})

    for pac in sifilis_pacientes_iter(sifilis_pacs):
        for det_col, caso in pac["cols"].items():
            grupo_key = (f"Sífilis ({pac['sub']})", det_col)
            stats[grupo_key]["total"] += 1
            n = caso_notif_label(caso)
            if "OK" in n:       stats[grupo_key]["ok"]    += 1
            elif "SKIP" in n:   stats[grupo_key]["skip"]  += 1
            else:               stats[grupo_key]["error"] += 1

    for c in otros:
        grupo_key = (c["_grupo"], c["_det_col"])
        stats[grupo_key]["total"] += 1
        n = caso_notif_label(c)
        if "OK" in n:       stats[grupo_key]["ok"]    += 1
        elif "SKIP" in n:   stats[grupo_key]["skip"]  += 1
        else:               stats[grupo_key]["error"] += 1

    for (grupo, det), s in sorted(stats.items()):
        ws.cell(row=r, column=1, value=grupo)
        ws.cell(row=r, column=2, value=det)
        ws.cell(row=r, column=3, value=s["total"])
        c_ok  = ws.cell(row=r, column=4, value=s["ok"])
        c_sk  = ws.cell(row=r, column=5, value=s["skip"])
        c_err = ws.cell(row=r, column=6, value=s["error"])
        c_ok.alignment  = ALIGN_C
        c_sk.alignment  = ALIGN_C
        c_err.alignment = ALIGN_C
        if s["ok"]    > 0: c_ok.fill  = C_SUMMARY_G
        if s["error"] > 0: c_err.fill = C_SUMMARY_R
        if s["skip"]  > 0: c_sk.fill  = C_GRAY
        r += 1

    # Leyenda
    r += 1
    ws.merge_cells(f"A{r}:F{r}")
    set_header(ws[f"A{r}"], "LEYENDA", fill=C_SUBHEAD)
    ws.row_dimensions[r].height = 20
    r += 1
    leyenda = [
        (C_GREEN,  "OK ✓ NUEVO  — Caso y muestra creados en SISA por primera vez"),
        (C_LGREEN, "OK ✓ REUSE  — Resultado cargado sobre muestra ya existente (p. ej. VDRL sobre treponémica)"),
        (C_GRAY,   "SKIP        — El caso ya existía en SISA antes de esta corrida"),
        (C_GRAY,   "SIN TREPO   — VDRL sin treponémica asociada, no se puede cargar"),
        (C_RED,    "ERROR ✗     — El caso no fue notificado por un error de API"),
    ]
    for fill, texto in leyenda:
        ws[f"A{r}"].fill  = fill
        ws[f"A{r}"].value = "  "
        ws.merge_cells(f"B{r}:F{r}")
        ws[f"B{r}"].value = texto
        r += 1


def sifilis_pacientes_iter(sifilis_pacs: dict):
    """Itera pacientes de sífilis ordenados por orden LIS."""
    return sorted(sifilis_pacs.values(), key=lambda p: str(p["orden"]).zfill(10))


def _build_sifilis(ws, sifilis_pacs: dict):
    """Sheet pivoteada de sífilis: una fila por paciente, columnas por determinación."""

    ws.column_dimensions["A"].width = 10  # Orden
    ws.column_dimensions["B"].width = 22  # Sucursal
    ws.column_dimensions["C"].width = 13  # DNI
    ws.column_dimensions["D"].width = 12  # Población

    # Columnas dinámicas por determinación (4 fijas para sífilis)
    col_start = 5  # E en adelante
    det_cols = SIFILIS_COLS

    # Cada determinación ocupa 3 columnas: Resultado | Estado | ID SISA
    det_col_map = {}
    for i, det in enumerate(det_cols):
        base = col_start + i * 3
        det_col_map[det] = base
        ws.column_dimensions[get_column_letter(base)].width     = 22  # Resultado
        ws.column_dimensions[get_column_letter(base + 1)].width = 12  # Estado
        ws.column_dimensions[get_column_letter(base + 2)].width = 14  # ID SISA

    # Columna de errores al final
    col_err = col_start + len(det_cols) * 3
    ws.column_dimensions[get_column_letter(col_err)].width = 45

    # ── Fila 1: título ────────────────────────────────────────────────────────
    last_col = col_err
    ws.merge_cells(f"A1:{get_column_letter(last_col)}1")
    set_header(ws["A1"], "CONTROL SÍFILIS — hoja de trabajo bacteriología")
    ws.row_dimensions[1].height = 26

    # ── Fila 2: grupo de determinaciones (merge por cada det) ─────────────────
    set_header(ws["A2"], "Orden");     ws["A2"].fill = C_SUBHEAD
    set_header(ws["B2"], "Sucursal");  ws["B2"].fill = C_SUBHEAD
    set_header(ws["C2"], "DNI");       ws["C2"].fill = C_SUBHEAD
    set_header(ws["D2"], "Población"); ws["D2"].fill = C_SUBHEAD

    for det, base in det_col_map.items():
        cl = get_column_letter(base)
        cr = get_column_letter(base + 2)
        ws.merge_cells(f"{cl}2:{cr}2")
        set_header(ws[f"{cl}2"], det, fill=C_SUBHEAD)

    set_header(ws[f"{get_column_letter(col_err)}2"], "Error / Detalle", fill=C_SUBHEAD)

    # ── Fila 3: sub-encabezados por columna ───────────────────────────────────
    for det, base in det_col_map.items():
        set_header(ws.cell(3, base),     "Resultado LIS",  fill=PatternFill("solid", fgColor="BDD7EE"), font=FONT_BOLD)
        set_header(ws.cell(3, base + 1), "Estado SISA",    fill=PatternFill("solid", fgColor="BDD7EE"), font=FONT_BOLD)
        set_header(ws.cell(3, base + 2), "ID caso SISA",   fill=PatternFill("solid", fgColor="BDD7EE"), font=FONT_BOLD)

    ws.cell(3, 1).value = "Orden";     ws.cell(3, 1).font = FONT_BOLD
    ws.cell(3, 2).value = "Sucursal";  ws.cell(3, 2).font = FONT_BOLD
    ws.cell(3, 3).value = "DNI";       ws.cell(3, 3).font = FONT_BOLD
    ws.cell(3, 4).value = "Población"; ws.cell(3, 4).font = FONT_BOLD
    ws.cell(3, col_err).value = "Error / Detalle"; ws.cell(3, col_err).font = FONT_BOLD

    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:{get_column_letter(last_col)}3"

    # ── Datos ─────────────────────────────────────────────────────────────────
    r = 4
    any_error = False
    for pac in sifilis_pacientes_iter(sifilis_pacs):
        # Color de fila base: si hay algún error → rojo, sino neutro
        tiene_error  = any(not c.get("ok") and c.get("modo") not in ("SKIP", "SKIP_VDRL")
                           for c in pac["cols"].values())
        any_error = any_error or tiene_error

        ws.cell(r, 1, pac["orden"]).alignment = ALIGN_C
        ws.cell(r, 2, pac["sucursal"])
        ws.cell(r, 3, pac["dni"]).alignment = ALIGN_C
        ws.cell(r, 4, pac["sub"]).alignment  = ALIGN_C

        errores_fila = []
        for det in det_cols:
            base = det_col_map[det]
            caso = pac["cols"].get(det)
            if caso is None:
                # No viene este estudio para este paciente
                ws.cell(r, base).value     = "—"
                ws.cell(r, base + 1).value = "—"
                ws.cell(r, base + 2).value = "—"
                ws.cell(r, base).fill      = C_GRAY
                ws.cell(r, base + 1).fill  = C_GRAY
                ws.cell(r, base + 2).fill  = C_GRAY
            else:
                fill   = caso_fill(caso)
                estado = caso_notif_label(caso)
                resultado = caso.get("resultado", "")
                id_caso = (caso.get("ws400") or {}).get("id_caso", "")

                ws.cell(r, base,     resultado).fill = fill
                ws.cell(r, base + 1, estado).fill    = fill
                ws.cell(r, base + 2, id_caso).fill   = fill
                ws.cell(r, base + 1).alignment = ALIGN_C
                ws.cell(r, base + 2).alignment = ALIGN_C

                err = caso_error(caso)
                if err:
                    errores_fila.append(f"{det}: {err}")

        ws.cell(r, col_err, " | ".join(errores_fila) if errores_fila else "")
        r += 1

    # Ajustar altura de filas de encabezado
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 18


def _build_otros(ws, grupo: str, casos: list):
    """Sheet flat para VIH, Chagas, HVC, Respiratorio."""

    headers = [
        ("Orden",        10),
        ("Sucursal",     22),
        ("DNI",          14),
        ("Determinación",30),
        ("Resultado LIS",30),
        ("Modo",         10),
        ("Estado SISA",  13),
        ("ID caso SISA", 15),
        ("ID muestra",   14),
        ("Error",        50),
    ]

    # Título
    ws.merge_cells(f"A1:{get_column_letter(len(headers))}1")
    set_header(ws["A1"], f"CONTROL {grupo.upper()}")
    ws.row_dimensions[1].height = 26

    # Encabezados
    for ci, (h, w) in enumerate(headers, 1):
        cell = ws.cell(2, ci, h)
        cell.fill  = PatternFill("solid", fgColor="BDD7EE")
        cell.font  = FONT_BOLD
        cell.alignment = ALIGN_C
        ws.column_dimensions[get_column_letter(ci)].width = w

    ws.freeze_panes = "A3"
    ws.auto_filter.ref = f"A2:{get_column_letter(len(headers))}2"

    for ri, caso in enumerate(sorted(casos, key=lambda c: str(c.get("orden","")).zfill(10)), start=3):
        fill   = caso_fill(caso)
        ws400  = caso.get("ws400") or {}
        api75  = caso.get("api75") or {}
        id_caso  = ws400.get("id_caso", "")
        id_muestra = api75.get("id_muestra", "")

        vals = [
            caso.get("orden", ""),
            caso.get("sucursal", ""),
            caso.get("dni", ""),
            caso.get("_det_col", ""),
            caso.get("resultado", ""),
            caso.get("modo", ""),
            caso_notif_label(caso),
            id_caso,
            id_muestra,
            caso_error(caso),
        ]
        for ci, val in enumerate(vals, 1):
            cell = ws.cell(ri, ci, val)
            cell.fill = fill
            if ci in (1, 3, 6, 7, 8, 9):
                cell.alignment = ALIGN_C


# ── Punto de entrada ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Genera planilla de control de interoperabilidad SISA"
    )
    parser.add_argument("log", help="Ruta al archivo de log JSON (generado por main.py)")
    parser.add_argument(
        "--out", "-o",
        help="Ruta de salida del Excel (default: _salida/control_<timestamp>.xlsx)",
        default=None,
    )
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"ERROR: No se encontró el archivo: {log_path}")
        sys.exit(1)

    with open(log_path, encoding="utf-8") as f:
        data = json.load(f)

    if args.out:
        out_path = Path(args.out)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = log_path.stem.replace("main_", "")
        out_dir = log_path.parent.parent / "_salida"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / f"control_{stem}_{ts}.xlsx"

    build_excel(data, str(out_path))
    return str(out_path)


if __name__ == "__main__":
    main()

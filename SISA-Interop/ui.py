#!/usr/bin/env python3
"""
ui.py — Interfaz gráfica para SISA Interop.

Permite seleccionar el TXT del LIS y ejecutar el procesamiento
sin necesidad de usar la terminal (PowerShell/CMD).

Uso:
    python ui.py
    pythonw ui.py   ← sin ventana de consola (recomendado en Windows)
"""
from __future__ import annotations

import csv
import json
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

ROOT = Path(__file__).resolve().parent
LOGS_DIR = ROOT / "logs"
PYTHON = sys.executable


# ─── Colores dark-mode para el log ────────────────────────────────────────────
TAG_COLORS = {
    "nuevo":      "#4ec994",   # verde    — OK NUEVO
    "reuse":      "#9cdcfe",   # azul     — OK REUSE
    "skip":       "#dcdcaa",   # amarillo — SKIP unicidad
    "skip_vdrl":  "#b0b0b0",   # gris     — SKIP VDRL sin treponémica
    "err":        "#f48771",   # rojo     — ERR / ERROR
    "warn":       "#ce9178",   # naranja  — AVISO
    "bold":       "#ffffff",   # blanco   — separadores / resumen
    "header":     "#c586c0",   # violeta  — encabezados de sección
    "info":       "#9ca3af",   # gris     — líneas de detalle
}

# Opciones de filtro por evento — deben coincidir con GRUPOS_EVENTO de main.py.
# Sentinel para "todavia no elegiste nada": NUNCA se manda a main.py, se valida
# en _start_process() y bloquea el procesamiento (ver incidente sep-2026: se
# corrio sin elegir filtro y se interoperó TODO el listado de la semana en vez
# de solo sífilis). "Todos los eventos" sigue existiendo pero ahora es una
# opción explícita más de la lista — nunca la preseleccionada — y pide
# confirmación extra al arrancar (ver _start_process).
FILTRO_SIN_SELECCIONAR = "__SIN_SELECCIONAR__"
FILTRO_OPCIONES: list[tuple[str, str | None]] = [
    ("— Seleccioná un evento —",       FILTRO_SIN_SELECCIONAR),
    ("Sífilis",                        "sifilis"),
    ("Chagas",                         "chagas"),
    ("VIH",                            "vih"),
    ("Dengue",                         "dengue"),
    ("Hepatitis A",                    "hepatitis_a"),
    ("Hepatitis B",                    "hepatitis_b"),
    ("Hepatitis C",                    "hepatitis_c"),
    ("Respiratorio (COVID/Influenza/VRS)", "respiratorio"),
    ("Rubéola / Sarampión",            "rubeola"),
    ("Todos los eventos (SIN filtro — requiere confirmación)", None),
]


class SisaInteropApp:
    """Ventana principal de SISA Interop."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SISA Interop — Laboratorio Central de Virología")
        self.root.minsize(780, 640)
        self.root.resizable(True, True)

        # Estado interno
        self._proc: subprocess.Popen | None = None
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._log_path: Path | None = None
        self._procesados: int = 0
        self._process_done: bool = False

        self._build_ui()
        self._poll_queue()

    # ─── Construcción de la UI ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Panel de configuración ──────────────────────────────────────────
        cfg = ttk.LabelFrame(self.root, text=" Configuración ", padding=(12, 8))
        cfg.pack(fill="x", padx=14, pady=(14, 0))
        cfg.columnconfigure(1, weight=1)

        # Archivo
        ttk.Label(cfg, text="Archivo TXT del LIS:").grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        self._archivo_var = tk.StringVar()
        ttk.Entry(cfg, textvariable=self._archivo_var).grid(
            row=0, column=1, sticky="ew", padx=(8, 4), pady=(0, 6))
        ttk.Button(cfg, text="Examinar…", command=self._browse_file).grid(
            row=0, column=2, pady=(0, 6))

        # Filtro de evento
        ttk.Label(cfg, text="Evento a interoperar:").grid(
            row=1, column=0, sticky="w", pady=(0, 6))
        self._filtro_var = tk.StringVar(value=FILTRO_OPCIONES[0][0])
        filtro_cb = ttk.Combobox(
            cfg,
            textvariable=self._filtro_var,
            values=[label for label, _ in FILTRO_OPCIONES],
            state="readonly",
            width=42,
        )
        filtro_cb.grid(row=1, column=1, columnspan=2, sticky="w", padx=(8, 4), pady=(0, 6))

        # Entorno
        ttk.Label(cfg, text="Entorno:").grid(
            row=2, column=0, sticky="w", pady=(0, 4))
        self._entorno_var = tk.StringVar(value="produccion")
        ent_frame = ttk.Frame(cfg)
        ent_frame.grid(row=2, column=1, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Radiobutton(ent_frame, text="Producción",
                        variable=self._entorno_var, value="produccion").pack(side="left")
        ttk.Radiobutton(ent_frame, text="QA",
                        variable=self._entorno_var, value="qa").pack(side="left", padx=(18, 0))

        # Opciones extra
        opts = ttk.Frame(cfg)
        opts.grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 0))
        self._dryrun_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts, text="Dry-run  (previsualizar sin enviar al SISA)",
            variable=self._dryrun_var
        ).pack(side="left")
        ttk.Separator(opts, orient="vertical").pack(side="left", fill="y", padx=14)
        ttk.Label(opts, text="Límite de casos:").pack(side="left")
        self._limite_var = tk.StringVar()
        ttk.Entry(opts, textvariable=self._limite_var, width=6).pack(side="left", padx=(6, 4))
        ttk.Label(opts, text="(vacío = todos)", foreground="gray").pack(side="left")

        # ── Barra de botones ────────────────────────────────────────────────
        btn_row = ttk.Frame(self.root)
        btn_row.pack(fill="x", padx=14, pady=10)

        self._btn_procesar = ttk.Button(
            btn_row, text="▶  Procesar", command=self._start_process)
        self._btn_procesar.pack(side="left")

        self._btn_detener = ttk.Button(
            btn_row, text="⏹  Detener", command=self._stop_process, state="disabled")
        self._btn_detener.pack(side="left", padx=(8, 0))

        self._status_lbl = ttk.Label(btn_row, text="Listo.", foreground="gray")
        self._status_lbl.pack(side="left", padx=(16, 0))

        # ── Log ─────────────────────────────────────────────────────────────
        log_frame = ttk.LabelFrame(self.root, text=" Log ", padding=(8, 6))
        log_frame.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        self._log_text = scrolledtext.ScrolledText(
            log_frame, wrap="word", state="disabled",
            font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white",
            relief="flat",
        )
        self._log_text.pack(fill="both", expand=True)

        for tag, color in TAG_COLORS.items():
            kw: dict = {"foreground": color}
            if tag == "bold":
                kw["font"] = ("Consolas", 9, "bold")
            self._log_text.tag_config(tag, **kw)

        # ── Barra de progreso ────────────────────────────────────────────────
        self._progress = ttk.Progressbar(self.root, mode="indeterminate")
        self._progress.pack(fill="x", padx=14, pady=(0, 2))
        self._progress_lbl = ttk.Label(self.root, text="", foreground="gray", anchor="center")
        self._progress_lbl.pack(pady=(0, 4))

        # ── Panel de resumen y exportación ──────────────────────────────────
        resumen = ttk.LabelFrame(self.root, text=" Resumen ", padding=(12, 8))
        resumen.pack(fill="x", padx=14, pady=(0, 14))

        self._resumen_var = tk.StringVar(value="—")
        ttk.Label(resumen, textvariable=self._resumen_var).pack(
            side="left", expand=True, anchor="w")

        self._btn_ver_log = ttk.Button(
            resumen, text="📄 Ver log JSON", command=self._open_log, state="disabled")
        self._btn_ver_log.pack(side="right", padx=(8, 0))

        self._btn_control = ttk.Button(
            resumen, text="📋 Planilla control", command=self._generar_control, state="disabled")
        self._btn_control.pack(side="right", padx=(8, 0))

        self._btn_export = ttk.Button(
            resumen, text="📊 Exportar CSV", command=self._export_csv, state="disabled")
        self._btn_export.pack(side="right")

    # ─── Selección de archivo ────────────────────────────────────────────────

    def _browse_file(self) -> None:
        initial = str(ROOT / "data") if (ROOT / "data").exists() else str(ROOT)
        path = filedialog.askopenfilename(
            title="Seleccioná el TXT exportado por el LIS",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos", "*.*")],
            initialdir=initial,
        )
        if path:
            self._archivo_var.set(path)

    # ─── Control del proceso ─────────────────────────────────────────────────

    def _start_process(self) -> None:
        archivo = self._archivo_var.get().strip()
        if not archivo:
            messagebox.showwarning("Falta archivo", "Seleccioná el TXT del LIS primero.")
            return
        if not Path(archivo).exists():
            messagebox.showerror("Archivo no encontrado",
                                 f"No se encontró el archivo:\n{archivo}")
            return

        # Filtro de evento — obligatorio. Sin esto, un dropdown que arranca en
        # "sin filtro" (como antes) deja pasar corridas que interoperan TODO
        # el listado sin que nadie lo haya pedido (incidente sep-2026).
        label_sel = self._filtro_var.get()
        filtro_val = next((v for lbl, v in FILTRO_OPCIONES if lbl == label_sel), FILTRO_SIN_SELECCIONAR)

        if filtro_val == FILTRO_SIN_SELECCIONAR:
            messagebox.showwarning(
                "Falta seleccionar evento",
                "Elegí qué evento vas a interoperar antes de procesar.\n\n"
                "Si realmente querés notificar TODOS los eventos sin filtrar, "
                "seleccioná esa opción explícitamente en el desplegable "
                "(vas a tener que confirmarlo aparte)."
            )
            return

        if filtro_val is None:
            # "Todos los eventos" elegido a propósito: confirmación dura,
            # no un simple Sí/No que se puede clickear sin leer.
            confirmacion = simpledialog.askstring(
                "Confirmar: notificar TODOS los eventos",
                "Estás a punto de interoperar TODO el listado del TXT, sin "
                "filtrar por evento (Sífilis, Chagas, VIH, Dengue, etc. — todo "
                "junto).\n\n"
                "Si la intención era notificar un solo evento, cancelá y "
                "elegilo en el desplegable.\n\n"
                "Para continuar sin filtro, escribí CONFIRMAR:",
                parent=self.root,
            )
            if confirmacion is None or confirmacion.strip().upper() != "CONFIRMAR":
                return

        # Armar comando
        cmd = [PYTHON, str(ROOT / "main.py"),
               "--archivo", archivo,
               "--entorno", self._entorno_var.get()]
        if self._dryrun_var.get():
            cmd.append("--dry-run")
        limite = self._limite_var.get().strip()
        if limite.isdigit() and int(limite) > 0:
            cmd += ["--limite", limite]
        if filtro_val:
            cmd += ["--filtro", filtro_val]

        # Resetear estado
        self._clear_log()
        self._resumen_var.set("—")
        self._log_path = None
        self._procesados = 0
        self._process_done = False
        self._btn_procesar.config(state="disabled")
        self._btn_detener.config(state="normal")
        self._btn_export.config(state="disabled")
        self._btn_ver_log.config(state="disabled")
        self._progress.config(mode="indeterminate")
        self._progress.start(12)

        modo = "DRY-RUN" if self._dryrun_var.get() else self._entorno_var.get().upper()
        self._status_lbl.config(text=f"Procesando [{modo}]…")
        self._progress_lbl.config(text="Iniciando…")

        ts = datetime.now().strftime("%H:%M:%S")
        self._log(f"[{ts}] Iniciando procesamiento — {modo}\n", "header")
        self._log(f"Archivo: {archivo}\n", "info")
        self._log(f"Filtro: {label_sel}\n", "info")
        self._log("\n", "info")

        # Lanzar subprocess en hilo background
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(ROOT),
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        except Exception as exc:
            messagebox.showerror("Error al iniciar", str(exc))
            self._on_done()
            return

        threading.Thread(target=self._read_output, daemon=True).start()

    def _stop_process(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._log("\n⚠  Proceso detenido por el usuario.\n", "warn")
        self._on_done()

    def _read_output(self) -> None:
        """Lee stdout del subprocess y encola cada línea (corre en hilo)."""
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            self._queue.put(line)
        self._proc.wait()
        self._queue.put(None)  # sentinel → proceso terminó

    def _poll_queue(self) -> None:
        """Drena la queue y actualiza el Text widget (corre en el hilo principal)."""
        try:
            while True:
                item = self._queue.get_nowait()
                if item is None:
                    if not self._process_done:
                        self._on_done()
                    break
                self._process_line(item)
        except queue.Empty:
            pass
        self.root.after(40, self._poll_queue)

    # ─── Clasificación y coloreo de líneas ───────────────────────────────────

    def _process_line(self, line: str) -> None:
        stripped = line.rstrip()

        if "OK NUEVO" in stripped:
            self._log(line, "nuevo")
            self._inc_progress()
        elif "OK REUSE" in stripped:
            self._log(line, "reuse")
            self._inc_progress()
        elif "SKIP VDRL" in stripped:
            self._log(line, "skip_vdrl")
            self._inc_progress()
        elif stripped.lstrip().startswith("SKIP") and "unicidad" not in stripped:
            self._log(line, "skip")
            self._inc_progress()
        elif stripped.lstrip().startswith("ERR") or "ERROR:" in stripped:
            self._log(line, "err")
            self._inc_progress()
        elif stripped.startswith("AVISO:"):
            self._log(line, "warn")
        elif "RESULTADO FINAL" in stripped or stripped.startswith("=" * 10):
            self._log(line, "bold")
        elif stripped.startswith("  Total") or stripped.startswith("  OK ") \
                or stripped.startswith("  SKIP") or stripped.startswith("  Con error") \
                or stripped.startswith("  Nuevo") or stripped.startswith("  Reuse"):
            self._log(line, "bold")
        elif "Log guardado en:" in stripped:
            self._log(line, "header")
            self._extract_log_path(stripped)
        elif stripped.startswith("[dry-run]"):
            self._log(line, "skip")
        elif stripped.startswith("  ") and stripped.strip().startswith(tuple("0123456789")):
            # líneas de casos en dry-run (numeradas)
            self._log(line, "info")
        else:
            self._log(line, "info")

    def _inc_progress(self) -> None:
        self._procesados += 1
        self._progress_lbl.config(text=f"{self._procesados} casos procesados")

    def _extract_log_path(self, line: str) -> None:
        try:
            raw = line.split("Log guardado en:")[-1].strip()
            p = Path(raw)
            if p.exists():
                self._log_path = p
        except Exception:
            pass

    # ─── Finalización ────────────────────────────────────────────────────────

    def _on_done(self) -> None:
        self._process_done = True
        self._progress.stop()
        self._progress.config(mode="determinate", value=100)
        self._progress_lbl.config(text="")
        self._btn_procesar.config(state="normal")
        self._btn_detener.config(state="disabled")
        self._status_lbl.config(text="Listo.")

        if self._dryrun_var.get():
            self._resumen_var.set("Dry-run completado — no se envió nada al SISA.")
            return

        # Leer resumen del log JSON
        if self._log_path and self._log_path.exists():
            try:
                with open(self._log_path, encoding="utf-8") as fh:
                    data = json.load(fh)
                nuevo      = data.get("nuevo", 0)
                reuse      = data.get("reuse", 0)
                skip       = data.get("skip_unicidad", 0)
                skip_vdrl  = data.get("skip_vdrl", 0)
                errores    = data.get("errores", 0)
                total      = data.get("total", 0)
                partes = [
                    f"✅ {nuevo} nuevos",
                    f"🔄 {reuse} reuse",
                    f"⏭ {skip} skip",
                ]
                if skip_vdrl:
                    partes.append(f"〰 {skip_vdrl} VDRL omitidos")
                partes.append(f"❌ {errores} errores")
                partes.append(f"Total: {total}")
                self._resumen_var.set("   ".join(partes))
                self._btn_export.config(state="normal")
                self._btn_control.config(state="normal")
                self._btn_ver_log.config(state="normal")
            except Exception as exc:
                self._resumen_var.set(f"(no se pudo leer el resumen: {exc})")

    # ─── Log helpers ──────────────────────────────────────────────────────────

    def _log(self, text: str, tag: str = "info") -> None:
        self._log_text.config(state="normal")
        self._log_text.insert("end", text, tag)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _clear_log(self) -> None:
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    # ─── Exportar / abrir log ─────────────────────────────────────────────────

    def _export_csv(self) -> None:
        if not self._log_path or not self._log_path.exists():
            messagebox.showwarning("Sin log", "No hay log disponible para exportar.")
            return

        with open(self._log_path, encoding="utf-8") as fh:
            data = json.load(fh)

        default_name = self._log_path.stem + ".csv"
        save_path = filedialog.asksaveasfilename(
            title="Guardar CSV de resultados",
            defaultextension=".csv",
            initialfile=default_name,
            initialdir=str(LOGS_DIR),
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if not save_path:
            return

        campos = ["orden", "sucursal", "dni", "estudio", "resultado",
                  "poblacion", "modo", "ok", "id_caso", "id_muestra", "error"]

        with open(save_path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
            writer.writeheader()
            for c in data.get("casos", []):
                id_caso    = (c.get("ws400") or {}).get("id_caso", "")
                id_muestra = (c.get("api75") or {}).get("id_muestra", "")
                writer.writerow({
                    "orden":      c.get("orden", ""),
                    "sucursal":   c.get("sucursal", ""),
                    "dni":        c.get("dni", ""),
                    "estudio":    c.get("estudio", ""),
                    "resultado":  c.get("resultado", ""),
                    "poblacion":  c.get("poblacion", ""),
                    "modo":       c.get("modo", ""),
                    "ok":         c.get("ok", ""),
                    "id_caso":    id_caso,
                    "id_muestra": id_muestra,
                    "error":      c.get("error") or "",
                })

        messagebox.showinfo("CSV exportado", f"Guardado en:\n{save_path}")

    def _generar_control(self) -> None:
        if not self._log_path or not self._log_path.exists():
            messagebox.showwarning("Sin log", "No hay log disponible.")
            return

        self._status_lbl.config(text="Generando planilla de control…")
        self._btn_control.config(state="disabled")
        result_holder: list = [None]

        def _run() -> None:
            try:
                proc = subprocess.run(
                    [PYTHON, str(ROOT / "scripts" / "generar_control.py"),
                     str(self._log_path)],
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    cwd=str(ROOT),
                )
                out_path = None
                for line in proc.stdout.splitlines():
                    if "Excel guardado en:" in line:
                        out_path = line.split("Excel guardado en:")[-1].strip()
                if proc.returncode == 0 and out_path:
                    result_holder[0] = ("ok", out_path)
                else:
                    result_holder[0] = ("error", proc.stderr or proc.stdout or "Error desconocido")
            except Exception as exc:
                result_holder[0] = ("error", str(exc))

        def _check() -> None:
            if result_holder[0] is None:
                self.root.after(200, _check)
                return
            self._status_lbl.config(text="Listo.")
            self._btn_control.config(state="normal")
            status, val = result_holder[0]
            if status == "ok":
                self._log(f"\n📋 Planilla de control generada: {val}\n", "nuevo")
                try:
                    os.startfile(val)
                except Exception:
                    pass
                messagebox.showinfo("Planilla generada",
                                    f"Excel guardado en:\n{val}\n\nSe abrirá automáticamente.")
            else:
                messagebox.showerror("Error al generar planilla", val[:500])

        threading.Thread(target=_run, daemon=True).start()
        self.root.after(200, _check)

    def _open_log(self) -> None:
        if not self._log_path or not self._log_path.exists():
            messagebox.showwarning("Sin log", "No hay log disponible.")
            return
        try:
            os.startfile(str(self._log_path))
        except Exception as exc:
            messagebox.showerror("Error", str(exc))


# ─── Entrada ──────────────────────────────────────────────────────────────────

def main() -> None:
    # En Windows, mejorar nitidez en pantallas de alta resolución
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()

    # Intentar tema moderno; si no está disponible, usar clam
    style = ttk.Style(root)
    try:
        style.theme_use("vista")
    except tk.TclError:
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    app = SisaInteropApp(root)  # noqa: F841
    root.mainloop()


if __name__ == "__main__":
    main()

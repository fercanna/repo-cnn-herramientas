#!/usr/bin/env python3
"""
main.py -- Orquestador SISA Interop.
WS400 -> API75 -> API76 (+-API81 para sifilis temprana).
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS_DIR = ROOT / "logs"
CREDS_PATH = ROOT / "config" / "credentials.json"
SETTINGS_PATH = ROOT / "config" / "settings.json"
CACHE_MUESTRAS_PATH = ROOT / "data" / "muestras_cache.json"

ENDPOINTS = {
    "produccion": {
        "WS400": "https://apisalud.msal.gob.ar/snvsCasoNominal/v2/snvsCasoNominal",
        "API75": "https://apisalud.msal.gob.ar/snvsLaboratoriosMuestra/v1/eventoMuestras",
        "API76": "https://apisalud.msal.gob.ar/snvsLaboratorios/v1/pruebaMuestras",
        "API81": "https://apisalud.msal.gob.ar/snvsClasificacionManual/v1/eventoCaso",
    },
    "qa": {
        "WS400": "https://ws400-qa.sisa.msal.gov.ar/snvsCasoNominal/v2/snvsCasoNominal",
        "API75": "https://apisalud-qa.msal.gob.ar/snvsLaboratoriosMuestra/v1/eventoMuestras",
        "API76": "https://apisalud-qa.msal.gob.ar/snvsLaboratorios/v1/pruebaMuestras",
        "API81": "https://api81-qa.sisa.msal.gov.ar/snvsClasificacionManual/v1/eventoCaso",
    },
}

CREDS_FALLBACK = {
    "WS400": {"APP_ID": "049fedb8", "APP_KEY": "a48ee247b7f45c54d56576d18825e5ac"},
    "API75": {"APP_ID": "58d0467b", "APP_KEY": "0052e382de8ac55469a5b17d78d68d39"},
    "API76": {"APP_ID": "a7bb9a90", "APP_KEY": "e82a937f5be5050ed05f48d26acda636"},
    "API81": {"APP_ID": "", "APP_KEY": ""},
}

SETTINGS_FALLBACK = {
    "entorno": "produccion",
    "refes_laboratorio": "51140142133784",
    "id_interno_sisa": "108202",
    "domicilio_default": {"idProvincia": 6, "idDepartamento": 194, "idLocalidad": 14021230, "idPais": 200},
}

GRUPOS_EVENTO: dict[str, set[int]] = {
    "chagas": {188, 108}, "sifilis": {193, 115}, "vih": {105, 117},
    "dengue": {109, 100}, "hepatitis_a": {1}, "hepatitis_b": {2, 286},
    "hepatitis_c": {3}, "respiratorio": {330}, "rubeola": {164}, "sarampion": {164},
}

# VDRLs son secundarias: REUSE sobre treponémica ya cargada.
ESTUDIOS_SECUNDARIOS: set[int] = {72}

# Titulo VDRL >= 16 DIL -> clasificacion 742 ("Sifilis temprana").
VDRL_UMBRAL_742 = 16


def _dilution_value(valor: str) -> int:
    import re
    m = re.search(r"REACTIVO\s+(\d+)\s+DIL", valor.upper())
    return int(m.group(1)) if m else 0


def _entorno_norm(s: str) -> str:
    return "produccion" if s.lower() in ("prod", "produccion") else "qa"


def _cargar_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return SETTINGS_FALLBACK
    with open(SETTINGS_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    data["entorno"] = _entorno_norm(data.get("entorno", "produccion"))
    return data


def _cargar_credenciales() -> dict:
    if not CREDS_PATH.exists():
        return CREDS_FALLBACK
    with open(CREDS_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("produccion", data)


def _domicilio_limpio(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _cache_key(dni: str, id_evento: int) -> str:
    return f"{dni}|{id_evento}"


def _cargar_cache_muestras() -> dict:
    if not CACHE_MUESTRAS_PATH.exists():
        return {}
    with open(CACHE_MUESTRAS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _guardar_cache_muestras(cache: dict) -> None:
    CACHE_MUESTRAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_MUESTRAS_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _llamar_api81(caso, id_caso: int, creds: dict, urls: dict, log_caso: dict) -> None:
    import scripts.api81 as api81
    if caso.estudio_codigo != 72 or caso.id_evento != 193:
        return
    dil = _dilution_value(caso.valor_resultado)
    if dil < VDRL_UMBRAL_742:
        return
    creds_81 = creds.get("API81", {})
    app_id = creds_81.get("app_id") or creds_81.get("APP_ID", "")
    if not app_id:
        print(f"    WARN API81: VDRL {dil} DIL sin credenciales -- clasificacion no actualizada")
        log_caso["api81"] = {"skipped": "sin_credenciales", "id_caso": id_caso}
        return
    try:
        res_81 = api81.cambiar_clasificacion(id_caso, 742, creds_81, urls["API81"])
        log_caso["api81"] = res_81
        print(f"    API81 OK -> caso={id_caso} clasificacion -> 742")
    except Exception as exc:
        print(f"    WARN API81: {exc}")
        log_caso["api81"] = {"error": str(exc), "id_caso": id_caso}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archivo", required=True)
    parser.add_argument("--entorno", default=None, choices=["prod", "produccion", "qa"])
    parser.add_argument("--limite", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--filtro", default=None, metavar="EVENTO",
                        help=f"Opciones: {', '.join(sorted(GRUPOS_EVENTO))}")
    parser.add_argument("--todos-los-eventos", action="store_true",
                        help="Notificar TODOS los eventos sin filtrar (requerido "
                             "explícitamente en vez de --filtro; ver incidente sep-2026: "
                             "una corrida sin --filtro interoperó todo el listado de la "
                             "semana en vez de solo sífilis).")
    args = parser.parse_args()

    if not args.filtro and not args.todos_los_eventos:
        print("ERROR: falta --filtro EVENTO. No se procesa sin especificar qué evento "
              "notificar (evita repetir el incidente de sep-2026, donde una corrida sin "
              "filtro interoperó TODO el listado en vez de solo sífilis).")
        print(f"Opciones de --filtro: {', '.join(sorted(GRUPOS_EVENTO))}")
        print("Si de verdad querés notificar todos los eventos sin filtrar, "
              "pasá --todos-los-eventos explícitamente.")
        return 1

    from scripts.parser_lis import parsear, imprimir_resumen
    from scripts.sisa_http import SisaError
    import scripts.ws400 as ws400
    import scripts.api75 as api75
    import scripts.api76 as api76

    settings = _cargar_settings()
    creds = _cargar_credenciales()
    entorno = _entorno_norm(args.entorno) if args.entorno else settings["entorno"]
    urls = ENDPOINTS[entorno]
    cod_sisa = settings["id_interno_sisa"]

    archivo = Path(args.archivo)
    if not archivo.exists():
        print(f"ERROR: no se encuentra el archivo '{archivo}'.")
        return 1

    casos, resumen = parsear(archivo)
    imprimir_resumen(resumen, archivo)

    if args.filtro:
        filtro = args.filtro.strip().lower()
        if filtro not in GRUPOS_EVENTO:
            print(f"ERROR: --filtro '{args.filtro}' no reconocido. Opciones: {', '.join(sorted(GRUPOS_EVENTO))}")
            return 1
        ids_evento = GRUPOS_EVENTO[filtro]
        antes = len(casos)
        casos = [c for c in casos if c.id_evento in ids_evento]
        print(f"Filtro '{filtro}': {antes} -> {len(casos)} casos del evento seleccionado.\n")

    if not casos:
        print("Sin casos notificables. Fin.")
        return 0

    if args.limite:
        casos = casos[:args.limite]
        print(f"AVISO: procesando solo los primeros {len(casos)} casos (--limite).\n")

    casos_prim = [c for c in casos if c.estudio_codigo not in ESTUDIOS_SECUNDARIOS]
    casos_sec  = [c for c in casos if c.estudio_codigo in ESTUDIOS_SECUNDARIOS]
    casos = casos_prim + casos_sec

    # Pre-scan: override clasificacion treponémica a 742 cuando VDRL >=16 en mismo dataset.
    vdrl_max_dil: dict[tuple[str, int], int] = {}
    for c in casos_sec:
        k = (c.numero_documento, c.id_evento)
        vdrl_max_dil[k] = max(vdrl_max_dil.get(k, 0), _dilution_value(c.valor_resultado))
    for c in casos_prim:
        if c.id_evento == 193:
            if vdrl_max_dil.get((c.numero_documento, c.id_evento), 0) >= VDRL_UMBRAL_742:
                c.id_clasificacion_manual_caso = 742

    if args.dry_run:
        prim_keys = {(p.numero_documento, p.id_evento) for p in casos_prim}
        muestras_cache_dr = _cargar_cache_muestras()
        print("[dry-run] Casos que se notificarian:\n")
        for i, caso in enumerate(casos, 1):
            es_sec = caso.estudio_codigo in ESTUDIOS_SECUNDARIOS
            tiene_trep = ((caso.numero_documento, caso.id_evento) in prim_keys
                          or _cache_key(caso.numero_documento, caso.id_evento) in muestras_cache_dr)
            clasif = f" clasif={caso.id_clasificacion_manual_caso}" if not es_sec else ""
            dil = _dilution_value(caso.valor_resultado) if es_sec else 0
            api81_hint = " +API81->742" if (es_sec and dil >= VDRL_UMBRAL_742 and caso.id_evento == 193) else ""
            if es_sec:
                modo = f" [REUSE-VDRL{api81_hint}]" if tiene_trep else " [SKIP-VDRL]"
            else:
                modo = ""
            print(f"  {i:3d}. orden={caso.orden} DNI={caso.numero_documento} "
                  f"cod={caso.estudio_codigo} {caso.estudio_nombre} "
                  f"res={caso.valor_resultado} pob={caso.poblacion}{clasif}{modo}")
        n_skip_dr = sum(1 for c in casos_sec
                        if (c.numero_documento, c.id_evento) not in prim_keys
                        and _cache_key(c.numero_documento, c.id_evento) not in muestras_cache_dr)
        print(f"\n[dry-run] Total: {len(casos)} casos")
        print(f"  {len(casos_prim)} primarios (treponémica)")
        print(f"  {len(casos_sec)-n_skip_dr} VDRLs con treponémica -> REUSE")
        print(f"  {n_skip_dr} VDRLs sin treponémica -> SKIP_VDRL")
        print("[dry-run] No se envio nada al SISA.")
        return 0

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    hoy = datetime.now()
    total = len(casos)
    n_nuevo = n_reuse = n_skip = n_skip_vdrl = n_err = 0
    logs_casos = []
    casos_de_esta_corrida: dict[tuple[str, int], dict] = {}
    muestras_cache = _cargar_cache_muestras()
    cache_modificado = False

    print(f"Notificando {total} casos al SISA ({entorno})...\n")

    for i, caso in enumerate(casos, 1):
        prefijo = f"[{i}/{total}] orden={caso.orden} DNI={caso.numero_documento} {caso.estudio_nombre}"
        log_caso: dict = {
            "orden": caso.orden, "sucursal": caso.sucursal_descripcion,
            "dni": caso.numero_documento, "estudio": f"{caso.estudio_codigo} {caso.estudio_nombre}",
            "resultado": caso.valor_resultado, "poblacion": caso.poblacion,
            "modo": None, "ws400": None, "api75": None, "api76": None, "api81": None,
            "ok": False, "error": None,
        }
        key = (caso.numero_documento, caso.id_evento)

        try:
            # -- REUSE: VDRL sobre treponémica cargada en esta corrida --
            if key in casos_de_esta_corrida and caso.estudio_codigo in ESTUDIOS_SECUNDARIOS:
                info = casos_de_esta_corrida[key]
                id_caso_reuse = info["id_caso"]
                log_caso["ws400"] = {"skipped": "REUSE", "id_caso": id_caso_reuse}
                log_caso["modo"] = "REUSE"
                id_muestra = info["id_muestra"]
                if id_muestra is None:
                    ck = _cache_key(caso.numero_documento, caso.id_evento)
                    cached = muestras_cache.get(ck)
                    if cached:
                        id_muestra = cached["id_muestra"]
                        info["id_muestra"] = id_muestra
                        log_caso["api75"] = {"skipped": "REUSE-CACHE", "id_muestra": id_muestra}
                    else:
                        log_caso["modo"] = "SKIP_VDRL"
                        log_caso["ok"] = True
                        n_skip_vdrl += 1
                        print(f"  SKIP VDRL {prefijo} -> treponémica sin muestra en cache")
                        logs_casos.append(log_caso)
                        continue
                else:
                    log_caso["api75"] = {"skipped": "REUSE", "id_muestra": id_muestra}
                log_caso["api76"] = api76.informar_resultado(caso, id_muestra, cod_sisa, creds["API76"], urls["API76"])
                _llamar_api81(caso, id_caso_reuse, creds, urls, log_caso)
                log_caso["ok"] = True
                n_reuse += 1
                print(f"  OK REUSE  {prefijo} -> caso={id_caso_reuse} muestra={id_muestra}")
                logs_casos.append(log_caso)
                continue

            # -- SKIP_VDRL: VDRL sin treponémica en esta corrida --
            if caso.estudio_codigo in ESTUDIOS_SECUNDARIOS:
                ck = _cache_key(caso.numero_documento, caso.id_evento)
                cached = muestras_cache.get(ck)
                if cached:
                    log_caso["ws400"] = {"skipped": "REUSE-CACHE", "id_caso": cached["id_caso"]}
                    log_caso["api75"] = {"skipped": "REUSE-CACHE", "id_muestra": cached["id_muestra"]}
                    log_caso["modo"] = "REUSE"
                    log_caso["api76"] = api76.informar_resultado(caso, cached["id_muestra"], cod_sisa, creds["API76"], urls["API76"])
                    _llamar_api81(caso, cached["id_caso"], creds, urls, log_caso)
                    log_caso["ok"] = True
                    n_reuse += 1
                    print(f"  OK REUSE  {prefijo} -> caso={cached['id_caso']} muestra={cached['id_muestra']} (cross-run)")
                    logs_casos.append(log_caso)
                    continue
                log_caso["modo"] = "SKIP_VDRL"
                log_caso["ok"] = True
                n_skip_vdrl += 1
                print(f"  SKIP VDRL {prefijo} -> sin treponémica previa")
                logs_casos.append(log_caso)
                continue

            # -- WS400 --
            print(f"    [WS400] refes={caso.refes_carga} | [API75] toma={caso.sisa_corto_toma}")
            res_ws = ws400.crear_caso(caso, caso.refes_carga, creds["WS400"], urls["WS400"])
            log_caso["ws400"] = res_ws
            id_caso = res_ws["id_caso"]

            if not res_ws["caso_nuevo"]:
                log_caso["modo"] = "SKIP"
                log_caso["ok"] = True
                n_skip += 1
                casos_de_esta_corrida[key] = {"id_caso": id_caso, "id_muestra": None}
                print(f"  SKIP      {prefijo} -> caso={id_caso} ya notificado")
                logs_casos.append(log_caso)
                continue

            # -- NUEVO --
            res_75 = api75.registrar_muestra(caso, id_caso, caso.sisa_corto_toma, creds["API75"], urls["API75"])
            log_caso["api75"] = res_75
            id_muestra = res_75["id_muestra"]

            # Registrar ANTES de API76: si API76 falla, VDRLs encuentran la muestra igualmente.
            casos_de_esta_corrida[key] = {"id_caso": id_caso, "id_muestra": id_muestra}
            ck = _cache_key(caso.numero_documento, caso.id_evento)
            muestras_cache[ck] = {"id_caso": id_caso, "id_muestra": id_muestra}
            cache_modificado = True

            log_caso["api76"] = api76.informar_resultado(caso, id_muestra, cod_sisa, creds["API76"], urls["API76"])
            log_caso["modo"] = "NUEVO"
            log_caso["ok"] = True
            n_nuevo += 1
            print(f"  OK NUEVO  {prefijo} -> caso={id_caso} muestra={id_muestra}")

        except SisaError as exc:
            for campo in ("ws400", "api75", "api76"):
                if log_caso[campo] is None:
                    log_caso[campo] = {"error": str(exc), "status_code": exc.status, "response": exc.body}
                    break
            log_caso["error"] = str(exc)
            n_err += 1
            print(f"  ERR       {prefijo} -> {exc}")

        logs_casos.append(log_caso)

    if cache_modificado:
        _guardar_cache_muestras(muestras_cache)

    print(f"\n{'='*70}")
    print(f"  RESULTADO FINAL  ({entorno})")
    print(f"{'='*70}")
    print(f"  Total procesados : {total}")
    print(f"  OK NUEVO         : {n_nuevo}")
    print(f"  OK REUSE         : {n_reuse}")
    print(f"  SKIP unicidad    : {n_skip}")
    print(f"  SKIP VDRL        : {n_skip_vdrl}")
    print(f"  Con error        : {n_err}")

    log_path = LOGS_DIR / f"main_{hoy.strftime('%Y%m%d_%H%M%S')}.json"
    log_doc = {
        "timestamp": hoy.isoformat(timespec="seconds"), "archivo": str(archivo),
        "entorno": entorno, "total": total, "nuevo": n_nuevo, "reuse": n_reuse,
        "skip_unicidad": n_skip, "skip_vdrl": n_skip_vdrl, "errores": n_err, "casos": logs_casos,
    }
    log_path.write_text(json.dumps(log_doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Log guardado en: {log_path}")
    print(f"{'='*70}\n")

    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

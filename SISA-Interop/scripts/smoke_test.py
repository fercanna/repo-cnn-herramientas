#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke test - SISA Interop
=========================
Notifica un caso REAL de Sifilis No Gestante REACTIVO tomado del export
del LIS (prueba_16_270426.txt) contra PRODUCCION del SISA.

Uso:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --yes        # sin pedir confirmacion
    python scripts/smoke_test.py --dry-run    # arma payloads y NO envia

Salida:
    logs/smoke_test_YYYYMMDD_HHMMSS.json  (request + response de cada paso)

Referencia:
    README.md y CONTEXTO_CLAUDE_CODE.md (seccion 10).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: falta el modulo 'requests'.")
    print("    Instalalo con:  pip install requests")
    sys.exit(1)


# ----------------------------------------------------------------------
# Paths y configuracion
# ----------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
CREDS_PATH = ROOT / "config" / "credentials.json"

ENDPOINTS = {
    "WS400": "https://apisalud.msal.gob.ar/snvsCasoNominal/v2/snvsCasoNominal",
    "API75": "https://apisalud.msal.gob.ar/snvsLaboratoriosMuestra/v1/eventoMuestras",
    "API76": "https://apisalud.msal.gob.ar/snvsLaboratorios/v1/pruebaMuestras",
}

# Credenciales de respaldo (publicadas en CONTEXTO_CLAUDE_CODE.md).
# Si existe config/credentials.json, se prefiere ese archivo.
CREDS_FALLBACK = {
    "WS400": {"app_id": "049fedb8", "app_key": "a48ee247b7f45c54d56576d18825e5ac"},
    "API75": {"app_id": "58d0467b", "app_key": "0052e382de8ac55469a5b17d78d68d39"},
    "API76": {"app_id": "a7bb9a90", "app_key": "e82a937f5be5050ed05f48d26acda636"},
}

# Codigos del Laboratorio Central de Virologia Cordoba.
# El catalogo SISA tiene DOS codigos por establecimiento:
#  - codigo_refes (largo, 14 digitos): RENAES / Registro Federal de Estab. de Salud
#  - codigo_sisa  (corto, interno):    ID interno de SISA, usado por algunos servicios
# WS400 usa el REFES largo en idEstablecimientoCarga (validado, funciona).
# API75 y API76 usan el codigo SISA corto en idEstablecimientoToma / idEstablecimiento.
REFES_LC = "51140142133784"     # WS400.idEstablecimientoCarga
COD_SISA_LC = "108202"          # API75.idEstablecimientoToma, API76.idEstablecimiento

# Caso de prueba: Sifilis No Gestante - REACTIVO
# Datos REALES tomados de prueba_16_270426.txt (fila SUCURSAL=UNQUILLO,
# ORDEN=79541, ESTUDIO=7101 SIFILISR2, RESULTADO=REACTIVO, TIPO=NORMAL).
# El APENOM ya viene anonimizado a nivel LIS (formato inicial + 4 letras +
# DDMMYYYY), por lo que se usa como apellido tal cual lo emite el LIS.
# Codigos clinicos del CONTEXTO_CLAUDE_CODE.md seccion 10.
CASO_PRUEBA = {
    # ---- Datos personales del usuario (Fer) - case se borra despues ----
    "apellido": "M FECA22101972",      # APENOM-style anonimizado
    "nombre": "ND",                     # placeholder >=2 chars (RENAPER resuelve por DNI)
    "tipoDocumento": 1,                 # 1 = DNI
    "numeroDocumento": "22011967",      # DNI real del usuario
    "sexo": "M",
    "fechaNacimiento": "22-10-1972",    # DD-MM-YYYY
    "fechaPapel": "20-04-2026",         # DD-MM-YYYY
    "fechaToma": "2026-04-20",          # YYYY-MM-DD
    "fechaResultado": "2026-04-22",     # YYYY-MM-DD
    # ---- Domicilio: RIO CEBALLOS (codigos propios de SISA, no INDEC) ----
    # idProvincia: nomenclador SISA (6 = Cordoba), NO INDEC (que seria 14)
    # idDepartamento: nomenclador SISA (194 = Colon), NO INDEC (seria 14021)
    # idLocalidad: INDEC (14021230 = Rio Ceballos)
    "idProvincia": 6,
    "idDepartamento": 194,
    "idLocalidad": 14021230,
    "idPais": 200,
    # Codigos clinicos: Sifilis No Gestante REACTIVO
    "idGrupoEvento": 109,
    "idEvento": 193,
    "idClasificacionManualCaso": 743,
    "idMuestra": 1,
    "idTipoMuestra": 3,
    "idTipoPrueba": 634,
    "idPrueba": 876,
    "idResultado": 109,
    "valorResultado": "REACTIVO",
}

TIMEOUT_S = 30

# Reintentos para errores transitorios (502/503/504 + errores de red).
# Segun CONTEXTO_CLAUDE_CODE.md sec. 9: "502 Bad Gateway -> reintentar con
# backoff exponencial (3 intentos)".
MAX_INTENTOS = 3
STATUS_REINTENTABLES = {502, 503, 504}
BACKOFF_BASE_S = 2  # 2s antes del 2do intento, 4s antes del 3ro


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def load_credentials() -> dict:
    if CREDS_PATH.exists():
        with open(CREDS_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        if "produccion" in data:
            return data["produccion"]
        return data
    return CREDS_FALLBACK


def confirm(skip: bool) -> bool:
    if skip:
        return True
    print()
    print("=" * 70)
    print("  ATENCION: este smoke test corre contra PRODUCCION del SISA.")
    print("  Notifica un caso de prueba con datos del usuario (a borrar luego):")
    print(f"    APENOM            : {CASO_PRUEBA['apellido']}")
    print(f"    DNI               : {CASO_PRUEBA['numeroDocumento']}")
    print(f"    Sexo / FECNAC     : {CASO_PRUEBA['sexo']} / {CASO_PRUEBA['fechaNacimiento']}")
    print(f"    Patologia         : Sifilis No Gestante (REACTIVO) - estudio 7101")
    print(f"    Fecha papel/toma  : {CASO_PRUEBA['fechaPapel']} / {CASO_PRUEBA['fechaToma']}")
    print(f"    Fecha resultado   : {CASO_PRUEBA['fechaResultado']}")
    print(f"    Domicilio         : RIO CEBALLOS (prov={CASO_PRUEBA['idProvincia']}, "
          f"depto={CASO_PRUEBA['idDepartamento']}, loc={CASO_PRUEBA['idLocalidad']})")
    print(f"    Establecimiento   : LC Virologia Cordoba (REFES {REFES_LC})")
    print("=" * 70)
    resp = input("Continuar? [s/N]: ").strip().lower()
    return resp in ("s", "si", "y", "yes")


def headers_for(creds_servicio: dict) -> dict:
    return {
        "app_id": creds_servicio["app_id"],
        "app_key": creds_servicio["app_key"],
        "Content-Type": "application/json",
    }


def imprimir_json(label: str, data) -> None:
    print(f"  {label}:")
    try:
        print("  " + json.dumps(data, indent=2, ensure_ascii=False).replace("\n", "\n  "))
    except (TypeError, ValueError):
        print(f"  {data}")


def post(nombre: str, url: str, headers: dict, payload: dict):
    print()
    print("-" * 70)
    print(f"{nombre}")
    print(f"POST {url}")
    print("-" * 70)
    imprimir_json("REQUEST", payload)

    ultimo_status = None
    ultimo_body = {"error": "sin intento"}

    for intento in range(1, MAX_INTENTOS + 1):
        if intento > 1:
            espera = BACKOFF_BASE_S * (2 ** (intento - 2))
            print(f"  Reintento {intento}/{MAX_INTENTOS} en {espera}s...")
            time.sleep(espera)

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_S)
        except (requests.ConnectionError, requests.Timeout) as exc:
            print(f"  AVISO: error de red ({type(exc).__name__}): {exc}")
            ultimo_status, ultimo_body = None, {"error_red": str(exc)}
            if intento < MAX_INTENTOS:
                continue
            print(f"  ERROR: se agotaron los {MAX_INTENTOS} intentos por errores de red.")
            return ultimo_status, ultimo_body
        except Exception as exc:
            print(f"  ERROR: excepcion no recuperable: {exc}")
            return None, {"error": str(exc)}

        print(f"  STATUS: {resp.status_code}")
        try:
            body = resp.json()
        except ValueError:
            body = {"raw_text": resp.text}
        imprimir_json("RESPONSE", body)

        ultimo_status, ultimo_body = resp.status_code, body

        if resp.status_code in STATUS_REINTENTABLES:
            print(f"  AVISO: status {resp.status_code} marcado como transitorio.")
            if intento < MAX_INTENTOS:
                continue
            print(f"  ERROR: se agotaron los {MAX_INTENTOS} intentos. SISA sigue devolviendo {resp.status_code}.")

        return ultimo_status, ultimo_body

    return ultimo_status, ultimo_body


def parse_id_caso_de_error(body) -> int | None:
    """
    Si el SISA contesta 'caso ya notificado', el ID_SNVS_EVENTO_CASO viene
    embebido en la descripcion. Lo extraemos para reutilizarlo como id_caso.
    """
    if not isinstance(body, dict):
        return None
    blob = " ".join([
        str(body.get("description") or ""),
        str(body.get("message") or ""),
        json.dumps(body.get("errors") or {}, ensure_ascii=False),
    ])
    m = re.search(r"ID_SNVS_EVENTO_CASO\D+(\d+)", blob)
    return int(m.group(1)) if m else None


# ----------------------------------------------------------------------
# Constructores de payload
# ----------------------------------------------------------------------
def build_payload_ws400(caso: dict, fecha_papel: str) -> dict:
    return {
        "ciudadano": {
            "apellido": caso["apellido"],
            "nombre": caso["nombre"],
            "tipoDocumento": caso["tipoDocumento"],
            "numeroDocumento": caso["numeroDocumento"],
            "sexo": caso["sexo"],
            "fechaNacimiento": caso["fechaNacimiento"],
            "paisEmisionTipoDocumento": None,
            "seDeclaraPuebloIndigena": "No",
            "domicilio": {
                "calle": "SIN DATO",
                "idDepartamento": caso["idDepartamento"],
                "idLocalidad": caso["idLocalidad"],
                "idProvincia": caso["idProvincia"],
                "idPais": caso["idPais"],
            },
            "telefono": None,
            "mail": None,
            "personaACargo": {
                "tipoDocumento": None,
                "numeroDocumento": None,
                "vinculo": None,
            },
        },
        "eventoCasoNominal": {
            "idGrupoEvento": caso["idGrupoEvento"],
            "idEvento": caso["idEvento"],
            "idClasificacionManualCaso": caso["idClasificacionManualCaso"],
            "fechaPapel": fecha_papel,
            "idEstablecimientoCarga": REFES_LC,
        },
    }


def build_payload_api75(caso: dict, id_caso: int, fecha_iso: str) -> dict:
    return {
        "adecuada": True,
        "aislamiento": False,
        "fechaToma": fecha_iso,
        "idEstablecimientoToma": COD_SISA_LC,
        "idEventoCaso": id_caso,
        "idMuestra": caso["idMuestra"],
        "idtipoMuestra": caso["idTipoMuestra"],
        "muestra": True,
    }


def build_payload_api76(caso: dict, id_muestra: int, fecha_iso: str) -> dict:
    return {
        "derivada": True,
        "fechaEmisionResultado": fecha_iso,
        "fechaRecepcion": fecha_iso,
        "idDerivacion": None,
        "idEstablecimiento": COD_SISA_LC,
        "idEvento": caso["idEvento"],
        "idEventoMuestra": id_muestra,
        "idPrueba": caso["idPrueba"],
        "idResultado": caso["idResultado"],
        "idTipoPrueba": caso["idTipoPrueba"],
        "noApta": False,
        "valor": caso["valorResultado"],
    }


# ----------------------------------------------------------------------
# Flujo principal
# ----------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test SISA - Sifilis No Gestante (PRODUCCION)"
    )
    parser.add_argument("--yes", "-y", action="store_true",
                        help="No pedir confirmacion antes de mandar")
    parser.add_argument("--dry-run", action="store_true",
                        help="Construye los payloads pero NO los envia")
    parser.add_argument("--id-muestra", type=int, default=None,
                        help="Si se provee, salta API75 y usa este id_muestra "
                             "para API76 (util cuando API75 ya devolvio "
                             "'El registro a crear ya existe').")
    args = parser.parse_args()

    if not confirm(args.yes or args.dry_run):
        print("Abortado por el usuario.")
        return 0

    creds = load_credentials()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    hoy = datetime.now()
    # Las fechas vienen del CASO_PRUEBA (datos reales del LIS)
    fecha_papel = CASO_PRUEBA["fechaPapel"]
    fecha_toma = CASO_PRUEBA["fechaToma"]
    fecha_resultado = CASO_PRUEBA["fechaResultado"]

    resumen = {
        "timestamp": hoy.isoformat(timespec="seconds"),
        "ambiente": "produccion",
        "dry_run": bool(args.dry_run),
        "caso": CASO_PRUEBA,
        "endpoints": ENDPOINTS,
        "pasos": {},
    }

    # ---- 1) WS400 -----------------------------------------------------
    payload_ws400 = build_payload_ws400(CASO_PRUEBA, fecha_papel)

    if args.dry_run:
        print("\n[dry-run] Payload WS400:")
        imprimir_json("WS400", payload_ws400)
        status_ws, body_ws = None, {"dry_run": True}
    else:
        status_ws, body_ws = post(
            "1) WS400 - Crear caso nominal",
            ENDPOINTS["WS400"], headers_for(creds["WS400"]), payload_ws400,
        )

    resumen["pasos"]["ws400"] = {
        "status_code": status_ws,
        "request": payload_ws400,
        "response": body_ws,
    }

    if args.dry_run:
        payload_api75 = build_payload_api75(CASO_PRUEBA, 0, fecha_toma)
        payload_api76 = build_payload_api76(CASO_PRUEBA, 0, fecha_resultado)
        print("\n[dry-run] Payload API75 (id_caso=0 placeholder):")
        imprimir_json("API75", payload_api75)
        print("\n[dry-run] Payload API76 (id_muestra=0 placeholder):")
        imprimir_json("API76", payload_api76)
        resumen["pasos"]["api75"] = {"status_code": None, "request": payload_api75, "response": {"dry_run": True}}
        resumen["pasos"]["api76"] = {"status_code": None, "request": payload_api76, "response": {"dry_run": True}}
        return _guardar_log(resumen, hoy, codigo_salida=0)

    # Resolver id_caso (sea nuevo o reutilizado)
    id_caso = None
    if isinstance(body_ws, dict):
        if body_ws.get("status") == "OK":
            id_caso = body_ws.get("id_caso")
        else:
            id_caso = parse_id_caso_de_error(body_ws)
            if id_caso:
                print(f"  Caso ya notificado en SNVS, reutilizo id_caso={id_caso}")

    if not id_caso:
        print("\nERROR: WS400 no devolvio id_caso. Se aborta el flujo.")
        return _guardar_log(resumen, hoy, codigo_salida=2)

    print(f"  OK id_caso = {id_caso}")

    # ---- 2) API75 -----------------------------------------------------
    if args.id_muestra:
        # Saltamos API75: el usuario ya conoce el id_muestra de una corrida
        # anterior (API75 detecta duplicados pero no devuelve el id existente).
        id_muestra = args.id_muestra
        print()
        print("-" * 70)
        print(f"2) API75 - SALTADA (usando --id-muestra={id_muestra})")
        print("-" * 70)
        resumen["pasos"]["api75"] = {
            "status_code": None,
            "request": None,
            "response": {"saltado": True, "id_muestra_provisto": id_muestra},
        }
    else:
        payload_api75 = build_payload_api75(CASO_PRUEBA, id_caso, fecha_toma)
        status_75, body_75 = post(
            "2) API75 - Registrar muestra",
            ENDPOINTS["API75"], headers_for(creds["API75"]), payload_api75,
        )
        resumen["pasos"]["api75"] = {
            "status_code": status_75,
            "request": payload_api75,
            "response": body_75,
        }

        id_muestra = None
        if isinstance(body_75, dict):
            # API75 devuelve el ID nuevo del evento-muestra en el campo "id".
            # NO confundir con "idMuestra" (que es el TIPO de muestra que enviamos)
            # ni con "idEventoCaso" (que es el id del caso WS400).
            id_muestra = (
                body_75.get("id")              # respuesta real de API75
                or body_75.get("idEventoMuestra")  # nombre canonico esperado por API76
                or body_75.get("id_muestra")   # alternativa documentada
            )

        if not id_muestra:
            # Caso especial: API75 detecto duplicado ("El registro a crear ya existe")
            # pero no devuelve el id. Sugerimos al usuario re-correr con --id-muestra.
            raw = body_75.get("raw_text", "") if isinstance(body_75, dict) else ""
            if "ya existe" in str(raw).lower():
                print("\nERROR: API75 dice que la muestra ya existe pero no devuelve el id.")
                print("       Volve a correr con: --id-muestra=<id_de_corrida_previa>")
            else:
                print("\nERROR: API75 no devolvio id_muestra. Se aborta el flujo.")
            return _guardar_log(resumen, hoy, codigo_salida=3)

        print(f"  OK id_muestra = {id_muestra}")

    # ---- 3) API76 -----------------------------------------------------
    payload_api76 = build_payload_api76(CASO_PRUEBA, id_muestra, fecha_resultado)
    status_76, body_76 = post(
        "3) API76 - Informar resultado",
        ENDPOINTS["API76"], headers_for(creds["API76"]), payload_api76,
    )
    resumen["pasos"]["api76"] = {
        "status_code": status_76,
        "request": payload_api76,
        "response": body_76,
    }

    ok_final = (status_76 is not None) and (200 <= status_76 < 300)
    print()
    print("=" * 70)
    print("  RESUMEN")
    print("=" * 70)
    print(f"  WS400  -> status {status_ws}   id_caso    = {id_caso}")
    if args.id_muestra:
        print(f"  API75  -> SALTADA       id_muestra = {id_muestra} (provisto)")
    else:
        print(f"  API75  -> status {status_75}   id_muestra = {id_muestra}")
    print(f"  API76  -> status {status_76}   {'OK' if ok_final else 'REVISAR'}")
    return _guardar_log(resumen, hoy, codigo_salida=0 if ok_final else 4)


def _guardar_log(resumen: dict, hoy: datetime, codigo_salida: int) -> int:
    out = LOGS_DIR / f"smoke_test_{hoy.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nLog guardado en: {out}")
    return codigo_salida


if __name__ == "__main__":
    sys.exit(main())

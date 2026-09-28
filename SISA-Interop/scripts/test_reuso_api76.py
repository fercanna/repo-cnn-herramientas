"""
test_reuso_api76.py — Prueba de reuso: segunda determinación sobre muestra existente.

Toma una entrada del muestras_cache.json (id_muestra ya creada en una corrida real)
y llama a la API76 con los parámetros de VDRL para ver si acepta una segunda
determinación sobre el mismo idEventoMuestra.

Uso:
    python scripts/test_reuso_api76.py
    python scripts/test_reuso_api76.py --dni 41139359 --id_evento 193
    python scripts/test_reuso_api76.py --resultado REACTIVO --dil 4
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Parámetros de VDRL por idEvento
VDRL_POR_EVENTO: dict[int, dict] = {
    193: {"idPrueba": 153, "idTipoPrueba": 145},   # Sífilis general
    115: {"idPrueba": 153, "idTipoPrueba": 145},   # Sífilis gestante
}

# idResultado VDRL por dilución; 2 = NO REACTIVO (para prueba segura)
VDRL_DIL_RESULTADO: dict[int, int] = {
    0:   2,     # NO REACTIVO
    1:   1059,  2: 1060, 4: 1061,  8: 1062,
    16:  1063,  32: 1064, 64: 1065, 128: 1066,
    256: 1067,  512: 1068, 1024: 1069,
}


def _cargar_cache() -> dict:
    p = ROOT / "data" / "muestras_cache.json"
    if not p.exists():
        raise FileNotFoundError("No se encontró data/muestras_cache.json")
    return json.loads(p.read_text(encoding="utf-8"))


def _cargar_credenciales() -> dict:
    p = ROOT / "config" / "credentials.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("produccion", data)


def _cargar_settings() -> dict:
    p = ROOT / "config" / "settings.json"
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test de reuso API76: segunda determinación sobre muestra existente."
    )
    parser.add_argument("--dni", default=None, help="DNI del paciente (sin guiones). Default: primer sífilis del cache.")
    parser.add_argument("--id_evento", type=int, default=None, help="idEvento SISA (193=sifilis gral, 115=gestante). Default: autodetectar del cache.")
    parser.add_argument("--resultado", choices=["NO_REACTIVO", "REACTIVO"], default="NO_REACTIVO",
                        help="Resultado a enviar. Default: NO_REACTIVO (seguro para prueba).")
    parser.add_argument("--dil", type=int, default=0,
                        help="Dilución VDRL (ej: 4, 8, 16). Solo aplica si --resultado REACTIVO. Default: 0.")
    args = parser.parse_args()

    # Cargar cache y seleccionar caso
    cache = _cargar_cache()
    eventos_sifilis = {193, 115}

    if args.dni and args.id_evento:
        key = f"{args.dni}|{args.id_evento}"
        if key not in cache:
            print(f"ERROR: '{key}' no está en el cache. Claves disponibles para sífilis:")
            for k in cache:
                ev = int(k.split("|")[1])
                if ev in eventos_sifilis:
                    print(f"  {k}")
            return
        id_evento = args.id_evento
    else:
        # Tomar el primer caso de sífilis disponible en el cache
        key = next((k for k in cache if int(k.split("|")[1]) in eventos_sifilis), None)
        if not key:
            print("ERROR: no hay casos de sífilis en el cache.")
            return
        id_evento = int(key.split("|")[1])

    entrada = cache[key]
    id_caso = entrada["id_caso"]
    id_muestra = entrada["id_muestra"]

    # Configurar payload VDRL
    vdrl = VDRL_POR_EVENTO[id_evento]
    dil = args.dil if args.resultado == "REACTIVO" else 0
    id_resultado = VDRL_DIL_RESULTADO.get(dil, 2)
    valor = f"NO REACTIVO" if dil == 0 else f"REACTIVO {dil} DIL"

    settings = _cargar_settings()
    creds = _cargar_credenciales()
    cod_sisa = settings["id_interno_sisa"]
    hoy = date.today().isoformat()

    payload = {
        "derivada": True,
        "fechaEmisionResultado": hoy,
        "fechaRecepcion": hoy,
        "idDerivacion": None,
        "idEstablecimiento": cod_sisa,
        "idEvento": id_evento,
        "idEventoMuestra": id_muestra,
        "idPrueba": vdrl["idPrueba"],
        "idResultado": id_resultado,
        "idTipoPrueba": vdrl["idTipoPrueba"],
        "noApta": False,
        "valor": valor,
    }

    url = "https://apisalud.msal.gob.ar/snvsLaboratorios/v1/pruebaMuestras"
    headers = {
        "Content-Type": "application/json",
        "APP_ID": creds["API76"]["app_id"],
        "APP_KEY": creds["API76"]["app_key"],
    }

    print("=" * 65)
    print("TEST REUSO API76 — segunda determinación sobre muestra existente")
    print("=" * 65)
    print(f"  Clave cache     : {key}")
    print(f"  id_caso SISA    : {id_caso}")
    print(f"  idEventoMuestra : {id_muestra}  ← el que ya existe en SISA")
    print(f"  idEvento        : {id_evento}  ({'sifilis gestante' if id_evento == 115 else 'sifilis general'})")
    print(f"  Prueba          : VDRL (idPrueba={vdrl['idPrueba']}, idTipoPrueba={vdrl['idTipoPrueba']})")
    print(f"  Resultado       : {valor} (idResultado={id_resultado})")
    print(f"  URL             : {url}")
    print()
    print("Payload que se enviará:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()

    confirm = input("¿Confirmar envío a PRODUCCIÓN? [s/N]: ").strip().lower()
    if confirm != "s":
        print("Cancelado. No se envió nada.")
        return

    import urllib.request
    import urllib.error

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    print("\nEnviando...")
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8")
    except Exception as e:
        print(f"ERROR de red: {e}")
        return

    print(f"\nStatus: {status}")
    print("Respuesta:")
    try:
        print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    except Exception:
        print(body)

    print()
    if 200 <= status < 300:
        print("✓ ÉXITO — API76 aceptó la segunda determinación sobre la muestra existente.")
        print("  → La opción 3 (REUSE via cache de id_muestra) ES VIABLE.")
    else:
        print("✗ ERROR — API76 rechazó la segunda determinación.")
        print("  → La opción 3 no funciona así. Hay que consultar a SISA.")


if __name__ == "__main__":
    main()

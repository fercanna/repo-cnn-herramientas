"""api75.py — Registrar muestra en SISA (API75).

Función principal:
    resultado = registrar_muestra(caso, id_caso, cod_sisa, creds, url)

Gotchas documentados en CONTEXTO_CLAUDE_CODE.md:
- El campo del payload se llama "idtipoMuestra" con 't' minúscula (capricho del API).
- El id del evento-muestra creado está en body["id"], NO en body["idMuestra"]
  (que es el tipo de muestra que enviamos).
- Si la muestra ya existe, API75 responde 400 con "El registro a crear ya existe"
  pero NO devuelve el id existente (a diferencia de WS400). En ese caso se lanza
  SisaError con instrucciones para retomar con el id conocido.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.sisa_http import SisaError, headers_para, post

if TYPE_CHECKING:
    from scripts.parser_lis import CasoNotificable


def _build_payload(caso: "CasoNotificable", id_caso: int, cod_sisa: str) -> dict:
    return {
        "adecuada": True,
        "aislamiento": False,
        "fechaToma": caso.fecha_toma,
        "idEstablecimientoToma": cod_sisa,
        "idEventoCaso": id_caso,
        "idMuestra": caso.id_muestra,
        "idtipoMuestra": caso.id_tipo_muestra,  # 't' minúscula — capricho del API75
        "muestra": True,
    }


def registrar_muestra(
    caso: "CasoNotificable",
    id_caso: int,
    cod_sisa: str,
    creds: dict,
    url: str,
) -> dict:
    """
    Registra la muestra asociada al caso.

    Returns:
        {
            "id_muestra": int,   # el campo "id" de la respuesta
            "payload": dict,
            "response": dict,
            "status_code": int | None,
        }

    Raises:
        SisaError: si la muestra ya existe (no se puede recuperar el id)
                   o si API75 devuelve un error no recuperable.
    """
    payload = _build_payload(caso, id_caso, cod_sisa)
    status, body = post(url, headers_para(creds), payload)

    id_muestra = None
    if isinstance(body, dict):
        # body["id"] es el identificador del evento-muestra recién creado.
        # body["idMuestra"] es el TIPO que enviamos — no confundir.
        id_muestra = body.get("id") or body.get("idEventoMuestra")

    if not id_muestra:
        raw = body.get("raw_text", "") if isinstance(body, dict) else str(body)
        if "ya existe" in raw.lower():
            raise SisaError(
                "API75: muestra ya existe y no devuelve el id. "
                "Revisá el log de la corrida anterior para obtener el id_muestra.",
                status=status,
                body=body,
            )
        raise SisaError(
            f"API75 no devolvió id_muestra (status={status})",
            status=status,
            body=body,
        )

    return {
        "id_muestra": id_muestra,
        "payload": payload,
        "response": body,
        "status_code": status,
    }

"""ws400.py — Crear caso nominal en SISA (WS400).

Función principal:
    resultado = crear_caso(caso, domicilio, refes, creds, url)

Si el caso ya existe en SNVS, WS400 devuelve 400 con el ID_SNVS_EVENTO_CASO
embebido en el mensaje de error — se extrae y reutiliza automáticamente.
El llamador puede distinguir casos nuevos de ya-existentes con resultado["caso_nuevo"].
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from scripts.sisa_http import SisaError, headers_para, post

if TYPE_CHECKING:
    from scripts.parser_lis import CasoNotificable


def _parse_id_caso_de_error(body: dict) -> int | None:
    """Extrae el ID_SNVS_EVENTO_CASO del mensaje cuando el caso ya existe."""
    blob = " ".join([
        str(body.get("description") or ""),
        str(body.get("message") or ""),
        json.dumps(body.get("errors") or {}, ensure_ascii=False),
    ])
    m = re.search(r"ID_SNVS_EVENTO_CASO\D+(\d+)", blob)
    return int(m.group(1)) if m else None


def _build_payload(caso: "CasoNotificable", refes: str, domicilio: dict | None = None) -> dict:
    ciudadano: dict = {
        "apellido": caso.apellido,
        "nombre": caso.nombre,
        "tipoDocumento": caso.tipo_documento,
        "numeroDocumento": caso.numero_documento,
        "sexo": caso.sexo,
        "fechaNacimiento": caso.fecha_nacimiento,
        "paisEmisionTipoDocumento": None,
        "seDeclaraPuebloIndigena": "No",
        "telefono": None,
        "mail": None,
        "personaACargo": {
            "tipoDocumento": None,
            "numeroDocumento": None,
            "vinculo": None,
        },
    }
    if domicilio is not None:
        ciudadano["domicilio"] = {
            "calle": domicilio.get("calle", "SIN DATO"),
            "idDepartamento": domicilio["idDepartamento"],
            "idLocalidad": domicilio["idLocalidad"],
            "idProvincia": domicilio["idProvincia"],
            "idPais": domicilio["idPais"],
        }
    return {
        "ciudadano": ciudadano,
        "eventoCasoNominal": {
            "idGrupoEvento": caso.id_grupo_evento,
            "idEvento": caso.id_evento,
            "idClasificacionManualCaso": caso.id_clasificacion_manual_caso,
            "fechaPapel": caso.fecha_papel,
            "idEstablecimientoCarga": refes,
        },
    }


def crear_caso(
    caso: "CasoNotificable",
    refes: str,
    creds: dict,
    url: str,
    domicilio: dict | None = None,
) -> dict:
    """
    Crea un caso nominal en SISA. Si el caso ya existe, extrae y reutiliza el id.

    domicilio: si es None (default), SISA usa el domicilio de RENAPER.
               Pasar un dict sólo como fallback explícito.

    Returns:
        {
            "id_caso": int,
            "payload": dict,
            "response": dict,
            "status_code": int | None,
            "caso_nuevo": bool,
        }

    Raises:
        SisaError: si WS400 no devuelve un id_caso utilizable.
    """
    payload = _build_payload(caso, refes, domicilio)
    status, body = post(url, headers_para(creds), payload)

    caso_nuevo = False
    id_caso = None

    if isinstance(body, dict):
        if body.get("status") == "OK":
            id_caso = body.get("id_caso")
            caso_nuevo = True
        else:
            id_caso = _parse_id_caso_de_error(body)

    if not id_caso:
        raise SisaError(
            f"WS400 no devolvió id_caso (status={status})",
            status=status,
            body=body,
        )

    return {
        "id_caso": id_caso,
        "payload": payload,
        "response": body,
        "status_code": status,
        "caso_nuevo": caso_nuevo,
    }

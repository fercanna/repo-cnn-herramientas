"""api81.py — Modificar clasificación manual de un caso en SISA (API81).

Función principal:
    resultado = cambiar_clasificacion(id_caso, id_clasificacion, creds, url)

Se usa para actualizar la clasificación de un caso de sífilis a 742
("Caso confirmado de sífilis temprana") cuando llega una VDRL ≥16 DIL
en una corrida posterior a la treponémica (cross-run).

Para mismo dataset, el pre-scan en main.py ya envía 742 en WS400 y
esta API no es necesaria.
"""
from __future__ import annotations

from scripts.sisa_http import SisaError, headers_para, put


def cambiar_clasificacion(
    id_caso: int,
    id_clasificacion: int,
    creds: dict,
    url: str,
) -> dict:
    """
    Cambia la clasificación manual de un EVENTO_CASO en SISA.

    Returns:
        {"payload": dict, "response": dict, "status_code": int | None}

    Raises:
        SisaError: si API81 devuelve un error no recuperable.
    """
    payload = {
        "idEventoCaso": id_caso,
        "idClasificacionManual": id_clasificacion,
    }
    status, body = put(url, headers_para(creds), payload)

    if status is None or not (200 <= status < 300):
        raise SisaError(
            f"API81 falló (status={status})",
            status=status,
            body=body,
        )

    return {
        "payload": payload,
        "response": body,
        "status_code": status,
    }

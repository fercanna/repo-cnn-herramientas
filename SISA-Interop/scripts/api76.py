"""api76.py — Informar resultado en SISA (API76).

Función principal:
    resultado = informar_resultado(caso, id_muestra, cod_sisa, creds, url)

Gotcha crítico: idEventoMuestra debe ser el campo "id" devuelto por API75,
NO el campo "idMuestra" (tipo de muestra). Pasarle el tipo falla con
"Ha ocurrido un error inesperado" — sin más contexto.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.sisa_http import SisaError, headers_para, post

if TYPE_CHECKING:
    from scripts.parser_lis import CasoNotificable


def _build_payload(caso: "CasoNotificable", id_muestra: int, cod_sisa: str) -> dict:
    # Si FECHAHORAVALIDACION < FECHAALTA (caso raro en LIS con datos retroactivos),
    # API76 rechaza con "fechaRecepcion debe ser posterior o igual a la fecha de toma".
    fecha_76 = caso.fecha_resultado if caso.fecha_resultado >= caso.fecha_toma else caso.fecha_toma
    return {
        "derivada": True,
        "fechaEmisionResultado": fecha_76,
        "fechaRecepcion": fecha_76,
        "idDerivacion": None,
        "idEstablecimiento": cod_sisa,
        "idEvento": caso.id_evento,
        "idEventoMuestra": id_muestra,  # el "id" de API75, NO el "idMuestra"
        "idPrueba": caso.id_prueba,
        "idResultado": caso.id_resultado,
        "idTipoPrueba": caso.id_tipo_prueba,
        "noApta": True,  # sic: SISA invierte el nombre — True = la muestra ES apta (ver Instructivo_API76.txt)
        "valor": caso.valor_resultado,
    }


def informar_resultado(
    caso: "CasoNotificable",
    id_muestra: int,
    cod_sisa: str,
    creds: dict,
    url: str,
) -> dict:
    """
    Informa el resultado de la prueba para la muestra registrada.

    Returns:
        {
            "payload": dict,
            "response": dict,
            "status_code": int | None,
        }

    Raises:
        SisaError: si API76 devuelve un error no recuperable.
    """
    payload = _build_payload(caso, id_muestra, cod_sisa)
    status, body = post(url, headers_para(creds), payload)

    if status is None or not (200 <= status < 300):
        raise SisaError(
            f"API76 falló (status={status})",
            status=status,
            body=body,
        )

    return {
        "payload": payload,
        "response": body,
        "status_code": status,
    }

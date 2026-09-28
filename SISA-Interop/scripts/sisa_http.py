"""sisa_http.py — HTTP utility compartido por ws400, api75 y api76.

Retry ante errores transitorios (502/503/504) con backoff exponencial,
tal como está documentado en CONTEXTO_CLAUDE_CODE.md sección 9.
"""
from __future__ import annotations

import time
from typing import Any

try:
    import requests
except ImportError:
    raise ImportError("Falta el módulo 'requests'. Instalá con: pip install requests")


TIMEOUT_S = 30
MAX_INTENTOS = 3
_STATUS_REINTENTABLES = {502, 503, 504}
_BACKOFF_BASE_S = 2


class SisaError(Exception):
    """Error no recuperable en la comunicación con SISA."""

    def __init__(self, mensaje: str, status: int | None = None, body: Any = None):
        super().__init__(mensaje)
        self.status = status
        self.body = body


def headers_para(creds: dict) -> dict:
    """Arma los headers HTTP. Acepta claves en mayúsculas (APP_ID) o minúsculas (app_id)."""
    c = {k.lower(): v for k, v in creds.items()}
    return {
        "app_id": c["app_id"],
        "app_key": c["app_key"],
        "Content-Type": "application/json",
    }


def put(url: str, headers: dict, payload: dict) -> tuple[int | None, dict]:
    """PUT con reintentos. Misma lógica que post."""
    ultimo_status: int | None = None
    ultimo_body: dict = {"error": "sin intento"}

    for intento in range(1, MAX_INTENTOS + 1):
        if intento > 1:
            time.sleep(_BACKOFF_BASE_S * (2 ** (intento - 2)))
        try:
            resp = requests.put(url, json=payload, headers=headers, timeout=TIMEOUT_S)
        except (requests.ConnectionError, requests.Timeout) as exc:
            ultimo_status, ultimo_body = None, {"error_red": str(exc)}
            if intento < MAX_INTENTOS:
                continue
            return ultimo_status, ultimo_body
        except Exception as exc:
            return None, {"error": str(exc)}
        try:
            body = resp.json()
        except ValueError:
            body = {"raw_text": resp.text}
        ultimo_status, ultimo_body = resp.status_code, body
        if resp.status_code not in _STATUS_REINTENTABLES:
            return ultimo_status, ultimo_body

    return ultimo_status, ultimo_body


def post(url: str, headers: dict, payload: dict) -> tuple[int | None, dict]:
    """
    POST con reintentos ante errores transitorios (502/503/504) y errores de red.
    Devuelve (status_code, body_dict). status_code es None si la red falló en
    todos los intentos. body puede contener 'raw_text' si la respuesta no es JSON.
    """
    ultimo_status: int | None = None
    ultimo_body: dict = {"error": "sin intento"}

    for intento in range(1, MAX_INTENTOS + 1):
        if intento > 1:
            time.sleep(_BACKOFF_BASE_S * (2 ** (intento - 2)))

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_S)
        except (requests.ConnectionError, requests.Timeout) as exc:
            ultimo_status, ultimo_body = None, {"error_red": str(exc)}
            if intento < MAX_INTENTOS:
                continue
            return ultimo_status, ultimo_body
        except Exception as exc:
            return None, {"error": str(exc)}

        try:
            body = resp.json()
        except ValueError:
            body = {"raw_text": resp.text}

        ultimo_status, ultimo_body = resp.status_code, body

        if resp.status_code not in _STATUS_REINTENTABLES:
            return ultimo_status, ultimo_body

    return ultimo_status, ultimo_body

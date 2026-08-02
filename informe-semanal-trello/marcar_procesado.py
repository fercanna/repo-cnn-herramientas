# -*- coding: utf-8 -*-
"""
Marca la corrida semanal como procesada en estado.json.

Uso:  python marcar_procesado.py <nombre_json_procesado> <transcripcion1> <transcripcion2> ...
"""
import json, os, sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(SCRIPT_DIR, 'estado.json')

if os.path.exists(STATE_PATH):
    with open(STATE_PATH, 'r', encoding='utf-8') as f:
        state = json.load(f)
else:
    state = {"ultimo_json_procesado": None, "ultima_corrida": None, "transcripciones_procesadas": []}

if len(sys.argv) < 2:
    sys.exit("Uso: python marcar_procesado.py <nombre_json> [transcripcion1 transcripcion2 ...]")

state["ultimo_json_procesado"] = sys.argv[1]
state["ultima_corrida"] = datetime.now().isoformat()
nuevas = sys.argv[2:]
existentes = set(state.get("transcripciones_procesadas", []))
existentes.update(nuevas)
state["transcripciones_procesadas"] = sorted(existentes)

with open(STATE_PATH, 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print("Estado actualizado: " + STATE_PATH)

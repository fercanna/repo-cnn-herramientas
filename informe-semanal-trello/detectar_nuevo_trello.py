# -*- coding: utf-8 -*-
"""
Detector de nuevo export de Trello - generico multi-cliente
=============================================================
Uso:  python detectar_nuevo_trello.py

Busca en la carpeta del script (raiz _trello) archivos .json de export de
Trello que todavia no fueron procesados (segun estado.json). Si encuentra
uno nuevo:
  - Calcula el numero de semana ISO de hoy y crea la carpeta seNN
    (o seNN_v2 si ya existiera, para no pisar una corrida anterior).
  - Copia el JSON a esa carpeta.
  - Imprime: NUEVO|<ruta_carpeta>|<ruta_json>

Si no hay ningun JSON nuevo desde la ultima corrida, imprime: SIN_NOVEDAD

No marca el JSON como procesado todavia - eso lo hace marcar_procesado.py
una vez que el informe se genero correctamente (para poder reintentar si
algo falla a mitad de camino).
"""
import json, os, glob, shutil, sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(SCRIPT_DIR, 'estado.json')

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"ultimo_json_procesado": None, "ultima_corrida": None, "transcripciones_procesadas": []}

state = load_state()
ya_procesado = state.get("ultimo_json_procesado")

EXCLUIR = ('estado.json', 'observaciones.json', 'config.json')
json_files = [f for f in glob.glob(os.path.join(SCRIPT_DIR, '*.json'))
              if os.path.basename(f) not in EXCLUIR]
json_files = sorted(json_files, key=os.path.getmtime)

if not json_files:
    print("SIN_NOVEDAD|No hay ningun JSON de Trello en " + SCRIPT_DIR)
    sys.exit(0)

candidato = json_files[-1]
nombre_candidato = os.path.basename(candidato)

if nombre_candidato == ya_procesado:
    print("SIN_NOVEDAD|El JSON mas nuevo (" + nombre_candidato + ") ya fue procesado en la corrida anterior")
    sys.exit(0)

hoy = datetime.now()
semana = hoy.isocalendar()[1]
base_folder = 'se' + str(semana)
folder = os.path.join(SCRIPT_DIR, base_folder)
i = 2
while os.path.exists(folder):
    folder = os.path.join(SCRIPT_DIR, base_folder + '_v' + str(i))
    i += 1
os.makedirs(folder, exist_ok=True)

destino_json = os.path.join(folder, nombre_candidato)
shutil.copy2(candidato, destino_json)
print("NUEVO|" + folder + "|" + destino_json)

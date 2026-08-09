"""
Configuración del lugar donde vive la base de datos.

Por qué existe este archivo:
Fer usa TimeTracker desde 3 máquinas distintas y quiere que todas lean/escriban
la misma base de datos (para que el Dashboard muestre el trabajo hecho en
cualquiera de ellas). La forma más simple es apuntar la carpeta de datos a una
carpeta sincronizada por OneDrive/Dropbox/Google Drive.

Como la ruta de esa carpeta sincronizada puede variar de una máquina a otra
(letra de unidad, usuario de Windows, etc.), NO se hardcodea en el código
versionado. En su lugar, cada máquina tiene su propio 'config.local.json'
(no se sube a git) con la ruta real en esa máquina.

Prioridad de resolución:
1. Variable de entorno TIMETRACKER_DB_DIR (si está seteada)
2. config.local.json en la carpeta del proyecto (por máquina, no versionado)
3. Carpeta 'data' local junto a la app (comportamiento anterior, sin sync)
"""
import os
import json

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_FILE = os.path.join(_APP_DIR, "config.local.json")


def get_db_folder():
    env_path = os.environ.get("TIMETRACKER_DB_DIR")
    if env_path:
        return env_path

    if os.path.exists(_CONFIG_FILE):
        try:
            # utf-8-sig: tolera el BOM que PowerShell agrega con Set-Content -Encoding UTF8
            with open(_CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            configured = data.get("db_folder")
            if configured:
                return configured
        except (json.JSONDecodeError, OSError):
            pass

    return os.path.join(_APP_DIR, "data")


def get_config_file_path():
    return _CONFIG_FILE

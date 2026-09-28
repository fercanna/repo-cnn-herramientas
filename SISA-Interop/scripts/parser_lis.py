"""
parser_lis.py — Parser del TXT exportado por el LIS del Laboratorio Central de Virología Córdoba.

Lee el TXT diario del LIS (separador TAB, encoding latin1) y devuelve la lista
de casos NOTIFICABLES al SISA, ya con todos los IDs clínicos resueltos.

NO se comunica con SISA. NO resuelve geografía del paciente
(eso lo hace el orquestador con scripts/geografia_sisa.py o un default
de settings.json al armar el payload final).

Reglas de negocio (definidas en CONTEXTO_CLAUDE_CODE.md):
- Solo filas con ESTADO == 'V' (validadas).
- Resultado válido (canonicalizado): RESULTADO debe estar en RESULTADOS_VALIDOS después de
  aplicar _canonicalizar_resultado() ('DEBIL REACTIVO'→'REACTIVO', 'Registra antecedentes'→'REACTIVO', etc.).
- Deduplicar por (ORDEN, ESTUDIO): cuando hay varias filas por orden (Sífilis, VHC con fila
  INTERPRETADO + filas extra), se conserva la fila con VARIABLEDESCRIPCION='INTERPRETADO'.
- Match contra mapeos/clinico.json por (estudio_codigo, estudio_nombre, poblacion, condicion_vigilancia).
  El nombre se incluye en la clave porque en el LIS el código de estudio NO es
  único — ej. ESTUDIO=14 puede ser 'ANTI HBC' o 'SIFILIS (BCO)'. Sin matchear
  por nombre, un ANTI HBC reactivo se notificaría incorrectamente como Sífilis.
- Estudios sin mapeo (combinación codigo+nombre+población+resultado) se descartan
  silenciosamente (Toxoplasmosis, EBV, ANTI HBC, etc.).
- Resultados con formato sucio se descartan (ej. 'pos.', 'POSITIVO PRESUNTIVO*', 'ZONA GRIS').
- APENOM viene como 'APELLIDO NOMBRE' en un campo. WS400 exige nombre >=2 chars,
  así que mandamos APENOM completo como apellido y 'ND' como nombre placeholder.

Uso CLI:
    python scripts/parser_lis.py path/al/lis.txt
    python scripts/parser_lis.py path/al/lis.txt --json
    python scripts/parser_lis.py path/al/lis.txt --csv salida.csv
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    print("ERROR: falta pandas. Instalá con: pip install pandas", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
CLINICO_PATH = REPO_ROOT / "mapeos" / "clinico.json"
ESTABLECIMIENTOS_PATH = REPO_ROOT / "mapeos" / "establecimientos.json"

# Encoding y separador del TXT del LIS — fijos por contrato.
LIS_ENCODING = "latin1"
LIS_SEP = "\t"

# Resultados aceptados (ya normalizados, en mayúsculas, sin acentos, sin guión bajo).
# El mapeo clínico usa las mismas etiquetas en su campo 'condicion_vigilancia'.
RESULTADOS_VALIDOS = {
    "REACTIVO", "POSITIVO", "DETECTABLE",
    "NO REACTIVO", "NEGATIVO", "NO DETECTABLE",
    "AMPLIFICACION POSITIVA",
}

# SISA tiene idResultado específico por título de dilución para VDRL (prueba no treponémica).
# El catálogo genérico (idResultado=109 "Reactivo") no es válido para esta prueba.
VDRL_DIL_RESULTADO: dict[int, int] = {
    1: 1059, 2: 1060, 4: 1061, 8: 1062,
    16: 1063, 32: 1064, 64: 1065, 128: 1066,
    256: 1067, 512: 1068, 1024: 1069,
}
# Estudio(s) que usan VDRL_DIL_RESULTADO en lugar del idResultado de clinico.json
ESTUDIOS_VDRL: set[int] = {72}


# ---------------- Modelos ----------------

@dataclass
class CasoNotificable:
    """Un caso listo para alimentar al orquestador (WS400 → API75 → API76)."""

    # Trazabilidad
    orden: str
    sucursal: str
    sucursal_descripcion: str
    fila_origen: int

    # Paciente
    apellido: str
    nombre: str
    tipo_documento: int  # 1=DNI
    numero_documento: str
    sexo: str            # 'F' / 'M'
    fecha_nacimiento: str  # DD-MM-YYYY (formato WS400)

    # Evento — del clinico.json
    id_grupo_evento: int
    id_evento: int
    id_clasificacion_manual_caso: int

    # Muestra — del clinico.json
    id_muestra: int           # tipo SISA
    id_tipo_muestra: int      # subtipo SISA

    # Prueba — del clinico.json
    id_tipo_prueba: int
    id_prueba: int
    id_resultado: int

    # Fechas — formatos distintos por API
    fecha_papel: str           # DD-MM-YYYY (WS400)
    fecha_toma: str            # YYYY-MM-DD (API75)
    fecha_resultado: str       # YYYY-MM-DD (API76)

    # Resultado textual (lo que va en API76.valor)
    valor_resultado: str

    # Contexto clínico
    estudio_codigo: int
    estudio_nombre: str
    poblacion: str             # GESTANTE / NO_GESTANTE / GENERAL
    condicion_vigilancia: str  # como llegó normalizado

    # Entidad derivante (sucursal del LIS) — útil para resolver geografía después
    entidad_derivante: str = ""

    # Establecimiento derivante — resuelto desde mapeos/establecimientos.json por SUCURSAL.
    # refes_carga  → WS400.idEstablecimientoCarga (14 dígitos).
    # sisa_corto_toma → API75.idEstablecimientoToma (6 dígitos).
    # Si la sucursal no está en el JSON el caso se descarta antes de llegar aquí.
    refes_carga: str = ""
    sisa_corto_toma: str = ""


@dataclass
class ResumenParseo:
    total_filas: int = 0
    validadas: int = 0
    interpretadas: int = 0
    con_mapeo: int = 0
    notificables: int = 0
    descartadas_resultado_sucio: int = 0
    descartadas_sin_mapeo: int = 0
    descartadas_sin_dni: int = 0
    descartadas_sucursal_desconocida: int = 0
    descartadas_sucursal_interna: int = 0
    descartadas_colision_codigo: int = 0
    estudios_sin_mapeo: Counter = field(default_factory=Counter)
    colisiones_codigo: Counter = field(default_factory=Counter)
    resultados_descartados: Counter = field(default_factory=Counter)
    notificables_por_estudio: Counter = field(default_factory=Counter)
    sucursales_desconocidas: Counter = field(default_factory=Counter)


# ---------------- Helpers ----------------

def _norm(s) -> str:
    """Lowercase + sin acentos + trim."""
    if pd.isna(s):
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.strip().lower()


def _norm_resultado(s) -> str:
    """Normaliza el campo RESULTADO a uppercase, sin acentos. Mantiene espacios."""
    if pd.isna(s):
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.strip().upper()


# Mapeo de formas del LIS → forma canónica usada en clinico.json.
# Aliases reactivos (DEBIL REACTIVO, Registra antecedentes) colapsan a REACTIVO.
_RESULTADO_CANONICAL: dict[str, str] = {
    "REACTIVO":              "REACTIVO",
    "DEBIL REACTIVO":        "REACTIVO",
    "REGISTRA ANTECEDENTES": "REACTIVO",
    "POSITIVO":              "POSITIVO",
    "DETECTABLE":            "DETECTABLE",
    "AMPLIFICACION POSITIVA":"AMPLIFICACION POSITIVA",
    "NO REACTIVO":           "NO REACTIVO",
    "NEGATIVO":              "NEGATIVO",
    "NO DETECTABLE":         "NO DETECTABLE",
}


def _dilution_value(valor: str) -> int:
    """Extrae el número de dilución de 'REACTIVO N DIL[S]', o 0 si no aplica."""
    import re
    m = re.search(r"REACTIVO\s+(\d+)\s+DIL", valor.upper())
    return int(m.group(1)) if m else 0


def _resolver_id_resultado(estudio_cod: int, valor_raw: str, id_resultado_base: int) -> int:
    """Para VDRL, mapea el título de dilución a su idResultado específico en SISA.
    Para el resto de estudios devuelve el idResultado de clinico.json sin cambios."""
    if estudio_cod in ESTUDIOS_VDRL:
        dil = _dilution_value(valor_raw)
        if dil in VDRL_DIL_RESULTADO:
            return VDRL_DIL_RESULTADO[dil]
    return id_resultado_base


def _canonicalizar_resultado(s) -> str:
    """
    Mapea el RESULTADO del LIS a la forma canónica que usa clinico.json.
    'DEBIL REACTIVO' → 'REACTIVO', 'Registra antecedentes' → 'REACTIVO'.
    'REACTIVO N DIL[S]' → 'REACTIVO' (diluciones VDRL de cualquier título).
    Devuelve '' para valores no reconocidos (la fila se descartará).
    """
    if pd.isna(s) or str(s).strip() == "":
        return ""
    normed = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").strip().upper()
    if normed in _RESULTADO_CANONICAL:
        return _RESULTADO_CANONICAL[normed]
    # Diluciones VDRL: "REACTIVO 8 DIL", "REACTIVO 16 DILS", etc.
    if normed.startswith("REACTIVO ") and "DIL" in normed:
        return "REACTIVO"
    return ""


def _norm_estudio_nombre(s) -> str:
    """
    Normaliza el ESTUDIODESCRIPCION para matching robusto contra clinico.json.
    Tolera paréntesis y espacios extra: 'SIFILIS (BCO)' == 'SIFILIS BCO'.
    Sin acentos, uppercase, sin signos de puntuación, espacios colapsados.
    """
    if pd.isna(s):
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.upper()
    # Reemplazar paréntesis y signos de puntuación por espacio
    for ch in "()[]{}.,;:_-/\\":
        s = s.replace(ch, " ")
    # Colapsar espacios
    return " ".join(s.split())


def _es_estudio_banco(nombre_norm: str) -> bool:
    """
    True si el ESTUDIODESCRIPCION normalizado indica que la fila es un panel
    de BANCO DE SANGRE (donante) y no un estudio de diagnostico clinico.

    El LIS marca esto de dos formas observadas en produccion:
    - Sufijo '(BCO)' en el nombre: 'SIFILIS (BCO)', 'ANTI VHC (BCO)'.
    - Prefijo 'BM ' (Banco - Marcador): 'BM HIV (BCO)', 'BM VHC (BCO)'.

    Se usa como mitad de la verificacion de simetria en
    MapeoClinico.nombre_lis_es_aceptable(): el LIS reusa numeros de ESTUDIO
    entre paneles de banco y estudios diagnosticos (ver docstring de esa
    clase), asi que un estudio de banco NUNCA debe poder matchear contra
    una entrada de clinico.json que no sea, a su vez, de banco.
    """
    tokens = nombre_norm.split()
    if not tokens:
        return False
    return "BCO" in tokens or tokens[0] == "BM"


def determinar_poblacion(sexo: str, diag_desc: str) -> str:
    """
    Devuelve la población MÁS específica del paciente.
    Usa DIAGNOSTICODESCRIPCION (no TIPOFISIOLOGICODESCRIPCION — demasiado ruidoso).
    GESTANTE sólo si SEXO='F' Y diagnóstico menciona 'embarazada'
    (descarta 'PAREJA DE EMBARAZADA' en hombres).
    """
    dd = _norm(diag_desc)
    sx = str(sexo).strip().upper()
    if sx == "F" and "embarazada" in dd:
        return "GESTANTE"
    if sx == "F":
        return "NO_GESTANTE"
    return "GENERAL"


def candidatos_poblacion(sexo: str, diag_desc: str) -> list[str]:
    """
    Candidatos de población para matching, del más específico al más general.
    Permite que un evento sin estratificación por embarazo (ej. DENGUE —
    sólo GENERAL en clinico.json) matchee a una mujer no embarazada.

    - mujer embarazada  → ['GESTANTE', 'GENERAL']
    - mujer no embarazada → ['NO_GESTANTE', 'GENERAL']
    - hombre / sin sexo → ['GENERAL']
    """
    dd = _norm(diag_desc)
    sx = str(sexo).strip().upper()
    if sx == "F" and "embarazada" in dd:
        return ["GESTANTE", "GENERAL"]
    if sx == "F":
        return ["NO_GESTANTE", "GENERAL"]
    return ["GENERAL"]


def parse_apenom(apenom: str) -> tuple[str, str]:
    """
    APENOM viene como 'APELLIDO NOMBRE...' en un campo. WS400 exige
    apellido>=2 chars y nombre>=2 chars. Mandamos APENOM completo como
    apellido y 'ND' como nombre placeholder. RENAPER hace el match real
    por DNI y resuelve los datos correctos.
    """
    s = "" if apenom is None else str(apenom).strip()
    if len(s) < 2:
        s = "SIN DATO"
    return s, "ND"


def _parse_fecha_lis(s) -> Optional[tuple[int, int, int]]:
    """
    El LIS exporta fechas como 'D/M/YYYY' o 'D/M/YYYY H:M:S' (sin padding).
    Devuelve (year, month, day) o None.
    """
    if s is None or pd.isna(s):
        return None
    s = str(s).strip()
    if not s:
        return None
    fecha_part = s.split(" ")[0]
    parts = fecha_part.split("/")
    if len(parts) != 3:
        return None
    try:
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        return (y, m, d)
    except ValueError:
        return None


def fecha_ws400(s) -> str:
    """Formato DD-MM-YYYY para WS400."""
    parsed = _parse_fecha_lis(s)
    if not parsed:
        return ""
    y, m, d = parsed
    return f"{d:02d}-{m:02d}-{y:04d}"


def fecha_api7x(s) -> str:
    """Formato YYYY-MM-DD para API75/API76."""
    parsed = _parse_fecha_lis(s)
    if not parsed:
        return ""
    y, m, d = parsed
    return f"{y:04d}-{m:02d}-{d:02d}"


# ---------------- Carga del mapeo de establecimientos ----------------

class MapeoEstablecimientos:
    """
    Resuelve SUCURSAL LIS → (refes, sisa_corto) del establecimiento derivante.
    Lee mapeos/establecimientos.json: array "establecimientos" con campos
    sucursal_lis, refes, sisa_corto, tipo.  Entradas con sucursal_lis=null se omiten
    (son establecimientos anticipados pero no vistos aún en un TXT).

    tipo="asistencial" / "banco_sangre": resolver() devuelve (refes, sisa_corto).
    tipo="interno": resolver() devuelve None y es_interno() devuelve True — el caso
      se descarta silenciosamente (es tráfico interno del Lab, no un error de mapeo).
    Si la sucursal no está en el índice: resolver() devuelve None y es_interno()
      devuelve False → el llamador emite WARN y cuenta como desconocida.
    """

    def __init__(self, path: Path = ESTABLECIMIENTOS_PATH):
        if not path.exists():
            raise FileNotFoundError(f"No se encuentra el mapeo de establecimientos: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        self._index: dict[str, dict] = {
            str(e["sucursal_lis"]).strip(): e
            for e in data.get("establecimientos", [])
            if e.get("sucursal_lis") is not None
        }

    def es_interno(self, sucursal: str) -> bool:
        """True si la sucursal está catalogada como tipo='interno'."""
        entry = self._index.get(str(sucursal).strip())
        return entry is not None and entry.get("tipo") == "interno"

    def resolver(self, sucursal: str) -> Optional[tuple[str, str]]:
        """
        Devuelve (refes, sisa_corto) si la sucursal está en el mapeo y no es interna.
        Devuelve None en cualquier otro caso — el llamador decide cómo manejarlo.
        """
        entry = self._index.get(str(sucursal).strip())
        if entry and entry.get("tipo") != "interno":
            return str(entry["refes"]), str(entry["sisa_corto"])
        return None


# ---------------- Carga del mapeo clínico ----------------

class MapeoClinico:
    """
    Indexa el clinico.json por (estudio_codigo, poblacion, condicion_vigilancia).

    El matching es por CÓDIGO porque la LIS usa nombres distintos a los
    canónicos del SISA (ej. LIS dice 'SIFILISR2' donde clinico.json dice
    'SIFILIS'; LIS dice 'IGM ANTI VHA' donde clinico.json dice 'HEPATITIS A').

    PROBLEMA CONOCIDO: el LIS reusa el mismo ESTUDIO para un panel de
    diagnóstico clínico y un panel de BANCO DE SANGRE (donantes) sin
    relación entre sí. Confirmado en producción — auditoría ago-2026:
        cod=14  'ANTI HBC'        (NO notificable) vs 'SIFILIS (BCO)'  (notificable)
        cod=18  'BM HIV (BCO)'    (banco, NO es Dengue)  vs clinico.json 'IGM DENGUE'
        cod=3   'ANTI VHC (BCO)'  (banco)                vs clinico.json 'HEPATITIS A'
        cod=4   'AG HBS (BCO)'    (banco)                vs clinico.json 'ANTI VHC'
        cod=5   'ANTI HBC (BCO)'  (banco)                vs clinico.json 'ANTI VIH COMBO AG_AC'
    Sin protección, cada uno de estos noticaría de forma incorrecta un
    resultado de banco como si fuera un caso clínico real (el incidente de
    ago-2026 fue exactamente esto: >180 'BM HIV (BCO)' notificados a SISA
    como Dengue IgM porque el código 018 se castea a 18 == IGM DENGUE).

    Dos capas de protección, ambas aplicadas SIEMPRE (no solo a códigos
    conocidos — cualquier código nuevo con el mismo patrón queda cubierto
    automáticamente):

    1. Simetría banco/diagnóstico (capa general, ver _es_estudio_banco()):
       un ESTUDIODESCRIPCION de banco ('(BCO)', 'BM ...') sólo puede
       matchear contra una entrada de clinico.json que TAMBIÉN sea de
       banco para ese mismo código, y viceversa. Si no coinciden, se
       rechaza el match aunque el código esté "cubierto" en el mapeo.
    2. DISAMBIGUACION_POR_NOMBRE (capa curada, manual): lista de patrones
       adicionales para códigos ambiguos que NO son casos de banco — hoy
       vacía porque la capa 1 ya cubre todos los casos detectados en la
       auditoría, pero queda disponible para el próximo caso raro que no
       siga el patrón banco/diagnóstico.
    """

    # Códigos ambiguos NO cubiertos por la simetría banco/diagnóstico
    # (ver capa 2 arriba). Agregar acá SOLO si aparece una colisión nueva
    # que la capa 1 no detecta — y documentar el caso real, como en el
    # ejemplo de cod=14 que dejamos comentado a modo de referencia.
    DISAMBIGUACION_POR_NOMBRE: dict[int, list[str]] = {
        # 14: ["SIFILIS"],  # ya cubierto por la capa 1 (banco/diagnostico); se deja de ejemplo
    }

    def __init__(self, path: Path = CLINICO_PATH):
        if not path.exists():
            raise FileNotFoundError(f"No se encuentra el mapeo clínico: {path}")
        self._raw = json.loads(path.read_text(encoding="utf-8"))
        self._index: dict[tuple[int, str, str], dict] = {}
        nombres_por_codigo: dict[int, set[str]] = {}
        for entry in self._raw["mapeo"]:
            cod = int(entry["estudio_codigo"])
            key = (
                cod,
                str(entry["poblacion"]).strip().upper().replace(" ", "_"),
                _norm_resultado(entry["condicion_vigilancia"]),
            )
            if key in self._index:
                raise ValueError(f"Clave duplicada en clinico.json: {key}")
            self._index[key] = entry
            nombres_por_codigo.setdefault(cod, set()).add(
                _norm_estudio_nombre(entry["estudio_nombre"])
            )
        # Set de códigos cubiertos (para descartar rápido estudios fuera del mapeo)
        self.codigos_cubiertos: set[int] = set(nombres_por_codigo)

        # Para cada código, ¿clinico.json lo define como panel de banco?
        # Si un código mezcla entradas de banco y de no-banco bajo el mismo
        # número, es una ambigüedad real que no podemos resolver solos —
        # falla fuerte en vez de adivinar en silencio.
        self._codigo_es_banco: dict[int, bool] = {}
        for cod, nombres in nombres_por_codigo.items():
            flags = {_es_estudio_banco(n) for n in nombres}
            if len(flags) > 1:
                raise ValueError(
                    f"clinico.json mezcla estudios de banco y de diagnostico bajo "
                    f"estudio_codigo={cod} ({sorted(nombres)}). Resolvé la ambigüedad "
                    f"a mano antes de continuar (ver MapeoClinico.DISAMBIGUACION_POR_NOMBRE)."
                )
            self._codigo_es_banco[cod] = flags.pop()

    def nombre_lis_es_aceptable(self, estudio_codigo: int, estudio_nombre_lis: str) -> tuple[bool, str]:
        """
        Valida que el ESTUDIODESCRIPCION del LIS sea compatible con lo que
        clinico.json define para ese código. Devuelve (aceptable, motivo);
        motivo queda vacío cuando aceptable=True.
        """
        cod = int(estudio_codigo)
        nombre_norm = _norm_estudio_nombre(estudio_nombre_lis)

        # Capa 1 (general): simetría banco/diagnóstico — ver docstring de la clase.
        lis_es_banco = _es_estudio_banco(nombre_norm)
        codigo_es_banco = self._codigo_es_banco.get(cod, False)
        if lis_es_banco != codigo_es_banco:
            motivo = (
                "estudio de banco de sangre pisando codigo de estudio diagnostico"
                if lis_es_banco else
                "estudio diagnostico pisando codigo reservado a banco de sangre"
            )
            return False, motivo

        # Capa 2 (curada): patrones adicionales para códigos ambiguos que no
        # siguen el patrón banco/diagnóstico.
        patrones = self.DISAMBIGUACION_POR_NOMBRE.get(cod)
        if patrones and not any(p in nombre_norm for p in patrones):
            return False, "no coincide con patron de disambiguacion curado"

        return True, ""

    def resolver(
        self,
        estudio_codigo: int,
        estudio_nombre: str,
        poblacion: str,
        resultado_norm: str,
    ) -> Optional[dict]:
        aceptable, _motivo = self.nombre_lis_es_aceptable(estudio_codigo, estudio_nombre)
        if not aceptable:
            return None
        key = (
            int(estudio_codigo),
            poblacion.strip().upper().replace(" ", "_"),
            resultado_norm.strip().upper(),
        )
        return self._index.get(key)


# ---------------- Pipeline principal ----------------

def cargar_txt(path: Path) -> pd.DataFrame:
    """Lee el TXT del LIS con encoding/separador correctos."""
    return pd.read_csv(path, sep=LIS_SEP, encoding=LIS_ENCODING, dtype=str, keep_default_na=False)


def parsear(
    path: Path | str,
    mapeo: Optional[MapeoClinico] = None,
    mapeo_est: Optional[MapeoEstablecimientos] = None,
) -> tuple[list[CasoNotificable], ResumenParseo]:
    """
    Pipeline completo. Devuelve (casos_notificables, resumen).
    """
    path = Path(path)
    if mapeo is None:
        mapeo = MapeoClinico()
    if mapeo_est is None:
        mapeo_est = MapeoEstablecimientos()

    df = cargar_txt(path)
    resumen = ResumenParseo(total_filas=len(df))

    # 1) ESTADO == 'V'
    df = df[df["ESTADO"].str.strip().str.upper() == "V"].copy()
    resumen.validadas = len(df)

    # 1b) Lookup de VDRL embebido en estudio 7101 (variable SIFILIS VDRLR / cod 609).
    # Para pacientes donde la VDRL no viene como estudio 72 separado sino como
    # sub-variable de la treponémica (lo más común en el LIS), extraemos el
    # resultado VDRL antes de la deduplicación para poder inyectar un caso
    # sintético estudio-72 cuando sea necesario.
    _mask_vdrlr = (df["ESTUDIO"].str.strip() == "7101") & (
        (df["ESTUDIOVARIABLE"].str.strip() == "609")
        | df["VARIABLEDESCRIPCION"].str.contains("VDRLR", case=False, na=False)
    )
    _vdrlr_lookup: dict[tuple[str, str], str] = {
        (str(r["ORDEN"]).strip(), str(r["NUMDOC"]).strip()): str(r["RESULTADO"]).strip()
        for _, r in df[_mask_vdrlr].iterrows()
    }

    # 2) Resultado válido — canonicalizar y filtrar; registrar los descartados para el resumen.
    # _resultado_raw_norm: valor normalizado sin alias (lo que se envía al SISA como "valor").
    # _resultado_canon: forma canónica para matching contra clinico.json.
    df["_resultado_raw_norm"] = df["RESULTADO"].apply(_norm_resultado)
    df["_resultado_canon"] = df["RESULTADO"].apply(_canonicalizar_resultado)
    invalid_df = df[~df["_resultado_canon"].isin(RESULTADOS_VALIDOS)]
    resumen.descartadas_resultado_sucio = len(invalid_df)
    for _, irow in invalid_df.iterrows():
        try:
            cod_r = int(str(irow["ESTUDIO"]).strip())
        except (ValueError, TypeError):
            cod_r = 0
        resumen.resultados_descartados[(cod_r, str(irow["RESULTADO"]).strip())] += 1
    df = df[df["_resultado_canon"].isin(RESULTADOS_VALIDOS)].copy()

    # 3) Deduplicar por (ORDEN, ESTUDIO): cuando hay varias filas (Sífilis/VHC tienen
    #    fila INTERPRETADO + filas extra), conservar la de INTERPRETADO; para estudios
    #    single-row (Chagas) la única fila ya queda seleccionada.
    df["_es_interp"] = df["VARIABLEDESCRIPCION"].str.contains("INTERPRETADO", case=False, na=False).astype(int)
    df = df.sort_values("_es_interp", ascending=False).drop_duplicates(subset=["ORDEN", "ESTUDIO"])
    resumen.interpretadas = len(df)

    casos: list[CasoNotificable] = []
    for idx, row in df.iterrows():
        # Estudio: parseo del código
        try:
            estudio_cod = int(str(row["ESTUDIO"]).strip())
        except (ValueError, TypeError):
            resumen.descartadas_sin_mapeo += 1
            continue

        estudio_nombre_raw = str(row.get("ESTUDIODESCRIPCION", "")).strip()
        # Filtro 1: el código tiene que estar en el mapeo clínico
        if estudio_cod not in mapeo.codigos_cubiertos:
            resumen.descartadas_sin_mapeo += 1
            resumen.estudios_sin_mapeo[(estudio_cod, estudio_nombre_raw)] += 1
            continue
        # Filtro 2: para códigos ambiguos (reusados por LIS entre panel de
        # banco de sangre y estudio diagnostico, ej. cod=14, cod=18), el
        # ESTUDIODESCRIPCION del LIS debe ser compatible con lo que clinico.json
        # define para ese código (ver MapeoClinico.nombre_lis_es_aceptable).
        aceptable, motivo = mapeo.nombre_lis_es_aceptable(estudio_cod, estudio_nombre_raw)
        if not aceptable:
            resumen.descartadas_sin_mapeo += 1
            resumen.descartadas_colision_codigo += 1
            resumen.colisiones_codigo[(estudio_cod, f"{estudio_nombre_raw} [{motivo}]")] += 1
            continue

        # Resultado ya canonicalizado y validado en el paso pandas anterior.
        resultado_norm = row["_resultado_canon"]

        # Población — del más específico al más general; permite fallback a GENERAL
        # para eventos sin estratificación (ej. DENGUE solo tiene GENERAL en clinico.json).
        poblacion_paciente = determinar_poblacion(row["SEXO"], row.get("DIAGNOSTICODESCRIPCION", ""))
        poblacion = poblacion_paciente
        m = None
        for cand in candidatos_poblacion(row["SEXO"], row.get("DIAGNOSTICODESCRIPCION", "")):
            m = mapeo.resolver(estudio_cod, estudio_nombre_raw, cand, resultado_norm)
            if m is not None:
                poblacion = cand
                break
        if not m:
            # El (codigo, nombre) está en el mapeo pero esta combinación
            # específica de población+resultado no se notifica (ej. SIFILIS BCO
            # NO_GESTANTE solo se mapea para REACTIVO; un NO REACTIVO no se notifica).
            resumen.descartadas_sin_mapeo += 1
            resumen.estudios_sin_mapeo[(estudio_cod, f"{estudio_nombre_raw} [{poblacion}/{resultado_norm}]")] += 1
            continue

        resumen.con_mapeo += 1

        # DNI
        numdoc = str(row.get("NUMDOC", "")).strip()
        if not numdoc:
            resumen.descartadas_sin_dni += 1
            continue

        # Establecimiento derivante — obligatorio; sin mapeo el caso no se notifica.
        cod_sucursal = str(row.get("SUCURSAL", "")).strip()
        desc_sucursal = str(row.get("SUCURSALDESCRIPCION", "")).strip()
        if mapeo_est.es_interno(cod_sucursal):
            resumen.descartadas_sucursal_interna += 1
            continue
        est_result = mapeo_est.resolver(cod_sucursal)
        if est_result is None:
            logger.warning(
                "SUCURSAL=%s (%s) no esta en mapeos/establecimientos.json -- caso descartado",
                cod_sucursal, desc_sucursal,
            )
            resumen.descartadas_sucursal_desconocida += 1
            resumen.sucursales_desconocidas[(cod_sucursal, desc_sucursal)] += 1
            continue
        refes_carga, sisa_corto_toma = est_result

        # APENOM
        apellido, nombre = parse_apenom(row.get("APENOM", ""))

        # Fechas
        fnac = fecha_ws400(row.get("FECNAC", ""))
        fpapel = fecha_ws400(row.get("FECHAALTA", ""))
        ftoma = fecha_api7x(row.get("FECHAALTA", ""))   # toma == ingreso al lab; ajustar si hay otro campo
        fres = fecha_api7x(row.get("FECHAHORAVALIDACION", ""))

        # Tipo de documento — TIPDOC en LIS es 'DNI' / 'LE' / 'CI'... solo manejamos DNI por ahora.
        tipdoc_str = str(row.get("TIPDOC", "")).strip().upper()
        tipo_documento = 1 if tipdoc_str in ("DNI", "1", "") else 1  # default DNI

        caso = CasoNotificable(
            orden=str(row.get("ORDEN", "")).strip(),
            sucursal=str(row.get("SUCURSAL", "")).strip(),
            sucursal_descripcion=str(row.get("SUCURSALDESCRIPCION", "")).strip(),
            fila_origen=int(idx),
            apellido=apellido,
            nombre=nombre,
            tipo_documento=tipo_documento,
            numero_documento=numdoc,
            sexo=str(row.get("SEXO", "")).strip().upper() or "M",
            fecha_nacimiento=fnac,
            id_grupo_evento=int(m["ws400"]["idGrupoEvento"]),
            id_evento=int(m["ws400"]["idEvento"]),
            id_clasificacion_manual_caso=int(m["ws400"]["idClasificacionManualCaso"]),
            id_muestra=int(m["api75"]["idMuestra"]),
            id_tipo_muestra=int(m["api75"]["idTipoMuestra"]),
            id_tipo_prueba=int(m["api76"]["idTipoPrueba"]),
            id_prueba=int(m["api76"]["idPrueba"]),
            id_resultado=_resolver_id_resultado(estudio_cod, str(row["_resultado_raw_norm"]), int(m["idResultado"])),
            fecha_papel=fpapel,
            fecha_toma=ftoma,
            fecha_resultado=fres,
            valor_resultado=str(row["_resultado_raw_norm"]),
            estudio_codigo=estudio_cod,
            estudio_nombre=estudio_nombre_raw,
            poblacion=poblacion,
            condicion_vigilancia=resultado_norm,
            entidad_derivante=str(row.get("ENTIDADDERIVANTEDESCRIPCION", "")).strip(),
            refes_carga=refes_carga,
            sisa_corto_toma=sisa_corto_toma,
        )
        # ── Manejo especial estudio 7101 (treponémica con VDRL embebida) ──
        # La treponémica es el estudio primario (siempre se carga si es positiva).
        # Si además trae VDRL reactiva embebida (sub-variable 609 SIFILIS VDRLR),
        # se inyecta un CasoNotificable sintético de estudio 72 (secundario/REUSE)
        # para que main.py lo cargue como segunda determinación vía API76 (± API81).
        if estudio_cod == 7101:
            vdrlr_raw = _vdrlr_lookup.get((str(row["ORDEN"]).strip(), caso.numero_documento), "")
            vdrlr_canon = _canonicalizar_resultado(vdrlr_raw)
            # Si hay VDRL reactiva embebida, inyectar caso sintético estudio-72 (secundario).
            # Si no hay VDRL reactiva, la treponémica se carga igual como "sin especificar".
            if vdrlr_canon == "REACTIVO":
                m_vdrl = None
                pob_vdrl = poblacion
                for cand in candidatos_poblacion(str(row.get("SEXO", "")), str(row.get("DIAGNOSTICODESCRIPCION", ""))):
                    m_vdrl = mapeo.resolver(72, "SIFILIS VDRL", cand, "REACTIVO")
                    if m_vdrl:
                        pob_vdrl = cand
                        break
                if m_vdrl:
                    vdrlr_norm = _norm_resultado(vdrlr_raw)
                    vdrl_caso = CasoNotificable(
                        orden=caso.orden,
                        sucursal=caso.sucursal,
                        sucursal_descripcion=caso.sucursal_descripcion,
                        fila_origen=caso.fila_origen,
                        apellido=caso.apellido,
                        nombre=caso.nombre,
                        tipo_documento=caso.tipo_documento,
                        numero_documento=caso.numero_documento,
                        sexo=caso.sexo,
                        fecha_nacimiento=caso.fecha_nacimiento,
                        id_grupo_evento=int(m_vdrl["ws400"]["idGrupoEvento"]),
                        id_evento=int(m_vdrl["ws400"]["idEvento"]),
                        id_clasificacion_manual_caso=int(m_vdrl["ws400"]["idClasificacionManualCaso"]),
                        id_muestra=int(m_vdrl["api75"]["idMuestra"]),
                        id_tipo_muestra=int(m_vdrl["api75"]["idTipoMuestra"]),
                        id_tipo_prueba=int(m_vdrl["api76"]["idTipoPrueba"]),
                        id_prueba=int(m_vdrl["api76"]["idPrueba"]),
                        id_resultado=_resolver_id_resultado(72, vdrlr_norm, int(m_vdrl["idResultado"])),
                        fecha_papel=caso.fecha_papel,
                        fecha_toma=caso.fecha_toma,
                        fecha_resultado=caso.fecha_resultado,
                        valor_resultado=vdrlr_norm,
                        estudio_codigo=72,
                        estudio_nombre="SIFILIS VDRL",
                        poblacion=pob_vdrl,
                        condicion_vigilancia="REACTIVO",
                        entidad_derivante=caso.entidad_derivante,
                        refes_carga=caso.refes_carga,
                        sisa_corto_toma=caso.sisa_corto_toma,
                    )
                    casos.append(vdrl_caso)
                    resumen.notificables += 1
                    resumen.notificables_por_estudio[(72, "SIFILIS VDRL [embebida en 7101]")] += 1
            # La treponémica se agrega siempre (con o sin VDRL)

        casos.append(caso)
        resumen.notificables += 1
        resumen.notificables_por_estudio[(estudio_cod, caso.estudio_nombre)] += 1

    return casos, resumen


# ---------------- Reporte humano ----------------

def imprimir_resumen(resumen: ResumenParseo, archivo: Path | str) -> None:
    print(f"\n{'='*72}")
    print(f"PARSEO LIS — {archivo}")
    print(f"{'='*72}")
    print(f"Total filas leídas        : {resumen.total_filas}")
    print(f"  → Validadas (ESTADO='V'): {resumen.validadas}")
    print(f"  → Interpretadas         : {resumen.interpretadas}")
    print(f"  → Con mapeo clínico     : {resumen.con_mapeo}")
    print(f"  → NOTIFICABLES (output) : {resumen.notificables}")
    print(f"\nDescartes:")
    print(f"  - Sin mapeo en clinico.json           : {resumen.descartadas_sin_mapeo}")
    print(f"  - Colision banco/diagnostico (seguridad): {resumen.descartadas_colision_codigo}")
    print(f"  - Resultado con formato sucio         : {resumen.descartadas_resultado_sucio}")
    print(f"  - Sin DNI                             : {resumen.descartadas_sin_dni}")
    print(f"  - Sucursales internas (descartadas)   : {resumen.descartadas_sucursal_interna}")
    print(f"  - Sucursales desconocidas (descartadas): {resumen.descartadas_sucursal_desconocida}")

    if resumen.colisiones_codigo:
        print(f"\n{'!'*72}")
        print(f"ALERTA: colisiones de codigo de estudio detectadas y descartadas")
        print(f"(revisar si corresponde agregar el estudio real a clinico.json):")
        print(f"{'!'*72}")
        for (cod, nombre), n in resumen.colisiones_codigo.most_common():
            print(f"  {n:4d}  cod={cod:>5}  {nombre}")

    if resumen.estudios_sin_mapeo:
        print(f"\nTop estudios sin mapeo (descartados silenciosamente):")
        for (cod, nombre), n in resumen.estudios_sin_mapeo.most_common(10):
            print(f"  {n:4d}  cod={cod:>5}  {nombre}")

    if resumen.resultados_descartados:
        print(f"\nResultados descartados por formato sucio:")
        for (cod, valor), n in resumen.resultados_descartados.most_common(10):
            print(f"  {n:4d}  cod={cod:>5}  '{valor}'")

    if resumen.sucursales_desconocidas:
        print(f"\nSucursales sin mapeo (casos descartados):")
        for (cod, desc), n in resumen.sucursales_desconocidas.most_common():
            print(f"  {n:4d}  suc={cod:>5}  {desc}")

    if resumen.notificables_por_estudio:
        print(f"\nNotificables por estudio:")
        for (cod, nombre), n in resumen.notificables_por_estudio.most_common():
            print(f"  {n:4d}  cod={cod:>5}  {nombre}")

    print(f"\n{'='*72}\n")


# ---------------- CLI ----------------

def _main() -> int:
    parser = argparse.ArgumentParser(description="Parser del TXT del LIS - casos notificables SISA.")
    parser.add_argument("archivo", help="Path al TXT exportado por el LIS")
    parser.add_argument("--json", action="store_true", help="Volcar casos a stdout en JSON")
    parser.add_argument("--csv", default=None, help="Guardar casos a un CSV en el path indicado")
    parser.add_argument("--limite", type=int, default=None, help="Mostrar/guardar solo los primeros N casos")
    args = parser.parse_args()

    casos, resumen = parsear(args.archivo)
    imprimir_resumen(resumen, args.archivo)

    if args.limite:
        casos = casos[: args.limite]

    if args.json:
        out = [asdict(c) for c in casos]
        print(json.dumps(out, ensure_ascii=False, indent=2))

    if args.csv:
        df_out = pd.DataFrame([asdict(c) for c in casos])
        df_out.to_csv(args.csv, index=False, encoding="utf-8")
        print(f"CSV guardado: {args.csv} ({len(df_out)} casos)")

    return 0 if casos else 1


if __name__ == "__main__":
    sys.exit(_main())

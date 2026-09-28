"""
geografia_sisa.py — Helper de lookup geográfico para WS400.

Carga los catálogos oficiales SISA de Córdoba y resuelve nombres del LIS
a los códigos (`idProvincia`, `idDepartamento`, `idLocalidad`) que espera WS400.

Catálogos:
- mapeos/catalogos/departamentos_sisa_cordoba.yaml
- mapeos/catalogos/localidades_sisa_cordoba.yaml

Match case-insensitive y sin acentos. Si una localidad no aparece en el
catálogo oficial, se devuelve None y el llamador decide qué hacer
(ej. usar un domicilio default desde settings.json).

Uso rápido:
    >>> from scripts.geografia_sisa import GeografiaSISA
    >>> g = GeografiaSISA.cargar()
    >>> g.resolver_localidad("Río Ceballos", departamento="Colón")
    {'idProvincia': 6, 'idDepartamento': 194, 'idLocalidad': 14021230, 'idPais': 200}

CLI:
    python scripts/geografia_sisa.py "Río Ceballos" --depto Colón
    python scripts/geografia_sisa.py "Villa María"
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    print("ERROR: falta PyYAML. Instalá con: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# Raíz del repo: este archivo vive en sisa-interop/scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = REPO_ROOT / "mapeos" / "catalogos"
DEP_YAML = CATALOG_DIR / "departamentos_sisa_cordoba.yaml"
LOC_YAML = CATALOG_DIR / "localidades_sisa_cordoba.yaml"

ID_PAIS_ARGENTINA = 200


def _norm(s: str) -> str:
    """Lowercase + sin acentos + trim. Para matching robusto."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.strip().lower()


@dataclass(frozen=True)
class Departamento:
    codigo_sisa: str
    nombre: str
    codigo_indec: str


@dataclass(frozen=True)
class Localidad:
    codigo_sisa: str
    nombre: str
    departamento_codigo_sisa: str


class GeografiaSISA:
    """Catálogos cargados en memoria con índices para lookup rápido."""

    def __init__(
        self,
        provincia_codigo_sisa: str,
        provincia_nombre: str,
        departamentos: list[Departamento],
        localidades: list[Localidad],
    ):
        self.provincia_codigo_sisa = provincia_codigo_sisa
        self.provincia_nombre = provincia_nombre
        self.departamentos = departamentos
        self.localidades = localidades

        # Índices
        self._dep_by_codigo: dict[str, Departamento] = {d.codigo_sisa: d for d in departamentos}
        self._dep_by_indec: dict[str, Departamento] = {d.codigo_indec: d for d in departamentos}
        self._dep_by_nombre: dict[str, Departamento] = {_norm(d.nombre): d for d in departamentos}

        # Localidades indexadas por (nombre_normalizado, depto) y solo nombre
        self._loc_by_codigo: dict[str, Localidad] = {l.codigo_sisa: l for l in localidades}
        self._loc_by_nombre_dep: dict[tuple[str, str], Localidad] = {
            (_norm(l.nombre), l.departamento_codigo_sisa): l for l in localidades
        }
        # Para nombres únicos: si una localidad existe en un solo depto, se puede resolver sin depto.
        nombre_count: dict[str, int] = {}
        for l in localidades:
            nombre_count[_norm(l.nombre)] = nombre_count.get(_norm(l.nombre), 0) + 1
        self._loc_by_nombre_unico: dict[str, Localidad] = {
            _norm(l.nombre): l for l in localidades if nombre_count[_norm(l.nombre)] == 1
        }

    # ---------- Carga ----------

    @classmethod
    def cargar(cls, dep_path: Path = DEP_YAML, loc_path: Path = LOC_YAML) -> "GeografiaSISA":
        if not dep_path.exists():
            raise FileNotFoundError(f"No se encuentra catálogo de departamentos: {dep_path}")
        if not loc_path.exists():
            raise FileNotFoundError(f"No se encuentra catálogo de localidades: {loc_path}")

        dep_doc = yaml.safe_load(dep_path.read_text(encoding="utf-8"))
        loc_doc = yaml.safe_load(loc_path.read_text(encoding="utf-8"))

        deps = [
            Departamento(
                codigo_sisa=str(d["codigo_sisa"]),
                nombre=d["nombre"],
                codigo_indec=str(d["codigo_indec"]),
            )
            for d in dep_doc.get("departamentos", [])
        ]
        locs = [
            Localidad(
                codigo_sisa=str(l["codigo_sisa"]),
                nombre=l["nombre"],
                departamento_codigo_sisa=str(l["departamento_codigo_sisa"]),
            )
            for l in loc_doc.get("localidades", [])
        ]
        return cls(
            provincia_codigo_sisa=str(dep_doc.get("provincia_codigo_sisa", "6")),
            provincia_nombre=str(dep_doc.get("provincia_nombre", "Córdoba")),
            departamentos=deps,
            localidades=locs,
        )

    # ---------- Lookups ----------

    def departamento_por_nombre(self, nombre: str) -> Departamento | None:
        return self._dep_by_nombre.get(_norm(nombre))

    def departamento_por_indec(self, codigo_indec: str) -> Departamento | None:
        return self._dep_by_indec.get(str(codigo_indec))

    def departamento_por_sisa(self, codigo_sisa: str | int) -> Departamento | None:
        return self._dep_by_codigo.get(str(codigo_sisa))

    def localidad_por_codigo(self, codigo_sisa: str) -> Localidad | None:
        return self._loc_by_codigo.get(str(codigo_sisa))

    def localidad_por_nombre(
        self, nombre: str, departamento: str | None = None
    ) -> Localidad | None:
        """
        Busca una localidad por nombre. Si se pasa `departamento` (nombre o
        código SISA), lo usa para desambiguar. Si no se pasa y el nombre
        es único en toda la provincia, igual lo resuelve.
        """
        norm_nombre = _norm(nombre)
        if departamento:
            dep = (
                self.departamento_por_sisa(departamento)
                or self.departamento_por_nombre(departamento)
                or self.departamento_por_indec(departamento)
            )
            if dep:
                return self._loc_by_nombre_dep.get((norm_nombre, dep.codigo_sisa))
            return None
        return self._loc_by_nombre_unico.get(norm_nombre)

    def resolver_localidad(
        self, nombre: str, departamento: str | None = None
    ) -> dict | None:
        """
        Devuelve el dict listo para `domicilio` del payload WS400, o None si
        no se puede resolver.
        """
        loc = self.localidad_por_nombre(nombre, departamento)
        if not loc:
            return None
        dep = self._dep_by_codigo[loc.departamento_codigo_sisa]
        return {
            "idProvincia": int(self.provincia_codigo_sisa),
            "idDepartamento": int(dep.codigo_sisa),
            "idLocalidad": int(loc.codigo_sisa) if loc.codigo_sisa.isdigit() else loc.codigo_sisa,
            "idPais": ID_PAIS_ARGENTINA,
            "_meta": {
                "provincia_nombre": self.provincia_nombre,
                "departamento_nombre": dep.nombre,
                "localidad_nombre": loc.nombre,
            },
        }


# ---------- CLI ----------

def _main() -> int:
    parser = argparse.ArgumentParser(description="Lookup geográfico SISA Córdoba.")
    parser.add_argument("localidad", help="Nombre de la localidad")
    parser.add_argument("--depto", "--departamento", default=None, help="Departamento (opcional)")
    parser.add_argument("--json", action="store_true", help="Salida en JSON")
    args = parser.parse_args()

    geo = GeografiaSISA.cargar()
    res = geo.resolver_localidad(args.localidad, args.depto)
    if not res:
        print(
            f"NO ENCONTRADO: localidad='{args.localidad}' depto='{args.depto}'.\n"
            "Probá pasando el departamento explícito con --depto, "
            "o revisá el catálogo en snvs-notificador/config/catalogos/.",
            file=sys.stderr,
        )
        return 1

    if args.json:
        # Sacamos _meta para no contaminar JSON consumido por otros scripts
        meta = res.pop("_meta")
        print(json.dumps({"domicilio": res, "meta": meta}, ensure_ascii=False, indent=2))
    else:
        meta = res["_meta"]
        print(f"Provincia      : {meta['provincia_nombre']}  (idProvincia={res['idProvincia']})")
        print(f"Departamento   : {meta['departamento_nombre']}  (idDepartamento={res['idDepartamento']})")
        print(f"Localidad      : {meta['localidad_nombre']}  (idLocalidad={res['idLocalidad']})")
        print(f"País           : Argentina  (idPais={res['idPais']})")
    return 0


if __name__ == "__main__":
    sys.exit(_main())

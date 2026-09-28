# CONTEXTO DEL PROYECTO: Interoperabilidad SISA - Laboratorio Central de Virología Córdoba

## 1. DESCRIPCIÓN GENERAL

Este proyecto automatiza la notificación de casos de Enfermedades de Notificación Obligatoria (ENO) al **SISA (Sistema Integrado de Información Sanitaria Argentino)**, consumiendo la exportación diaria del LIS (Sistema de información de laboratorio) del Laboratorio Central de Virología de la Provincia de Córdoba.

El sistema reemplaza un proveedor externo que opera con problemas de timing, costos y dependencia. La solución corre **localmente** en las PCs del Laboratorio Central (Windows).

---

## 2. ARQUITECTURA DEL FLUJO

Para cada caso notificable se ejecutan **3 llamadas API en secuencia obligatoria**:

```
LIS TXT → parser → filtro notificables → por cada caso:
    1. WS400  → crea caso nominal → devuelve id_caso
    2. API75  → registra muestra → devuelve id_muestra  (usa id_caso)
    3. API76  → informa resultado  (usa id_muestra)
```

Si cualquier paso falla, el flujo se detiene para ese caso y se loguea el error.

---

## 3. ESTRUCTURA DEL PROYECTO

```
sisa-interop/
├── config/
│   ├── credentials.json        # APP_ID y APP_KEY por servicio
│   └── settings.json           # REFES, entorno (qa/prod), paths
├── mapeos/
│   ├── clinico.json            # Mapeo ESTUDIO+POBLACIÓN → IDs SISA
│   ├── establecimientos.json   # SUCURSAL → REFES + ID_ORIGEN
│   └── resultados.json         # Texto resultado → idResultado SISA
├── scripts/
│   ├── smoke_test.py           # PRIMERA TAREA: prueba hardcodeada
│   ├── parser_lis.py           # Lee y filtra el TXT del LIS
│   ├── ws400.py                # Módulo WS400
│   ├── api75.py                # Módulo API75
│   └── api76.py                # Módulo API76
├── logs/
│   └── (generados automáticamente con fecha)
├── data/
│   └── ejemplo_lis.txt         # Archivo de muestra del LIS
├── main.py                     # Orquestador principal
└── README.md
```

---

## 4. CREDENCIALES Y ENDPOINTS

### Credenciales de PRODUCCIÓN (ya verificadas y funcionales)

```json
{
  "WS400": {
    "APP_ID": "049fedb8",
    "APP_KEY": "a48ee247b7f45c54d56576d18825e5ac"
  },
  "API75": {
    "APP_ID": "58d0467b",
    "APP_KEY": "0052e382de8ac55469a5b17d78d68d39"
  },
  "API76": {
    "APP_ID": "a7bb9a90",
    "APP_KEY": "e82a937f5be5050ed05f48d26acda636"
  }
}
```

### Endpoints

```json
{
  "produccion": {
    "WS400": "https://apisalud.msal.gob.ar/snvsCasoNominal/v2/snvsCasoNominal",
    "API75": "https://apisalud.msal.gob.ar/snvsLaboratoriosMuestra/v1/eventoMuestras",
    "API76": "https://apisalud.msal.gob.ar/snvsLaboratorios/v1/pruebaMuestras"
  },
  "qa": {
    "WS400": "https://ws400-qa.sisa.msal.gov.ar/snvsCasoNominal/v2/snvsCasoNominal",
    "API75": "https://apisalud-qa.msal.gob.ar/snvsLaboratoriosMuestra/v1/eventoMuestras",
    "API76": "https://apisalud-qa.msal.gob.ar/snvsLaboratorios/v1/pruebaMuestras"
  }
}
```

### Establecimientos: TRES roles distintos por caso

Cada caso involucra hasta **tres establecimientos**, no uno solo. Es la causa #2 de fallas/errores conceptuales después del nomenclador geográfico:

| Rol | API y campo | Quién es | Fuente |
|---|---|---|---|
| **DERIVANTE / Carga** | WS400 → `idEstablecimientoCarga` | El efector que **abrió el caso** y derivó la muestra al Lab Central | `mapeos/establecimientos.json` (lookup por `SUCURSAL` del LIS) |
| **DERIVANTE / Toma** | API75 → `idEstablecimientoToma` | Mismo efector derivante (no Lab Central) | `mapeos/establecimientos.json` (lookup por `SUCURSAL` del LIS) |
| **DIAGNÓSTICO** | API76 → `idEstablecimiento` | El laboratorio que hizo la determinación → **siempre Lab Central de Virología** | `config/settings.json` (`id_interno_sisa`) |

> **Lo que cambió respecto del modelo viejo:** durante el smoke test usábamos el Lab Central como `idEstablecimientoCarga` y `idEstablecimientoToma`. Esto era técnicamente válido (el SISA aceptaba) pero clínicamente incorrecto: los casos quedaban registrados en SNVS como abiertos por Lab Central cuando en realidad los abrió el hospital derivante. El parser ahora resuelve la sucursal del LIS contra `mapeos/establecimientos.json` y usa los códigos correctos por caso.

#### Cada establecimiento tiene DOS códigos distintos

Mezclarlos hace fallar la llamada con `DataIntegrityViolationException` genérico (sin pista de qué campo).

| Código | Tipo | Longitud | Va en |
|---|---|---|---|
| `refes` | RENAES / Registro Federal de Establecimientos de Salud | 14 dígitos | **WS400** → `idEstablecimientoCarga` |
| `sisa_corto` | Código Interno SISA | ~6 dígitos | **API75** → `idEstablecimientoToma`, **API76** → `idEstablecimiento` |

Para el Lab Central de Virología: `refes=51140142133784`, `sisa_corto=108202`.

#### Convención de bancos de sangre en el LIS

Los bancos de sangre de los hospitales públicos de Córdoba **comparten establecimiento físico (mismo REFES) que el hospital madre** pero el evento clínico SISA es distinto: por ejemplo, una sífilis reactiva detectada en banco de sangre se notifica como **"Sífilis en banco de sangre"** y NO como "Sífilis No Gestante" o "Gestante".

El LIS los identifica por convención de naming en `SUCURSALDESCRIPCION`:
- Empieza con un punto (`.`)
- Tiene `:` en el medio
- Ej.: `.ALTA GRACIA: H. ARTURO ILLIA` (sucursal 710 = banco de sangre del Hospital Arturo Illia, sucursal 5).

`mapeos/establecimientos.json` los marca con `tipo: "banco_sangre"` y `sucursal_principal` apunta a la sucursal del hospital madre. El parser y el `clinico.json` deben tener una **dimensión adicional de ámbito** (asistencial vs banco_sangre) para rutear al evento SISA correcto.

> **Estado actual:** El catálogo de establecimientos ya distingue ambos tipos. El `clinico.json` todavía NO tiene la dimensión "ámbito" — sólo modela asistencial. Cuando llegue el primer caso de banco de sangre vamos a necesitar los IDs SISA del evento "Sífilis en banco de sangre" (idGrupoEvento, idEvento, idClasificacionManualCaso, idResultado, etc.) y extender el clinico.json.

#### Catálogos relacionados

- `mapeos/establecimientos.json` → mapeo operativo SUCURSAL del LIS → REFES + sisa_corto + tipo.
- `mapeos/catalogos/establecimientos_cordoba_oficial.json` → 3.727 establecimientos de Córdoba del listado nacional REFES (fuente de verdad para nuevas altas). Generado a partir de `listadoCompleto_sisa_con_CodREFES_y_Codigo interno.xlsx`.

---

## 4.1 NOMENCLADOR GEOGRÁFICO SISA (catálogo oficial, validado contra producción)

**SISA NO usa INDEC para provincia ni departamento.** Usa un **nomenclador propio**. El campo `idLocalidad` también usa formato SISA (NO los códigos INDEC de 10 dígitos del catálogo INDEC tradicional). Esto fue verificado contra producción: cualquier código INDEC tipo `14`/`14014`/`1401401003` se rechaza con `"id Departamento inexistente."` / `"El id no es un codigo valido"`.

| Campo | Nomenclador | Ejemplo Córdoba | Formato |
|---|---|---|---|
| `idProvincia` | SISA propio | `6` (Córdoba) | 1–2 dígitos |
| `idDepartamento` | SISA propio | `194` (Colón) | 3 dígitos |
| `idLocalidad` | SISA propio (no INDEC clásico) | `14021230` (Río Ceballos) | **8 dígitos** (algunos registros BAHRA modernos: 10 dígitos `91…`) |
| `idPais` | SISA | `200` (Argentina) | |

### Catálogos oficiales (en el repo)
A partir del 27-04-2026 quedan en `snvs-notificador/config/catalogos/`:
- `departamentos_sisa_cordoba.yaml` — 26 departamentos con `codigo_sisa` + `codigo_indec` para crosswalk.
- `localidades_sisa_cordoba.yaml` — 1616 localidades con `codigo_sisa` (8 dígitos) + `departamento_codigo_sisa`.

### Departamentos SISA de Córdoba (los 26 — catálogo oficial)

| Cód. SISA | Departamento | Cód. INDEC |
|---|---|---|
| `192` | Calamuchita | `14007` |
| `193` | Capital | `14014` |
| `194` | Colón | `14021` |
| `195` | Cruz del Eje | `14028` |
| `196` | General Roca | `14035` |
| `197` | General San Martín | `14042` |
| `198` | Ischilín | `14049` |
| `199` | Juárez Celman | `14056` |
| `200` | Marcos Juárez | `14063` |
| `201` | Minas | `14070` |
| `202` | Pocho | `14077` |
| `203` | Presidente Roque Sáenz Peña | `14084` |
| `204` | Punilla | `14091` |
| `205` | Río Cuarto | `14098` |
| `206` | Río Primero | `14105` |
| `207` | Río Seco | `14112` |
| `208` | Río Segundo | `14119` |
| `209` | San Alberto | `14126` |
| `210` | San Javier | `14133` |
| `211` | San Justo | `14140` |
| `212` | Santa María | `14147` |
| `213` | Sobremonte | `14154` |
| `214` | Tercero Arriba | `14161` |
| `215` | Totoral | `14168` |
| `216` | Tulumba | `14175` |
| `217` | Unión | `14182` |

### Localidades — extracto validado (8 dígitos)

| Localidad | `idLocalidad` SISA | Departamento |
|---|---|---|
| Río Ceballos | `14021230` | Colón (194) |
| Unquillo | `14021280` | Colón (194) |
| Córdoba (capital) | `14014010` | Capital (193) |
| La Calera | `14021360` | Colón (194) |
| Alta Gracia | `14147010` | Santa María (212) |

> El catálogo completo (1616 localidades) está en `localidades_sisa_cordoba.yaml`.

### YAML viejo vs catálogo oficial
El archivo `snvs-notificador/config/catalogos/geografia_desde_sucursales.yaml` (heredado del proveedor anterior) tiene **inconsistencias** detectadas en la auditoría del 27-04-2026:
- **Provincia:** usa `'14'` (INDEC) en vez de `'6'` (SISA).
- **Departamentos:** los 20 entries usan códigos INDEC de 5 dígitos (`14014`, `14021`, …) en vez de los códigos SISA (`193`, `194`, …).
- **Localidades:** 27/29 con formato correcto de 8 dígitos. **2 con formato roto de 10 dígitos**: Córdoba (`1401401003` → debería ser `14014010`), La Calera (`1402115002` → debería ser `14021360`).

Tratar el YAML viejo como referencia histórica únicamente. Los catálogos oficiales `departamentos_sisa_cordoba.yaml` y `localidades_sisa_cordoba.yaml` son la fuente de verdad para el código nuevo.

### Cómo se valida el domicilio en WS400
WS400 hace un lookup contra **RENAPER** por DNI para resolver los datos del paciente. Aún así, el bloque `domicilio` que enviamos **se valida contra el nomenclador SISA** — no se ignora ni se reemplaza por el de RENAPER. Por eso los tres códigos (`idProvincia`, `idDepartamento`, `idLocalidad`) tienen que ser válidos en SISA para que el WS400 pase.

---

## 5. FORMATO DEL ARCHIVO TXT DEL LIS

### Especificaciones técnicas
- **Separador:** TAB (`\t`)
- **Encoding:** latin1 (ISO-8859-1)
- **Primera fila:** encabezados
- **Registros:** cada fila es una determinación individual de una orden

### Columnas relevantes (de las 56 totales)

| Columna | Descripción | Ejemplo |
|---|---|---|
| `SUCURSAL` | Código numérico de sucursal | `5` |
| `SUCURSALDESCRIPCION` | Nombre de la sucursal derivante | `ALTA GRACIA` |
| `ORDEN` | Número de orden del LIS | `121981` |
| `NUMDOC` | DNI del paciente | `23636390` |
| `TIPDOC` | Tipo de documento | `DNI` |
| `APENOM` | Apellido y nombre | `VIERA ELINA PAOLA` |
| `FECNAC` | Fecha de nacimiento | `16/1/1974` |
| `SEXO` | Sexo (`F`/`M`) | `F` |
| `FECHAALTA` | Fecha/hora de ingreso de orden | `20/4/2026 10:45:00` |
| `ESTUDIO` | Código numérico del estudio | `527` |
| `ESTUDIODESCRIPCION` | Nombre del estudio | `FLUA-FLUB-SARSCOV2-OVR` |
| `ESTUDIOVARIABLE` | Código de la variable/determinación | `514` |
| `VARIABLEDESCRIPCION` | Nombre de la variable | `INFLUENZA A MULTIPLEX` |
| `RESULTADO` | Resultado de la determinación | `NO DETECTABLE` |
| `ESTADO` | Estado del resultado (`V`=Validado) | `V` |
| `FECHAHORAVALIDACION` | Fecha/hora de validación | `20/4/2026 16:42:26` |
| `TIPOFISIOLOGICODESCRIPCION` | Indica si es EMBARAZADA u otro | `EMBARAZADA` / `CONTROL` / `NORMAL` |
| `ENTIDAD` | Nombre del laboratorio central | `LABORATORIO CENTRAL DE VIROLOGIA CORDOBA` |

### Lógica de filtrado para identificar notificables

```python
# Paso 1: Solo validados
df = df[df['ESTADO'] == 'V']

# Paso 2: Solo filas con VARIABLEDESCRIPCION que contenga "INTERPRETADO"
# (las demás son valores numéricos crudos, no el resultado final)
df = df[df['VARIABLEDESCRIPCION'].str.contains('INTERPRETADO', na=False)]

# Paso 3: Solo estudios que tienen mapeo en clinico.json
# (descartar estudios no notificables como ANTI HBC, etc.)
df = df[df['ESTUDIO'].isin(ESTUDIOS_NOTIFICABLES)]

# Paso 4: Solo resultados positivos/reactivos/detectables (notificables)
# Los negativos/no reactivos NO se notifican al SISA
RESULTADOS_NOTIFICABLES = ['REACTIVO', 'POSITIVO', 'DETECTABLE', 'AMPLIFICACION POSITIVA']
```

### Determinación de POBLACIÓN (para el mapeo clínico)
La columna `TIPOFISIOLOGICODESCRIPCION` determina la población:
- `EMBARAZADA` → `GESTANTE`
- Todo lo demás → mirar el sexo:
  - `F` (no embarazada) → `NO GESTANTE`  
  - `M` → `GENERAL`
  - Estudios sin distinción de población → `GENERAL`

---

## 6. MAPEO CLÍNICO COMPLETO (clinico.json)

La clave de búsqueda es la combinación `ESTUDIO` (código numérico) + `POBLACIÓN`.

```json
{
  "mapeo": [
    {
      "estudio_codigo": 67,
      "estudio_nombre": "AC ANTI TRYPANOSOMA CRUZI ELISA",
      "poblacion": "NO_GESTANTE",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 89, "idEvento": 188, "idGrupoEvento": 120},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 569, "idTipoPrueba": 468},
      "idResultado": 1
    },
    {
      "estudio_codigo": 67,
      "estudio_nombre": "AC ANTI TRYPANOSOMA CRUZI ELISA",
      "poblacion": "GESTANTE",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 82, "idEvento": 108, "idGrupoEvento": 120},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 569, "idTipoPrueba": 468},
      "idResultado": 1
    },
    {
      "estudio_codigo": 49,
      "estudio_nombre": "DENGUE",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NO REACTIVO",
      "ws400": {"idClasificacionManualCaso": 104, "idEvento": 109, "idGrupoEvento": 107},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 583, "idTipoPrueba": 383},
      "idResultado": 508
    },
    {
      "estudio_codigo": 49,
      "estudio_nombre": "DENGUE",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 174, "idEvento": 109, "idGrupoEvento": 107},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 583, "idTipoPrueba": 383},
      "idResultado": 109
    },
    {
      "estudio_codigo": 522,
      "estudio_nombre": "DETECCION CUALITATIVA PCR RNA",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "DETECTABLE",
      "ws400": {"idClasificacionManualCaso": 895, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 294, "idTipoMuestra": 4},
      "api76": {"idPrueba": 247, "idTipoPrueba": 228},
      "idResultado": 3
    },
    {
      "estudio_codigo": 522,
      "estudio_nombre": "DETECCION CUALITATIVA PCR RNA",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NO DETECTABLE",
      "ws400": {"idClasificacionManualCaso": 903, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 294, "idTipoMuestra": 4},
      "api76": {"idPrueba": 247, "idTipoPrueba": 228},
      "idResultado": 4
    },
    {
      "estudio_codigo": 452,
      "estudio_nombre": "FLUA-FLUB-SARSCOV2 (COBAS 5800)",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "DETECTABLE",
      "ws400": {"idClasificacionManualCaso": 895, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 294, "idTipoMuestra": 4},
      "api76": {"idPrueba": 247, "idTipoPrueba": 228},
      "idResultado": 3
    },
    {
      "estudio_codigo": 452,
      "estudio_nombre": "FLUA-FLUB-SARSCOV2 (COBAS 5800)",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NO DETECTABLE",
      "ws400": {"idClasificacionManualCaso": 903, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 294, "idTipoMuestra": 4},
      "api76": {"idPrueba": 247, "idTipoPrueba": 228},
      "idResultado": 4
    },
    {
      "estudio_codigo": 3,
      "estudio_nombre": "HEPATITIS A",
      "poblacion": "NO_GESTANTE",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 815, "idEvento": 1, "idGrupoEvento": 1},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 4, "idTipoPrueba": 2},
      "idResultado": 1
    },
    {
      "estudio_codigo": 3,
      "estudio_nombre": "HEPATITIS A",
      "poblacion": "GESTANTE",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 274, "idEvento": 1, "idGrupoEvento": 1},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 4, "idTipoPrueba": 2},
      "idResultado": 1
    },
    {
      "estudio_codigo": 202,
      "estudio_nombre": "HEPATITIS B GENERAL",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 278, "idEvento": 2, "idGrupoEvento": 1},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 714, "idTipoPrueba": 10},
      "idResultado": 1
    },
    {
      "estudio_codigo": 142,
      "estudio_nombre": "AG HBS CUALITATIVO",
      "poblacion": "NO_GESTANTE",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 278, "idEvento": 2, "idGrupoEvento": 1},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 19, "idTipoPrueba": 10},
      "idResultado": 1
    },
    {
      "estudio_codigo": 142,
      "estudio_nombre": "AG HBS CUALITATIVO",
      "poblacion": "GESTANTE",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 278, "idEvento": 286, "idGrupoEvento": 1},
      "api75": {"idMuestra": 238, "idTipoMuestra": 3},
      "api76": {"idPrueba": 19, "idTipoPrueba": 10},
      "idResultado": 1
    },
    {
      "estudio_codigo": 479,
      "estudio_nombre": "HEPATITIS C POSITIVO",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 286, "idEvento": 3, "idGrupoEvento": 1},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 715, "idTipoPrueba": 14},
      "idResultado": 1
    },
    {
      "estudio_codigo": 4,
      "estudio_nombre": "ANTI VHC",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 286, "idEvento": 3, "idGrupoEvento": 1},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 28, "idTipoPrueba": 14},
      "idResultado": 1
    },
    {
      "estudio_codigo": 18,
      "estudio_nombre": "IGM DENGUE",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NO REACTIVO",
      "ws400": {"idClasificacionManualCaso": 104, "idEvento": 109, "idGrupoEvento": 107},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 577, "idTipoPrueba": 484},
      "idResultado": 508
    },
    {
      "estudio_codigo": 18,
      "estudio_nombre": "IGM DENGUE",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 174, "idEvento": 109, "idGrupoEvento": 107},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 577, "idTipoPrueba": 484},
      "idResultado": 109
    },
    {
      "estudio_codigo": 35,
      "estudio_nombre": "INFLUENZA A IF",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NEGATIVO",
      "ws400": {"idClasificacionManualCaso": 903, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 103, "idTipoMuestra": 4},
      "api76": {"idPrueba": 1192, "idTipoPrueba": 792},
      "idResultado": 508
    },
    {
      "estudio_codigo": 35,
      "estudio_nombre": "INFLUENZA A IF",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 895, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 103, "idTipoMuestra": 4},
      "api76": {"idPrueba": 235, "idTipoPrueba": 195},
      "idResultado": 109
    },
    {
      "estudio_codigo": 203,
      "estudio_nombre": "MODULAR INFLUENZA A",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "DETECTABLE",
      "ws400": {"idClasificacionManualCaso": 895, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 294, "idTipoMuestra": 4},
      "api76": {"idPrueba": 247, "idTipoPrueba": 228},
      "idResultado": 3
    },
    {
      "estudio_codigo": 203,
      "estudio_nombre": "MODULAR INFLUENZA A",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NO DETECTABLE",
      "ws400": {"idClasificacionManualCaso": 903, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 294, "idTipoMuestra": 4},
      "api76": {"idPrueba": 247, "idTipoPrueba": 228},
      "idResultado": 4
    },
    {
      "estudio_codigo": 236,
      "estudio_nombre": "MOLECULAR DENGUE",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "DETECTABLE",
      "ws400": {"idClasificacionManualCaso": 104, "idEvento": 109, "idGrupoEvento": 107},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 958, "idTipoPrueba": 471},
      "idResultado": 109
    },
    {
      "estudio_codigo": 236,
      "estudio_nombre": "MOLECULAR DENGUE",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NO DETECTABLE",
      "ws400": {"idClasificacionManualCaso": 104, "idEvento": 100, "idGrupoEvento": 107},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 958, "idTipoPrueba": 471},
      "idResultado": 508
    },
    {
      "estudio_codigo": 194,
      "estudio_nombre": "RUBEOLA",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NEGATIVO",
      "ws400": {"idClasificacionManualCaso": 815, "idEvento": 164, "idGrupoEvento": 115},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 515, "idTipoPrueba": 440},
      "idResultado": 508
    },
    {
      "estudio_codigo": 194,
      "estudio_nombre": "RUBEOLA",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 197, "idEvento": 164, "idGrupoEvento": 115},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 515, "idTipoPrueba": 440},
      "idResultado": 109
    },
    {
      "estudio_codigo": 175,
      "estudio_nombre": "SARAMPION",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NEGATIVO",
      "ws400": {"idClasificacionManualCaso": 815, "idEvento": 164, "idGrupoEvento": 115},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 521, "idTipoPrueba": 441},
      "idResultado": 2
    },
    {
      "estudio_codigo": 175,
      "estudio_nombre": "SARAMPION",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 198, "idEvento": 164, "idGrupoEvento": 115},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 521, "idTipoPrueba": 441},
      "idResultado": 1
    },
    {
      "estudio_codigo": 201,
      "estudio_nombre": "SIFILIS GENERAL",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 743, "idEvento": 193, "idGrupoEvento": 109},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 1010, "idTipoPrueba": 143},
      "idResultado": 109
    },
    {
      "estudio_codigo": 7101,
      "estudio_nombre": "SIFILIS",
      "poblacion": "NO_GESTANTE",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 743, "idEvento": 193, "idGrupoEvento": 109},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 876, "idTipoPrueba": 634},
      "idResultado": 109
    },
    {
      "estudio_codigo": 14,
      "estudio_nombre": "SIFILIS BCO",
      "poblacion": "NO_GESTANTE",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 743, "idEvento": 193, "idGrupoEvento": 135},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 876, "idTipoPrueba": 634},
      "idResultado": 109
    },
    {
      "estudio_codigo": 7101,
      "estudio_nombre": "SIFILIS",
      "poblacion": "GESTANTE",
      "condicion_vigilancia": "REACTIVO",
      "ws400": {"idClasificacionManualCaso": 153, "idEvento": 115, "idGrupoEvento": 109},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 876, "idTipoPrueba": 634},
      "idResultado": 109
    },
    {
      "estudio_codigo": 200,
      "estudio_nombre": "VIH GENERAL",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 5, "idEvento": 105, "idGrupoEvento": 103},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 116, "idTipoPrueba": 123},
      "idResultado": 109
    },
    {
      "estudio_codigo": 5,
      "estudio_nombre": "ANTI VIH COMBO AG_AC",
      "poblacion": "NO_GESTANTE",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 5, "idEvento": 105, "idGrupoEvento": 103},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 114, "idTipoPrueba": 123},
      "idResultado": 109
    },
    {
      "estudio_codigo": 5,
      "estudio_nombre": "ANTI VIH COMBO AG_AC",
      "poblacion": "GESTANTE",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 5, "idEvento": 117, "idGrupoEvento": 103},
      "api75": {"idMuestra": 1, "idTipoMuestra": 3},
      "api76": {"idPrueba": 114, "idTipoPrueba": 123},
      "idResultado": 109
    },
    {
      "estudio_codigo": 37,
      "estudio_nombre": "VIRUS RESPIRATORIO SINCITIAL",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "NEGATIVO",
      "ws400": {"idClasificacionManualCaso": 903, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 103, "idTipoMuestra": 4},
      "api76": {"idPrueba": 1192, "idTipoPrueba": 792},
      "idResultado": 508
    },
    {
      "estudio_codigo": 37,
      "estudio_nombre": "VIRUS RESPIRATORIO SINCITIAL",
      "poblacion": "GENERAL",
      "condicion_vigilancia": "POSITIVO",
      "ws400": {"idClasificacionManualCaso": 339, "idEvento": 330, "idGrupoEvento": 113},
      "api75": {"idMuestra": 103, "idTipoMuestra": 4},
      "api76": {"idPrueba": 238, "idTipoPrueba": 193},
      "idResultado": 109
    }
  ]
}
```

---

## 7. ESTUDIOS DEL LIS QUE **NO** SE NOTIFICAN AL SISA

Los siguientes estudios aparecen en el TXT pero **no tienen mapeo SISA** y deben ser ignorados:

| Estudio código | Nombre |
|---|---|
| 14 | ANTI HBC (sin mapeo, es marcador no notificable) |
| 527 | FLUA-FLUB-SARSCOV2-OVR (variante no mapeada) |
| 68 | AC ANTI TRYPANOSOMA CRUZI HAI |
| 57/58 | Variables crudas de Chagas HAI |

> **IMPORTANTE:** El archivo TXT contiene múltiples filas por orden/paciente. La mayoría son determinaciones intermedias (valores numéricos, fechas). Solo las filas donde `VARIABLEDESCRIPCION` contiene `"INTERPRETADO"` representan el resultado final interpretado.

---

## 8. ESTRUCTURA DE LOS PAYLOADS API

### WS400 - Crear caso nominal

```json
{
  "ciudadano": {
    "apellido": "APELLIDO",
    "nombre": "ND",
    "tipoDocumento": 1,
    "numeroDocumento": "22011967",
    "sexo": "M",
    "fechaNacimiento": "22-10-1972",
    "paisEmisionTipoDocumento": null,
    "seDeclaraPuebloIndigena": "No",
    "domicilio": {
      "calle": "SIN DATO",
      "idDepartamento": 194,
      "idLocalidad": 14021230,
      "idProvincia": 6,
      "idPais": 200
    },
    "telefono": null,
    "mail": null,
    "personaACargo": {
      "tipoDocumento": null,
      "numeroDocumento": null,
      "vinculo": null
    }
  },
  "eventoCasoNominal": {
    "idGrupoEvento": 109,
    "idEvento": 193,
    "idClasificacionManualCaso": 743,
    "fechaPapel": "20-04-2026",
    "idEstablecimientoCarga": "51140142133784"
  }
}
```

**Respuesta exitosa:** `{"status": "OK", "id_caso": 39050581}`

**Notas (validadas contra producción):**
- `fechaNacimiento` y `fechaPapel` en formato `DD-MM-YYYY`
- `tipoDocumento: 1` = DNI
- **`ciudadano.nombre` requiere mínimo 2 caracteres.** Si el LIS no lo expone separado del apellido (caso APENOM anonimizado), usar placeholder `"ND"` — RENAPER hace el match real por DNI igual.
- **`ciudadano.apellido` requiere mínimo 2 caracteres.** Mandar el APENOM completo del LIS está OK.
- **`domicilio.idProvincia` / `idDepartamento`** usan **nomenclador SISA propio**, no INDEC (ver sección 4.1).
- **`domicilio.idLocalidad`** usa **INDEC**.
- **`idEstablecimientoCarga`** = `codigo_refes` largo (14 dígitos), NO el `codigo_sisa` corto.
- Si el caso ya existe en SNVS, la respuesta es 400 con `description: "...ID_SNVS_EVENTO_CASO: <id>"` y campo `id_caso: <id>` — capturarlo y reutilizar.

### API75 - Registrar muestra

```json
{
  "adecuada": true,
  "aislamiento": false,
  "fechaToma": "2026-04-20",
  "idEstablecimientoToma": "108202",
  "idEventoCaso": 39050581,
  "idMuestra": 1,
  "idtipoMuestra": 3,
  "muestra": true
}
```

**Respuesta exitosa:**
```json
{
  "id": 41317147,
  "idEventoCaso": 39050581,
  "idMuestra": 1,
  "idtipoMuestra": 3,
  "fechaToma": "2026-04-20",
  "idEstablecimientoToma": 108202,
  "muestra": true,
  "aislamiento": false,
  "adecuada": true
}
```

**Notas (validadas contra producción):**
- `fechaToma` en formato `YYYY-MM-DD`.
- **`idEstablecimientoToma`** = `codigo_sisa` corto (ej. `"108202"`), NO el REFES largo. Si se manda el REFES, falla con `DataIntegrityViolationException`.
- **El campo se llama `idtipoMuestra` con `t` minúscula** (no `idTipoMuestra`). Capricho del API.
- **El ID nuevo del evento-muestra está en el campo `id`** de la respuesta — NO en `idMuestra` (que es el TIPO que enviamos) ni en `idEventoMuestra`.
- **Comportamiento al reintentar:** si la muestra ya existe, devuelve `400` con texto plano `"El registro a crear ya existe"` y **NO retorna el id existente**. Diferencia con WS400 que sí lo devuelve.

### API76 - Informar resultado

```json
{
  "derivada": true,
  "fechaEmisionResultado": "2026-04-22",
  "fechaRecepcion": "2026-04-22",
  "idDerivacion": null,
  "idEstablecimiento": "108202",
  "idEvento": 193,
  "idEventoMuestra": 41317147,
  "idPrueba": 876,
  "idResultado": 109,
  "idTipoPrueba": 634,
  "noApta": false,
  "valor": "REACTIVO"
}
```

**Notas (validadas contra producción):**
- `fechaEmisionResultado` y `fechaRecepcion` en formato `YYYY-MM-DD`.
- **`idEstablecimiento`** = `codigo_sisa` corto, igual que API75.
- **`idEventoMuestra`** = el `id` que devolvió API75 (ej. `41317147`), NO el `idMuestra` (tipo).
- `noApta: false` para muestras válidas. El cliente viejo usaba `true`, pero la corrida exitosa fue con `false`.

---

## 9. MANEJO DE ERRORES CONOCIDOS

| API | Error | Causa | Acción |
|---|---|---|---|
| Cualquiera | `502 Bad Gateway` | SISA caído o sobrecargado | Reintentar con backoff exponencial (3 intentos) |
| WS400 | `"El caso que intenta notificar ya está notificado"` con `ID_SNVS_EVENTO_CASO: <id>` | El caso ya existe en SNVS | Parsear el id del mensaje y/o leer el campo `id_caso` de la respuesta. Reutilizarlo como `idEventoCaso` para API75. **WS400 SÍ devuelve el id existente.** |
| WS400 | `"id Departamento inexistente."` / `"El id no es un codigo valido"` | Se mandó código INDEC en `idDepartamento`/`idProvincia` | Usar **nomenclador SISA** (no INDEC) para provincia y departamento. Ver sección 4.1. `idLocalidad` sí es INDEC. |
| WS400 | `nombre` o `apellido` rechazado por longitud | El campo tiene <2 caracteres | Usar placeholder `"ND"` si el LIS no expone `nombre` separado del apellido. RENAPER hace el match por DNI. |
| API75 | `400 DataIntegrityViolationException` (sin más detalle) | Se mandó `codigo_refes` largo en `idEstablecimientoToma` | Usar `codigo_sisa` corto (~6 dígitos), no el REFES de 14 dígitos. Ver sección 4. |
| API75 | `400` con texto plano `"El registro a crear ya existe"` | La muestra (idEventoCaso + tipoMuestra) ya fue creada | **API75 NO devuelve el id existente** en la respuesta de error (a diferencia de WS400). En el smoke test se usa el flag `--id-muestra=N` para saltar API75 con un id conocido. Para producción, conviene loguear el `id` apenas se crea la muestra. |
| API76 | `400 "Ha ocurrido un error inesperado"` con `idEventoMuestra` correcto | Se pasó como `idEventoMuestra` el `idMuestra` (tipo) en lugar del `id` que devolvió API75 | Extraer `body_75["id"]` (no `body_75["idMuestra"]`) al guardar el id de la muestra. |
| Cualquiera | `"Default description if JSON is invalid"` | Payload malformado | Revisar campos obligatorios y formato de fechas (WS400 usa `DD-MM-YYYY`, API75/76 usan `YYYY-MM-DD`). |

---

## 10. SMOKE TEST (estado: VALIDADO EN PRODUCCIÓN)

`scripts/smoke_test.py` ejecuta el flujo completo WS400 → API75 → API76 en producción con un caso de Sífilis No Gestante hardcodeado.

**Características implementadas:**
1. Pide confirmación interactiva antes de tocar producción.
2. Loguea status code + body de cada respuesta a stdout.
3. Persiste el resultado completo en `logs/smoke_test_FECHA.json`.
4. Captura el `id_caso` cuando WS400 detecta duplicado y continúa con API75/API76.
5. Acepta el flag `--id-muestra=N` para saltar API75 cuando ya se conoce el id de la muestra (necesario porque API75 no devuelve el id existente al detectar duplicado).

**Datos de prueba reales (caso de prueba ejecutado con DNI del autor del proyecto):**
```python
CASO_PRUEBA = {
    "apellido": "M FECA22101972",    # APENOM tal como vendría del LIS
    "nombre": "ND",                  # placeholder >=2 chars; RENAPER resuelve por DNI
    "tipoDocumento": 1,              # DNI
    "numeroDocumento": "22011967",
    "sexo": "M",
    "fechaNacimiento": "22-10-1972", # WS400: DD-MM-YYYY
    "fechaPapel":      "20-04-2026", # WS400: DD-MM-YYYY
    "fechaToma":       "2026-04-20", # API75: YYYY-MM-DD
    "fechaResultado":  "2026-04-22", # API76: YYYY-MM-DD
    # Geografía — nomenclador SISA propio para prov/depto, INDEC para localidad:
    "idProvincia": 6,                # SISA (Córdoba)
    "idDepartamento": 194,           # SISA (Colón)
    "idLocalidad": 14021230,         # INDEC (Río Ceballos)
    "idPais": 200,
    # Sífilis No Gestante:
    "idGrupoEvento": 109,
    "idEvento": 193,
    "idClasificacionManualCaso": 743,
    "idMuestra": 1,
    "idTipoMuestra": 3,
    "idTipoPrueba": 634,
    "idPrueba": 876,
    "idResultado": 109,
    "valorResultado": "REACTIVO",
}

REFES_LC      = "51140142133784"  # WS400.idEstablecimientoCarga (REFES, 14 dígitos)
COD_SISA_LC   = "108202"          # API75.idEstablecimientoToma + API76.idEstablecimiento (codigo_sisa)
```

**Resultado validado contra producción (corrida del 22-04-2026):**
- WS400 → caso `39050581` creado.
- API75 → muestra `41317147` creada.
- API76 → resultado `REACTIVO` registrado, `200 OK`.

> **Pendiente operativo:** eliminar el caso `39050581` de SISA producción (es de prueba con datos reales del autor del proyecto).

---

## 11. SEGUNDA TAREA: PARSER DEL LIS

Crear `scripts/parser_lis.py` que:

1. Lea el TXT con `pd.read_csv(path, sep='\t', encoding='latin1')`
2. Filtre solo `ESTADO == 'V'`
3. Filtre solo filas con `"INTERPRETADO"` en `VARIABLEDESCRIPCION`
4. Identifique la **población** desde `TIPOFISIOLOGICODESCRIPCION`:
   - `"EMBARAZADA"` → `"GESTANTE"`
   - `"F"` no embarazada → `"NO_GESTANTE"`
   - `"M"` → `"GENERAL"`
5. Busque el mapeo en `clinico.json` usando `ESTUDIO` + `POBLACION` + `RESULTADO`
6. Devuelva un DataFrame con los casos notificables con sus IDs SISA ya resueltos

---

## 12. NOTAS TÉCNICAS IMPORTANTES

- **Python 3.x**, dependencias: `requests`, `pandas`
- **Encoding del TXT:** siempre `latin1`, nunca `utf-8`
- **Separador del TXT:** TAB (`\t`), no coma
- **APENOM → apellido + nombre:** el LIS expone `APENOM` como un solo campo `"APELLIDO NOMBRE"`. WS400 valida `nombre` con **mínimo 2 caracteres**, así que mandar el `nombre` vacío rompe la llamada. La estrategia validada es mandar el APENOM completo como `apellido` y un placeholder `"ND"` como `nombre` — RENAPER resuelve el match real por DNI igual.
- El campo `SEXO` en el TXT es `F`/`M`, el SISA acepta los mismos valores
- **Formatos de fecha distintos por API:** el TXT del LIS llega en `DD/MM/YYYY HH:MM:SS`. WS400 (`fechaNacimiento`, `fechaPapel`) usa `DD-MM-YYYY`. API75 (`fechaToma`) y API76 (`fechaEmisionResultado`, `fechaRecepcion`) usan `YYYY-MM-DD`. Una misma corrida tiene los dos formatos.
- **Geografía mixta:** `idProvincia` e `idDepartamento` usan nomenclador SISA propio; `idLocalidad` usa INDEC. Mezclarlos es la causa #1 de fallas en WS400. Ver sección 4.1.
- **Dos códigos de establecimiento:** WS400 quiere REFES (14 dígitos), API75/API76 quieren `codigo_sisa` (~6 dígitos). Ver sección 4.
- **`idtipoMuestra` con `t` minúscula:** capricho del API75. Cualquier otra capitalización falla.
- **`id` (no `idMuestra`):** el id que devuelve API75 está en el campo `id` de la respuesta. `idMuestra` es el TIPO que enviamos, no el identificador del registro creado. Pasarle el tipo a API76 como `idEventoMuestra` falla con `"Ha ocurrido un error inesperado"`.
- **Duplicados:** WS400 devuelve el id existente en la respuesta de error → reutilizar. API75 NO lo devuelve → loguear el `id` apenas se crea la muestra para poder retomar.
- El TXT tiene **2000+ filas** para un día de trabajo — el parser debe ser eficiente
- Los errores de casos ya notificados son **esperables y frecuentes** — no deben romper el flujo

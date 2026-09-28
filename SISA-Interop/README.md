# SISA Interop — Laboratorio Central de Virología Córdoba

Automatización de notificación de Enfermedades de Notificación Obligatoria (ENO) al SISA, consumiendo la exportación diaria del LIS del Laboratorio Central de Virología de la Provincia de Córdoba.

Reemplaza un proveedor externo con problemas de timing, costos y dependencia. Corre **localmente** en las PCs del Laboratorio Central (Windows).

---

## Flujo principal

```
LIS TXT (diario)
    └─► parser_lis.py       → filtra casos notificables + resuelve IDs SISA
            └─► ws400.py    → crea caso nominal          → devuelve id_caso
                    └─► api75.py  → registra muestra     → devuelve id_muestra
                            └─► api76.py  → informa resultado
```

---

## Estructura del proyecto

```
sisa-interop/
├── config/
│   ├── credentials.json            # APP_ID y APP_KEY por servicio (NO versionado)
│   ├── credentials.json.example    # Plantilla pública
│   ├── settings.json               # REFES, entorno, domicilio default (NO versionado)
│   └── settings.json.example       # Plantilla pública
├── mapeos/
│   ├── clinico.json                # Estudio + Población → IDs SISA (WS400, API75, API76)
│   └── catalogos/
│       ├── departamentos_sisa_cordoba.yaml   # 26 departamentos oficiales SISA
│       └── localidades_sisa_cordoba.yaml     # 1616 localidades oficiales SISA
├── scripts/
│   ├── smoke_test.py               # Prueba E2E hardcodeada (validar conectividad)
│   ├── parser_lis.py               # Parsea TXT del LIS → casos notificables
│   ├── geografia_sisa.py           # Resuelve nombre de localidad → IDs SISA
│   ├── ws400.py                    # [PENDIENTE] Crear caso nominal
│   ├── api75.py                    # [PENDIENTE] Registrar muestra
│   └── api76.py                    # [PENDIENTE] Informar resultado
├── data/                           # TXTs del LIS (NO versionado, datos de pacientes)
├── logs/                           # Resultados por fecha (NO versionado)
├── _archivo/                       # Material viejo del prestador externo (descartable)
├── main.py                         # [PENDIENTE] Orquestador
├── CONTEXTO_CLAUDE_CODE.md         # Documento técnico completo
├── README.md                       # Este archivo
├── requirements.txt                # Dependencias Python
└── .gitignore                      # Qué NO subir al repo
```

> Lo que está marcado `[PENDIENTE]` todavía no se construyó. Lo demás está validado en producción (caso 39050581 — eliminado tras la prueba).

---

## Instalación en una máquina nueva

Pensado para un usuario que recibe la carpeta y quiere ponerla en marcha. Asumimos Python 3.10+ instalado.

### 1. Copiar la carpeta `sisa-interop/` a la PC de destino

Cualquier método sirve: pendrive, copiar de red, descargar de un repo. La estructura debe quedar como la de arriba.

### 2. Instalar dependencias

Abrir PowerShell o CMD en la carpeta `sisa-interop/` y ejecutar:

```bash
python -m pip install -r requirements.txt
```

### 3. Crear `config/credentials.json`

Copiar `config/credentials.json.example` a `config/credentials.json` y completar con las credenciales reales que provee SISA:

```json
{
  "produccion": {
    "WS400": {"APP_ID": "...", "APP_KEY": "..."},
    "API75": {"APP_ID": "...", "APP_KEY": "..."},
    "API76": {"APP_ID": "...", "APP_KEY": "..."}
  }
}
```

### 4. Crear `config/settings.json`

Copiar `config/settings.json.example` a `config/settings.json` y ajustar según el laboratorio:

```json
{
  "entorno": "prod",
  "refes_laboratorio": "51140142133784",
  "id_interno_sisa": "108202",
  "domicilio_default": {
    "idProvincia": 6,
    "idDepartamento": 194,
    "idLocalidad": 14021230,
    "idPais": 200
  }
}
```

> **Atención al nomenclador.** `idProvincia` e `idDepartamento` usan el **nomenclador propio de SISA** (NO el de INDEC). `idLocalidad` sí usa INDEC. Mezclarlos es la causa #1 de fallas en WS400.
>
> El laboratorio tiene **dos códigos** que NO son intercambiables:
> - `refes_laboratorio` (14 dígitos) → WS400 lo recibe como `idEstablecimientoCarga`.
> - `id_interno_sisa` (~6 dígitos) → API75 / API76 lo reciben como `idEstablecimientoToma` / `idEstablecimiento`.
>
> Mandar el equivocado falla con `DataIntegrityViolationException` genérico.

### 5. Validar conectividad

```bash
python scripts/smoke_test.py
```

Hace una prueba end-to-end con un caso hardcodeado. Pide confirmación antes de impactar en SISA. Si responde con un `id_caso` y un `id_muestra`, todo OK.

---

## Uso normal

### Procesar un TXT diario del LIS

```bash
python main.py --archivo data/exportacion_20260427.txt
```

Opciones (cuando esté implementado el orquestador):

| Opción | Descripción |
|---|---|
| `--archivo` | Path al TXT exportado del LIS (obligatorio) |
| `--entorno` | `prod` (default) o `qa` |
| `--limite` | Cantidad máxima de casos a procesar (útil para pruebas) |
| `--dry-run` | Parsea y muestra casos sin enviar al SISA |

### Probar el parser sin enviar nada

```bash
python scripts/parser_lis.py data/exportacion_20260427.txt
```

Imprime resumen: cuántas filas, cuántas notificables, qué se descartó y por qué.

### Resolver geografía manualmente

```bash
python scripts/geografia_sisa.py "Río Ceballos" --depto Colón
```

---

## Formato del TXT del LIS

- **Separador:** TAB (`\t`)
- **Encoding:** `latin1`
- **Estructura:** una fila por determinación — múltiples filas por paciente/orden
- **Filtro clave:** solo filas con `ESTADO == 'V'` y `VARIABLEDESCRIPCION` que contenga `"INTERPRETADO"` representan resultados finales notificables

Columnas usadas: `SUCURSAL`, `ORDEN`, `NUMDOC`, `TIPDOC`, `APENOM`, `FECNAC`, `SEXO`, `FECHAALTA`, `ESTUDIO`, `ESTUDIODESCRIPCION`, `VARIABLEDESCRIPCION`, `RESULTADO`, `ESTADO`, `FECHAHORAVALIDACION`, `TIPOFISIOLOGICODESCRIPCION`, `ENTIDAD`.

---

## Errores frecuentes y cómo se manejan

| API | Error SISA | Causa | Acción del sistema |
|---|---|---|---|
| Cualquiera | `502 Bad Gateway` | SISA caído o sobrecargado | Reintento automático (3 intentos, backoff exponencial) |
| WS400 | Caso ya notificado | El caso existe en SNVS | Captura el `ID_SNVS_EVENTO_CASO` del mensaje y lo reutiliza como `idEventoCaso` |
| WS400 | `id Departamento inexistente` | Se mandó código INDEC en `idDepartamento` / `idProvincia` | Usar nomenclador SISA propio (ver `settings.json`) |
| API75 | `DataIntegrityViolationException` | Se mandó REFES largo en `idEstablecimientoToma` | Usar `id_interno_sisa` corto |
| API75 | "El registro a crear ya existe" | La muestra ya fue creada y API75 no devuelve el id existente | Loguear el `id` apenas se crea cada muestra; reanudar con `--id-muestra=N` |
| API76 | "Ha ocurrido un error inesperado" | Se pasó `idMuestra` (tipo) en lugar del `id` que devolvió API75 | Extraer `body_75["id"]`, no `body_75["idMuestra"]` |
| Cualquiera | JSON inválido | Payload malformado | Loguea el error y continúa con el siguiente caso |

---

## Estado del proyecto

- [x] Contexto y mapeos definidos
- [x] Catálogo SISA completo (26 departamentos + 1616 localidades de Córdoba)
- [x] `smoke_test.py` — validar credenciales y conectividad
- [x] **Prueba end-to-end exitosa en producción** (caso 39050581 / muestra 41317147 — ya eliminado)
- [x] `parser_lis.py` — parsear y filtrar TXT del LIS
- [x] `geografia_sisa.py` — resolver localidades a códigos SISA
- [x] `mapeos/clinico.json` — mapeo Estudio + Población → IDs SISA
- [ ] `ws400.py` — módulo crear caso
- [ ] `api75.py` — módulo registrar muestra
- [ ] `api76.py` — módulo informar resultado
- [ ] `main.py` — orquestador completo

---

## Notas importantes

- Este sistema opera sobre **producción**. Los casos creados quedan registrados en el SNVS nacional.
- El entorno de QA del SISA ha estado históricamente inestable — si falla, pasar directamente a producción con datos controlados.
- **APENOM del LIS:** viene como `"APELLIDO NOMBRE"` en un solo campo. WS400 valida `nombre` con mínimo 2 caracteres, así que mandar el APENOM completo como `apellido` y un placeholder `"ND"` en `nombre` es el patrón validado. RENAPER hace el match real por DNI.
- **Fechas:** el LIS llega en `DD/MM/YYYY HH:MM:SS`. WS400 quiere `DD-MM-YYYY`. API75/API76 quieren `YYYY-MM-DD`.
- **`idtipoMuestra`** en API75 va con `t` minúscula (capricho del API).
- **El id de la muestra** está en `body_75["id"]`, no en `body_75["idMuestra"]` (este último es el TIPO).
- **ESTUDIO=14 en LIS:** está reusado para "ANTI HBC" (NO notificable) y "SIFILIS BCO" (notificable). El parser desambigua por `ESTUDIODESCRIPCION` — sólo notifica el segundo.

---

**Leer `CONTEXTO_CLAUDE_CODE.md` para el detalle técnico completo: payloads, mapeo clínico, lógica de filtrado y especificaciones de cada tarea.**

# Estado del proyecto SISA Interop

> **Ultima actualizacion:** 28 de septiembre de 2026
>
> **Para que sirve este documento:** retomar el proyecto sin perder contexto. Si abris un chat nuevo (Cowork, Claude Code, o cualquier herramienta que asista), pedile que lea **este archivo primero** y despues `CONTEXTO_CLAUDE_CODE.md` (el doc tecnico).

---

## 1. Estado del sistema

**Funcional y corriendo en produccion.** El flujo LIS -> WS400 -> API75 -> API76 esta validado end-to-end para sifilis (treponémica + VDRL), Chagas, VIH, Hepatitis A/B/C, Dengue, Respiratorio, Rubeola, Sarampion. El sistema se refactorizo completamente en junio 2026 para soportar el flujo correcto de sifilis con VDRL como determinacion secundaria.

### Flujo de sifilis (diseño vigente, junio 2026)

```
Treponémica (7101, 201, 14) = PRIMARIA siempre
  - Positiva -> WS400 + API75 + API76 (clasif=743/153, o 742 si VDRL >=16 en mismo dataset)
  - Negativa -> SKIP

VDRL (72) = SECUNDARIA (REUSE)
  - REACTIVO + treponémica en esta corrida -> solo API76 (intra-corrida)
  - REACTIVO + treponémica en cache (corrida anterior) -> solo API76 (cross-run)
  - REACTIVO + VDRL >=16 + cross-run -> API76 + API81 para subir clasif 743->742
  - REACTIVO sin treponémica -> SKIP_VDRL
  - NO REACTIVO -> no se parsea (removido de clinico.json)
```

### Clasificaciones de sifilis

| Clasificacion | ID | Cuando aplica |
|---|---|---|
| Sin especificar | 743 | Treponémica general, sin VDRL o VDRL < 16 |
| Sifilis temprana | 742 | Treponémica general + VDRL >= 16 DIL |
| Caso confirmado | 153 | Gestante, siempre (sin importar titulo VDRL) |

### Cache persistente

`data/muestras_cache.json` guarda `"{dni}|{id_evento}" -> {id_caso, id_muestra}` de forma permanente. Permite que VDRLs de corridas posteriores encuentren la muestra de la treponémica sin necesidad de crearla de nuevo.

---

## 2. Corridas en produccion

| Fecha | Dataset | Evento | Total | NUEVO | REUSE | SKIP | SKIP_VDRL | Errores | Notas |
|-------|---------|--------|-------|-------|-------|------|-----------|---------|-------|
| 27-abr | SE15-16 | Sifilis | ~130 | ? | ? | ? | — | — | Primer run |
| 11-may | SE17 | VIH, Chagas, Sifilis | ~130 | ? | ? | ? | — | — | Con UI |
| 18-may | SE19 | Sifilis | 199 | 42 | 0 | 2 | 139 | 16 | Primer run VDRL (params erroneos) |
| 01-jun | SE21 | Sifilis | 83 | 23 | 3 | 10 | 47 | 0 | Primer REUSE exitoso (7 VDRLs) |
| 04-jun | Parcial SE22 | Sifilis | 110 | 38 | 45 | 8 | 15 | 25 | 25 errores: params 201 GESTANTE + casos viejos cerrados |
| 05-jun | Parcial SE22 | Sifilis | 110 | — | — | — | — | — | Fix aplicado, listo para produccion |
| 12-jun | Completo_se23_parcial | Sifilis | 105 | 40 | 21 | 12 | 31 | 1 | 1 error WS400 status=400 DNI=43603625 (revisar) |

---

## 3. Scripts y archivos clave

```
sisa-interop/
├── ESTADO_DEL_PROYECTO.md          <- este archivo
├── CONTEXTO_CLAUDE_CODE.md         <- documentacion tecnica
├── main.py                         <- orquestador principal
├── scripts/
│   ├── parser_lis.py               <- transforma TXT LIS en casos notificables
│   ├── ws400.py                    <- API WS400 (crear/recuperar caso nominal)
│   ├── api75.py                    <- API75 (registrar muestra)
│   ├── api76.py                    <- API76 (informar resultado)
│   ├── api81.py                    <- API81 (cambiar clasificacion manual) [NUEVO jun-2026]
│   ├── generar_control.py          <- genera planilla Excel de control post-corrida [NUEVO jun-2026]
│   ├── sisa_http.py                <- HTTP util con retry (POST + PUT)
│   └── smoke_test.py
├── mapeos/
│   ├── clinico.json                <- mapeo LIS -> SISA (estudios, poblacion, IDs)
│   └── establecimientos.json       <- sucursales LIS -> REFES + sisa_corto
├── config/
│   ├── credentials.json            <- APP_ID/APP_KEY por API (NO versionado)
│   └── settings.json               <- entorno, refes_laboratorio, id_interno_sisa
├── data/
│   └── muestras_cache.json         <- cache dni|id_evento -> {id_caso, id_muestra}
└── logs/                           <- main_YYYYMMDD_HHMMSS.json por corrida
```

---

## 4. Parametros criticos de sifilis en clinico.json (vigentes)

| Estudio | Poblacion | idEvento | idPrueba | idTipoPrueba | Descripcion |
|---------|-----------|----------|----------|--------------|-------------|
| 7101 SIFILISR2 | GENERAL | 193 | 876 | 634 | Quimioluminiscencia Ac totales |
| 7101 SIFILISR2 | GESTANTE | 115 | 876 | 634 | Quimioluminiscencia Ac totales |
| 201 TEST RAPIDO | GENERAL | 193 | 1010 | 143 | Metodos Rapidos |
| 201 TEST RAPIDO | GESTANTE | 115 | 143 | 143 | Inmunocromatografia (corregido jun-2026) |
| 14 SIFILIS BCO | NO_GESTANTE | 193 | 876 | 634 | Quimioluminiscencia |
| 72 VDRL | GENERAL | 193 | 153 | 145 | VDRL (corregido jun-2026) |
| 72 VDRL | GESTANTE | 115 | 153 | 145 | VDRL (corregido jun-2026) |

**idResultado VDRL por dilucion:** 1 DIL->1059, 2->1060, 4->1061, 8->1062, 16->1063, 32->1064, 64->1065, 128->1066, 256->1067, 512->1068, 1024->1069.

---

## 5. Credenciales

| API | Credencial | Estado |
|-----|-----------|--------|
| WS400 | app_id=049fedb8 | OK |
| API75 | app_id=58d0467b | OK |
| API76 | app_id=a7bb9a90 | OK |
| API81 | app_id=049fedb8 (WS400) | 401 - pedir a soporte@sisa.msal.gov.ar |

---

## 6. Tareas pendientes

### Bloqueantes / prioritarias

**Validar en QA y re-correr SE36/SE38 en dry-run antes de la proxima corrida real (sep-2026).**
Se corrigieron dos bugs de seguridad en `scripts/parser_lis.py`, `main.py` y `ui.py`
(ver detalle en seccion 7). Antes de la proxima corrida de produccion:
1. Correr `python scripts/parser_lis.py data/<ultimo_txt>.json` (o via UI en dry-run)
   y revisar la seccion "ALERTA: colisiones de codigo de estudio" del resumen.
2. Confirmar con el equipo el nuevo flujo obligatorio de filtro en la UI (ya no hay
   "sin filtro" preseleccionado) y el flujo de confirmacion para correr sin filtro.

**Decidido (sep-2026):** los estudios de banco de sangre que colisionaban de codigo
(cod 3, 4, 5, 18 — Anti VHC, AG HBS, Anti HBC, BM HIV) NO se notifican a SISA como
"banco de sangre". Se descartan y quedan asi de forma permanente — no hace falta
agregarlos a `clinico.json`. Los casos que habian ingresado mal a SISA production
(los ~180+ "Dengue IgM" que en realidad eran BM HIV de banco) ya fueron eliminados
manualmente por el equipo.

**Credenciales API81.** Sin ellas, los casos con VDRL >=16 en corridas anteriores no se reclasifican a 742 (sifilis temprana). El codigo esta implementado y listo; solo falta el APP_ID/APP_KEY. Solicitarlos a soporte@sisa.msal.gov.ar.

### Corridas pendientes de revision manual

- **1 error de Completo_se23_parcial (12-jun):** WS400 status=400 para DNI=43603625 (7101 SIFILISR2). Revisar en SISA si el caso existe manualmente o si hay problema con el ciudadano.

### Tecnicos (no bloquean produccion)

- Banco de sangre: en el dataset actual aparecen solo como VDRL REUSE, funcionan correctamente. Pendiente agregar treponémicas de banco de sangre a clinico.json cuando aparezcan.
- Sucursal 75 BIENESTAR ESTUDIANTIL: no mapeada. Confirmar con el laboratorio y agregar a establecimientos.json.
- Programacion diaria (Task Scheduler): configurar cuando se estabilice el flujo manual.
- Rotacion de logs: comprimir mensualmente.

---

## 7. Gotchas criticos (no repetir estos errores)

### Parser

- **Codigo de estudio ambiguo entre banco de sangre y diagnostico (INCIDENTE sep-2026).**
  El LIS reusa el mismo numero de `ESTUDIO` para un panel de banco de sangre
  (donantes) y un estudio de diagnostico clinico sin ninguna relacion entre si.
  Ejemplo real que causo el incidente: `ESTUDIO="018"` (banco, "BM HIV (BCO)")
  se castea a `int(18)` en el parser, que es el mismo codigo que "IGM DENGUE" en
  `clinico.json` — mas de 180 resultados de banco de sangre se notificaron a
  produccion de SISA como casos probables de Dengue. Auditoria de sep-2026 sobre
  dos TXT reales encontro 3 colisiones MAS del mismo patron, tambien silenciosas
  hasta ese momento: cod=3 (Anti VHC banco vs Hepatitis A), cod=4 (AG HBS banco
  vs Anti VHC), cod=5 (Anti HBC banco vs Anti VIH Combo). Fix: `MapeoClinico` en
  `scripts/parser_lis.py` ahora exige "simetria banco/diagnostico" para TODO
  codigo (no solo los conocidos) — un `ESTUDIODESCRIPCION` de banco ('(BCO)',
  prefijo 'BM ') solo matchea contra una entrada de `clinico.json` que TAMBIEN
  sea de banco para ese mismo codigo, y viceversa; si no coinciden se descarta y
  queda logueado en el resumen bajo "ALERTA: colisiones de codigo de estudio".
  Si aparece una colision que NO sigue el patron banco/diagnostico, agregarla a
  mano en `MapeoClinico.DISAMBIGUACION_POR_NOMBRE`.
- **Filtro de evento ahora es obligatorio en la UI y en main.py (INCIDENTE sep-2026).**
  Antes, el combo de filtro en `ui.py` arrancaba preseleccionado en "Todos los
  eventos (sin filtro)"; si alguien apretaba Procesar sin cambiar el desplegable,
  se interoperaba TODO el listado del TXT (paso exactamente esto: se queria
  notificar solo Sifilis y se interoperaron tambien VIH, Chagas, Sarampion, etc.
  de toda la semana). Fix: el combo ya no tiene "sin filtro" preseleccionado —
  arranca en un placeholder que bloquea Procesar hasta elegir un evento puntual.
  "Todos los eventos" sigue existiendo como opcion, pero ahora hay que elegirla
  a proposito y confirmar escribiendo "CONFIRMAR" en un dialogo aparte. Mismo
  criterio en `main.py` via CLI: `--filtro` es obligatorio salvo que se pase
  `--todos-los-eventos` explicitamente.
- **VDRL embebida en 7101:** el LIS no exporta el VDRL como estudio 72 separado para todos los pacientes. Para muchos, viene como sub-variable codigo 609 (SIFILIS VDRLR) dentro del estudio 7101. El parser extrae esto y genera un CasoNotificable sintetico de estudio 72. Si se modifica el parser, preservar esta logica.
- **Deduplicacion:** siempre priorizar fila INTERPRETADO para estudios multi-fila (Sifilis, VHC). Chagas y similares son single-row, no tienen INTERPRETADO.
- **TIPOFISIOLOGICODESCRIPCION es ruidoso.** Usar DIAGNOSTICODESCRIPCION para detectar gestantes. Solo SEXO='F' + 'embarazada' en DIAGNOSTICODESCRIPCION = GESTANTE.

### APIs SISA

- **idtipoMuestra con t MINUSCULA en API75.** Capricho del API.
- **body_75["id"] es el idEventoMuestra.** No confundir con body_75["idMuestra"] que es el TIPO. El error resultante en API76 es "Ha ocurrido un error inesperado" sin mas contexto.
- **WS400 idEstablecimientoCarga = REFES (14 digitos). API75 idEstablecimientoToma = codigo interno (~6 digitos).** Mezclarlos da DataIntegrityViolationException.
- **NO mandar domicilio en WS400.** SISA usa el de RENAPER. Si lo mandas, todos los casos quedan con el mismo domicilio.
- **La muestra se registra en cache ANTES de llamar API76.** Si API76 falla, las VDRLs de esa corrida y las futuras igual encuentran la muestra correcta en el cache.

### Flujo de sifilis

- **Treponémica primero, VDRL despues.** El pre-scan en main.py garantiza el orden incluso si el TXT viene mezclado.
- **El REUSE es por (dni, id_evento).** Si la treponémica es GESTANTE (idEvento=115) y la VDRL mapea a GENERAL (idEvento=193), no hay match -> SKIP_VDRL. Siempre verificar que el mismo paciente tenga el mismo idEvento en treponémica y VDRL.
- **Cross-run REUSE:** si la treponémica fue SKIP (ya existia en SISA), casos_de_esta_corrida tiene id_muestra=None. El sistema busca en cache automaticamente. Solo falla si nunca se guardo la muestra (corridas muy viejas antes de implementar el cache).

---

## 8. Sistema de control/auditoria (implementado jun-2026)

**Solucion implementada:** `scripts/generar_control.py` + boton "Planilla control" en la UI.

**Como funciona:**
- Lee el log JSON de una corrida y genera un Excel en `_salida/control_<timestamp>.xlsx`
- Sheet "Sifilis": pivoteada por paciente (una fila), columnas por determinacion (SIFI treponémica, Banco de Sangre, Test Rapido, VDRL), semaforo verde/rojo/gris por estado
- Sheet "Resumen": totales y tabla por sub-evento (General / Gestante)
- Sheets adicionales para VIH, Chagas, Hepatitis, Respiratorio si hay casos
- El bacteriologo compara contra su hoja de trabajo de THARSIS por Orden y DNI

**Uso:**
```
python scripts/generar_control.py logs/main_YYYYMMDD_HHMMSS.json
```
O directamente desde la UI con el boton "📋 Planilla control" que aparece al finalizar cada corrida.

**Base nominalizada NOM_P14.csv:**
- Exportacion del SNVS provincial con 410.000+ casos (2025-2026), 185 columnas
- Guardada en `_salida/NOM_P14.csv`
- Permite cruce por IDEVENTOCASO para confirmar que los casos estan efectivamente en SISA
- La mayor parte de los casos de LABORATORIO CENTRAL no vienen del interop (carga manual u otros sistemas); la huella del interop es: Deteccion Ac totales/Quimioluminiscencia + VDRL + Inmunocromatografia

**Proximo paso posible:** integrar cruce automatico contra NOM_P14 en la planilla de control (columna "Confirmado en SISA") una vez que se actualice periodicamente la exportacion.

---

## 9. Como retomar

### Chat nuevo (Cowork)

1. Pedile al asistente: "lee ESTADO_DEL_PROYECTO.md y CONTEXTO_CLAUDE_CODE.md".
2. Decile que tarea queres trabajar.

### Uso diario

Abrir `Iniciar SISA Interop.bat`. Seleccionar TXT, elegir filtro (sifilis), modo dry-run para previsualizar, luego produccion.

### Para re-correr errores

Los casos con error en API76 pero con WS400+API75 exitosos tienen la muestra creada en SISA y en el cache. Al re-correr el mismo TXT, WS400 devolvera SKIP para las treponémicas (ya existen) y las VDRLs encontraran la muestra en casos_de_esta_corrida o en cache -> REUSE automatico.

---

**Fin del documento.** Actualizar al cerrar sesiones largas. No hace falta detallar cada cambio (eso lo hace git), pero si los pendientes abiertos y decisiones tomadas con su porque.

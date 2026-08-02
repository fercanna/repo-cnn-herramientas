# informe-semanal-trello

Copia maestra (fuente única de verdad) de los 3 scripts que arman el
informe semanal de seguimiento de certificación combinando un export de
Trello con las minutas de reuniones.

- `detectar_nuevo_trello.py` — detecta si hay un export de Trello nuevo.
- `generar_informe.py` — genera los 4 entregables (xlsx, csv, html, docx).
- `marcar_procesado.py` — marca la corrida como procesada.
- `config.example.json` — plantilla de configuración por cliente.

**Importante:** estos scripts NO corren desde acá. Cada cliente tiene su
propia copia funcional dentro de `20_Minutas` en su carpeta de Drive
(`G:\Mi unidad\CNN.AI - Clientes\<Cliente>\20_Minutas\`), junto con su
propio `config.json` y `estado.json` — porque los scripts usan la carpeta
donde están guardados (`SCRIPT_DIR`) para encontrar el export de Trello y
guardar el estado. Si se corrige un bug o se cambia el diseño acá, hay que
volver a copiar los `.py` actualizados a la carpeta `20_Minutas` de cada
cliente activo (por ahora: AnalyticsNOA, LACE).

Ver la skill completa en `informe-semanal-trello-consultoria.md` (raíz de
este repo).

Migrado desde `Consultoria_cal` (deprecada) el 01/08/2026.

---
name: informe-semanal-trello-consultoria
description: Genera el informe semanal de seguimiento de certificación combinando el export de Trello y las minutas de reuniones, para AnalyticsNOA y LACE.
---

Generá el informe semanal de seguimiento de certificación para AnalyticsNOA y LACE, combinando dos inputs por cliente: el export de Trello del tablero de gestión, y las minutas de reuniones de seguimiento ya generadas.

**Convención de carpetas (actualizada 01/08/2026):** `Consultoria_cal` quedó deprecada — ya no se usa. Los datos de cliente viven en Drive, en `G:\Mi unidad\CNN.AI - Clientes\<Cliente>\`. Los scripts (`generar_informe.py`, `detectar_nuevo_trello.py`, `marcar_procesado.py`) más `config.json` y `estado.json` viven directamente dentro de `20_Minutas` de cada cliente — la misma carpeta donde `generar_minuta` ya deja los `.md`/`.docx`/`.json` de cada reunión. Fer agrega el export de Trello ahí mismo; el informe también se genera ahí.

La copia maestra de los 3 scripts (código genérico, sin datos de cliente) vive en `C:\Users\Equipo\repos\repo-cnn-herramientas_LISTO\informe-semanal-trello\` — si en algún momento hay que corregir un bug o cambiar el diseño de los informes, editar ahí y volver a copiar a la carpeta `20_Minutas` de cada cliente (los scripts no se actualizan solos).

Clientes a procesar (recorré la lista completa, uno por uno, sin detenerte si uno falla — seguí con el siguiente):

1. **AnalyticsNOA** — `G:\Mi unidad\CNN.AI - Clientes\AnalyticsNOA\20_Minutas\`
2. **LACE** — `G:\Mi unidad\CNN.AI - Clientes\LACE\20_Minutas\`

Tctech y Hormigones quedan fuera de esta skill por ahora (no son prioridad para Fer) — si en el futuro se vuelven a necesitar, se agregan copiando los 3 scripts + un `config.json` propio a la carpeta `20_Minutas` de ese cliente (ver `config.example.json` en la copia maestra del repo como plantilla).

Cada `20_Minutas` tiene su propio `config.json` con `nombre_laboratorio` y `normas` — no hace falta conocerlos de antemano, los scripts los leen solos.

Para CADA cliente de la lista, repetí este proceso:

**PASO 1 — Detectar si hay un export nuevo de Trello.**
Corré, parado en `20_Minutas` de ese cliente: `python3 detectar_nuevo_trello.py`. El script imprime:
- `SIN_NOVEDAD|...` → No hay ningún JSON de Trello nuevo desde la última corrida para este cliente. No generes nada. Anotá esto para el resumen final y pasá al siguiente cliente.
- `NUEVO|<carpeta_semana>|<ruta_json>` → Hay un export nuevo. La `carpeta_semana` ya fue creada con el JSON copiado adentro. Continuá al paso 2 para este cliente.

**PASO 2 — Redactar la Sección 5 (Observaciones y Compromisos) a partir de las minutas.**
Fuente: los archivos `.md` ya generados por `generar_minuta` en la misma carpeta `20_Minutas` (son resúmenes ya curados de cada reunión — no uses las transcripciones crudas).

Leé el archivo `estado.json` en `20_Minutas` de este cliente (tiene la lista `transcripciones_procesadas`). Listá los `.md` de minuta en la carpeta y quedate solo con los que NO estén en esa lista.

Si hay minutas nuevas: leé su contenido completo y redactá, en español, un resumen breve y profesional para tres campos (2 a 5 viñetas cada uno, concisas):
- `novedades`: avances y novedades relevantes discutidas en las reuniones.
- `decisiones`: decisiones concretas que se tomaron con el cliente.
- `compromisos`: compromisos y próximos pasos acordados, con responsable si se menciona.

Guardá esto como `observaciones.json` dentro de la `carpeta_semana` del paso 1, con este formato exacto:
```json
{
  "fuente_reuniones": ["2026-07-17_minuta.md", "2026-07-24_minuta.md"],
  "novedades": ["...", "..."],
  "decisiones": ["...", "..."],
  "compromisos": ["...", "..."]
}
```
Si no hay minutas nuevas para este cliente, no crees `observaciones.json`.

**PASO 3 — Generar el informe.**
Corré: `python3 generar_informe.py <carpeta_semana>` (ruta absoluta de la `carpeta_semana` del paso 1). Genera 4 archivos: `tareas_sgc_*.xlsx`, `tareas_sgc_*.csv`, `informe_interno_*.html`, `informe_direccion_*.docx`.

**PASO 4 — Marcar como procesado.**
Corré: `python3 marcar_procesado.py "<nombre_del_json_procesado>" "<minuta1.md>" ...` (nombre del JSON procesado y las minutas nuevas usadas en el paso 2, si hubo).

**PASO 5 — Entregar.**
Después de recorrer los 2 clientes, compartí con Fer todos los `informe_direccion_*.docx` e `informe_interno_*.html` que se hayan generado en esta corrida (de los clientes que sí tenían novedad). Armá un resumen final con 1 línea por cliente: si se generó informe o no (y por qué no, si corresponde), y si se incorporaron novedades de reuniones.

**Notas importantes:**
- No inventes datos: si algo no está claro en las minutas, no lo incluyas en `observaciones.json`.
- No modifiques los scripts (`generar_informe.py`, `detectar_nuevo_trello.py`, `marcar_procesado.py`, `config.json`) desde acá — si hace falta un cambio, editar la copia maestra en el repo (`repo-cnn-herramientas_LISTO/informe-semanal-trello/`) y volver a copiarlo a `20_Minutas` de cada cliente.
- Los archivos `config.json`, `estado.json` y `observaciones.json` NO son exports de Trello ni minutas, no los trates como tales.
- Cada cliente es independiente: un error o falta de novedad en uno no debe frenar el procesamiento de los demás.

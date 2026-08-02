# Pendiente — mover manualmente a Drive (CNN.AI - Clientes)

**Actualización 2026-07-11:** las 5 actas (.txt) ya se subieron automáticamente
vía API de Drive a CURF/02_Actas (2), Goodapps/02_Actas, Tctech/02_Actas y
FCEFyN/02_Actas — quitadas de la lista de abajo. Los binarios (.docx/.xlsx)
NO se pudieron subir por API: se probó con uno y llegó corrupto (checksum
distinto al original, el archivo no abre bien). Quedan pendientes de mover
a mano, arrastrando desde el Explorador de Windows a drive.google.com — es
más confiable que la API para este tipo de archivo.

**Antes de nada: borrar el archivo de prueba corrupto** que quedó en
`CURF/04_Documentos_SGC` → `Resumen de reactivos para F Canna.xlsx`
(id `1on6ItRTVssCcosXQhwx97pPrRxcbzLxM`, no lo abras, está dañado).

Los archivos NO-código que quedaron dentro de las carpetas de herramientas
en Consultoria_her. Los originales siguen intactos ahí, esto no borra nada.

## CPR Lab 2.0 → Drive/CNN.AI - Clientes/CURF/
- ~~`_minutas/Meeting Transcription_nuevos_requerimientos_curf_260526.txt`, `_minutas/reu-CPR_male_050626.txt` → 02_Actas~~ **YA MIGRADO**
- `Propuesta_CURF_Desarrollo_v1.docx`, `Propuesta_CURF_Desarrollo_v2.docx` → 07_Contratos_Propuestas (manual)
- `Reactivos Virologia 2026 Fer Canna.xlsx`, `Resumen de reactivos para F Canna.xlsx` → 04_Documentos_SGC (manual)
- `_modelo/CPR-VI-RE-1 Gestión de Compras_v2.4.xlsx`, `_modelo/Copia de BioNoa-RE-1 Gestión de Compras_v2.4.xlsx` → 04_Documentos_SGC (manual)
- `_contexto_CURF/*.md` → NO va a Drive, ya se fusionó a repo-cnn-contexto/repo-cnn-herramientas (ver tarea de contextos)

## GeCO Lab 2.0 → Drive
- ~~`_minutas/Meeting Transcription_val_GoodApps.txt` → CNN.AI - Clientes/Goodapps/02_Actas~~ **YA MIGRADO**
- ~~`_minutas/Meeting Transcription_val_tectech.txt` → CNN.AI - Clientes/Tctech/02_Actas~~ **YA MIGRADO**
- ~~`_minutas/reu seguimiento_val_geco_fcefyn.txt` → CNN.AI - Clientes/FCEFyN/02_Actas~~ **YA MIGRADO**
- `_recursos/Copia de GeCO Lab 2.0 - SE-FCEFyN.xlsx` → CNN.AI - Clientes/FCEFyN/04_Documentos_SGC (manual)

## AuDit Lab → Drive/CNN.AI - Clientes/AnalyticsNOA/
- `PG-GAI-001_Gestion-Auditorias-Internas_v00.docx` → 06_Auditorias
- `R-PG-GAI-001-01_Registro-Auditorias-Internas_v00.xlsx` → 06_Auditorias

## Mejora Lab → Drive/CNN.AI - Clientes/AnalyticsNOA/
- `R-PG-GME-001-01 Registro de puntos de mejora (respuestas).xlsx` → 03_Hallazgos_NC

## Docencia → Drive/CNN.AI - Clientes/Docencia/05_Materiales_Capacitacion/
- Toda la carpeta `Fuentes/` (PDFs, mp3, plantillas, papers, programas académicos)
- `Salidas_Generadas/` (imágenes, guiones generados)
- `Modelos/`, `Videos_Audios/`
- `Contenido para Presentación en Goog.txt`, `Diseño_Visual_Presentacion_Canva.md`, `datos_canva.txt`

Después de mover cada uno y confirmar que abre bien desde Drive, se puede
borrar el original en Consultoria_her.

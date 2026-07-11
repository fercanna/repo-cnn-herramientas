# repo-cnn-herramientas

Fuente única de verdad para el código de las herramientas de CNN.AI. Migrado
2026-07-11 desde carpetas locales sueltas (Etapa 2 del proyecto "Dejar de ser
cuello de botella").

## Contenido

| Carpeta | Herramienta | Cliente(s) | Stack |
|---|---|---|---|
| `CPR-Lab-CURF/` | Gestión de compras | CURF | Google Apps Script |
| `GeCO-Lab-FCEFyN/` | Gestión de evaluaciones/competencias | FCEFyN | Google Apps Script |
| `AuDit-Lab-AnalyticsNOA/` | Auditorías internas | AnalyticsNOA | Google Apps Script |
| `Timetracker/` | Registro de tiempo por tarea | Interno | Python/Streamlit |
| `Docencia-Presentaciones/` | Generación de presentaciones con IA | Docencia | Python |
| `Mejora-Lab/sistema-no-conformidades/` | Gestión de no conformidades (vigente) | AnalyticsNOA | Python/Flask |
| `Mejora-Lab/appscript-analyticsnoa-legacy/` | Variante Apps Script (desactualizada, a evaluar si se archiva) | AnalyticsNOA | Google Apps Script |

## Lo que NO está acá

Contenido no-código (Word, Excel, PDF, actas de reunión, propuestas
comerciales) que vivía mezclado dentro de estas carpetas se dejó pendiente de
migrar manualmente a Drive (`CNN.AI - Clientes/<Cliente>/`) — ver checklist en
`PENDIENTE_MIGRAR_A_DRIVE.md`.

Secretos (`.env`), bases de datos locales (`*.db`) y entornos virtuales
(`venv/`) están excluidos por `.gitignore` — cada máquina genera los suyos.

## Uso diario

Ver `INSTRUCTIVO_GIT.md` en `repo-cnn-contexto` (o el que te haya entregado
Claude junto con esta migración) para el flujo de trabajo paso a paso.

# Memoria del proyecto: herramienta de flujogramas

## Objetivo

Recuperar la capacidad de generar flujogramas de procesos de clientes (que Fer perdió
al dejar de tener Visio), para tener una vista macro de los procesos incluidos en el
alcance de un sistema de gestión de calidad. El flujo de trabajo pensado es:

1. Relevar un proceso del cliente.
2. Consolidar los elementos del proceso en una planilla Excel estructurada.
3. Pasarle esa planilla a la herramienta, que devuelve un flujograma en PowerPoint
   como primer borrador.
4. Ajustar el borrador a mano en PowerPoint hasta llevarlo a la realidad del proceso.

## Decisiones de diseño (y por qué)

- **Salida en PowerPoint (.pptx), no draw.io ni Mermaid.** Fer probó draw.io después
  de Visio y le resultó poco práctico como editor. PowerPoint tiene una edición de
  formas y conectores similar a Visio, y es una herramienta que ya conoce — no hay
  curva de aprendizaje. El .pptx generado usa formas nativas (no imágenes), así que
  se edita directamente arrastrando cajas.
- **Layout vertical (de arriba hacia abajo), no horizontal.** El primer prototipo fue
  horizontal con carriles de actor de ancho completo; Fer mostró un flujograma viejo
  de Visio con estructura vertical, fases como bloques punteados apilados, y pidió
  ese estilo. Se rehizo el generador para ese formato.
- **Fases como bloques punteados, no como color de fondo continuo.** Coincide con el
  estilo de referencia (etiqueta de fase arriba a la izquierda del bloque, borde
  punteado, no una banda de color que ocupa toda la fila).
- **Auto-layout en vez de posicionamiento manual.** El script calcula automáticamente
  filas (orden topológico del proceso) y columnas (ramas en paralelo), para que el
  usuario no tenga que acomodar cajas una por una — clave para que el "borrador
  automático" ahorre trabajo real, sobre todo en procesos grandes.

## Estado actual: qué funciona

Probado con dos casos reales dentro de esta sesión:

1. **Proceso de ejemplo** ("Gestión de reclamos de clientes") — sintético, armado
   para validar el pipeline completo.
2. **Proceso preanalítico de AnalyticsNoa** — relevamiento real de Fer, con un loop
   real (vuelta de "¿muestra en condiciones? → No" hacia un paso anterior). Confirmó
   que el layout y el manejo de loops funcionan sobre datos reales.

Funcionalidades confirmadas:

- Conversión planilla Excel → JSON → PowerPoint.
- Formas por tipo de paso: óvalo (Inicio/Fin), rectángulo redondeado (Proceso), rombo
  (Decisión).
- Bloques de fase con borde punteado y color automático por fase.
- Ramas de decisión con etiqueta (ej. "Sí"/"No").
- Detección automática de loops (vueltas hacia atrás) vía DFS, para que no rompan el
  cálculo de filas — se dibujan enrutadas por un carril lateral a la derecha.
- Enrutamiento en ángulo recto (no diagonal) para saltos de más de una fila, evitando
  que una flecha pase por detrás de otra caja.
- Validación de archivo (`validate.py` del skill de pptx) y QA visual (conversión a
  imagen) antes de entregar.

## Estructura de archivos

```
flowchart_tool/
├── planilla_flujograma.xlsx    # plantilla: hoja Instrucciones + Proceso (vacía) + Ejemplo (cargada)
├── xlsx_to_json.py             # planilla → JSON de pasos
├── generate_flowchart.js       # JSON de pasos → .pptx (requiere pptxgenjs, ver package.json)
├── flujograma_ejemplo.pptx     # resultado del caso de ejemplo
├── flujograma_analyticsnoa.pptx # resultado del proceso preanalítico real
└── flujograma-proceso.skill    # la herramienta empaquetada como skill de Claude
```

## Esquema de la planilla

Una fila por paso del proceso. Columnas:

| Columna | Contenido |
|---|---|
| `ID` | Identificador único (I1, P1, D1, F1...) |
| `Nombre` | Texto corto del paso |
| `Tipo` | `Inicio/Fin`, `Proceso`, `Decisión`, `Documento`, `Conector` |
| `Fase` | Etapa macro que agrupa pasos (define los bloques punteados) |
| `Carril` | Actor/área responsable (hoy se guarda pero no se dibuja visualmente todavía) |
| `Siguientes` | ID(s) del/los paso(s) siguiente(s), separados por coma |
| `Etiqueta_rama` | Si `Tipo=Decisión` con más de un `Siguiente`: etiqueta de cada rama en el mismo orden (ej. `Sí,No`) |
| `Notas` | Aclaración libre (referencia a formulario, sistema, anexo) |

Un `Siguiente` que apunta a un paso anterior es simplemente un loop — no requiere
marcarlo de forma especial, la herramienta lo detecta sola.

## Cómo se usa (línea de comandos)

```bash
python3 xlsx_to_json.py planilla_flujograma.xlsx Proceso pasos.json
node generate_flowchart.js pasos.json "Nombre del proceso" salida.pptx
```

## Cómo arma el diagrama (lógica interna, para debug futuro)

- **Filas** = orden topológico del proceso, calculado ignorando los arcos de retroceso
  (se identifican con un DFS de detección de ciclos antes de calcular niveles).
- **Columnas** = ramas en paralelo dentro de una fila; el algoritmo intenta heredar la
  columna del predecesor para mantener el flujo recto, y busca la columna libre más
  cercana si hay conflicto.
- **Fases** = se agrupan filas consecutivas por la fase dominante de esa fila, y se
  dibuja un bloque punteado por fase con su propio color (asignado por orden de
  aparición desde una paleta fija).
- **Conectores**: fila siguiente inmediata → línea directa (recta o diagonal); misma
  fila → línea lateral; salto de más de una fila o vuelta hacia atrás → rodea por un
  carril fijo a la derecha del diagrama, en ángulo recto, para no cruzar cajas
  intermedias.

## Limitaciones conocidas / próximos pasos

- **No dibuja carriles de actor (swimlanes).** La columna `Carril` se guarda en los
  datos pero no tiene representación visual todavía. Es la extensión más pedida por
  el estilo Visio de referencia.
- **Sin íconos de actor ni notas de documento con línea de referencia**, como en el
  flujograma viejo de Visio que mostró Fer (persona + etiqueta al costado, hoja de
  documento conectada con línea fina). Hoy las notas van como texto chico debajo de
  la caja.
- **Sin conectores de entrada/salida (E/S)** para vincular este flujograma con otros
  procesos dentro de un mapa macro de procesos del SGC — necesario si se quiere
  encadenar varios flujogramas entre sí.
- **Carril lateral único para rutas largas**: si dos saltos de fila caen en la misma
  zona del diagrama, sus líneas pueden superponerse ahí (cosmético, se corrige a
  mano en PowerPoint). Solucionable asignando varios carriles en vez de uno solo.

Estas son las líneas de trabajo naturales para la siguiente iteración, ya evaluadas
en la conversación pero pospuestas para validar primero el flujo básico end-to-end.

## Empaquetado

La herramienta quedó empaquetada como skill de Claude (`flujograma-proceso.skill`,
en `flowchart_tool/`), con el `SKILL.md`, los scripts y la plantilla de planilla
incluidos. Pendiente: sumarla al repo del proyecto Hermes (ubicación a definir por
Fer — no se encontró un repo Git en las carpetas conectadas a esta sesión).

## Skill hermana: instructivo → planilla (2026-08-02)

Se armó una segunda skill, `instructivo_a_flujograma`, en
`repo-cnn-agente_LISTO/_agente/skills/instructivo_a_flujograma/`. Invierte el primer
paso del flujo de arriba: en vez de relevar el proceso a mano y completar la planilla,
parte de un instructivo del cliente ya redactado (ISO 9001, PDF/Word) y genera un
borrador de `planilla_flujograma.xlsx` vía LLM, con una columna extra `Confianza`
(Alta/Media/Baja) para que la revisión se enfoque en lo que el modelo tuvo que
inferir. El resultado se pasa tal cual a `xlsx_to_json.py` + `generate_flowchart.js`
de esta carpeta — no cambia nada del pipeline planilla → pptx. Probada con dos
instructivos reales de LACE (AGGP05I01 y TGGI09); ver README de esa skill para el
detalle de los casos de prueba y las reglas de extracción (qué cuenta como paso, qué
se ignora, cómo trata las cláusulas "en caso de no cumplir...").

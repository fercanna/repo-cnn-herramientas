# 🎯 CÓMO FUNCIONA EL SISTEMA DE TRIAGE AUTOMÁTICO

## 📌 VISIÓN GENERAL

El sistema automatiza el análisis y gestión de hallazgos de calidad, reduciendo dramáticamente el trabajo manual:

**ANTES:**
- ❌ Analizar 120 hallazgos uno por uno
- ❌ Crear 120 documentos individuales
- ❌ Revisar y eliminar manualmente los no pertinentes
- ❌ Migrar manualmente a Trello
- ❌ Horas de trabajo administrativo

**AHORA:**
- ✅ Análisis automático al enviar formulario
- ✅ Solo se procesan los hallazgos de alto riesgo
- ✅ Tarjetas de Trello creadas automáticamente
- ✅ Agrupación inteligente de hallazgos similares
- ✅ 90% menos de trabajo manual

---

## 🔄 FLUJO AUTOMÁTICO PASO A PASO

### 1️⃣ UN USUARIO REPORTA UN HALLAZGO (Google Form)

```
Usuario → Llena formulario → Submit
```

El formulario guarda los datos en el Google Sheet como siempre.

---

### 2️⃣ TRIGGER AUTOMÁTICO SE ACTIVA

```
onFormSubmit() → Se ejecuta automáticamente
```

**¿Cuándo?** Inmediatamente después de que se envía el formulario.

**¿Qué hace?** Llama a la función `triageHallazgo()` con el número de la nueva fila.

---

### 3️⃣ EVALUACIÓN DE GRAVEDAD (Gemini AI)

```
triageHallazgo() → evaluarGravedad()
```

**Gemini analiza el hallazgo y lo clasifica:**

- 🔴 **CRÍTICA**: Riesgo para el paciente, error de identificación, violación legal grave
- 🟠 **MAYOR**: Compromete el diagnóstico, pérdida de muestra, controles fuera de rango
- 🟡 **MENOR**: Impacto operativo, demoras leves, errores administrativos
- ⚪ **INSIGNIFICANTE**: Sin impacto real, consultas triviales

**Ejemplo:**
```
Descripción: "Paciente Kopelman Eduardo DNI 10680468. Se le solicita antígeno urinario 
de histoplasma y en lugar de pedirle orina se le toma muestra de sangre."

Gemini evalúa → GRAVEDAD: MAYOR
(Compromete el diagnóstico, requiere nueva muestra)
```

**Resultado se guarda en Columna O**

---

### 4️⃣ CÁLCULO DE FRECUENCIA (Búsqueda de similares)

```
triageHallazgo() → buscarHallazgosSimilares()
```

**El script busca hallazgos similares en los últimos 30 días:**

1. Compara la misma **FASE** (Preanalítica, Analítica, Postanalítica)
2. Analiza **similitud textual** de las descripciones
3. Cuenta cuántos hallazgos parecidos hay

**Ejemplo:**
```
Hallazgo actual: "Secretaria Coti no hizo firmar consentimiento HIV..."

Busca en los últimos 30 días → Encuentra:
- Fila 52: "Secretaria Nati no hizo firmar consentimiento HIV..."
- Fila 60: "Secretaria Caro Zalazar no hizo firmar consentimiento HIV..."
- ... (y más)

FRECUENCIA: 12 (incluyendo el actual)
```

**Resultado se guarda en Columna P**

---

### 5️⃣ CÁLCULO DE RIESGO (Matriz de Riesgo)

```
triageHallazgo() → calcularRiesgo(gravedad, frecuencia)
```

**Aplica la matriz de riesgo ISO:**

| GRAVEDAD | FRECUENCIA Alta (3+) | FRECUENCIA Media (2) | FRECUENCIA Baja (1) |
|----------|---------------------|---------------------|---------------------|
| **CRÍTICA** | 🔴 ALTO | 🔴 ALTO | 🔴 ALTO |
| **MAYOR** | 🔴 ALTO | 🔴 ALTO | 🟠 MEDIO |
| **MENOR** | 🟠 MEDIO | 🟡 BAJO | 🟡 BAJO |
| **INSIGNIFICANTE** | 🟡 BAJO | ⚪ NO PERTINENTE | ⚪ NO PERTINENTE |

**Ejemplo (Consentimientos HIV):**
```
GRAVEDAD: MAYOR (compromete aspecto legal)
FRECUENCIA: 12

RIESGO = ALTO 🔴
```

**Resultado se guarda en Columna Q**

---

### 6️⃣ CLASIFICACIÓN DE CATEGORÍA (Gemini AI)

```
triageHallazgo() → clasificarCategoria()
```

**Gemini asigna una categoría para agrupar hallazgos similares:**

Categorías principales:
- "Consentimiento HIV"
- "Rotulación/Identificación de muestra"
- "Almacenamiento de muestra"
- "Transporte de muestra"
- "Control de Calidad"
- "Ingreso de orden"
- "Pedido médico"
- "Comunicación interna"
- "Stock/Insumos"
- "Equipamiento"
- "Procesamiento de muestra"

**Ejemplo:**
```
Descripción: "Secretaria no hizo firmar consentimiento HIV..."

Gemini clasifica → CATEGORIA: "Consentimiento HIV"
```

**Resultado se guarda en Columna R**

---

### 7️⃣ DECISIÓN: ¿ES AGRUPABLE?

```
triageHallazgo() → Evalúa si FRECUENCIA >= 3 Y RIESGO != ALTO
```

**Lógica:**
- Si `FRECUENCIA >= 3` Y `RIESGO != ALTO` → `AGRUPABLE: SÍ`
- Estos hallazgos se procesarán en lote a fin de mes
- Si `RIESGO = ALTO` → `AGRUPABLE: NO` (se procesa inmediatamente)

**Resultado se guarda en Columna S**

---

### 8️⃣ BIFURCACIÓN: ¿RIESGO ALTO?

```
SI RIESGO = ALTO → procesarAltoRiesgo()
SI RIESGO != ALTO → Esperar procesamiento mensual
```

#### 🔴 RUTA A: RIESGO ALTO (Procesamiento Inmediato)

```
procesarAltoRiesgo()
  ├─ analizarCausaRaizIndividual() → Análisis profundo con Gemini
  ├─ crearTarjetaTrelloAltoRiesgo() → Crea tarjeta en Trello
  └─ escribirInfoTrello() → Guarda link en Sheet
```

**¿Qué pasa?**

1. **Análisis de Causa Raíz Individual** (Gemini):
   - Aplica técnica de los "5 Porqués"
   - Genera plan de acción con:
     - Acciones inmediatas (contención)
     - Acciones correctivas (eliminar causa raíz)
     - Acciones preventivas (evitar recurrencia)
     - Lección aprendida

2. **Creación de Tarjeta en Trello**:
   - Se crea en la lista "PENDIENTE"
   - Título: `[Fase] Categoría - Hallazgo #ID`
   - Descripción completa con toda la info
   - Etiqueta: "RIESGO CONSIDERABLE"
   - Checklist automático con acciones inmediatas

3. **Actualización del Sheet**:
   - Columna T: ID de la tarjeta
   - Columna U: Link a la tarjeta
   - Columna V: "En Trello - Alto Riesgo"

**Ejemplo de tarjeta creada:**

```
Título: [Analítica] Cruce de muestras - Hallazgo #055

Descripción:
🔴 HALLAZGO DE ALTO RIESGO
Gravedad: CRÍTICA
Categoría: Rotulación/Identificación de muestra
Fecha: 02/05/2025
Notificado por: Ines Microbiología

DESCRIPCIÓN DEL HALLAZGO:
Recipiente mal rotulado dice Torres Amparo pero es Tobares Amparo...

ANÁLISIS DE CAUSA RAÍZ:
1er Porqué: Rotulación incorrecta
2do Porqué: Personal médico no siguió protocolo...
[Análisis completo]

ACCIONES INMEDIATAS:
☐ Verificar todos los tubos del día con discrepancias
☐ Comunicar a jefes médicos del piso
☐ Reforzar protocolo de doble chequeo

ACCIONES CORRECTIVAS:
☐ Implementar código de barras obligatorio
☐ Capacitación específica a personal médico

ACCIONES PREVENTIVAS:
☐ Auditoría semanal de rotulación
☐ Sistema de alertas en HIS

LECCIÓN APRENDIDA:
El doble chequeo de identidad debe ser obligatorio sin excepciones
```

#### 🟡 RUTA B: RIESGO MEDIO/BAJO (Procesamiento Mensual)

```
Hallazgo marcado como "Triado"
Espera a procesarGruposMensuales() → FASE 3 (próxima implementación)
```

Estos hallazgos se agruparán a fin de mes y tendrán UN análisis de causa raíz por GRUPO.

---

## 📊 RESULTADO FINAL EN EL SHEET

Después del triage, cada fila tendrá:

| Columna | Campo | Ejemplo |
|---------|-------|---------|
| O | GRAVEDAD_IA | MAYOR |
| P | FRECUENCIA | 12 |
| Q | RIESGO_IA | ALTO |
| R | CATEGORIA_IA | Consentimiento HIV |
| S | AGRUPABLE | NO |
| T | TRELLO_CARD_ID | 6a7b8c9d... |
| U | TRELLO_CARD_URL | https://trello.com/c/abc123 |
| V | ESTADO_PROCESAMIENTO | En Trello - Alto Riesgo |

---

## 🎯 VENTAJAS DEL SISTEMA

### Para Hallazgos de ALTO RIESGO:
✅ **Detección inmediata** - No espera a fin de mes
✅ **Análisis profundo individual** - Causa raíz + plan de acción
✅ **Tarjeta en Trello automática** - Con checklist de acciones
✅ **Trazabilidad completa** - Link directo desde el Sheet

### Para Hallazgos de MEDIO/BAJO Riesgo:
✅ **Clasificación automática** - Sin intervención manual
✅ **Agrupación inteligente** - Los similares se procesan juntos
✅ **Análisis eficiente** - Un análisis por grupo, no por hallazgo
✅ **Priorización** - Se atienden primero los de alto riesgo

### Para Hallazgos NO PERTINENTES:
✅ **Filtrado automático** - Marcados pero no procesados
✅ **Visibilidad** - Quedan registrados para auditoría
✅ **Sin ruido** - No generan tarjetas ni distraen

---

## 🔢 IMPACTO EN NÚMEROS

**Escenario real: 120 hallazgos en 2.5 meses**

### ANTES (Sistema Manual):
- 120 análisis individuales con IA
- 120 documentos de Word generados
- ~60 documentos eliminados manualmente (no pertinentes)
- ~60 documentos revisados y editados
- ~40 hallazgos migrados a Trello manualmente
- **Tiempo estimado: 20-30 horas/mes**

### AHORA (Sistema Automático):

**Hallazgos de ALTO RIESGO (~15% = 18 hallazgos):**
- ✅ 18 análisis automáticos completos
- ✅ 18 tarjetas Trello creadas automáticamente
- ⏱️ Tiempo de intervención manual: **0 horas** (solo revisión en Trello)

**Hallazgos de MEDIO/BAJO RIESGO (~70% = 84 hallazgos):**
- ✅ Clasificados automáticamente
- ✅ Agrupados en ~10-15 categorías
- ✅ Análisis por grupo (no individual)
- ⏱️ Tiempo de intervención: **2-3 horas/mes** (revisión de grupos)

**Hallazgos NO PERTINENTES (~15% = 18 hallazgos):**
- ✅ Filtrados automáticamente
- ✅ No generan ruido
- ⏱️ Tiempo de intervención: **0 horas**

**TIEMPO TOTAL: 2-3 horas/mes** (reducción del 90%)

---

## 🚀 PRÓXIMAS FASES

### FASE 2: Integración Completa con Trello (Completada)
✅ Tarjetas de alto riesgo creadas automáticamente
✅ Checklists con acciones
✅ Etiquetas de riesgo
✅ Links bidireccionales Sheet ↔ Trello

### FASE 3: Agrupación Mensual (En desarrollo)
- Función `procesarGruposMensuales()`
- Análisis de causa raíz por GRUPO
- Tarjetas agrupadas en Trello (Ej: "Consentimientos HIV - 12 casos")
- Informe mensual automatizado

### FASE 4: Dashboard e Informes (Futuro)
- Métricas automáticas: hallazgos por fase, tendencias, KPIs
- Gráficos de evolución
- Informe ejecutivo mensual
- Email automático a responsables

---

## 💡 CONSEJOS DE USO

### Para aprovechar al máximo el sistema:

1. **Confía en el triage inicial**: Gemini está entrenado con criterios ISO, su evaluación es confiable

2. **Revisa las tarjetas de Alto Riesgo en Trello**: Son las que realmente importan y necesitan acción inmediata

3. **No te preocupes por los hallazgos clasificados como Bajo/Medio**: Se procesarán eficientemente en grupos

4. **Usa los filtros del Sheet**: Filtra por `RIESGO_IA = ALTO` para ver solo lo urgente

5. **Monitorea los logs**: Si algo falla, los logs de Apps Script te dirán exactamente qué pasó

6. **Ajusta umbrales si es necesario**: Si 3 hallazgos te parecen poco para agrupar, podés cambiar `UMBRAL_AGRUPACION` en el código

---

## ❓ PREGUNTAS FRECUENTES

### ¿Qué pasa si Gemini se equivoca en la clasificación?
Podés ejecutar el triage manualmente de nuevo en esa fila. O simplemente editá las columnas O-Q manualmente.

### ¿Puedo desactivar el procesamiento automático?
Sí, deshabilitá el trigger `onFormSubmit` en la sección de Activadores de Apps Script.

### ¿Los hallazgos antiguos se procesan automáticamente?
No, solo los nuevos que se envíen por el formulario. Si querés procesar antiguos, usá "Ejecutar Triage Manual" fila por fila.

### ¿Cuánto cuesta usar la API de Gemini?
Google AI tiene una cuota gratuita generosa. Para este volumen (120 hallazgos/mes) no deberías pagar nada.

### ¿Se pueden personalizar las categorías?
Sí, editá el prompt en la función `clasificarCategoria()` y agregá/quitá categorías según necesites.

---

## 📈 MÉTRICAS DE ÉXITO

Para evaluar si el sistema está funcionando bien, monitoreá:

- ✅ **% de hallazgos clasificados automáticamente**: Debería ser ~100%
- ✅ **Tiempo promedio de creación de tarjeta**: Debería ser <30 segundos
- ✅ **% de falsos positivos en Alto Riesgo**: Debería ser <10%
- ✅ **Horas ahorradas por mes**: Debería ser >15 horas

---

¡El sistema está diseñado para aprender y mejorar con el tiempo! 🚀

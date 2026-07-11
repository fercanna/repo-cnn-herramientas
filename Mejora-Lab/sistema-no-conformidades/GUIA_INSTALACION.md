# 📋 GUÍA DE INSTALACIÓN - MÓDULO DE TRIAGE AUTOMÁTICO

## ✅ FASE 1: Triage Automático con Integración Trello

### Pre-requisitos completados:
- [x] Columnas nuevas agregadas al Sheet (O a V)
- [x] Credenciales de Trello obtenidas
- [x] API Key de Google AI configurada

---

## 📝 PASOS DE INSTALACIÓN

### 1. Abrir el Editor de Apps Script

1. En tu Google Sheet, ve a **Extensiones → Apps Script**
2. Se abrirá el editor con tu script actual

### 2. Agregar el Módulo de Triage

**Opción A: Crear archivo nuevo (RECOMENDADO)**
1. En el editor de Apps Script, haz clic en el **+** junto a "Archivos"
2. Selecciona **Script**
3. Nómbralo: `ModuloTriage`
4. Copia TODO el contenido del archivo `modulo_triage_trello.js`
5. Pégalo en este nuevo archivo
6. Guarda (Ctrl+S o Cmd+S)

**Opción B: Agregar al script existente**
1. Ve al final de tu script actual
2. Agrega un comentario: `// === MÓDULO DE TRIAGE ===`
3. Copia TODO el contenido del archivo `modulo_triage_trello.js`
4. Pégalo después del comentario
5. Guarda

### 3. Actualizar la función `onOpen()`

**IMPORTANTE:** Tu script ya tiene una función `onOpen()`. Hay dos opciones:

**Opción A: Reemplazar (RECOMENDADO si no has personalizado mucho el menú)**
- Busca tu función `onOpen()` actual
- Reemplázala completamente con la que está en el módulo de triage (líneas finales del archivo)

**Opción B: Fusionar (si tienes muchas personalizaciones)**
- Mantén tu función `onOpen()` actual
- Solo agrega esta sección antes del `.addToUi()`:
```javascript
.addSeparator()
.addSubMenu(SpreadsheetApp.getUi().createMenu('🔥 Sistema de Triage')
  .addItem('▶️ Ejecutar Triage en Fila Seleccionada', 'ejecutarTriageManual')
  .addItem('📊 Procesar Grupos Mensuales', 'procesarGruposMensuales')
  .addItem('🧪 Test: Crear Tarjeta de Prueba', 'testCrearTarjetaTrello'))
```

### 4. Configurar el Trigger Automático

1. En el editor de Apps Script, haz clic en el **ícono del reloj** ⏰ (Triggers/Activadores) en el menú lateral izquierdo
2. Haz clic en **+ Agregar activador** (abajo a la derecha)
3. Configura así:
   - **Elige la función que deseas ejecutar:** `onFormSubmit`
   - **Elige el origen del evento:** `Desde una hoja de cálculo`
   - **Tipo de evento:** `Al enviar un formulario`
   - **Notificaciones de fallos:** `Notificarme diariamente`
4. Haz clic en **Guardar**
5. Te pedirá autorizar permisos - **ACEPTA TODO**

### 5. Actualizar CONFIG.COLUMNAS en el script original

En tu script original (el que ya tenías), busca la sección `CONFIG.COLUMNAS` y **verifica** que coincida con esta estructura:

```javascript
COLUMNAS: {
  ID: 0,                           // Col A
  MARCA_TEMPORAL: 1,               // Col B
  EMAIL_NOTIFICA: 2,               // Col C
  QUIEN_NOTIFICA: 3,               // Col D
  FASE: 4,                         // Col E
  TIPO_HALLAZGO: 5,                // Col F
  PRIORIDAD: 6,                    // Col G
  DESCRIPCION: 7,                  // Col H
  LINK_EVIDENCIA: 8,               // Col I
  ANALISIS_CAUSA_RAIZ: 9,          // Col J
  PLAN_MEJORA: 10,                 // Col K
  OBSERVACIONES: 11,               // Col L
  LINK_INFORME: 12,                // Col M
  CLASIFICACION_IA: 13             // Col N
}
```

**Las nuevas columnas (O a V) están definidas en `CONFIG_TRIAGE.COLUMNAS_NUEVAS`, no hace falta modificar nada más.**

---

## 🧪 PRUEBA DE FUNCIONAMIENTO

### Test 1: Crear Tarjeta de Prueba en Trello

1. Recarga tu Google Sheet (F5)
2. Verás un nuevo menú: **"Gestión de Calidad (Lab)"**
3. Ve a: **Sistema de Triage → 🧪 Test: Crear Tarjeta de Prueba**
4. Debería aparecer un diálogo con un link a la tarjeta creada en Trello
5. Abre el link y verifica que la tarjeta se creó correctamente en la lista "PENDIENTE"

**Si funciona → ✅ La integración con Trello está OK**

### Test 2: Ejecutar Triage Manual en una Fila

1. Selecciona una fila con datos (cualquier hallazgo existente)
2. Ve a: **Sistema de Triage → ▶️ Ejecutar Triage en Fila Seleccionada**
3. Espera unos segundos (Gemini está procesando)
4. Revisa las columnas O a V - deberían tener valores:
   - Columna O: GRAVEDAD_IA (Ej: "MAYOR")
   - Columna P: FRECUENCIA (Ej: "2")
   - Columna Q: RIESGO_IA (Ej: "MEDIO")
   - Columna R: CATEGORIA_IA (Ej: "Consentimiento HIV")
   - Columna S: AGRUPABLE (Ej: "NO")
   - Columna V: ESTADO_PROCESAMIENTO (Ej: "Triado")

**Si funciona → ✅ El triage está OK**

### Test 3: Prueba Automática con Formulario

1. Abre tu Google Form vinculado
2. Llena un hallazgo de prueba (usa algo realista para que Gemini lo evalúe bien)
3. Envía el formulario
4. Espera 10-20 segundos
5. Revisa la última fila del Sheet - debería tener las columnas O a V completadas

**Si funciona → ✅ El trigger automático está OK**

**Si además es RIESGO ALTO → debería haber creado una tarjeta en Trello automáticamente**

---

## 🔍 VERIFICACIÓN DE COLUMNAS

Tu Sheet debería tener esta estructura:

| A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q | R | S | T | U | V |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ID | Marca temporal | Email | Quién notifica | Fase | Tipo hallazgo | Prioridad | Descripción | Link evidencia | Análisis causa raíz | Plan mejora | Observaciones | Link informe | Clasificación IA | **GRAVEDAD_IA** | **FRECUENCIA** | **RIESGO_IA** | **CATEGORIA_IA** | **AGRUPABLE** | **TRELLO_CARD_ID** | **TRELLO_CARD_URL** | **ESTADO_PROCESAMIENTO** |

---

## ⚠️ SOLUCIÓN DE PROBLEMAS

### Problema 1: "onFormSubmit no está definido"
**Solución:** Asegúrate de haber copiado TODO el módulo de triage, incluyendo la función `onFormSubmit()`.

### Problema 2: "No se crea tarjeta en Trello"
**Verificar:**
1. API Key y Token correctos en `TRELLO_CONFIG`
2. ID del tablero correcto
3. ID de la lista "PENDIENTE" correcto
4. Permisos del script (volver a autorizar en Triggers)

**Revisar logs:**
- En Apps Script, ve a **Ejecuciones** (menú lateral)
- Busca errores en las ejecuciones recientes

### Problema 3: "Gemini no responde o da error"
**Verificar:**
1. API Key de Google AI configurada correctamente
2. En el menú: **Gestión de Calidad (Lab) → 1. Configurar API Key**
3. Pega tu API Key nuevamente

### Problema 4: Trigger no se ejecuta automáticamente
**Solución:**
1. Ve a **Activadores** (reloj ⏰)
2. Elimina el trigger existente
3. Créalo de nuevo siguiendo el paso 4 de la instalación
4. Asegúrate de seleccionar "Al enviar un formulario" (no "Al editar")

---

## 📊 LOGS Y MONITOREO

Para ver qué está pasando detrás de escena:

1. En Apps Script, ve a **Ejecuciones** (menú lateral izquierdo)
2. Verás todas las ejecuciones recientes del script
3. Haz clic en cualquiera para ver el log detallado
4. Busca líneas como:
   - `[onFormSubmit] Procesando nueva fila: X`
   - `[triageHallazgo] Gravedad evaluada: MAYOR`
   - `[procesarAltoRiesgo] Tarjeta creada: https://...`

---

## ✅ CHECKLIST FINAL

Antes de poner en producción, verifica:

- [ ] Script del módulo copiado completamente
- [ ] Función `onOpen()` actualizada
- [ ] Trigger `onFormSubmit` configurado
- [ ] Test de tarjeta de prueba exitoso
- [ ] Test de triage manual exitoso
- [ ] Test de formulario real exitoso
- [ ] Columnas O a V visibles y funcionando
- [ ] Tarjetas se crean en Trello correctamente

---

## 🚀 SIGUIENTE FASE

Una vez que esta FASE 1 esté funcionando correctamente durante algunos días:

**FASE 2: Análisis de Grupos Mensuales**
- Agrupación automática de hallazgos similares
- Análisis de causa raíz por grupo (no individual)
- Creación de tarjetas agrupadas en Trello
- Informe mensual automatizado

**¿Todo funcionando? ¡Felicitaciones! 🎉**

---

## 📞 SOPORTE

Si algo no funciona:
1. Revisa los logs en "Ejecuciones"
2. Verifica las credenciales de Trello
3. Asegúrate de que las columnas estén en el orden correcto
4. Comparte el error específico que aparece en los logs


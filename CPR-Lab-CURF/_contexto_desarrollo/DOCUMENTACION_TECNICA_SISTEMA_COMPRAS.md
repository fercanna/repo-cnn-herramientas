# DOCUMENTACIÃ“N TECNICA - Sistema de GestiÃ³n de Compras e Inventario CURF

**VersiÃ³n:** 2.1  
**Fecha:** Febrero 2026  
**Cliente:** Laboratorio CURF (MicrobiologÃ­a)  
**Desarrollador:** Fernando (BioquÃ­mico - Consultor ISO)  

---

## ðŸŽ¯ DESCRIPCIÃ“N GENERAL

Sistema completo de gestiÃ³n de compras e inventario para laboratorio de microbiologÃ­a, construido sobre Google Sheets + Apps Script. Gestiona el ciclo completo: desde la creaciÃ³n de Ã³rdenes de compra hasta el control de stock con metodologÃ­a FIFO y alertas de criticidad.

---

## ðŸ“Š ESTRUCTURA DE HOJAS

### 1. **Insumos** (CatÃ¡logo Maestro)
CatÃ¡logo de productos disponibles para compra.

**Columnas:**
- `codigo_insumo` (ej: INS001, INS002...)
- `descripcion` (ej: "Kit PCR SARS-CoV-2")
- `categoria` (ej: "REACTIVOS", "CONSUMIBLES")
- `clasificacion` (opcional)
- `precio_referencial` (nÃºmero)
- `stock_critico` (nÃºmero - umbral de alerta)
- `activo` (TRUE/FALSE)

---

### 2. **Proveedores** (CatÃ¡logo de Proveedores)
Listado de proveedores activos.

**Columnas:**
- `codigo_proveedor` (ej: PROVE24)
- `razon_social` (ej: "DroguerÃ­a XYZ S.A.")
- `contacto` (opcional)
- `telefono` (opcional)
- `email` (opcional)
- `activo` (TRUE/FALSE)

---

### 3. **Ordenes_Compra** (Cabecera de Ã“rdenes)
Registro de Ã³rdenes de compra generadas.

**Columnas:**
- A: `numero_orden` (ej: OC-2026-001)
- B: `fecha_emision` (fecha)
- C: `codigo_proveedor` (ej: PROVE24)
- D: `nombre_proveedor` (ej: "DroguerÃ­a XYZ S.A.") **â† NUEVA COLUMNA agregada**
- E: `estado` (Pendiente | RecepciÃ³n Parcial | Recepcionada | Cancelada)
- F: `usuario_solicita` (email)
- G: `fecha_entrega_estimada` (fecha)
- H: `total_orden` (nÃºmero)
- I: `observaciones` (texto)

**Estados posibles:**
- `Pendiente`: Orden creada, sin recepciones
- `RecepciÃ³n Parcial`: Algunos items recibidos, otros pendientes
- `Recepcionada`: Todos los items recibidos completamente
- `Cancelada`: Orden cancelada

---

### 4. **Detalle_Ordenes** (Items de cada orden)
Detalle de productos solicitados en cada orden.

**Columnas:**
- `numero_orden` (relaciÃ³n con Ordenes_Compra)
- `item` (1, 2, 3...)
- `codigo_insumo` (relaciÃ³n con Insumos)
- `descripcion` (nombre del producto)
- `cantidad` (cantidad solicitada)
- `precio_unitario` (nÃºmero)
- `subtotal` (cantidad Ã— precio)
- `cantidad_recepcionada` (acumulado de lo recibido)
- `estado_item` (Pendiente | Parcial | Completo)
- `fecha_pedido` (fecha de emisiÃ³n de la orden)

---

### 5. **Recepciones** (Cabecera de Recepciones)
Registro de recepciones realizadas.

**Columnas:**
- `numero_recepcion` (ej: REC-2026-001)
- `fecha_recepcion` (fecha/hora)
- `numero_orden` (relaciÃ³n con Ordenes_Compra)
- `usuario_recibe` (email)
- `observaciones` (texto general de la recepciÃ³n)
- `tiene_discrepancias` (TRUE si hay No Conforme)

---

### 6. **Detalle_Recepciones** (Items recibidos)
Detalle de productos recepcionados con trazabilidad.

**Columnas:**
- `numero_recepcion` (relaciÃ³n con Recepciones)
- `item` (1, 2, 3...)
- `codigo_insumo` (relaciÃ³n con Insumos)
- `nombre_insumo` (descripciÃ³n del producto)
- `cantidad_recibida` (lo que efectivamente ingresÃ³)
- `cantidad_esperada` (lo que estaba pendiente)
- `estado_conformidad` (Conforme | Conforme Parcial | No Conforme) **â† Con formato condicional**
- `observaciones` (texto especÃ­fico del item)
- `lote` (obligatorio - trazabilidad)
- `vencimiento` (fecha)
- `categoria` (REACTIVOS, CONSUMIBLES, etc.)

**Formato condicional aplicado:**
- ðŸŸ¢ Verde: "Conforme"
- ðŸŸ¡ Amarillo: "Conforme Parcial"
- ðŸ”´ Rojo: "No Conforme"

---

### 7. **Movimientos_Inventario** (Trazabilidad completa)
Registro de todos los movimientos (ingresos/egresos).

**Columnas:**
- `id_movimiento` (ej: MOV-1234567890-abc12)
- `fecha` (fecha/hora)
- `tipo_movimiento` (Ingreso | Egreso | Ajuste)
- `codigo_insumo`
- `nombre_insumo`
- `cantidad` (nÃºmero positivo)
- `referencia` (nÃºmero de recepciÃ³n o motivo)
- `usuario` (quien registrÃ³)
- `observaciones`
- `lote`
- `vencimiento`
- `categoria`

**Formato condicional aplicado:**
- ðŸŸ¢ Verde claro: "Ingreso"
- ðŸ”´ Rojo claro: "Egreso"

---

### 8. **Stock_Actual** (Vista FIFO del inventario)
Vista calculada automÃ¡ticamente. **NO editar manualmente.**

**Columnas:**
- A: `codigo_insumo`
- B: `descripcion`
- C: `stock_disponible` (cantidad del lote especÃ­fico)
- D: `stock_critico` (umbral de alerta)
- E: `estado_stock` (OK | CrÃ­tico | Agotado) **â† Evaluado por stock TOTAL del insumo**
- F: `ultima_actualizacion` (timestamp)
- G: `lote`
- H: `vencimiento` (fecha)
- I: `clasificacion`

**LÃ³gica de estado (corregida en Ãºltima versiÃ³n):**
- Estado se calcula sumando TODOS los lotes del mismo insumo
- Si stock_total > stock_critico â†’ "OK" âœ…
- Si stock_total â‰¤ stock_critico y > 0 â†’ "CrÃ­tico" âš ï¸
- Si stock_total â‰¤ 0 â†’ "Agotado" ðŸ”´

**Ordenamiento:** Por vencimiento ascendente (FIFO) - los mÃ¡s prÃ³ximos a vencer primero.

**Formato condicional aplicado:**
- ðŸŸ¢ Verde: "OK"
- ðŸŸ¡ Amarillo: "CrÃ­tico"
- ðŸ”´ Rojo: "Agotado"

---

### 9. **Dashboard** (Vista ejecutiva)
Panel de control con KPIs y alertas consolidadas. Se actualiza con `actualizarDashboard()`.

**Contenido actual:**
- **Tarjeta 1:** Ã“rdenes Pendientes (cuenta: Pendiente + RecepciÃ³n Parcial)
- **Tarjeta 2:** Stock CrÃ­tico (insumos con stock total â‰¤ crÃ­tico)
- **Tarjeta 3:** Insumos Agotados (stock total = 0)
- **Tabla de alertas:** Productos crÃ­ticos/agotados con stock consolidado

**Nota:** Stock consolidado = suma de todos los lotes por `codigo_insumo`

---

### 10. **Bajas_Consumo** (Formulario de egreso)
Interfaz para registrar consumo de insumos con lÃ³gica FIFO.

**Estructura:**
- **B2:** Input de bÃºsqueda (cÃ³digo o nombre de insumo)
- **C2:** CÃ³digo encontrado (automÃ¡tico)
- **D2:** DescripciÃ³n (automÃ¡tico)
- **B3:** Desplegable de lotes disponibles (ordenados por vencimiento FIFO)
- **C3:** Info del lote: "Stock: X | Vence: DD/MM/AAAA"
- **B4:** Cantidad a consumir
- **B5:** Observaciones
- **BotÃ³n:** REGISTRAR CONSUMO (ejecuta `procesarBajaDesdeHoja()`)

**LÃ³gica implementada en `onEdit()`:**
1. Usuario escribe en B2 (cÃ³digo o nombre)
2. Script busca el insumo en Stock_Actual
3. Filtra lotes con stock > 0
4. Ordena por vencimiento (FIFO)
5. Crea desplegable en B3
6. Preselecciona el lote mÃ¡s prÃ³ximo a vencer
7. Muestra info del lote en C3

---

## ðŸ”§ FUNCIONES PRINCIPALES DEL SCRIPT

### **ConfiguraciÃ³n Global**

```javascript
const CONFIG = {
  SHEETS: {
    INSUMOS: 'Insumos',
    PROVEEDORES: 'Proveedores',
    ORDENES: 'Ordenes_Compra',
    DETALLE_ORDENES: 'Detalle_Ordenes',
    RECEPCIONES: 'Recepciones',
    DETALLE_RECEPCIONES: 'Detalle_Recepciones',
    MOVIMIENTOS: 'Movimientos_Inventario',
    STOCK: 'Stock_Actual',
    DASHBOARD: 'Dashboard'
  },
  ESTADOS: {
    ORDEN: {
      PENDIENTE: 'Pendiente',
      PARCIAL: 'RecepciÃ³n Parcial',
      RECEPCIONADA: 'Recepcionada',
      CANCELADA: 'Cancelada'
    },
    ITEM: {
      PENDIENTE: 'Pendiente',
      PARCIAL: 'Parcial',
      COMPLETO: 'Completo'
    }
  }
};
```

---

## ðŸ”„ FLUJOS DE TRABAJO COMPLETOS

### **Flujo 1: Crear Orden de Compra**
1. Usuario: MenÃº â†’ ðŸ“ Nueva Orden de Compra
2. Sistema: Abre FormularioOrden.html
3. Usuario: Selecciona proveedor, agrega items, completa datos
4. Usuario: Click en "ðŸ’¾ Guardar Orden"
5. Sistema: `crearOrdenCompra(ordenData)`
6. Sistema: Escribe en Ordenes_Compra + Detalle_Ordenes
7. Sistema: Muestra mensaje "âœ… Orden OC-2026-XXX creada"
8. Sistema: Cierra diÃ¡logo

---

### **Flujo 2: Ver Ã“rdenes Pendientes**
1. Usuario: MenÃº â†’ ðŸ“‹ Ver Pendientes
2. Sistema: Abre ListaPendientes.html
3. Sistema: Llama `getOrdenesPendientes()`
4. Sistema: Renderiza tabla con Ã³rdenes pendientes
5. Usuario: Click en "Ver X producto(s) â–¼"
6. Sistema: Expande detalle de items pendientes
7. Usuario (opcional): Click en "ðŸ–¨ï¸ Imprimir/PDF" o "ðŸ“‹ Copiar a Excel"

---

### **Flujo 3: Recepcionar Pedido**
1. Usuario: MenÃº â†’ ðŸ“¦ Recepcionar Pedido
2. Sistema: Abre FormularioRecepcion.html
3. Sistema: Carga dropdown con Ã³rdenes pendientes
4. Usuario: Selecciona orden
5. Sistema: Llama `getDetalleOrden(numeroOrden)`
6. Sistema: Muestra items con cantidades pendientes
7. Usuario: Completa cantidad recibida, lote, vencimiento, conformidad, observaciones
8. Usuario: Click en "âœ… Confirmar Ingreso a Stock"
9. Sistema: Valida lote obligatorio
10. Sistema: `registrarRecepcion(recepcionData)`
11. Sistema: Escribe en Recepciones, Detalle_Recepciones, Movimientos_Inventario
12. Sistema: Actualiza Detalle_Ordenes (cantidad_recepcionada, estado_item)
13. Sistema: Actualiza estado de orden en Ordenes_Compra
14. Sistema: Recalcula Stock_Actual (FIFO)
15. Sistema: Aplica formatos condicionales
16. Sistema: Muestra mensaje "RecepciÃ³n registrada con Ã©xito: REC-2026-XXX"
17. Sistema: Cierra diÃ¡logo

---

### **Flujo 4: Registrar Consumo (Baja)**
1. Usuario: Abre hoja Bajas_Consumo
2. Usuario: Escribe en B2 cÃ³digo o nombre de insumo
3. Sistema: Trigger `onEdit()`
4. Sistema: Busca insumo, filtra lotes con stock > 0
5. Sistema: Ordena lotes por vencimiento (FIFO)
6. Sistema: Crea desplegable en B3
7. Sistema: Preselecciona lote prÃ³ximo a vencer
8. Sistema: Muestra info en C3
9. Usuario: Ajusta lote si quiere (opcional)
10. Usuario: Completa cantidad (B4) y observaciones (B5)
11. Usuario: Click en botÃ³n "REGISTRAR CONSUMO"
12. Sistema: `procesarBajaDesdeHoja()`
13. Sistema: Valida stock disponible
14. Sistema: Escribe en Movimientos_Inventario (tipo: Egreso)
15. Sistema: Recalcula Stock_Actual
16. Sistema: Actualiza Dashboard
17. Sistema: Limpia formulario
18. Sistema: Muestra mensaje "âœ… Consumo registrado exitosamente"

---

## ðŸ› PROBLEMAS RESUELTOS (Historial)

### âœ… Issue #1: Cantidades negativas en recepciÃ³n
**Problema:** Al recepcionar, aparecÃ­an cantidades pendientes negativas.  
**Causa:** `getDetalleOrden()` no leÃ­a correctamente `cantidad_recepcionada`.  
**SoluciÃ³n:** Reescribir funciÃ³n para leer headers dinÃ¡micamente y mapear correctamente las columnas.

### âœ… Issue #2: Ã“rdenes nuevas no aparecÃ­an en dropdown
**Problema:** Ã“rdenes reciÃ©n creadas no se listaban en formulario de recepciÃ³n.  
**Causa:** Estado con espacios en blanco o timing de `flush()`.  
**SoluciÃ³n:** Agregar `String(row[3]).trim()` en el filtro de `getOrdenesPendientes()`.

### âœ… Issue #3: Stock crÃ­tico mal calculado
**Problema:** Insumos con mÃºltiples lotes marcaban cada lote como crÃ­tico independientemente.  
**Causa:** ComparaciÃ³n de stock por lote vs. nivel crÃ­tico del insumo.  
**SoluciÃ³n:** Calcular stock TOTAL por insumo (sumando todos los lotes) y comparar contra crÃ­tico. Asignar el mismo estado a todos los lotes del insumo.

### âœ… Issue #4: Sistema de bajas no funcionaba
**Problema:** Desplegable de lotes no se generaba, bÃºsqueda fallaba.  
**Causa:** FÃ³rmulas frÃ¡giles en celdas C2/D2, lÃ³gica de `onEdit()` incompleta.  
**SoluciÃ³n:** Eliminar fÃ³rmulas, implementar bÃºsqueda robusta por cÃ³digo O nombre en `onEdit()`, agregar ordenamiento FIFO de lotes.

### âœ… Issue #5: Faltaba nombre del proveedor en Ordenes_Compra
**Problema:** Solo se guardaba el cÃ³digo del proveedor.  
**Causa:** DiseÃ±o inicial sin columna de nombre.  
**SoluciÃ³n:** Agregar columna D `nombre_proveedor`, modificar `crearOrdenCompra()` para buscar y guardar el nombre, ajustar Ã­ndices en `getOrdenesPendientes()` y `actualizarEstadoOrden()`.

### âœ… Issue #6: Estado de conformidad siempre "Conforme"
**Problema:** Aunque recibÃ­as menos cantidad, marcaba "Conforme".  
**Causa:** Campo hardcodeado sin lÃ³gica.  
**SoluciÃ³n:** Agregar select manual en FormularioRecepcion.html con 3 opciones (Conforme | Conforme Parcial | No Conforme), capturar valor y aplicar formato condicional en Detalle_Recepciones.

---

## ðŸ“ˆ MEJORAS PROPUESTAS (Pendientes de feedback)

### **Mejora A: Alertas de Vencimientos PrÃ³ximos**
Agregar secciÃ³n al Dashboard que muestre productos prÃ³ximos a vencer en 30 dÃ­as.

### **Mejora B: Ã“rdenes con Demora en Entrega**
Comparar `fecha_entrega_estimada` con fecha actual y alertar Ã³rdenes vencidas.

### **Mejora C: Top 5 Insumos MÃ¡s Consumidos**
AnÃ¡lisis de Movimientos_Inventario (tipo: Egreso) de Ãºltimos 30 dÃ­as para planificar compras recurrentes.

### **Mejora D: Reportes Automatizados**
ExportaciÃ³n mensual de movimientos, stock, Ã³rdenes en formato PDF o Excel.

### **Mejora E: Vista "Compras" Dedicada**
Solapa adicional con anÃ¡lisis profundos para el responsable de compras.

---

## ðŸŽ¯ ESTADO ACTUAL DEL SISTEMA

**VersiÃ³n:** 2.1 (Estable - Productivo)  
**Ãšltima actualizaciÃ³n:** Febrero 2026  
**MÃ³dulos completados:**
- âœ… GestiÃ³n de Ã³rdenes de compra
- âœ… RecepciÃ³n con conformidad
- âœ… Stock FIFO con alertas consolidadas
- âœ… Bajas/consumo con trazabilidad
- âœ… Dashboard ejecutivo
- âœ… Movimientos completos

**Pendiente de feedback:**
- â³ Alertas de vencimientos
- â³ Seguimiento de demoras
- â³ AnÃ¡lisis de consumo histÃ³rico
- â³ Reportes automatizados

---

**FIN DEL DOCUMENTO TÃ‰CNICO**

*Este documento contiene la informaciÃ³n esencial para continuar el desarrollo del sistema sin pÃ©rdida de contexto.*
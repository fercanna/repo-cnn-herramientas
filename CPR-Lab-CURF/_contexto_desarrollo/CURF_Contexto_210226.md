# Contexto de Desarrollo
## Estado al 21/02/2026 — Para continuar en nuevo proyecto

---

## Sistema

**Nombre:** Sistema de Gestión de Compras e Inventario  
**Stack:** Google Sheets + Google Apps Script  
**Versión base:** 2.1 productiva  
**Usuario:** Fernando (Bioquímico, Consultor ISO)  
**Deploy producción:** 24/02/2026

---

## Arquitectura — Hojas del Spreadsheet

| Nombre hoja | Descripción |
|---|---|
| `Insumos` | Catálogo maestro de insumos activos |
| `Proveedores` | Proveedores activos con mail, contacto |
| `Ordenes_Compra` | Cabecera de OC |
| `Detalle_Ordenes` | Items de cada OC |
| `Recepciones` | Cabecera de recepciones |
| `Detalle_Recepciones` | Items recibidos por recepción |
| `Movimientos_Inventario` | Todos los movimientos (Ingreso/Egreso/Ajuste) |
| `Stock_Actual` | Stock vigente por lote (se regenera) |
| `Dashboard` | KPIs y alertas automáticas |
| `Config_Conversiones` | Factores caja→unidad editables por usuario |
| `Historial_Precios` | Registro automático de variaciones de precio |
| `Stock_por_Proveedor` | Vista de stock filtrada por proveedor (se regenera) |

---

## Módulos implementados en esta sesión (Fase 1 + Fase 2 parcial)

### ✅ Módulo 1 — Conversión Cajas → Unidades
- **Archivo:** `modulo_conversion_v2.2.gs`
- Hoja `Config_Conversiones` con 24 insumos de Virología
- Factores editables por Male sin tocar código
- `registrarRecepcion()` aplica conversión antes de grabar stock
- Trazabilidad en `Detalle_Recepciones`: `[CONV x24] 1 caja → 24 Det.`

### ✅ Módulo 2 — Historial de Variación de Precios
- **Archivo:** `modulo_historial_precios_v2.2.gs`
- Hoja `Historial_Precios` se completa automáticamente al crear OC y al recepcionar con precio diferente
- `crearOrdenCompra()` registra precio y actualiza `precio_referencial` en catálogo
- `registrarRecepcion()` tiene campo opcional `precio_recepcion` para cuando el precio real llega con la factura
- Dashboard muestra sección "📈 Variación de Precios": **una fila por insumo**, variación neta del período, sin duplicados por proveedor
- `agregarSeccionPrecios()` consolida por `codigo_insumo` tomando precio base del primer evento y precio final del último

### ✅ Módulo 3 — Formulario OC filtrado por proveedor
- **Archivo:** `FormularioOrden_v2.2.html`
- Al elegir proveedor muestra solo sus insumos (filtrado por `proveedor_preferido`)
- Insumos agrupados por categoría con badge de stock (✓ OK / ⚡ Crítico / ⚠ Agotado)
- El usuario tilda los insumos → se habilitan campos de cantidad y precio
- Precios y cantidades editables antes de guardar
- Botón "➕ Agregar insumo de otro proveedor" para casos de proveedor alternativo (buscador libre sobre catálogo completo)
- **Nueva función .gs:** `getInsumosPorProveedor(codigoProveedor)` — devuelve insumos con stock actual y estado

### ✅ Módulo 4 — Stock por Proveedor con generación de OC
- **Archivos:** `modulo_stock_por_proveedor_v2.3.gs`, `DialogOrdenStock.html`, `getOcDesdeStockDatos.gs`
- Hoja `Stock_por_Proveedor`: sección por proveedor, insumos ordenados por frecuencia de consumo (egresos 90 días)
- Columna A: checkbox de selección
- Columna J: cantidad a pedir sugerida = `max(stock_crítico × 2 - stock_actual, 1)`, editable
- Semáforo visual por estado de stock
- Top 3 insumos más consumidos en negrita
- Flujo: tildar insumos → Menú → "🛒 Generar OC desde Stock" → mini-diálogo fecha+obs → `crearOrdenCompra()` → checkboxes se limpian solos
- Si hay insumos de 2 proveedores tildados → crea 2 OC separadas automáticamente
- Mapa de filas guardado en `ScriptProperties` para que la función sepa qué leer

---

## Funciones nuevas agregadas al script principal

```
getInsumosPorProveedor(codigoProveedor)   → Módulo 3
actualizarStockPorProveedor()              → Módulo 4
generarOrdenDesdeStock()                   → Módulo 4
confirmarOrdenDesdeStock(fecha, obs)       → Módulo 4
getOcDesdeStockDatos()                     → Módulo 4 (auxiliar para HTML)
```

### Modificaciones a funciones existentes
- `registrarRecepcion()` — agrega conversión + campo precio_recepcion opcional
- `crearOrdenCompra()` — agrega llamada a `registrarHistorialPrecios()`
- `actualizarDashboard()` — agrega llamada a `agregarSeccionPrecios()`
- `onOpen()` — ítems nuevos en el menú

### onOpen() final
```javascript
function onOpen() {
  SpreadsheetApp.getUi().createMenu('🛒 Gestión Compras')
    .addItem('📋 Nueva Orden de Compra', 'mostrarFormularioOrden')
    .addSeparator()
    .addItem('📋 Ver Pendientes', 'mostrarListaPendientes')
    .addItem('📦 Recepcionar Pedido', 'mostrarFormularioRecepcion')
    .addSeparator()
    .addItem('📊 Actualizar Dashboard', 'actualizarDashboard')
    .addSeparator()
    .addItem('⚙️ Gestionar Conversiones', 'abrirConfigConversiones')
    .addItem('📈 Ver Historial Precios', 'mostrarHistorialPrecios')
    .addItem('📦 Stock por Proveedor', 'actualizarStockPorProveedor')
    .addItem('🛒 Generar OC desde Stock', 'generarOrdenDesdeStock')
    .addToUi(); // siempre al final
}
```

---

## Fase 1 — Estado final

| Item | Estado |
|---|---|
| Importación masiva stock inicial | ⏳ Pendiente — esperando planillas Bacterio/Viro |
| División Cajas → Unidades | ✅ Productivo |
| Detalle recepción parcial UI v2.2 | ✅ Listo |
| Historial variación de precios | ✅ Productivo |

---

## Fase 2 — Estado

| Item | Estado |
|---|---|
| Formulario OC filtrado por proveedor | ✅ Productivo |
| Stock por Proveedor con generación OC | ✅ Productivo |
| Actualización masiva precios por % | ⏳ Pendiente |
| Historial de gastos mes a mes (Pati) | ⏳ Pendiente — datos disponibles en Detalle_Ordenes |

---

## ANOA — Onboarding Caro

- Excel normalizado: 299 insumos en 4 hojas (`ANOA_CatalogoInsumos_v1.xlsx`)
- Instructivo Word enviado a Caro (`Instructivo_CargaInicial_ANOA.docx`)
- Caro debe completar: `unidad_medida`, `stock_critico`, stock físico inicial, contactos proveedores
- Script de importación masiva: **pendiente** hasta que Caro devuelva el Excel completado

---

## Pendientes críticos antes del 24/02

1. **Script importación masiva** — desarrollar cuando lleguen planillas Bacterio/Viro (lunes)
2. **Test completo** del flujo Stock → OC desde Stock con datos reales
3. **Caro ANOA** — completar Excel y ejecutar importación

---

## Archivos a compartir en el nuevo proyecto

### Código fuente (copiar contenido completo de Apps Script)
- `Código.gs` — script principal
- `FormularioOrden.html`
- `FormularioRecepcion.html`
- `ListaPendientes.html`
- `DialogOrdenStock.html`

### Módulos nuevos generados (ya en outputs de esta sesión)
- `modulo_conversion_v2.2.gs`
- `modulo_historial_precios_v2.2.gs`
- `modulo_stock_por_proveedor_v2.3.gs`
- `getInsumosPorProveedor.gs`
- `getOcDesdeStockDatos.gs`

### Documentación
- `DOCUMENTACION_TECNICA_SISTEMA_COMPRAS.md` (del proyecto actual)
- Este archivo `CURF_Contexto_210226.md`

### Datos de referencia (capturas o exports)
- Estructura de columnas de la hoja `Insumos` (screenshot o export)
- Estructura de columnas de la hoja `Stock_Actual`
- Estructura de columnas de `Movimientos_Inventario`

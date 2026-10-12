# Guía de despliegue v2.9.6 — planillas de producción (Virología y Bacteriología)

Versión a instalar: `Codigo_gs_v2.9.6_CONSOLIDADO.txt` + 7 archivos HTML. Se instala **igual en las dos planillas** (CPR-VI-RE-1 y CPR-BA-RE-1); lo único que cambia entre áreas son los valores de la hoja `Config_Area`.

## 0. Antes de empezar (10 min)
1. En cada planilla: **Archivo → Crear una copia** y nombrarla `…_respaldo_antes_v2.9.6_AAAAMMDD`. Es el plan de vuelta atrás.
2. Elegir un momento sin recepciones ni órdenes en curso, y avisar a las personas del área que no usen la planilla durante la instalación.
3. Tener a mano esta carpeta: `CPR-Lab-CURF/_actualización_v2.9/`.

## 1. Pegar el código (por planilla)
En la planilla: **Extensiones → Apps Script**.

| Dónde | Qué hacer |
|---|---|
| `Código.gs` (o como se llame el archivo principal) | Borrar todo el contenido y pegar el de `Codigo_gs_v2.9.6_CONSOLIDADO.txt` |
| HTML `FormularioOrden` | Reemplazar contenido con `FormularioOrden_html.txt` |
| HTML `FormularioEditarOC` | Reemplazar con `FormularioEditarOC_html.txt` |
| HTML `DialogOrdenStock` (ojo: en Apps Script no lleva la "o") | Reemplazar con `DialogoOrdenStock_html.txt` |
| HTML `FormularioRecepcion` | Reemplazar con `FormularioRecepcion_html.txt` |
| HTML `ListaPendientes` | Reemplazar con `ListaPendientes_html.txt` |
| HTML `DevolucionesProveedor` | Reemplazar con `DevolucionesProveedor_html.txt` |
| HTML `FormularioNoConformeUso` | **Archivo nuevo** (+ → HTML), con ese nombre exacto; pegar `FormularioNoConformeUso_html.txt` |

No tocar: `FormularioAjusteStock`, `FormularioConversiones`, `FormularioCancelar*`, `FormularioImportarStock` (no cambiaron).
Guardar (Ctrl+S) y **recargar la planilla**: debe aparecer el menú "🛒 Gestión Compras" con los ítems nuevos "⚠️ No Conforme detectado en uso" y "📊 Resumen No Conformes por Proveedor".

## 2. Configurar el área (`Config_Area`)
La hoja se crea sola al usar el menú por primera vez (o al abrir cualquier formulario). Abrirla y completar:

| clave | Virología | Bacteriología |
|---|---|---|
| `laboratorio` | revisar | revisar |
| `area` | Virología | Bacteriología |
| `mail_area` | mail de Virología (ya cargado) | **completar** con el mail de Bacteriología |
| `razon_social`, `cuit`, `condicion_iva` | revisar | revisar |
| `personal` | lista confirmada con María | **completar** con las personas de Bacteriología, separadas por `;` |
| `umbral_nc_incidencia` | 3 | 3 (o el criterio del área) |

Si `mail_area` queda con el de Virología en la planilla de Bacteriología, los mails de OC saldrían con el Reply-To equivocado: verificarlo.

## 3. Ocultar hojas internas (una sola vez por planilla)
En Apps Script, elegir la función `ocultarHojasInternas` en el selector superior y tocar **Ejecutar** (la primera vez pide autorización). Oculta: Detalle_Ordenes, Detalle_Recepciones, Movimientos_Inventario, Historial_Precios, Config_Conversiones, Log_Cierres_OC, Log_Envios_OC.
Quedan **visibles** a propósito: Stock_por_Proveedor (se usa para generar OC desde stock), Config_Area, Devoluciones_Proveedor, Resumen_NC_Proveedor, Stock_Actual, Ordenes_Compra, Recepciones, Insumos, Proveedores, Dashboard, Bajas_Consumo.
Para volver a verlas: Ver → Hojas ocultas.

## 4. Verificación rápida en cada planilla (15 min)
Hacerla con datos de prueba y anularlos después (Correcciones → Cancelar), o en la copia de respaldo.
1. **Nueva OC**: el selector "Solicitado por" lista las personas de `Config_Area`. Crear una OC con una observación por ítem. **Ver PDF**: sin precios, con la observación.
2. **Ver Pendientes**: se ve la OC; probar *Anular pendiente* en una línea (pide motivo) y que desaparezca.
3. **Recepcionar**: ventana grande, observación por ítem, elegir "Conforme parcial" sin observación → debe frenar.
4. **Devoluciones**: recepcionar un ítem "No conforme" → aparece en Devoluciones a Proveedores con origen "Recepción".
5. **No Conforme detectado en uso**: dar de baja 1 unidad de un lote de prueba → baja en Stock_Actual y fila nueva con "Detectado en uso".
6. **Resumen No Conformes por Proveedor**: genera la hoja y cuenta los de prueba.
7. En el menú **no existe** ningún "Reset" (se eliminó en v2.8).
Cualquier error rojo → no seguir: copiar el mensaje y avisar.

## 5. Datos que se completan solos
Nada que migrar a mano: se agregan solas las hojas `Config_Area`, `Log_Cierres_OC`, `Resumen_NC_Proveedor` y las columnas `observacion_item`, `cantidad_anulada`, `motivo_cierre`, `usuario_cierre`, `fecha_cierre` (Detalle_Ordenes) y `origen` (Devoluciones_Proveedor). Los registros anteriores se leen igual: sin `origen` = recepción.

## 6. Volver atrás
Si algo falla de forma grave: abrir la copia de respaldo y usarla como planilla vigente (renombrar), o en Apps Script **Ver → Historial de versiones** para recuperar el código anterior. Los datos cargados desde la instalación tendrían que volver a cargarse.

## 7. Cierre
- Entregar a María la planilla actualizada y el checklist de revisión final (ella probaba la v2.8).
- Anotar fecha de instalación y versión por planilla en el registro del proyecto.

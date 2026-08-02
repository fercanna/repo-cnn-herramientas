# Cadena de edición de audio en Audacity — biblioteca de contenidos

Fecha: 24 de julio de 2026
Contexto: preparación técnica del flujo "reunión con cliente → guion → píldora con voz clonada" (ver `idea-microicho-biblioteca-contenidos.md`). Define los pasos fijos y mecánicos de limpieza de audio, separados en dos cadenas según el destino del archivo.

## Por qué dos cadenas, no una

La grabación semilla que alimenta el clonador de voz necesita quedar lo más limpia y "cruda" posible — sin compresión ni normalización agresiva — porque cualquier artefacto de procesamiento queda aprendido en el modelo de voz. La píldora final que se publica sí necesita compresión y normalización de loudness para sonar pareja en el feed de podcast. Por eso son dos macros distintos, no uno.

## Paso previo manual (una vez por sesión de grabación, no por archivo)

Antes de grabar, capturar 20-30 segundos de silencio en el mismo ambiente donde se va a grabar (mismo micrófono, misma sala). Al terminar la sesión:

1. Abrir ese fragmento de silencio en Audacity.
2. Seleccionarlo completo.
3. `Effect > Noise Reduction > Get Noise Profile`.

Este perfil queda activo en Audacity para esa sesión — no hace falta repetirlo en cada archivo, solo si cambia el ambiente o el micrófono.

## Cómo crear un Macro en Audacity (primera vez)

1. `Tools > Macro Manager` (en algunas versiones aparece como `Tools > Macros`).
2. Click en `New` y ponerle nombre (ej. `Semilla_Clonacion` o `Pildora_Final`).
3. Con el macro nuevo seleccionado, click en `Insert` para agregar cada paso de la lista de abajo, en orden. Al insertar cada efecto, Audacity abre su diálogo de parámetros — ahí es donde se fijan los valores (importante: si no se fijan, Audacity usa el último valor usado manualmente, que puede variar).
4. Guardar el macro.
5. Para correrlo sobre un archivo: `Tools > Apply Macro`, elegir el macro.
6. Para correrlo sobre varios archivos de una sesión de golpe: `Tools > Apply Macro > Palette`, elegir el macro, botón `Files…`, seleccionar todos los audios a procesar.

## Cadena "Semilla_Clonacion" (grabaciones que alimentan el clonador de voz)

| # | Efecto | Parámetros sugeridos |
|---|--------|----------------------|
| 1 | Truncate Silence | Recorta silencios largos al inicio/final (umbral -30dB, duración mínima 0.5s) |
| 2 | High-Pass Filter | Frecuencia de corte 80Hz, rolloff 12dB/oct |
| 3 | Noise Reduction | Reducción 12dB, sensibilidad 6, suavizado de frecuencia 3 (usa el perfil capturado en el paso previo) |
| 4 | Normalize | Pico a -3dB (deja margen, sin comprimir) |
| 5 | Export as WAV | 44.1kHz, 24-bit — sin pérdida, mejor calidad de entrenamiento para el clonador |

## Cadena "Pildora_Final" (audio que se publica en el feed del cliente)

| # | Efecto | Parámetros sugeridos |
|---|--------|----------------------|
| 1 | Truncate Silence | Igual que arriba |
| 2 | High-Pass Filter | Igual que arriba |
| 3 | Noise Reduction | Igual que arriba (mismo perfil de sesión) |
| 4 | Compressor | Ratio 3:1, threshold -18dB — pareja el volumen entre frases |
| 5 | Loudness Normalization | -16 LUFS (estándar de podcast) |
| 6 | Export as MP3 | 192kbps |

## Pendiente de validar con Fer

- Confirmar que los valores de Noise Reduction/Compressor funcionan bien con el micrófono real una vez grabadas las primeras muestras — son puntos de partida, no valores probados en la práctica todavía.
- Decidir si -16 LUFS es el target correcto o si el feed de podcast privado (RSS no listado, ver doc de biblioteca) tiene otro requisito.

# Guía de instalación — Chatterbox TTS Server (clonación de voz)

Fecha: 25 de julio de 2026
Contexto: primer paso técnico del flujo de píldoras con voz clonada (ver `idea-microicho-biblioteca-contenidos.md` y memoria `skill_pildoras_voz_clonada`). Objetivo de esta guía: dejar el servidor corriendo local y hacer una primera prueba de clonación, no todavía integrarlo con Hermes.

## Qué vamos a instalar y por qué

No instalamos Chatterbox "pelado" (la librería sola requiere escribir Python para cada generación). Usamos **devnen/Chatterbox-TTS-Server** — un proyecto de la comunidad que envuelve Chatterbox en un servidor local con interfaz web (subís un audio de referencia, tipeás el texto, generás desde el navegador). Trae:

- Web UI para probar clonación sin escribir código.
- Instalador automático (`start.bat`) que detecta tu hardware y arma el entorno solo.
- API compatible con OpenAI — útil más adelante para que Hermes lo llame como herramienta, sin reescribir nada.

## ⚠️ Importante para tu GPU (RTX 5060 Ti)

Tu placa es arquitectura **Blackwell** (compute capability `sm_120`). Necesita específicamente **CUDA 12.8**, no la versión por default (CUDA 12.1) — con la versión equivocada da el error `CUDA error: no kernel image is available for execution on the device`. El instalador automático detecta esto solo si elegís la opción correcta en el menú (ver Paso 3). No lo dejes en automático sin revisar.

## Prerequisitos

- **Git** instalado (para clonar el repo). Si no lo tenés: `winget install --id Git.Git -e` desde PowerShell, o descargarlo de git-scm.com.
- **No hace falta instalar Python 3.10 aparte.** El instalador de Windows ofrece un "Modo Portable" que trae su propio Python 3.10 embebido — mejor opción para vos, porque ya sabemos por `generar_minuta` que el Python de sistema de tu MSI (3.14) rompe con paquetes que piden versiones viejas. Elegí Portable cuando te lo pregunte.
- Drivers NVIDIA actualizados (versión 570+). Si hace mucho no actualizás: Panel de NVIDIA / GeForce Experience.

## Paso 1 — Clonar el repositorio

Abrí PowerShell donde quieras dejar la instalación (ej. al lado de tus otros repos, `C:\Users\Equipo\repos\`) y corré:

```powershell
git clone https://github.com/devnen/Chatterbox-TTS-Server.git
cd Chatterbox-TTS-Server
```

## Paso 2 — Ejecutar el instalador

Doble click en `start.bat` (o desde PowerShell, parado en la carpeta del repo: `.\start.bat`).

## Paso 3 — Elegir las opciones correctas en el menú

El instalador te va a preguntar dos cosas:

1. **Tipo de instalación** → elegí **Portable Mode** (recomendado, evita el problema de versión de Python).
2. **Tipo de hardware** → el menú lista varias opciones NVIDIA. **No elijas la opción por default (CUDA 12.1)** — buscá la que dice explícitamente **CUDA 12.8 / Blackwell / RTX 5090 series** (cubre también tu RTX 5060 Ti). Si tenés dudas de cuál es exactamente por el texto del menú, pegame la lista completa que te muestra y te digo cuál tocar.

Esto descarga PyTorch, el modelo de Chatterbox y arma todo el entorno — puede tardar varios minutos y ocupar varios GB (normal, incluye las librerías de GPU).

## Paso 4 — Verificar que la GPU quedó bien detectada

Una vez terminada la instalación, en la misma carpeta corré (ajustando la ruta al Python que haya quedado — el instalador te lo muestra al final, va a ser algo como `python_embedded\python.exe` si elegiste Portable):

```powershell
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}'); print(f'Arquitecturas: {torch.cuda.get_arch_list()}')"
```

Tiene que decir `CUDA: True`, `GPU: ... 5060 Ti ...`, y que `sm_120` aparezca en la lista de arquitecturas. Si `CUDA` da `False` o falta `sm_120`, la instalación agarró la versión de CUDA equivocada — avisame con el output completo antes de seguir.

## Paso 5 — Arrancar el servidor y abrir la interfaz

Si no quedó corriendo solo después del instalador, doble click en `start.bat` de nuevo (las próximas veces arranca directo, sin volver a instalar). Se abre automáticamente el navegador en:

```
http://localhost:8004
```

Si no se abre solo, entrá esa URL a mano.

## Paso 6 — Primera prueba de clonación

Esto es lo que conecta con la cadena de Audacity que ya armamos:

1. Grabá una muestra corta (unos 10-15 segundos) siguiendo la cadena **"Semilla_Clonacion"** de `cadena-edicion-audacity.md`, exportada como WAV.
2. Copiá ese WAV a la carpeta `reference_audio` que se creó dentro de la instalación de Chatterbox.
3. En la Web UI: arriba elegí el motor **Chatterbox Multilingual** (dropdown de selección de motor).
4. En el modo de voz, elegí **Voice Cloning** y seleccioná tu archivo de `reference_audio`.
5. Escribí un texto corto en español (algo que digas normalmente en una píldora) y generá.
6. Escuchá el resultado — este es el punto de decisión: si el timbre se parece a tu voz real, seguimos escalando el pipeline; si no, probamos con XTTS v2 como plan B (ver memoria `skill_pildoras_voz_clonada`) o ajustamos la calidad de la muestra semilla.

## Si algo falla

- **Error `no kernel image is available`**: instaló la versión de CUDA equivocada (12.1 en vez de 12.8). Solución: `python start.py --reinstall --nvidia-cu128` desde la carpeta del repo.
- **El navegador no abre solo**: andá manual a `http://localhost:8004`.
- **Querés reinstalar de cero**: `python start.py --reinstall` (te vuelve a mostrar el menú de opciones).

## Qué queda para después (no en esta guía)

- Conectar este servidor como herramienta de Hermes (vía su API compatible con OpenAI) para que la generación de audio final sea parte del flujo automático — hoy es un paso manual desde la Web UI.
- Definir el texto/guion real de la primera píldora piloto para LACE.

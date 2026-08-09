# Cómo poner TimeTracker en una máquina nueva

Guía paso a paso para instalar TimeTracker en una máquina que todavía no lo tiene (por ejemplo, la de la oficina), y que quede conectada a la misma base de datos compartida en Drive.

Asumimos que Drive ya está sincronizado en esa máquina y que la carpeta `G:\Mi unidad\CNN.AI - Clientes\TimeTrackerData` ya existe ahí (se sincroniza sola, no hace falta crearla).

## 1. Instalar Python (si no lo tenés)

Descargar de https://www.python.org/downloads/ e instalar. **Importante:** marcar la casilla "Add python.exe to PATH" durante la instalación.

## 2. Instalar Git (si no lo tenés)

Descargar de https://git-scm.com/download/win e instalar con las opciones por defecto.

## 3. Verificar instalación

Cerrar y volver a abrir PowerShell, después correr:

```powershell
python --version
git --version
```

Si ambos responden con un número de versión (sin error de "no se reconoce como comando"), seguir.

## 4. Clonar el repo

```powershell
cd $HOME
mkdir repos -ErrorAction SilentlyContinue
cd repos
git clone https://github.com/fercanna/repo-cnn-herramientas.git
cd repo-cnn-herramientas\Timetracker
```

## 5. Instalar dependencias

```powershell
pip install -r requirements.txt --timeout 120
```

Si se corta por timeout (conexión lenta), reintentar el mismo comando — pip retoma lo ya descargado.

## 6. Crear `config.local.json`

Este archivo es específico de cada máquina (no viaja con git) y le dice a TimeTracker dónde está la base de datos compartida.

**Usar rutas completas, no relativas**, y este método exacto (evita el problema del BOM que ya nos pasó una vez):

```powershell
$configPath = "$PWD\config.local.json"
[System.IO.File]::WriteAllText($configPath, '{
  "db_folder": "G:\\Mi unidad\\CNN.AI - Clientes\\TimeTrackerData"
}')
Get-Content $configPath
```

Confirmar que el `Get-Content` muestra el JSON correcto, con la ruta de Drive.

## 7. Correr la app

```powershell
python run.py
```

Se abre solo en el navegador en `http://localhost:8501`. Deberías ver ahí las tareas ya cargadas desde las otras máquinas.

## 8. (Opcional) Acceso directo de escritorio

Clic derecho sobre `TimeTracker_silencioso.vbs` (dentro de la carpeta `Timetracker`) → Enviar a → Escritorio (crear acceso directo). Doble clic desde ahí abre la app sin pasar por la terminal.

---

## Errores típicos y cómo resolverlos

**"No se reconoce el término python/git"** → no se marcó "Add to PATH" al instalar, o falta reabrir PowerShell. Reinstalar marcando esa opción, o agregar Python al PATH manualmente.

**La app abre pero no aparecen las tareas de las otras máquinas** → revisar `config.local.json`: que la ruta a Drive esté bien escrita (con `\\` dobles) y que el `Get-Content` no muestre caracteres raros al principio del archivo.

**Cambié código en una máquina pero no se ve en otra** → los cambios de código viajan por git (`git push` en el origen, `git pull` en destino), no por Drive. Drive solo sincroniza la carpeta de datos (`TimeTrackerData`), no el código de la app. Después de un `git pull`, hay que reiniciar `python run.py` (Ctrl+C y volver a correrlo) para que tome páginas nuevas — el navegador no alcanza con refrescar.

**`git push` o `git commit` tira error de `index.lock`** → cerrar cualquier terminal/VS Code/GitHub Desktop que tenga el repo abierto, borrar el archivo `.git\index.lock` a mano (`Remove-Item .git\index.lock -Force`), y reintentar.

**No uses la app desde dos máquinas al mismo tiempo** → SQLite no tolera bien escritura simultánea desde dos lados. Usala en una, cerrala, y esperá un momento a que Drive sincronice antes de abrirla en otra.

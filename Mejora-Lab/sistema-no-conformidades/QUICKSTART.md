# Guía de Inicio Rápido

## Instalación rápida (5 minutos)

### 1. Crear y activar entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate

# Activar (Linux/Mac)
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación

```bash
python app.py
```

### 4. Abrir en el navegador

```
http://localhost:5000
```

## Primera vez usando el sistema

### Registrar tu primera No Conformidad

1. Haz clic en **"Nueva NC"** en el menú superior
2. Completa los campos obligatorios:
   - Descripción de la NC
   - Área afectada
   - Tipo de NC (Mayor/Menor/Observación)
   - Severidad (Alta/Media/Baja)
   - Registrado por
3. Opcionalmente agrega:
   - Responsable
   - Acción inmediata
   - Observaciones
4. Haz clic en **"Registrar NC"**

El sistema generará automáticamente un número único (ej: NC-2025-0001).

### Navegar por el Dashboard

El dashboard muestra:
- **Total de NC**: Todas las no conformidades registradas
- **Abiertas**: NC que requieren atención
- **En proceso**: NC que están siendo trabajadas
- **Cerradas**: NC resueltas y cerradas

### Gestionar No Conformidades

1. **Ver todas**: Click en "No Conformidades" en el menú
2. **Filtrar**: Usa los filtros por estado o área
3. **Ver detalle**: Click en el icono de ojo 👁️
4. **Editar**: Click en el icono de lápiz ✏️
5. **Actualizar estado**: Edita la NC y cambia el estado

### Cerrar una No Conformidad

1. Ve al detalle de la NC
2. Click en "Editar"
3. Completa:
   - Causa raíz
   - Acción correctiva
   - Acción preventiva (opcional)
4. Cambia el estado a **"Cerrada"**
5. Guarda los cambios

El sistema registrará automáticamente la fecha de cierre.

## Resolución de problemas

### Error al iniciar la aplicación

```bash
# Verifica que el entorno virtual esté activado
# Deberías ver (venv) al inicio de tu línea de comandos

# Reinstala las dependencias
pip install -r requirements.txt
```

### La base de datos no se crea

```bash
# Verifica que la carpeta instance/ se haya creado
# Si no existe, créala manualmente:
mkdir instance
```

### Puerto 5000 ocupado

Edita el archivo `.env` o cambia el puerto en `app.py`:

```python
port = 8000  # Cambia a otro puerto disponible
```

## Comandos útiles

```bash
# Ver todas las dependencias instaladas
pip list

# Actualizar pip
python -m pip install --upgrade pip

# Desactivar entorno virtual
deactivate

# Ver logs de la aplicación
# Los errores aparecerán en la consola donde ejecutaste python app.py
```

## Próximos pasos

- Explora todas las funcionalidades del sistema
- Personaliza las áreas según tu laboratorio
- Revisa el README.md para funcionalidades futuras
- Considera agregar autenticación de usuarios para producción

## Soporte

Para dudas o problemas, revisa:
- README.md - Documentación completa
- config.py - Configuración del sistema
- app/models.py - Estructura de datos

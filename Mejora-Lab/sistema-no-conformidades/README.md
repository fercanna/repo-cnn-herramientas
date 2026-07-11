# Sistema de Gestión de No Conformidades

Sistema web para la gestión y seguimiento de no conformidades en laboratorios, diseñado para facilitar el control de calidad y el cumplimiento de normativas.

## Descripción

Este sistema permite a los laboratorios registrar, gestionar y dar seguimiento a las no conformidades detectadas durante los procesos de análisis y control de calidad. Facilita la trazabilidad completa desde la detección hasta la resolución de cada incidencia.

## Características principales

- **Registro de no conformidades**: Captura detallada de incidencias con clasificación por tipo y severidad
- **Seguimiento y trazabilidad**: Historial completo de cada no conformidad desde su detección hasta su cierre
- **Gestión de acciones correctivas**: Definición y seguimiento de planes de acción para resolver las incidencias
- **Reportes y análisis**: Generación de informes y estadísticas para análisis de tendencias
- **Gestión de usuarios y permisos**: Control de acceso basado en roles
- **Auditoría**: Registro de todas las acciones realizadas en el sistema

## Beneficios

- Mejora continua de los procesos del laboratorio
- Cumplimiento de requisitos normativos (ISO 17025, ISO 9001, etc.)
- Reducción de errores y problemas recurrentes
- Toma de decisiones basada en datos
- Mayor eficiencia en la gestión de la calidad

## Tecnologías

- **Backend**: Flask 3.0 (Python)
- **Base de datos**: SQLAlchemy con SQLite (desarrollo) / PostgreSQL (producción)
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **ORM**: SQLAlchemy 2.0

## Estructura del Proyecto

```
sistema-no-conformidades/
├── app/
│   ├── __init__.py              # Inicialización de la aplicación Flask
│   ├── models.py                # Modelos de base de datos
│   ├── routes/
│   │   ├── __init__.py
│   │   └── main.py              # Rutas principales
│   ├── templates/               # Plantillas HTML
│   │   ├── base.html
│   │   ├── index.html
│   │   └── no_conformidades/
│   └── static/                  # Archivos estáticos
│       ├── css/
│       └── js/
├── instance/                    # Base de datos SQLite (generada automáticamente)
├── config.py                    # Configuración de la aplicación
├── app.py                       # Punto de entrada
├── requirements.txt             # Dependencias Python
└── .env.example                 # Ejemplo de variables de entorno
```

## Instalación

### Requisitos previos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

```bash
# 1. Clonar el repositorio (o usar el directorio actual)
# git clone <url-del-repositorio>
# cd sistema-no-conformidades

# 2. Crear entorno virtual (recomendado)
python -m venv venv

# 3. Activar el entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
# source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables de entorno (opcional)
# cp .env.example .env
# Editar .env según necesidades

# 6. Ejecutar la aplicación
python app.py
```

## Uso

1. Acceder a la aplicación en: `http://localhost:5000`

2. **Dashboard**: Vista general con estadísticas de NC
   - Total de NC registradas
   - NC por estado (Abiertas, En proceso, Cerradas)
   - Últimas NC registradas

3. **Registrar nueva NC**:
   - Ir a "Nueva NC" en el menú
   - Completar el formulario con información de la no conformidad
   - El número de NC se genera automáticamente (formato: NC-YYYY-NNNN)

4. **Gestionar NC**:
   - Ver lista completa de NC con filtros por estado y área
   - Ver detalle de cada NC
   - Editar y actualizar estado de NC
   - Agregar acciones correctivas y preventivas

## Características del MVP

### Módulo de No Conformidades
- ✅ Registro de NC con numeración automática
- ✅ Clasificación por tipo (Mayor, Menor, Observación)
- ✅ Clasificación por severidad (Alta, Media, Baja)
- ✅ Estados: Abierta, En proceso, Cerrada
- ✅ Campos para análisis: causa raíz, acciones correctivas/preventivas
- ✅ Auditoría: registro de quién creó/modificó cada NC
- ✅ Dashboard con estadísticas
- ✅ Filtros por estado y área
- ✅ Paginación de resultados

### Próximas funcionalidades sugeridas
- Autenticación de usuarios
- Gestión de roles y permisos
- Carga de evidencias (archivos adjuntos)
- Reportes en PDF/Excel
- Gráficos y análisis de tendencias
- Notificaciones por email
- API REST para integraciones

## Licencia

Por definir

## Contacto

Para consultas y soporte, contactar al equipo de desarrollo.

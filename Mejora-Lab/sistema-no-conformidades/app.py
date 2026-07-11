"""
Sistema de Gestión de No Conformidades
Punto de entrada principal de la aplicación
"""
import os
from app import create_app

# Crear la aplicación Flask
app = create_app(os.getenv('FLASK_ENV') or 'development')

if __name__ == '__main__':
    # Obtener configuración del entorno
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    print(f"""
===============================================================
  Sistema de Gestion de No Conformidades - Laboratorio ISO
===============================================================

Servidor iniciado en: http://{host}:{port}
Modo: {'Desarrollo' if debug else 'Produccion'}

Presione CTRL+C para detener el servidor
    """)

    # Ejecutar la aplicación
    app.run(host=host, port=port, debug=debug)

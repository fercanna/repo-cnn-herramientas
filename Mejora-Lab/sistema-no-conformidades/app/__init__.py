import os
from flask import Flask
from config import config
from app.models import db


def create_app(config_name=None):
    """Factory para crear la aplicación Flask"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Inicializar extensiones
    db.init_app(app)

    # Crear carpeta instance si no existe
    instance_path = os.path.join(app.root_path, '..', 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

    # Registrar blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    # Crear tablas de base de datos
    with app.app_context():
        db.create_all()

    return app

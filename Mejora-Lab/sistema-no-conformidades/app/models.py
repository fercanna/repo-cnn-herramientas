from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class NoConformidad(db.Model):
    """Modelo para registrar las No Conformidades"""
    __tablename__ = 'no_conformidades'

    id = db.Column(db.Integer, primary_key=True)
    numero_nc = db.Column(db.String(50), unique=True, nullable=False, index=True)
    fecha_deteccion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_cierre = db.Column(db.DateTime, nullable=True)

    # Información de la NC
    descripcion = db.Column(db.Text, nullable=False)
    area_afectada = db.Column(db.String(100), nullable=False)
    tipo_nc = db.Column(db.String(50), nullable=False)  # Mayor, Menor, Observación
    severidad = db.Column(db.String(50), nullable=False)  # Alta, Media, Baja

    # Análisis y acciones
    causa_raiz = db.Column(db.Text, nullable=True)
    accion_inmediata = db.Column(db.Text, nullable=True)
    accion_correctiva = db.Column(db.Text, nullable=True)
    accion_preventiva = db.Column(db.Text, nullable=True)

    # Estado y seguimiento
    estado = db.Column(db.String(50), nullable=False, default='Abierta')  # Abierta, En proceso, Cerrada
    responsable = db.Column(db.String(100), nullable=True)
    verificado_por = db.Column(db.String(100), nullable=True)
    fecha_verificacion = db.Column(db.DateTime, nullable=True)

    # Auditoría
    creado_por = db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    modificado_por = db.Column(db.String(100), nullable=True)
    fecha_modificacion = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)

    # Observaciones adicionales
    observaciones = db.Column(db.Text, nullable=True)
    evidencias = db.Column(db.Text, nullable=True)  # Rutas a archivos o URLs

    def __repr__(self):
        return f'<NoConformidad {self.numero_nc}>'

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'numero_nc': self.numero_nc,
            'fecha_deteccion': self.fecha_deteccion.isoformat() if self.fecha_deteccion else None,
            'fecha_cierre': self.fecha_cierre.isoformat() if self.fecha_cierre else None,
            'descripcion': self.descripcion,
            'area_afectada': self.area_afectada,
            'tipo_nc': self.tipo_nc,
            'severidad': self.severidad,
            'estado': self.estado,
            'responsable': self.responsable,
            'creado_por': self.creado_por
        }

    @staticmethod
    def generar_numero_nc():
        """Genera el siguiente número de NC en formato NC-YYYY-NNNN"""
        year = datetime.utcnow().year
        ultima_nc = NoConformidad.query.filter(
            NoConformidad.numero_nc.like(f'NC-{year}-%')
        ).order_by(NoConformidad.id.desc()).first()

        if ultima_nc:
            ultimo_numero = int(ultima_nc.numero_nc.split('-')[-1])
            nuevo_numero = ultimo_numero + 1
        else:
            nuevo_numero = 1

        return f'NC-{year}-{nuevo_numero:04d}'


class Usuario(db.Model):
    """Modelo para gestión de usuarios"""
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default='Usuario')  # Admin, Gestor, Usuario
    activo = db.Column(db.Boolean, default=True)

    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ultimo_acceso = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Usuario {self.username}>'


class Area(db.Model):
    """Modelo para áreas o departamentos del laboratorio"""
    __tablename__ = 'areas'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    responsable = db.Column(db.String(100), nullable=True)
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Area {self.nombre}>'

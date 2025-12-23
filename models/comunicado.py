from models import db
from datetime import datetime

# 1. Tabla intermedia para guardar quién vio el comunicado
comunicado_vistos = db.Table('comunicado_vistos',
    db.Column('comunicado_id', db.Integer, db.ForeignKey('comunicado.id'), primary_key=True),
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True),
    db.Column('fecha_visto', db.DateTime, default=datetime.utcnow)
)

class Comunicado(db.Model):
    __tablename__ = 'comunicado'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(20), default='info') 
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # 2. Relación para acceder a los usuarios que ya lo vieron
    # Usamos string 'Usuario' para evitar problemas de importación circular
    usuarios_vistos = db.relationship('Usuario', secondary=comunicado_vistos, backref=db.backref('comunicados_leidos', lazy='dynamic'))

    def __repr__(self):
        return f'<Comunicado {self.titulo}>'
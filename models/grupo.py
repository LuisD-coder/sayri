from models import db
from datetime import datetime

class Grupo(db.Model):
    __tablename__ = 'grupo'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    prestamos_grupales = db.relationship('PrestamoGrupal', backref='grupo', lazy=True)
    clientes = db.relationship('Cliente', backref='grupo', lazy=True)

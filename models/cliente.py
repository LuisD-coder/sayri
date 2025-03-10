from models import db
from datetime import datetime

class Cliente(db.Model):
    __tablename__ = 'cliente'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(15), unique=True, nullable=False)
    celular = db.Column(db.String(20), nullable=False)
    operadora = db.Column(db.String(50))
    banco = db.Column(db.String(50))
    numero_cuenta = db.Column(db.String(50))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=False)

    prestamos_individuales = db.relationship('PrestamoIndividual', backref='cliente', lazy=True)

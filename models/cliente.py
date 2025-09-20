from models import db
from datetime import datetime
from sqlalchemy.orm import relationship

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

    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=True)

    # Relaciones
    # --- Agrega esta línea para completar la relación con el modelo Pago ---
    pagos = relationship('Pago', back_populates='cliente')
    # ----------------------------------------------------------------------
    prestamos_individuales = db.relationship('PrestamoIndividual', backref='cliente', lazy=True)
    contratos = relationship('Contrato', back_populates='cliente', lazy=True)
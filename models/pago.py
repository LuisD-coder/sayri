from models import db
from datetime import datetime

class Pago(db.Model):
    __tablename__ = 'pago'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    prestamo_individual_id = db.Column(db.Integer, db.ForeignKey('prestamoindividual.id'), nullable=False)
    monto_pendiente = db.Column(db.Numeric(10, 2), nullable=True)
    monto_pagado = db.Column(db.Numeric(10, 2), nullable=True)
    estado = db.Column(db.String(20), default="Pendiente")
    fecha_pago = db.Column(db.Date, nullable=False)

    cliente = db.relationship('Cliente', backref='pagos')
    
    # Usamos back_populates en lugar de backref
    prestamo_individual = db.relationship('PrestamoIndividual', back_populates='pagos')

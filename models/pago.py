from models import db
from datetime import datetime

class Pago(db.Model):
    __tablename__ = 'pago'
    
    id = db.Column(db.Integer, primary_key=True)
    prestamo_individual_id = db.Column(db.Integer, db.ForeignKey('prestamoindividual.id'), nullable=False)
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)
    monto_pagado = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(20), default='Pendiente')  # Puede ser 'Pendiente', 'Atrasado' o 'Pagado'

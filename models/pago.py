from models import db
from datetime import datetime
from sqlalchemy.orm import relationship

class Pago(db.Model):
    __tablename__ = 'pago'

    id = db.Column(db.Integer, primary_key=True)
    prestamo_individual_id = db.Column(db.Integer, db.ForeignKey('prestamoindividual.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    fecha_pago = db.Column(db.Date, nullable=False)
    monto_pagado = db.Column(db.Float, default=0.0)
    estado = db.Column(db.String(50), default='Pendiente')
    monto_pendiente = db.Column(db.Float, default=0.0)
    
    # ------------------- CAMPOS AGREGADOS -------------------
    fecha_cancelacion_pago_cuota = db.Column(db.Date, nullable=True)
    dias_atraso = db.Column(db.Integer, default=0)
    monto_mora = db.Column(db.Float, default=0.0) # Cargo por mora
    # --------------------------------------------------------

    # Relaciones
    prestamo_individual = relationship('PrestamoIndividual', back_populates='pagos')
    cliente = relationship('Cliente', back_populates='pagos')

    def __repr__(self):
        return f'<Pago {self.id}>'
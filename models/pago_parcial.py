from models import db
from datetime import datetime
from sqlalchemy.orm import relationship

class PagoParcial(db.Model):
    __tablename__ = 'pago_parcial'

    id = db.Column(db.Integer, primary_key=True)
    pago_id = db.Column(db.Integer, db.ForeignKey('pago.id'), nullable=False)
    monto_abono = db.Column(db.Float, nullable=False)
    fecha_abono = db.Column(db.DateTime, default=datetime.utcnow)
    observaciones = db.Column(db.String(255))
    usuario_registro_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    
    # Relaciones
    pago = relationship('Pago', back_populates='pagos_parciales')
    usuario_registro = relationship('Usuario', backref='pagos_parciales_registrados')

    def __repr__(self):
        return f'<PagoParcial {self.id} - S/{self.monto_abono}>'
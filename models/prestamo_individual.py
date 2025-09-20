from models import db
from sqlalchemy import func
from sqlalchemy.orm import relationship # Asegúrate de que esta importación esté presente

class PrestamoIndividual(db.Model):
    __tablename__ = 'prestamoindividual'
    
    id = db.Column(db.Integer, primary_key=True)
    prestamo_grupal_id = db.Column(db.Integer, db.ForeignKey('prestamogrupal.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    monto_pagado = db.Column(db.Float, default=0.0)
    monto = db.Column(db.Float, nullable=False)

    # Relación con los pagos
    pagos = relationship('Pago', back_populates='prestamo_individual', cascade='all, delete-orphan', lazy='subquery')
    
    # Agrega esta línea corregida para manejar la relación con Contrato
    contratos = relationship('Contrato', back_populates='prestamo_individual', cascade='all, delete-orphan')
    
    # Relación con el préstamo grupal
    prestamo_grupal = relationship('PrestamoGrupal', back_populates='prestamos_individuales')
    
    @property
    def monto_pendiente(self):
        from models.pago import Pago # Importación dentro del método para evitar ciclos

        monto_pagado = db.session.query(db.func.sum(Pago.monto_pagado)).filter(
        Pago.prestamo_individual_id == self.id,
        Pago.estado.in_(["Pagado", "Incompleto"])
    ).scalar() or 0
        
        return float(monto_pagado)

    def obtener_numero_cuota(self):
        cuotas = {
            500: 151, 600: 181, 700: 211, 800: 241, 900: 271,
            1000: 302, 1100: 331, 1200: 361, 1300: 391,
            1400: 421, 1500: 451
        }
        return cuotas.get(self.monto, None)
from models import db

class PrestamoIndividual(db.Model):
    __tablename__ = 'prestamoindividual'
    
    id = db.Column(db.Integer, primary_key=True)
    prestamo_grupal_id = db.Column(db.Integer, db.ForeignKey('prestamogrupal.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    monto_pagado = db.Column(db.Float, default=0.0)
    monto = db.Column(db.Float, nullable=False)

    # Relación con los pagos
    pagos = db.relationship('Pago', back_populates='prestamo_individual', cascade='all, delete-orphan', lazy='subquery')  # Considerar 'subquery' si hay muchos pagos
    # Relación con el préstamo grupal
    prestamo_grupal = db.relationship('PrestamoGrupal', back_populates='prestamos_individuales')
    

    @property
    def monto_pendiente(self):
        # Verificar que monto_pagado no sea None
        if self.monto_pagado is None:
            return self.monto
        return self.monto - self.monto_pagado

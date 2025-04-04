from models import db
from datetime import date

class PrestamoGrupal(db.Model):
    __tablename__ = 'prestamogrupal'
    
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=False)
    fecha_desembolso = db.Column(db.Date, nullable=False, default=date.today)  # Valor por defecto: hoy

    # Relación con PrestamoIndividual
    prestamos_individuales = db.relationship('PrestamoIndividual', back_populates='prestamo_grupal', cascade='all, delete-orphan', lazy='subquery')


    @property
    def monto_total(self):
        """Calcula automáticamente el monto total sumando los préstamos individuales."""
        return sum(prestamo.monto for prestamo in self.prestamos_individuales) if self.prestamos_individuales else 0.0

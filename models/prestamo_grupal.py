from models import db
from datetime import datetime

class PrestamoGrupal(db.Model):
    __tablename__ = 'prestamogrupal'
    
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=False)
    monto_total = db.Column(db.Float, nullable=True)
    fecha_desembolso = db.Column(db.DateTime, nullable=False)

    prestamos_individuales = db.relationship('PrestamoIndividual', backref='prestamo_grupal', lazy=True)

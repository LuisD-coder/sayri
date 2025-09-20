from models import db
from sqlalchemy.orm import relationship

class Contrato(db.Model):
    __tablename__ = 'contrato'

    id = db.Column(db.Integer, primary_key=True)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    datos_binarios = db.Column(db.LargeBinary, nullable=False, default=b'') # b'' es un valor binario vacío
    
    # Clave foránea al préstamo individual
    prestamo_individual_id = db.Column(db.Integer, db.ForeignKey('prestamoindividual.id'), nullable=False)
    
    # Relación con el cliente (si es necesaria)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True) # Lo hago nullable=True por si un contrato no está vinculado a un cliente

    # Agrega esta relación para la vinculación bidireccional
    prestamo_individual = relationship('PrestamoIndividual', back_populates='contratos')
    cliente = relationship('Cliente', back_populates='contratos')
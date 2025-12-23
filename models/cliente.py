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

    # --- NUEVOS CAMPOS DE CONTACTO Y UBICACIÓN ---
    email = db.Column(db.String(120), nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    referencia = db.Column(db.String(255), nullable=True)
    latitud = db.Column(db.String(50), nullable=True)
    longitud = db.Column(db.String(50), nullable=True)
    # ---------------------------------------------

    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=True)

    # Relaciones
    pagos = relationship('Pago', back_populates='cliente')
    prestamos_individuales = db.relationship('PrestamoIndividual', backref='cliente', lazy=True)
    contratos = relationship('Contrato', back_populates='cliente', lazy=True)

    def get_num_fotos(self):
        """Retorna el número de fotos del cliente"""
        from models.foto_cliente import FotoCliente
        return FotoCliente.query.filter_by(cliente_id=self.id).count()
from models import db

class Contrato(db.Model):
    __tablename__ = 'contrato'
    id = db.Column(db.Integer, primary_key=True)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    archivo = db.Column(db.LargeBinary, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp())
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    cliente = db.relationship('Cliente', backref=db.backref('contratos', lazy=True))

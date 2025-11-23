from models import db
from datetime import datetime

class FotoCliente(db.Model):
    __tablename__ = 'fotos_clientes'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)
    orden = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'orden': self.orden,
            'fecha_subida': self.fecha_subida.strftime('%Y-%m-%d %H:%M:%S')
        }
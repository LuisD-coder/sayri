from models import db
from datetime import datetime

class Comunicado(db.Model):
    __tablename__ = 'comunicado'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    # Tipos: 'info' (azul), 'warning' (amarillo), 'danger' (rojo), 'success' (verde)
    tipo = db.Column(db.String(20), default='info') 
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Comunicado {self.titulo}>'
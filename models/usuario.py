from models import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Importamos la tabla intermedia desde su archivo
from models.usuario_grupo import usuario_grupo 

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    rol = db.relationship('Rol', backref=db.backref('usuarios', lazy=True))

    # ✅ CORREGIDO: Usamos back_populates para conectar con 'Grupo.usuarios'
    grupos = db.relationship('Grupo', secondary=usuario_grupo, back_populates='usuarios')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Usuario {self.nombre} {self.apellido} - {self.rol.nombre}>"
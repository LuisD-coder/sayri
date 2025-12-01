from models import db
from datetime import datetime
# Importamos la tabla intermedia para que coincida con el modelo Usuario
from models.usuario_grupo import usuario_grupo

class Grupo(db.Model):
    __tablename__ = 'grupo'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ✅ CORREGIDO: Usamos back_populates para conectar con 'Usuario.grupos'
    usuarios = db.relationship('Usuario', secondary=usuario_grupo, back_populates='grupos')
    
    # Relaciones existentes
    clientes = db.relationship('Cliente', backref='grupo', lazy=True)
    prestamos_grupales = db.relationship('PrestamoGrupal', backref='grupo', lazy=True)
    
    def __repr__(self):
        return f'<Grupo {self.nombre}>'
    
    # Verificar si un usuario tiene acceso
    def tiene_acceso(self, usuario):
        if usuario.rol.nombre == 'admin':
            return True
        return usuario in self.usuarios
    
    # Agregar usuario al grupo
    def agregar_usuario(self, usuario):
        if usuario not in self.usuarios:
            self.usuarios.append(usuario)
    
    # Remover usuario del grupo
    def remover_usuario(self, usuario):
        if usuario in self.usuarios:
            self.usuarios.remove(usuario)
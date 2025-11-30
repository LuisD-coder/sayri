from models import db
from datetime import datetime

class Grupo(db.Model):
    __tablename__ = 'grupo'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ✅ NUEVA RELACIÓN: Muchos a muchos con Usuario
    usuarios = db.relationship('Usuario', 
                               secondary='usuario_grupo',
                               backref=db.backref('grupos_asignados', lazy='dynamic'))
    
    # Relaciones existentes
    clientes = db.relationship('Cliente', backref='grupo', lazy=True)
    prestamos_grupales = db.relationship('PrestamoGrupal', backref='grupo', lazy=True)
    
    def __repr__(self):
        return f'<Grupo {self.nombre}>'
    
    # ✅ NUEVO MÉTODO: Verificar si un usuario tiene acceso
    def tiene_acceso(self, usuario):
        """Verifica si el usuario tiene acceso a este grupo"""
        # Admin siempre tiene acceso
        if usuario.rol.nombre == 'admin':
            return True
        # Verificar si el usuario está en la lista de usuarios del grupo
        return usuario in self.usuarios
    
    # ✅ NUEVO MÉTODO: Agregar usuario al grupo
    def agregar_usuario(self, usuario):
        """Agrega un usuario al grupo"""
        if usuario not in self.usuarios:
            self.usuarios.append(usuario)
    
    # ✅ NUEVO MÉTODO: Remover usuario del grupo
    def remover_usuario(self, usuario):
        """Remueve un usuario del grupo"""
        if usuario in self.usuarios:
            self.usuarios.remove(usuario)
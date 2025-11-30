from models import db

# Tabla intermedia para la relación muchos a mucos entre Usuario y Grupo
usuario_grupo = db.Table('usuario_grupo',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True),
    db.Column('grupo_id', db.Integer, db.ForeignKey('grupo.id'), primary_key=True),
    db.Column('fecha_asignacion', db.DateTime, default=db.func.now())
)
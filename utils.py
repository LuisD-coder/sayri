from models import db, Rol, Usuario
from werkzeug.security import generate_password_hash

def inicializar_roles():
    roles = ["admin", "manager", "agent"]
    for nombre in roles:
        if not Rol.query.filter_by(nombre=nombre).first():
            nuevo_rol = Rol(nombre=nombre)
            db.session.add(nuevo_rol)
    db.session.commit()
    print("Roles inicializados.")

def crear_admin():
    # Verificar que el rol 'admin' exista
    admin_rol = Rol.query.filter_by(nombre="admin").first()
    if not admin_rol:
        print("⚠️ El rol 'admin' no existe. Ejecuta primero la inicialización de roles.")
        return

    # Verificar si ya existe un usuario admin
    admin_user = Usuario.query.filter_by(email="luis.d.irigoin@gmail.com").first()
    if admin_user:
        print("✅ El usuario administrador ya existe.")
        return

    # Crear el nuevo usuario admin
    nuevo_admin = Usuario(
        nombre="Luis",
        apellido="Domínguez",
        email="luis.d.irigoin@gmail.com",  # Cambié el email para que sea único
        password_hash=generate_password_hash("admin123", method="pbkdf2:sha256"),
        rol_id=admin_rol.id,
        is_active=True  # Asegúrate de agregar este atributo
    )

    # Agregar y confirmar el usuario en la base de datos
    db.session.add(nuevo_admin)
    db.session.commit()
    print("🎉 Usuario administrador 'Luis Domínguez' creado con éxito.")
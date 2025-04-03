from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Usuario, Rol
from werkzeug.security import generate_password_hash

usuarios_bp = Blueprint('admin', __name__, url_prefix='/admin')

@usuarios_bp.route('/crear_usuario', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    # Solo el admin puede crear usuarios
    if current_user.rol.nombre != 'admin':
        abort(403)  # Acceso denegado

    roles = Rol.query.all()  # Obtener todos los roles disponibles

    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        password = request.form['password']
        rol_id = request.form['rol_id']

        # Verificar que el correo no exista ya en la base de datos
        if Usuario.query.filter_by(email=email).first():
            flash("El correo ya está registrado.", "danger")
            return redirect(url_for('admin.crear_usuario'))  # ✅ Redirección corregida

        nuevo_usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            email=email,
            password_hash=generate_password_hash(password),
            rol_id=rol_id
        )

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("Usuario creado con éxito.", "success")
        return redirect(url_for('admin.listar_usuarios'))  # ✅ Redirección corregida

    return render_template('admin/crear_usuario.html', roles=roles)


@usuarios_bp.route('/usuarios')
@login_required
def listar_usuarios():
    # Solo el admin puede ver la lista de usuarios
    if current_user.rol.nombre != 'admin':
        abort(403)

    usuarios = Usuario.query.all()
    return render_template('admin/listar_usuarios.html', usuarios=usuarios)


@usuarios_bp.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if current_user.rol.nombre != 'admin':
        abort(403)

    usuario = Usuario.query.get_or_404(id)
    roles = Rol.query.all()

    if request.method == 'POST':
        usuario.nombre = request.form['nombre']
        usuario.apellido = request.form['apellido']
        usuario.email = request.form['email']
        usuario.rol_id = request.form['rol_id']

        # Actualizar la contraseña solo si se proporciona una nueva
        nueva_password = request.form.get('password')
        if nueva_password:
            usuario.password_hash = generate_password_hash(nueva_password)

        db.session.commit()
        flash("Usuario actualizado con éxito.", "success")
        return redirect(url_for('admin.listar_usuarios'))

    return render_template('admin/editar_usuario.html', usuario=usuario, roles=roles)


@usuarios_bp.route('/eliminar_usuario/<int:id>', methods=['POST'])
@login_required
def eliminar_usuario(id):
    if current_user.rol.nombre != 'admin':
        abort(403)

    usuario = Usuario.query.get_or_404(id)

    db.session.delete(usuario)
    db.session.commit()
    flash("Usuario eliminado con éxito.", "success")
    
    return redirect(url_for('admin.listar_usuarios'))
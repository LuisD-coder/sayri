from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.security import check_password_hash
from models import db, Usuario

# Crear un Blueprint para login
login_bp = Blueprint('login', __name__)

# Ruta de login
@login_bp.route('/login', methods=['GET', 'POST'])
def login_view():
    if current_user.is_authenticated:
        return redirect(url_for('base.home'))  # Redirigir a la página principal si el usuario ya está autenticado

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Buscar al usuario por email
        user = Usuario.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)  # Iniciar sesión

            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('base.home'))  # Redirigir a la página de inicio (raíz del proyecto)

        flash('Correo o contraseña incorrectos', 'danger')

    return render_template('login/login.html')

# Ruta del dashboard (página protegida)
@login_bp.route('/')
@login_required
def base():
    return render_template('base.html')  # Se asume que base.html está en la carpeta templates



# Ruta de logout
@login_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login.login_view'))

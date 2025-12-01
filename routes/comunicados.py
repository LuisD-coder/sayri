from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Comunicado

comunicados_bp = Blueprint('comunicados', __name__, url_prefix='/comunicados')

@comunicados_bp.route('/', methods=['GET', 'POST'])
@login_required
def gestion():
    # 1. Seguridad: Solo admin
    if current_user.rol.nombre != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('home.index')) # O tu ruta de inicio

    # 2. Crear Nuevo Comunicado
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        mensaje = request.form.get('mensaje')
        tipo = request.form.get('tipo')
        
        nuevo = Comunicado(titulo=titulo, mensaje=mensaje, tipo=tipo, activo=True)
        db.session.add(nuevo)
        db.session.commit()
        flash('Comunicado publicado exitosamente.', 'success')
        return redirect(url_for('comunicados.gestion'))

    # 3. Listar existentes (Ordenados por fecha)
    comunicados = Comunicado.query.order_by(Comunicado.fecha_creacion.desc()).all()
    return render_template('comunicados/gestion.html', comunicados=comunicados)

@comunicados_bp.route('/<int:id>/cambiar_estado', methods=['POST'])
@login_required
def cambiar_estado(id):
    if current_user.rol.nombre != 'admin':
        return redirect(url_for('home.index'))
        
    comunicado = Comunicado.query.get_or_404(id)
    comunicado.activo = not comunicado.activo # Invierte el estado (True/False)
    db.session.commit()
    
    estado = "activado" if comunicado.activo else "desactivado"
    flash(f'Comunicado {estado}.', 'info')
    return redirect(url_for('comunicados.gestion'))

@comunicados_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar(id):
    if current_user.rol.nombre != 'admin':
        return redirect(url_for('home.index'))

    comunicado = Comunicado.query.get_or_404(id)
    db.session.delete(comunicado)
    db.session.commit()
    flash('Comunicado eliminado.', 'warning')
    return redirect(url_for('comunicados.gestion'))
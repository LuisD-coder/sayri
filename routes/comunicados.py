from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Comunicado, Usuario

comunicados_bp = Blueprint('comunicados', __name__, url_prefix='/comunicados')

@comunicados_bp.route('/', methods=['GET', 'POST'])
@login_required
def gestion():
    if current_user.rol.nombre != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('home.index'))

    if request.method == 'POST':
        # ... (código de creación igual que antes) ...
        titulo = request.form.get('titulo')
        mensaje = request.form.get('mensaje')
        tipo = request.form.get('tipo')
        nuevo = Comunicado(titulo=titulo, mensaje=mensaje, tipo=tipo, activo=True)
        db.session.add(nuevo)
        db.session.commit()
        flash('Comunicado publicado.', 'success')
        return redirect(url_for('comunicados.gestion'))

    comunicados = Comunicado.query.order_by(Comunicado.fecha_creacion.desc()).all()
    
    # ✅ NUEVO: Obtenemos todos los usuarios activos para calcular "quien falta"
    # Ajusta el filtro si tienes un campo 'is_active' o similar
    todos_usuarios = Usuario.query.all() 

    return render_template('comunicados/gestion.html', comunicados=comunicados, todos_usuarios=todos_usuarios)

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


@comunicados_bp.route('/marcar_visto/<int:id>', methods=['POST'])
@login_required
def marcar_visto(id):
    comunicado = Comunicado.query.get_or_404(id)
    
    # Si el usuario no está en la lista, lo agregamos
    if current_user not in comunicado.usuarios_vistos:
        comunicado.usuarios_vistos.append(current_user)
        db.session.commit()
        
    return jsonify({'success': True})
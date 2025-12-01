from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models import db, Grupo, Cliente, PrestamoGrupal, PrestamoIndividual, Pago, Contrato, Usuario, Rol
from datetime import datetime
from flask_login import login_required, current_user
from sqlalchemy.orm import session

grupos_bp = Blueprint('grupos', __name__, url_prefix='/grupos')

@grupos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_grupo():
    if request.method == 'POST':
        nombre = request.form['nombre']
        nuevo_grupo = Grupo(nombre=nombre)
        
        # Asignar automáticamente el usuario creador al grupo
        nuevo_grupo.agregar_usuario(current_user)
        
        db.session.add(nuevo_grupo)
        db.session.commit()
        
        flash(f'Grupo "{nombre}" creado exitosamente', 'success')
        return redirect(url_for('grupos.lista_grupos'))

    return render_template('grupos/nuevo_grupo.html')


@grupos_bp.route('/<int:grupo_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_grupo(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    
    if not grupo.tiene_acceso(current_user):
        flash('No tienes permiso para editar este grupo', 'danger')
        return redirect(url_for('grupos.lista_grupos'))

    if request.method == 'POST':
        nuevo_nombre = request.form['nombre']

        if nuevo_nombre.strip():
            grupo.nombre = nuevo_nombre.strip()
            db.session.commit()
            flash('Grupo actualizado exitosamente.', 'success')
            return redirect(url_for('grupos.lista_grupos'))
        else:
            flash('El nombre del grupo no puede estar vacío.', 'danger')

    return render_template('grupos/editar_grupo.html', grupo=grupo)


@grupos_bp.route('/')
@login_required
def lista_grupos():
    if current_user.rol.nombre == 'admin':
        grupos = Grupo.query.all()
    else:
        # ✅ CORREGIDO: Usamos .grupos en lugar de .grupos_asignados
        # Al no ser lazy='dynamic', esto ya devuelve una lista, no necesitamos .all()
        grupos = current_user.grupos
    
    return render_template('grupos/lista_grupos.html', grupos=grupos)


@grupos_bp.route('/<int:grupo_id>/asignar_clientes', methods=['GET', 'POST'])
@login_required
def asignar_clientes(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    
    if not grupo.tiene_acceso(current_user):
        flash('No tienes permiso para gestionar clientes de este grupo', 'danger')
        return redirect(url_for('grupos.lista_grupos'))

    clientes_asignados = Cliente.query.filter_by(grupo_id=grupo_id).all()
    filtro = request.args.get('filtro', '').strip()
    clientes_disponibles = []
    
    if filtro:
        clientes_disponibles = Cliente.query.filter(
            (Cliente.nombre.ilike(f"%{filtro}%")) | (Cliente.dni.ilike(f"%{filtro}%"))
        ).all()
        clientes_disponibles = [c for c in clientes_disponibles if c.id not in [cli.id for cli in clientes_asignados]]

    if request.method == 'POST':
        for cliente_id in request.form.getlist('clientes'):
            cliente = Cliente.query.get(cliente_id)
            cliente.grupo_id = grupo.id
            db.session.commit()
        
        flash('Clientes asignados exitosamente', 'success')
        return redirect(url_for('grupos.asignar_clientes', grupo_id=grupo.id))

    return render_template(
        'grupos/asignar_clientes.html',
        grupo=grupo,
        clientes_asignados=clientes_asignados,
        clientes_disponibles=clientes_disponibles,
        filtro=filtro
    )


@grupos_bp.route('/<int:grupo_id>/eliminar', methods=['POST'])
@login_required
def eliminar_grupo(grupo_id):
    if not current_user.is_authenticated or current_user.rol.nombre not in ['admin', 'manager']:
        abort(403)

    grupo = Grupo.query.get_or_404(grupo_id)
    
    if current_user.rol.nombre == 'manager' and not grupo.tiene_acceso(current_user):
        flash('No tienes permiso para eliminar este grupo', 'danger')
        return redirect(url_for('grupos.lista_grupos'))

    try:
        with db.session.no_autoflush: 
            prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo.id).all()

            for prestamo_grupal in prestamos_grupales:
                prestamos_individuales = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal.id).all()
                for prestamo_individual in prestamos_individuales:
                    contratos = Contrato.query.filter_by(prestamo_individual_id=prestamo_individual.id).all()
                    for contrato in contratos:
                        db.session.delete(contrato)

                    pagos = Pago.query.filter_by(prestamo_individual_id=prestamo_individual.id).all()
                    for pago in pagos:
                        db.session.delete(pago)

                    db.session.delete(prestamo_individual)

                db.session.delete(prestamo_grupal)

            clientes = Cliente.query.filter_by(grupo_id=grupo.id).all()
            for cliente in clientes:
                cliente.grupo_id = None

        db.session.commit()
        db.session.delete(grupo)
        db.session.commit()

        flash('Grupo y todas sus relaciones eliminadas exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar el grupo: {str(e)}")
        flash(f'Ocurrió un error al eliminar el grupo: {str(e)}', 'danger')

    return redirect(url_for('grupos.lista_grupos'))


@grupos_bp.route('/<int:grupo_id>/usuarios', methods=['GET', 'POST'])
@login_required
def gestionar_usuarios_grupo(grupo_id):
    if current_user.rol.nombre != 'admin':
        flash('No tienes permiso para esta acción', 'danger')
        return redirect(url_for('grupos.lista_grupos'))
    
    grupo = Grupo.query.get_or_404(grupo_id)
    
    if request.method == 'POST':
        usuario_id = request.form.get('usuario_id')
        accion = request.form.get('accion')
        
        usuario = Usuario.query.get_or_404(usuario_id)
        
        if accion == 'agregar':
            grupo.agregar_usuario(usuario)
            flash(f'Usuario {usuario.nombre} {usuario.apellido} agregado al grupo', 'success')
        elif accion == 'remover':
            grupo.remover_usuario(usuario)
            flash(f'Usuario {usuario.nombre} {usuario.apellido} removido del grupo', 'success')
        
        db.session.commit()
        return redirect(url_for('grupos.gestionar_usuarios_grupo', grupo_id=grupo_id))
    
    todos_usuarios = Usuario.query.all()
    
    return render_template('grupos/gestionar_usuarios.html', 
                          grupo=grupo, 
                          todos_usuarios=todos_usuarios)


@grupos_bp.route('/<int:grupo_id>')
@login_required
def detalle_grupo(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    
    if not grupo.tiene_acceso(current_user):
        flash('No tienes permiso para ver este grupo', 'danger')
        return redirect(url_for('grupos.lista_grupos'))
    
    clientes = Cliente.query.filter_by(grupo_id=grupo_id).all()
    prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).order_by(PrestamoGrupal.fecha_desembolso.desc()).all()
    
    return render_template('grupos/detalle_grupo.html', 
                          grupo=grupo, 
                          clientes=clientes,
                          prestamos_grupales=prestamos_grupales)


@grupos_bp.route('/asignacion_masiva', methods=['GET', 'POST'])
@login_required
def asignacion_masiva():
    if current_user.rol.nombre != 'admin':
        flash('No tienes permiso para acceder a esta vista.', 'danger')
        return redirect(url_for('grupos.lista_grupos'))

    asesores = Usuario.query.join(Rol).filter(Rol.nombre != 'admin').all()
    todos_los_grupos = Grupo.query.order_by(Grupo.nombre).all()
    
    usuario_seleccionado_id = request.args.get('usuario_id', type=int)
    usuario_seleccionado = None
    grupos_ids_asignados = []

    if usuario_seleccionado_id:
        usuario_seleccionado = Usuario.query.get_or_404(usuario_seleccionado_id)
        # ✅ CORREGIDO: Usamos .grupos en lugar de .grupos_asignados
        grupos_ids_asignados = [g.id for g in usuario_seleccionado.grupos]

    if request.method == 'POST':
        usuario_id_post = request.form.get('usuario_id')
        
        if not usuario_id_post:
            flash('Debes seleccionar un asesor.', 'warning')
            return redirect(url_for('grupos.asignacion_masiva'))

        usuario_a_actualizar = Usuario.query.get(usuario_id_post)
        grupos_seleccionados_ids = request.form.getlist('grupos_ids')
        
        nuevos_grupos = Grupo.query.filter(Grupo.id.in_(grupos_seleccionados_ids)).all()
        # ✅ CORREGIDO: Usamos .grupos para actualizar
        usuario_a_actualizar.grupos = nuevos_grupos
        
        db.session.commit()
        
        flash(f'Asignaciones actualizadas correctamente para {usuario_a_actualizar.nombre}.', 'success')
        return redirect(url_for('grupos.asignacion_masiva', usuario_id=usuario_id_post))

    return render_template('grupos/asignacion_masiva.html',
                           asesores=asesores,
                           grupos=todos_los_grupos,
                           usuario_seleccionado=usuario_seleccionado,
                           grupos_ids_asignados=grupos_ids_asignados)
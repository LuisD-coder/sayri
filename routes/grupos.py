from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models import db, Grupo, Cliente, PrestamoGrupal,PrestamoIndividual,Pago,Contrato
from datetime import datetime
from flask_login import login_required, current_user
from sqlalchemy.orm import session


grupos_bp = Blueprint('grupos', __name__, url_prefix='/grupos')

# Crear un nuevo grupo
@grupos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_grupo():
    if request.method == 'POST':
        nombre = request.form['nombre']
        nuevo_grupo = Grupo(nombre=nombre)
        db.session.add(nuevo_grupo)
        db.session.commit()
        return redirect(url_for('grupos.lista_grupos'))

    return render_template('grupos/nuevo_grupo.html')

# Listar todos los grupos
@grupos_bp.route('/')
@login_required
def lista_grupos():
    grupos = Grupo.query.all()
    return render_template('grupos/lista_grupos.html', grupos=grupos)


@grupos_bp.route('/<int:grupo_id>/asignar_clientes', methods=['GET', 'POST'])
@login_required
def asignar_clientes(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)

    # Obtener los clientes ya asignados al grupo actual
    clientes_asignados = Cliente.query.filter_by(grupo_id=grupo_id).all()

    # Obtener el valor del filtro
    filtro = request.args.get('filtro', '').strip()

    clientes_disponibles = []  # Inicializar la lista de clientes disponibles
    
    if filtro:
        # Buscar clientes por nombre o DNI, incluso si están en otro grupo
        clientes_disponibles = Cliente.query.filter(
            (Cliente.nombre.ilike(f"%{filtro}%")) | (Cliente.dni.ilike(f"%{filtro}%"))
        ).all()

        # Excluir los clientes que ya están en el grupo actual
        clientes_disponibles = [c for c in clientes_disponibles if c.id not in [cli.id for cli in clientes_asignados]]

    if request.method == 'POST':
        # Asignar clientes seleccionados al grupo
        for cliente_id in request.form.getlist('clientes'):
            cliente = Cliente.query.get(cliente_id)
            cliente.grupo_id = grupo.id
            db.session.commit()
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
    # Verificar si el usuario tiene los roles permitidos
    if current_user.rol not in ['admin', 'manager']:
        abort(403)  # Denegar acceso (403 Forbidden)

    grupo = Grupo.query.get_or_404(grupo_id)

    try:
        with db.session.no_autoflush:  # Prevenir autoflush conflictivo
            # Obtener todos los préstamos grupales del grupo
            prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo.id).all()

            for prestamo_grupal in prestamos_grupales:
                # Obtener todos los préstamos individuales del préstamo grupal
                prestamos_individuales = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal.id).all()
                for prestamo_individual in prestamos_individuales:
                    # Eliminar contratos asociados al préstamo individual
                    contratos = Contrato.query.filter_by(prestamo_individual_id=prestamo_individual.id).all()
                    for contrato in contratos:
                        db.session.delete(contrato)

                    # Eliminar pagos asociados al préstamo individual
                    pagos = Pago.query.filter_by(prestamo_individual_id=prestamo_individual.id).all()
                    for pago in pagos:
                        db.session.delete(pago)

                    # Eliminar el préstamo individual
                    db.session.delete(prestamo_individual)

                # Eliminar el préstamo grupal
                db.session.delete(prestamo_grupal)

            # Desasignar clientes del grupo
            clientes = Cliente.query.filter_by(grupo_id=grupo.id).all()
            for cliente in clientes:
                cliente.grupo_id = None  # Asignar NULL al grupo_id

        db.session.commit()  # Guardar todos los cambios

        # Finalmente, eliminar el grupo
        db.session.delete(grupo)
        db.session.commit()

        flash('Grupo y todas sus relaciones eliminadas exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar el grupo: {str(e)}")
        flash(f'Ocurrió un error al eliminar el grupo: {str(e)}', 'danger')

    return redirect(url_for('grupos.lista_grupos'))


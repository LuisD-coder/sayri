from flask import Blueprint, render_template, request, redirect, url_for, abort
from models import db, Cliente, Grupo, PrestamoGrupal, PrestamoIndividual,Contrato, Pago
from flask_login import login_required, current_user

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')

# Crear un nuevo cliente
@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_cliente():
    grupos = Grupo.query.all()
    
    if request.method == 'POST':
        nombre = ' '.join(word.capitalize() for word in request.form['nombre'].strip().split())
        apellido = ' '.join(word.capitalize() for word in request.form['apellido'].strip().split())
        dni = request.form['dni'].strip()
        celular = request.form['celular'].strip()
        operadora = request.form['operadora'].strip().capitalize()
        banco = request.form['banco'].strip().upper()  # Los nombres de bancos suelen ir en mayúsculas
        numero_cuenta = request.form['numero_cuenta'].strip()
        grupo_id = request.form['grupo_id'].strip()
        
        nuevo_cliente = Cliente(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            celular=celular,
            operadora=operadora,
            banco=banco,
            numero_cuenta=numero_cuenta,
            grupo_id=grupo_id
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        return redirect(url_for('clientes.lista_clientes'))

    return render_template('clientes/nuevo_cliente.html', grupos=grupos)



@clientes_bp.route('/')
@login_required
def lista_clientes():
    page = request.args.get('page', 1, type=int)
    grupo_id = request.args.get('grupo_id', type=int)
    search = request.args.get('search', '').strip()

    # Si no hay filtros seleccionados, no ejecutar la consulta
    if not grupo_id and not search:
        return render_template('clientes/lista_clientes.html', clientes=None, grupos=Grupo.query.all(), selected_grupo=None)

    query = Cliente.query
    if grupo_id:
        query = query.filter_by(grupo_id=grupo_id)
    if search:
        query = query.filter(
            Cliente.nombre.ilike(f"%{search}%") | Cliente.dni.ilike(f"%{search}%")
        )

    clientes = query.paginate(page=page, per_page=10)  # 10 clientes por página
    grupos = Grupo.query.all()  # Obtener todos los grupos

    return render_template('clientes/lista_clientes.html', clientes=clientes, grupos=grupos, selected_grupo=grupo_id)

    page = request.args.get('page', 1, type=int)
    grupo_id = request.args.get('grupo_id', type=int)
    search = request.args.get('search', '').strip()

    query = Cliente.query
    if grupo_id:
        query = query.filter_by(grupo_id=grupo_id)
    if search:
        query = query.filter(
            Cliente.nombre.ilike(f"%{search}%") | Cliente.dni.ilike(f"%{search}%")
        )

    clientes = query.paginate(page=page, per_page=10)  # 10 clientes por página
    grupos = Grupo.query.all()  # Obtener todos los grupos

    return render_template('clientes/lista_clientes.html', clientes=clientes, grupos=grupos, selected_grupo=grupo_id)




@clientes_bp.route('/<int:cliente_id>')
@login_required
def detalle_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Obtener los préstamos individuales, contratos, pagos y préstamos grupales relacionados con el cliente
    prestamos = cliente.prestamos_individuales  # Relación con los préstamos individuales
    contratos = cliente.contratos  # Relación con los contratos
    pagos = cliente.pagos  # Relación con los pagos
    prestamos_grupales = PrestamoGrupal.query.join(PrestamoIndividual).filter(PrestamoIndividual.cliente_id == cliente.id).all()  # Obtener préstamos grupales del cliente
    
    return render_template('clientes/detalle_cliente.html', cliente=cliente, prestamos=prestamos, contratos=contratos, pagos=pagos, prestamos_grupales=prestamos_grupales)



@clientes_bp.route('/eliminar/<int:cliente_id>', methods=['POST'])
@login_required
def eliminar_cliente(cliente_id):


    # Verificar si el usuario tiene los roles permitidos
    if not current_user.is_authenticated or current_user.rol.nombre not in ['admin', 'manager']:
        print(f"Acceso denegado. Rol encontrado: {getattr(current_user.rol, 'nombre', 'Sin rol')}")
        abort(403)  # Denegar acceso (403 Forbidden)

    cliente = Cliente.query.get_or_404(cliente_id)  # Obtener el cliente
    
    try:
        # Eliminar todos los préstamos individuales relacionados con el cliente
        PrestamoIndividual.query.filter_by(cliente_id=cliente.id).delete()
        # Eliminar los contratos asociados
        Contrato.query.filter_by(cliente_id=cliente.id).delete()
        # Eliminar todos los pagos relacionados con el cliente
        Pago.query.filter_by(cliente_id=cliente.id).delete()
        
        
        # Ahora eliminar el cliente
        db.session.delete(cliente)
        db.session.commit()
        return redirect(url_for('clientes.lista_clientes'))
    except Exception as e:
        db.session.rollback()
        return f"Error al eliminar el cliente: {str(e)}", 500


@clientes_bp.route('/editar/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def actualizar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)  # Obtener el cliente por su ID
    grupos = Grupo.query.all()  # Listar los grupos disponibles

    if request.method == 'POST':
        try:
            # Actualizar los datos del cliente con los valores del formulario
            cliente.nombre = ' '.join(word.capitalize() for word in request.form['nombre'].strip().split())
            cliente.apellido = ' '.join(word.capitalize() for word in request.form['apellido'].strip().split())
            cliente.dni = request.form['dni'].strip()
            cliente.celular = request.form['celular'].strip()
            cliente.operadora = request.form['operadora'].strip().capitalize()
            cliente.banco = request.form['banco'].strip().upper()
            cliente.numero_cuenta = request.form['numero_cuenta'].strip()
            cliente.grupo_id = request.form['grupo_id'].strip()

            db.session.commit()  # Guardar los cambios en la base de datos
            return redirect(url_for('clientes.detalle_cliente', cliente_id=cliente.id))
        except Exception as e:
            db.session.rollback()  # Revertir los cambios en caso de error
            return f"Error al actualizar el cliente: {str(e)}", 500

    # En caso de GET, renderizar el formulario de edición con los datos existentes
    return render_template('clientes/editar_cliente.html', cliente=cliente, grupos=grupos)

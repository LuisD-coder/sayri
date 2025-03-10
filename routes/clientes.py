from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Cliente, Grupo

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')

# Crear un nuevo cliente
@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    grupos = Grupo.query.all()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        dni = request.form['dni']
        celular = request.form['celular']
        operadora = request.form['operadora']
        banco = request.form['banco']
        numero_cuenta = request.form['numero_cuenta']
        grupo_id = request.form['grupo_id']
        
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

# Listar todos los clientes
@clientes_bp.route('/')
def lista_clientes():
    clientes = Cliente.query.all()
    return render_template('clientes/lista_clientes.html', clientes=clientes)

@clientes_bp.route('/<int:cliente_id>')
def detalle_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    return render_template('clientes/detalle_cliente.html', cliente=cliente)
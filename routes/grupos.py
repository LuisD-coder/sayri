from flask import Blueprint, render_template, request, redirect, url_for
from models import db, Grupo, Cliente, PrestamoGrupal
from datetime import datetime

grupos_bp = Blueprint('grupos', __name__, url_prefix='/grupos')

# Crear un nuevo grupo
@grupos_bp.route('/nuevo', methods=['GET', 'POST'])
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
def lista_grupos():
    grupos = Grupo.query.all()
    return render_template('grupos/lista_grupos.html', grupos=grupos)

# Asignar clientes a un grupo
@grupos_bp.route('/<int:grupo_id>/asignar_clientes', methods=['GET', 'POST'])
def asignar_clientes(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    clientes = Cliente.query.all()

    if request.method == 'POST':
        # Aquí agregarías la lógica para asignar clientes al grupo
        for cliente_id in request.form.getlist('clientes'):
            cliente = Cliente.query.get(cliente_id)
            cliente.grupo_id = grupo.id
            db.session.commit()
        return redirect(url_for('grupos.lista_grupos'))

    return render_template('grupos/asignar_clientes.html', grupo=grupo, clientes=clientes)


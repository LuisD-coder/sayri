from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.pago import Pago
from models.cliente import Cliente
from models.grupo import Grupo
from models.prestamo_grupal import PrestamoGrupal

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

@reportes_bp.route('/')
@login_required
def lista_reportes():
    return render_template('reportes/reportes.html')  # Asegúrate de crear esta plantilla en 'templates'


@reportes_bp.route('/get_prestamos_clientes')
@login_required
def get_prestamos_clientes():
    grupo_id = request.args.get('grupo_id')

    if grupo_id:
        prestamos = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).all()
        prestamos_data = [{"id": p.id, "fecha_desembolso": p.fecha_desembolso.strftime('%d-%m-%Y')} for p in prestamos]

        clientes = Cliente.query.filter_by(grupo_id=grupo_id).all()
        clientes_data = [{"id": c.id, "nombre": c.nombre, "apellido": c.apellido} for c in clientes]

        return jsonify({"prestamos": prestamos_data, "clientes": clientes_data})

    return jsonify({"prestamos": [], "clientes": []})


@reportes_bp.route('/pagos_realizados')
@login_required
def pagos_realizados():
    grupo_id = request.args.get('grupo_id')
    prestamo_grupal_id = request.args.get('prestamo_grupal_id')
    cliente_id = request.args.get('cliente_id')

    pagos = []
    prestamos_grupales = []
    clientes = []

    if grupo_id:
        # Obtener préstamos grupales y clientes del grupo seleccionado
        prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).all()
        clientes = Cliente.query.filter_by(grupo_id=grupo_id).all()

        # Ejecutar consulta de pagos con orden por cliente y fecha de pago
        query = Pago.query.join(Pago.cliente).join(Pago.prestamo_individual).order_by(Pago.cliente_id, Pago.fecha_pago.desc())

        if prestamo_grupal_id:
            query = query.filter(Pago.prestamo_individual.has(prestamo_grupal_id=prestamo_grupal_id))
        if cliente_id:
            query = query.filter(Pago.cliente_id == cliente_id)
        
        pagos = query.all()

    grupos = Grupo.query.all()

    return render_template('reportes/pagos_realizados.html', pagos=pagos, grupos=grupos, prestamos_grupales=prestamos_grupales, clientes=clientes)

@login_required
def pagos_realizados():
    grupo_id = request.args.get('grupo_id')
    prestamo_grupal_id = request.args.get('prestamo_grupal_id')
    cliente_id = request.args.get('cliente_id')

    pagos = []
    if grupo_id or prestamo_grupal_id or cliente_id:
        query = Pago.query.join(Pago.cliente).join(Pago.prestamo_individual).order_by(Pago.fecha_pago.desc())
        if grupo_id:
            query = query.filter(Cliente.grupo_id == grupo_id)
        if prestamo_grupal_id:
            query = query.filter(Pago.prestamo_individual.has(prestamo_grupal_id=prestamo_grupal_id))
        if cliente_id:
            query = query.filter(Pago.cliente_id == cliente_id)
        pagos = query.all()

    grupos = Grupo.query.all()
    return render_template('reportes/pagos_realizados.html', pagos=pagos, grupos=grupos)
    # Obtener valores de filtros
    grupo_id = request.args.get('grupo_id')
    prestamo_grupal_id = request.args.get('prestamo_grupal_id')
    cliente_id = request.args.get('cliente_id')

    # Inicialmente, pagos será una lista vacía
    pagos = []
    
    # Solo ejecuta la consulta si se aplica algún filtro
    if grupo_id or prestamo_grupal_id or cliente_id:
        query = Pago.query.join(Pago.cliente).join(Pago.prestamo_individual).order_by(Pago.fecha_pago.desc())
        if grupo_id:
            query = query.filter(Cliente.grupo_id == grupo_id)
        if prestamo_grupal_id:
            query = query.filter(Pago.prestamo_individual.has(prestamo_grupal_id=prestamo_grupal_id))
        if cliente_id:
            query = query.filter(Pago.cliente_id == cliente_id)
        pagos = query.all()

    # Obtener listas para los filtros
    grupos = Grupo.query.all()
    prestamos_grupales = PrestamoGrupal.query.all()
    clientes = Cliente.query.all()

    return render_template('reportes/pagos_realizados.html', pagos=pagos, grupos=grupos, prestamos_grupales=prestamos_grupales, clientes=clientes)


@reportes_bp.route('/pagos_vencidos')
def pagos_vencidos():
    return render_template('reportes/pagos_vencidos.html')

@reportes_bp.route('/pagos_proximos')
def pagos_proximos():
    return render_template('reportes/pagos_proximos.html')
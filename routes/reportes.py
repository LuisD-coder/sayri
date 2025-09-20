from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import db
from models.pago import Pago
from models.cliente import Cliente  # Asegúrate de que Cliente esté importado
from models.grupo import Grupo
from models.prestamo_grupal import PrestamoGrupal
from models.prestamo_individual import PrestamoIndividual # Asegúrate de que PrestamoIndividual esté importado
from sqlalchemy.orm import aliased

from openpyxl import Workbook
from io import BytesIO
from flask import send_file, make_response
from sqlalchemy import func
from sqlalchemy.orm import aliased

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

@reportes_bp.route('/')
@login_required
def lista_reportes():
    return render_template('reportes/reportes.html')


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
    estado = request.args.get('estado')

    pagos = []
    prestamos_grupales = []
    clientes = []

    if grupo_id:
        prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).all()
        clientes = Cliente.query.filter_by(grupo_id=grupo_id).all()

        query = Pago.query.join(Pago.prestamo_individual).join(PrestamoGrupal).filter(PrestamoGrupal.grupo_id == grupo_id)

        if prestamo_grupal_id:
            query = query.filter(Pago.prestamo_individual.has(prestamo_grupal_id=prestamo_grupal_id))
        if cliente_id:
            query = query.filter(Pago.cliente_id == cliente_id)
        if estado:
            query = query.filter(Pago.estado == estado)

        pagos = query.order_by(Pago.cliente_id, PrestamoGrupal.id, Pago.fecha_pago.desc()).all()

    grupos = Grupo.query.all()

    return render_template('reportes/pagos_realizados.html', pagos=pagos, grupos=grupos, prestamos_grupales=prestamos_grupales, clientes=clientes)


@reportes_bp.route('/pagos_xfecha')
@login_required 
def pagos_xfecha():
    rango_fecha_param = request.args.get('rango_fecha')
    rango_fecha_actual = rango_fecha_param if rango_fecha_param in ["ultima_semana", "semana_2", "semana_3", "semana_4"] else "ultima_semana"

    pagos = [] 
    fecha_inicio = fecha_fin = None
    fecha_hoy = datetime.today()
    fecha_lunes_actual = datetime.combine(fecha_hoy - timedelta(days=fecha_hoy.weekday()), datetime.min.time())

    semanas_offset = {
        "ultima_semana": 0,
        "semana_2": 1,
        "semana_3": 2,
        "semana_4": 3
    }
    fecha_inicio = fecha_lunes_actual + timedelta(weeks=semanas_offset[rango_fecha_actual])
    fecha_fin = fecha_inicio + timedelta(days=6)

    fecha_inicio_comparacion = fecha_inicio.date()
    fecha_fin_comparacion = fecha_fin.date()

    # Subconsulta para obtener el ID del prestamo_grupal más reciente por grupo
    subq = db.session.query(
        PrestamoGrupal.grupo_id,
        db.func.max(PrestamoGrupal.fecha_desembolso).label('fecha_max')
    ).group_by(PrestamoGrupal.grupo_id).subquery()

    pg_alias = aliased(PrestamoGrupal)

    prestamos_grupales_ids = db.session.query(pg_alias.id).join(
        subq,
        (pg_alias.grupo_id == subq.c.grupo_id) &
        (pg_alias.fecha_desembolso == subq.c.fecha_max)
    ).all()

    ids_filtrados = [x[0] for x in prestamos_grupales_ids]


    # Consulta final usando PrestamoIndividual.prestamo_grupal_id
    query = Pago.query \
        .join(Pago.prestamo_individual) \
        .join(Pago.cliente) \
        .filter(
            PrestamoIndividual.prestamo_grupal_id.in_(ids_filtrados),
            db.func.DATE(Pago.fecha_pago) >= fecha_inicio_comparacion,
            db.func.DATE(Pago.fecha_pago) <= fecha_fin_comparacion
        ) \
        .order_by(
            Cliente.nombre,
            Pago.fecha_pago
        )

    pagos = query.all()

    return render_template('reportes/pagos_xfecha.html', 
                           pagos=pagos, 
                           fecha_inicio=fecha_inicio, 
                           timedelta=timedelta,
                           rango_fecha_seleccionado_backend=rango_fecha_actual)
                           
                           


@reportes_bp.route('/pagos_proximos')
def pagos_proximos():
    return render_template('reportes/pagos_proximos.html')




@reportes_bp.route('/exportar_informe_grupos')
@login_required
def exportar_informe_grupos():
    # 1. Preparar la consulta para obtener los datos de los grupos
    grupos = Grupo.query.all()
    
    # 2. Crear el libro de Excel en memoria
    wb = Workbook()
    ws = wb.active
    ws.title = "Informe de Grupos"

    # Encabezados de las columnas
    headers = [
        'ID del Grupo', 'Nombre del Grupo', 'Nombres del Cliente', 'Apellidos del Cliente', 'DNI',
        'Cuota del Cliente', 'N° de Préstamos Grupales', 'N° de Miembros del Grupo',
        'Fecha Desembolso Último Préstamo', 'Fecha Última Cuota'
    ]
    ws.append(headers)

    # Iterar sobre cada grupo para obtener los datos
    for grupo in grupos:
        # Consulta para obtener el último préstamo grupal del grupo actual
        ultimo_prestamo_grupal = PrestamoGrupal.query.filter_by(
            grupo_id=grupo.id
        ).order_by(PrestamoGrupal.fecha_desembolso.desc()).first()

        # Consulta para obtener el número de miembros del grupo
        num_miembros = db.session.query(func.count(Cliente.id)).filter_by(grupo_id=grupo.id).scalar()

        # Iterar sobre cada cliente del grupo
        for cliente in grupo.clientes:
            # Obtener el último préstamo individual del cliente dentro del último préstamo grupal
            cuota_cliente = 0
            if ultimo_prestamo_grupal:
                ultimo_prestamo_individual = PrestamoIndividual.query.filter_by(
                    cliente_id=cliente.id,
                    prestamo_grupal_id=ultimo_prestamo_grupal.id
                ).first()
                if ultimo_prestamo_individual:
                    # Usar el método que ya tienes en el modelo PrestamoIndividual
                    cuota_cliente = ultimo_prestamo_individual.obtener_numero_cuota()

            # Obtener el número de préstamos grupales del cliente
            num_prestamos_grupales_cliente = PrestamoGrupal.query \
                .join(PrestamoIndividual) \
                .filter(PrestamoIndividual.cliente_id == cliente.id).count()

            # Obtener la fecha del último pago del cliente
            fecha_ultima_cuota = None
            ultimo_pago = Pago.query.filter_by(cliente_id=cliente.id).order_by(Pago.fecha_pago.desc()).first()
            if ultimo_pago:
                fecha_ultima_cuota = ultimo_pago.fecha_pago.strftime('%Y-%m-%d')

            # Añadir una nueva fila al archivo Excel
            ws.append([
                grupo.id,
                grupo.nombre,
                cliente.nombre,
                cliente.apellido,
                cliente.dni,
                cuota_cliente,
                num_prestamos_grupales_cliente,
                num_miembros,
                ultimo_prestamo_grupal.fecha_desembolso.strftime('%Y-%m-%d') if ultimo_prestamo_grupal else '',
                fecha_ultima_cuota
            ])

    # 3. Preparar el archivo para el envío
    excel_stream = BytesIO()
    wb.save(excel_stream)
    excel_stream.seek(0)

    # 4. Enviar el archivo como respuesta
    response = make_response(send_file(
        excel_stream,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='informe_grupos.xlsx'
    ))

    return response
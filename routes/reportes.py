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
from sqlalchemy.orm import aliased, joinedload

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
    """
    Vista de agenda semanal de pagos con FILTRO DE PERMISOS.
    """
    # 1. LÓGICA DE FECHAS (Se mantiene igual)
    rango_fecha_param = request.args.get('rango_fecha')
    rango_fecha_actual = rango_fecha_param if rango_fecha_param in [
        "ultima_semana", "semana_2", "semana_3", "semana_4"
    ] else "ultima_semana"

    fecha_hoy = datetime.today()
    fecha_lunes_actual = datetime.combine(
        fecha_hoy - timedelta(days=fecha_hoy.weekday()), 
        datetime.min.time()
    )

    semanas_offset = {
        "ultima_semana": 0, "semana_2": 1, "semana_3": 2, "semana_4": 3
    }

    fecha_inicio = fecha_lunes_actual + timedelta(weeks=semanas_offset[rango_fecha_actual])
    fecha_fin = fecha_inicio + timedelta(days=6)
    fecha_inicio_comparacion = fecha_inicio.date()
    fecha_fin_comparacion = fecha_fin.date()
    fecha_inicio_query = (fecha_inicio - timedelta(days=1)).date()

    # 2. CONSULTA DE PRÉSTAMOS GRUPALES MÁS RECIENTES
    subq = db.session.query(
        PrestamoGrupal.grupo_id,
        db.func.max(PrestamoGrupal.fecha_desembolso).label('fecha_max')
    ).group_by(PrestamoGrupal.grupo_id).subquery()

    pg_alias = aliased(PrestamoGrupal)

    # Construimos la consulta base (Query Builder)
    query_ids = db.session.query(pg_alias.id).join(
        subq,
        (pg_alias.grupo_id == subq.c.grupo_id) & 
        (pg_alias.fecha_desembolso == subq.c.fecha_max)
    )

    # ---------------------------------------------------------
    # 🔒 AQUI ESTÁ EL FILTRO QUE PEDISTE 🔒
    # ---------------------------------------------------------
    # Si el rol NO es admin, filtramos usando la relación que arreglamos en el modelo
    if current_user.rol.nombre != 'admin':
        # Obtenemos los IDs de los grupos asignados a este usuario
        # Esto ahora funciona gracias al arreglo en models/usuario.py
        mis_grupos_ids = [g.id for g in current_user.grupos]
        
        if not mis_grupos_ids:
            # Si el usuario no tiene grupos asignados, filtramos por un ID imposible (-1)
            # para que la agenda salga vacía en lugar de mostrar todo.
            query_ids = query_ids.filter(pg_alias.grupo_id == -1)
        else:
            # Filtramos: Solo mostrar préstamos de MIS grupos
            query_ids = query_ids.filter(pg_alias.grupo_id.in_(mis_grupos_ids))
    # ---------------------------------------------------------

    # Ejecutamos la consulta con el filtro aplicado
    prestamos_grupales_ids = query_ids.all()
    ids_filtrados = [x[0] for x in prestamos_grupales_ids]

    # Si no hay préstamos visibles, retornamos vacío
    if not ids_filtrados:
        return render_template(
            'reportes/pagos_xfecha.html',
            pagos_organizados={},
            fecha_inicio=fecha_inicio,
            timedelta=timedelta,
            rango_fecha_seleccionado_backend=rango_fecha_actual
        )

    # 3. OBTENCIÓN DE PAGOS (Se mantiene igual)
    from sqlalchemy.orm import joinedload
    pagos = (
        Pago.query
        .options(
            joinedload(Pago.cliente),
            joinedload(Pago.prestamo_individual)
                .joinedload(PrestamoIndividual.prestamo_grupal)
                .joinedload(PrestamoGrupal.grupo)
        )
        .join(Pago.prestamo_individual)
        .join(Pago.cliente)
        .filter(
            PrestamoIndividual.prestamo_grupal_id.in_(ids_filtrados),
            db.func.DATE(Pago.fecha_pago) >= fecha_inicio_query,
            db.func.DATE(Pago.fecha_pago) <= fecha_fin_comparacion
        )
        .order_by(Pago.fecha_pago, Cliente.nombre)
        .all()
    )

    # 4. ORGANIZACIÓN Y REPROGRAMACIÓN DE DOMINGOS (Se mantiene igual)
    pagos_organizados = {}
    for i in range(7):
        fecha_dia = (fecha_inicio + timedelta(days=i)).date()
        pagos_organizados[fecha_dia] = {}

    for pago in pagos:
        fecha_pago_original = pago.fecha_pago
        if isinstance(fecha_pago_original, datetime):
            fecha_pago_original = fecha_pago_original.date()
        
        fecha_pago = fecha_pago_original
        grupo_nombre = pago.prestamo_individual.prestamo_grupal.grupo.nombre
        es_reprogramado = False

        if fecha_pago.weekday() == 6:  # Domingo
            fecha_pago_reprogramada = fecha_pago + timedelta(days=1)
            es_reprogramado = True
            if fecha_inicio_comparacion <= fecha_pago_reprogramada <= fecha_fin_comparacion:
                fecha_pago = fecha_pago_reprogramada
            else:
                continue

        if fecha_pago not in pagos_organizados:
            pagos_organizados[fecha_pago] = {}
        if grupo_nombre not in pagos_organizados[fecha_pago]:
            pagos_organizados[fecha_pago][grupo_nombre] = []

        pagos_organizados[fecha_pago][grupo_nombre].append({
            'pago': pago,
            'cuota': pago.prestamo_individual.obtener_numero_cuota(),
            'reprogramado': es_reprogramado,
            'fecha_original': fecha_pago_original if es_reprogramado else None
        })

    return render_template(
        'reportes/pagos_xfecha.html',
        pagos_organizados=pagos_organizados,
        fecha_inicio=fecha_inicio,
        timedelta=timedelta,
        rango_fecha_seleccionado_backend=rango_fecha_actual
    )

                           


@reportes_bp.route('/pagos_proximos')
def pagos_proximos():
    return render_template('reportes/pagos_proximos.html')




@reportes_bp.route('/exportar_informe_grupos')
@login_required
def exportar_informe_grupos():
    # 1. OPTIMIZACIÓN: Cargar todo de una sola vez (Eager Loading)
    # Esto evita cientos de consultas a la BD y hace que el excel se genere rápido
    grupos = Grupo.query.options(
        joinedload(Grupo.clientes),
        joinedload(Grupo.prestamos_grupales)
    ).all()
    
    # 2. Crear Excel en memoria
    wb = Workbook()
    ws = wb.active
    ws.title = "Informe de Grupos"

    headers = [
        'ID del Grupo', 'Nombre del Grupo', 'Nombres del Cliente', 'Apellidos del Cliente', 'DNI',
        'Cuota del Cliente', 'N° de Préstamos Grupales', 'N° de Miembros del Grupo',
        'Fecha Desembolso Último Préstamo', 'Fecha Última Cuota'
    ]
    ws.append(headers)

    for grupo in grupos:
        # Lógica en Python (Rápida)
        prestamos_del_grupo = sorted(grupo.prestamos_grupales, key=lambda x: x.fecha_desembolso, reverse=True)
        ultimo_prestamo_grupal = prestamos_del_grupo[0] if prestamos_del_grupo else None
        
        num_miembros = len(grupo.clientes)

        for cliente in grupo.clientes:
            cuota_cliente = 0
            if ultimo_prestamo_grupal:
                # Buscamos el préstamo individual específico
                prestamo_ind = PrestamoIndividual.query.filter_by(
                    cliente_id=cliente.id, 
                    prestamo_grupal_id=ultimo_prestamo_grupal.id
                ).first()
                
                if prestamo_ind:
                    cuota_cliente = prestamo_ind.obtener_numero_cuota()

            # Contar préstamos totales
            num_prestamos_grupales_cliente = PrestamoGrupal.query \
                .join(PrestamoIndividual) \
                .filter(PrestamoIndividual.cliente_id == cliente.id).count()

            # Último pago
            fecha_ultima_cuota = ""
            ultimo_pago = Pago.query.filter_by(cliente_id=cliente.id).order_by(Pago.fecha_pago.desc()).first()
            if ultimo_pago:
                fecha_ultima_cuota = ultimo_pago.fecha_pago.strftime('%Y-%m-%d')

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

    # 3. Guardar en memoria
    excel_stream = BytesIO()
    wb.save(excel_stream)
    excel_stream.seek(0)

    # 4. SOLUCIÓN AL ERROR DE HOSTING (io.UnsupportedOperation: fileno)
    # En lugar de 'send_file', enviamos los bytes crudos con 'Response'.
    # Esto evita que uWSGI/Gunicorn intente buscar un archivo físico en disco.
    return Response(
        excel_stream.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            "Content-Disposition": "attachment;filename=informe_grupos.xlsx"
        }
    )
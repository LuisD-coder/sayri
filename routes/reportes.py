from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
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
    estado = request.args.get('estado')

    pagos = []
    prestamos_grupales = []
    clientes = []

    if grupo_id:
        # Filtrar préstamos grupales y clientes del grupo seleccionado
        prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).all()
        clientes = Cliente.query.filter_by(grupo_id=grupo_id).all()

        # Filtrar pagos
        query = Pago.query.join(Pago.prestamo_individual).join(PrestamoGrupal).filter(PrestamoGrupal.grupo_id == grupo_id)

        if prestamo_grupal_id:
            query = query.filter(Pago.prestamo_individual.has(prestamo_grupal_id=prestamo_grupal_id))
        if cliente_id:
            query = query.filter(Pago.cliente_id == cliente_id)
        if estado:
            query = query.filter(Pago.estado == estado)  # Filtrar por estado

        # Ordenar pagos por Cliente -> Préstamo Grupal -> Fecha de Pago
        pagos = query.order_by(Pago.cliente_id, PrestamoGrupal.id, Pago.fecha_pago.desc()).all()

    grupos = Grupo.query.all()

    return render_template('reportes/pagos_realizados.html', pagos=pagos, grupos=grupos, prestamos_grupales=prestamos_grupales, clientes=clientes)



@reportes_bp.route('/pagos_xfecha')
@login_required # Asegura que solo usuarios autenticados puedan acceder a esta vista
def pagos_xfecha():
    rango_fecha = request.args.get('rango_fecha')

    # Si no hay filtro de fecha seleccionado (primera carga de la página),
    # renderizar la plantilla sin datos de pagos pero con el timedelta disponible.
    if not rango_fecha:
        return render_template('reportes/pagos_xfecha.html', pagos=[], fecha_inicio=None, timedelta=timedelta)

    pagos = []
    # Inicializa la consulta base con los joins necesarios
    query = Pago.query.join(Pago.prestamo_individual).join(PrestamoGrupal)

    # -------------------------------------------------------------------
    # Lógica para determinar el rango de fechas de la semana seleccionada
    # -------------------------------------------------------------------

    fecha_hoy = datetime.today()
    # weekday() devuelve 0 para lunes, 6 para domingo
    dia_semana_hoy = fecha_hoy.weekday() 

    # Calcula el Lunes de la semana actual (00:00:00)
    # Resta los días necesarios para llegar al lunes de la semana en curso.
    fecha_lunes_semana_actual = fecha_hoy - timedelta(days=dia_semana_hoy)
    
    # Aseguramos que la fecha_lunes_semana_actual no tenga información de tiempo (solo fecha)
    fecha_lunes_semana_actual = fecha_lunes_semana_actual.replace(hour=0, minute=0, second=0, microsecond=0)

    fecha_inicio = None
    fecha_fin = None

    if rango_fecha == "ultima_semana": # Corresponde a "Semana 1 (Actual)"
        fecha_inicio = fecha_lunes_semana_actual
        fecha_fin = fecha_inicio + timedelta(days=6) # El domingo de esa misma semana

    elif rango_fecha == "semana_2": # La siguiente semana
        fecha_inicio = fecha_lunes_semana_actual + timedelta(days=7)
        fecha_fin = fecha_inicio + timedelta(days=6)

    elif rango_fecha == "semana_3": # Dos semanas después de la actual
        fecha_inicio = fecha_lunes_semana_actual + timedelta(days=14)
        fecha_fin = fecha_inicio + timedelta(days=6)

    elif rango_fecha == "semana_4": # Tres semanas después de la actual
        fecha_inicio = fecha_lunes_semana_actual + timedelta(days=21)
        fecha_fin = fecha_inicio + timedelta(days=6)
    
    # -------------------------------------------------------------------
    # Aplicar el filtro de fecha a la consulta de la base de datos
    # -------------------------------------------------------------------

    if fecha_inicio and fecha_fin:
        # Extraer solo la parte de la fecha para la comparación con la DB
        # Esto es crucial si Pago.fecha_pago es un tipo DATETIME y queremos ignorar la hora.
        fecha_inicio_comparacion = fecha_inicio.date()
        fecha_fin_comparacion = fecha_fin.date()

        print(f"DEBUG: Filtrando pagos entre {fecha_inicio_comparacion.strftime('%d-%m-%Y')} y {fecha_fin_comparacion.strftime('%d-%m-%Y')}")

        # Filtra los pagos cuya fecha_pago cae dentro del rango [fecha_inicio, fecha_fin]
        # Usamos db.func.DATE() para asegurar que la comparación se haga solo a nivel de día,
        # sin importar la hora exacta en Pago.fecha_pago.
        query = query.filter(
            db.func.DATE(Pago.fecha_pago) >= fecha_inicio_comparacion,
            db.func.DATE(Pago.fecha_pago) <= fecha_fin_comparacion
        )
    else:
        # Si por alguna razón no se calculó un rango de fechas (ej. rango_fecha inválido),
        # no se deben cargar pagos.
        pagos = []
        return render_template('reportes/pagos_xfecha.html', pagos=pagos, fecha_inicio=fecha_inicio, timedelta=timedelta)


    # Ejecutar la consulta final
    # Ordenar los pagos para una mejor visualización en la tabla
    pagos = query.order_by(
        Pago.cliente_id,
        PrestamoGrupal.id, # Asumiendo que esta es una buena forma de ordenar dentro del grupo/cliente
        Pago.fecha_pago.desc()
    ).all()
    
    print(f"DEBUG: Número de pagos filtrados dentro del rango: {len(pagos)}")

    # Renderizar la plantilla con los datos obtenidos
    return render_template('reportes/pagos_xfecha.html', pagos=pagos, fecha_inicio=fecha_inicio, timedelta=timedelta)



@reportes_bp.route('/pagos_proximos')
def pagos_proximos():
    return render_template('reportes/pagos_proximos.html')
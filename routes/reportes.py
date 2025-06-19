from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import db
from models.pago import Pago
from models.cliente import Cliente  # Asegúrate de que Cliente esté importado
from models.grupo import Grupo
from models.prestamo_grupal import PrestamoGrupal
from models.prestamo_individual import PrestamoIndividual # Asegúrate de que PrestamoIndividual esté importado

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

    # Determinar el rango de fecha seleccionado o establecer "ultima_semana" por defecto
    # Si no se envía rango_fecha, o si el valor es vacío/inválido, se usa "ultima_semana"
    if not rango_fecha_param or rango_fecha_param not in ["ultima_semana", "semana_2", "semana_3", "semana_4"]:
        rango_fecha_actual = "ultima_semana" # Valor por defecto
    else:
        rango_fecha_actual = rango_fecha_param

    pagos = [] 
    fecha_inicio = None
    fecha_fin = None

    fecha_hoy = datetime.today()
    dia_semana_hoy = fecha_hoy.weekday() 
    
    # Calcula el Lunes de la semana actual (hora 00:00:00)
    # Se usa .date() para obtener solo la parte de la fecha y luego se convierte a datetime
    fecha_lunes_semana_actual = datetime.combine(fecha_hoy - timedelta(days=dia_semana_hoy), datetime.min.time())

    # Lógica para calcular fecha_inicio y fecha_fin basada en rango_fecha_actual
    if rango_fecha_actual == "ultima_semana":
        fecha_inicio = fecha_lunes_semana_actual
        fecha_fin = fecha_inicio + timedelta(days=6)
    elif rango_fecha_actual == "semana_2":
        fecha_inicio = fecha_lunes_semana_actual + timedelta(weeks=1)
        fecha_fin = fecha_inicio + timedelta(days=6)
    elif rango_fecha_actual == "semana_3":
        fecha_inicio = fecha_lunes_semana_actual + timedelta(weeks=2)
        fecha_fin = fecha_inicio + timedelta(days=6)
    elif rango_fecha_actual == "semana_4":
        fecha_inicio = fecha_lunes_semana_actual + timedelta(weeks=3)
        fecha_fin = fecha_inicio + timedelta(days=6)
    
    # Realizar la consulta si se pudo determinar un rango de fechas válido
    if fecha_inicio and fecha_fin:
        # Extraer solo la parte de la fecha para la comparación con la DB
        fecha_inicio_comparacion = fecha_inicio.date()
        fecha_fin_comparacion = fecha_fin.date()

        print(f"DEBUG: Filtrando pagos entre {fecha_inicio_comparacion.strftime('%d-%m-%Y')} y {fecha_fin_comparacion.strftime('%d-%m-%Y')} para {rango_fecha_actual}")

        # La consulta debe unirse a Cliente, PrestamoIndividual y PrestamoGrupal
        query = Pago.query \
                    .join(Pago.cliente) \
                    .join(Pago.prestamo_individual) \
                    .join(PrestamoIndividual.prestamo_grupal) \
                    .filter(
                        db.func.DATE(Pago.fecha_pago) >= fecha_inicio_comparacion,
                        db.func.DATE(Pago.fecha_pago) <= fecha_fin_comparacion
                    )
        pagos = query.order_by(
            Cliente.nombre, # Ahora podemos ordenar por Cliente.nombre
            Pago.fecha_pago,
            PrestamoGrupal.id 
        ).all()
        
        print(f"DEBUG: Número de pagos filtrados dentro del rango: {len(pagos)}")
    else:
        # En caso de que `rango_fecha_actual` no se haya mapeado a una fecha válida
        # (aunque con el valor por defecto esto debería ser raro ahora)
        print(f"DEBUG: No se pudo determinar el rango de fechas válido para el filtro: {rango_fecha_actual}. Mostrando agenda vacía.")

    # Renderizar la plantilla
    return render_template('reportes/pagos_xfecha.html', 
                           pagos=pagos, 
                           fecha_inicio=fecha_inicio, 
                           timedelta=timedelta,
                           rango_fecha_seleccionado_backend=rango_fecha_actual) # Pasamos el valor final para el `selected` del HTML


@reportes_bp.route('/pagos_proximos')
def pagos_proximos():
    return render_template('reportes/pagos_proximos.html')
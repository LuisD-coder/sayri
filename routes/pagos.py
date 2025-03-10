from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime, date
from models import Pago, PrestamoIndividual, Cliente, Grupo, PrestamoGrupal
from models import db
from decimal import Decimal

# Crear un Blueprint para la gestión de pagos
pagos_bp = Blueprint('pagos', __name__)

@pagos_bp.route('/pagos', methods=['GET', 'POST'])
def lista_pagos():
    grupos = Grupo.query.all()  # Obtener todos los grupos disponibles
    selected_grupo_id = None
    prestamos = []

    if request.method == 'GET' and request.args.get('grupo_id'):
        selected_grupo_id = int(request.args.get('grupo_id'))
        grupo = Grupo.query.get_or_404(selected_grupo_id)
        
        # Filtrar los préstamos del grupo seleccionado
        prestamos = PrestamoIndividual.query.filter_by(prestamo_grupal_id=grupo.id).all()

        # Agregar las fechas de pago y su estado
        for prestamo in prestamos:
            prestamo.fechas_pago_estado = {}
            pagos = Pago.query.filter_by(prestamo_individual_id=prestamo.id).all()

            for pago in pagos:
                # Verificar si el pago está pendiente y la fecha ya pasó
                if pago.estado == "Pendiente" and pago.fecha_pago < date.today():
                    pago.estado = "Atrasado"

                prestamo.fechas_pago_estado[pago.fecha_pago] = pago.estado

        db.session.commit()  # Guardar cambios en la base de datos si se actualizó algún pago

        return render_template('pagos/pagos.html', grupos=grupos, selected_grupo=grupo, prestamos=prestamos)

    return render_template('pagos/pagos.html', grupos=grupos, selected_grupo_id=selected_grupo_id, prestamos=prestamos)



# Ruta para agregar un pago
@pagos_bp.route('/agregar_pago/<int:prestamo_id>', methods=['POST'])
def agregar_pago(prestamo_id):
    prestamo = PrestamoIndividual.query.get_or_404(prestamo_id)
    monto_pago = float(request.form['monto_pago'])  # Obtener monto_pago como float
    monto_pago_decimal = Decimal(monto_pago)  # Convertir a Decimal

    # Obtener la fecha del pago
    fecha_pago_str = request.form['fecha_pago']
    fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()

    # Buscar si ya existe un pago registrado para esta fecha y cliente
    pago_existente = Pago.query.filter_by(
        prestamo_individual_id=prestamo.id, fecha_pago=fecha_pago
    ).first()

    if pago_existente:
        # Si el pago ya existe, actualizamos el monto
        pago_existente.monto_pagado += monto_pago_decimal  # Ahora es Decimal
        pago_existente.monto_pendiente = Decimal(prestamo.monto) - pago_existente.monto_pagado
        pago_existente.estado = "Pagado"  # Ajustar si es un pago parcial

        # Actualizar el monto pagado del préstamo individual (convertimos a Decimal)
        prestamo.monto_pagado = Decimal(prestamo.monto_pagado) + monto_pago_decimal
    else:
        # Si no existe un pago para esa fecha, no hacemos nada o mostramos un error
        return "No se encontró un pago para esa fecha.", 400

    # Guardar los cambios
    db.session.commit()

    # Redirigir a la lista de pagos del grupo
    return redirect(url_for('pagos.lista_pagos', grupo_id=prestamo.prestamo_grupal_id))
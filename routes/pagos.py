from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime, date
from models import Pago, PrestamoIndividual, Cliente, Grupo, PrestamoGrupal
from models import db
from decimal import Decimal
from flask_login import login_required

# Crear un Blueprint para la gestión de pagos
pagos_bp = Blueprint('pagos', __name__)

# Definir constantes para el interés y los días de retraso
INTERES_RETRASO = 0.05  # 5% de interés por retraso
DIAS_RETRASO = 10  # Si el retraso es mayor a 10 días, se aplica interés

@pagos_bp.route('/pagos', methods=['GET'])
@login_required
def lista_pagos():
    grupos = Grupo.query.all()
    grupo_id = request.args.get('grupo_id')

    selected_grupo = None
    prestamos_grupales = []

    if grupo_id:
        selected_grupo = Grupo.query.get(grupo_id)
        if selected_grupo:
            # Obtener solo el préstamo grupal más actual
            prestamo_grupal_reciente = PrestamoGrupal.query \
                .filter_by(grupo_id=selected_grupo.id) \
                .order_by(PrestamoGrupal.fecha_desembolso.desc()) \
                .first()

            if prestamo_grupal_reciente:
                prestamos_grupales = [prestamo_grupal_reciente]

    current_date = datetime.today().date()

    return render_template(
        'pagos/pagos.html',
        grupos=grupos,
        selected_grupo=selected_grupo,
        prestamos_grupales=prestamos_grupales,
        current_date=current_date
    )

@pagos_bp.route('/guardar_pagos', methods=['POST'])
@login_required
def guardar_pagos():
    try:
        grupo_id = request.args.get('grupo_id')
        if not grupo_id:
            flash('Error: ID de grupo no especificado.', 'error')
            return redirect(url_for('pagos.lista_pagos'))

        # Obtener el préstamo grupal más reciente para el grupo seleccionado
        prestamo_grupal = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).order_by(PrestamoGrupal.fecha_desembolso.desc()).first()
        if not prestamo_grupal:
            flash('No se encontró un préstamo grupal para este grupo.', 'error')
            return redirect(url_for('pagos.lista_pagos', grupo_id=grupo_id))

        # Iterar sobre los préstamos individuales del préstamo grupal
        for prestamo in prestamo_grupal.prestamos_individuales:
            pago_activo = Pago.query.filter(
                Pago.prestamo_individual_id == prestamo.id,
                Pago.estado.in_(['Pendiente', 'Incompleto', 'Atrasado'])
            ).order_by(Pago.fecha_pago).first()

            if not pago_activo:
                continue

            monto_abonado_str = request.form.get(f'monto_abonado_{prestamo.id}')
            pago_completo_marcado = request.form.get(f'pago_completo_{prestamo.id}') == 'true'

            monto_cuota = prestamo.obtener_numero_cuota()

            # Lógica principal de actualización del pago
            if pago_completo_marcado:
                # Caso 1: El checkbox de "Pago Completo" está marcado
                pago_activo.monto_pagado = monto_cuota
                pago_activo.estado = "Pagado"
                pago_activo.monto_pendiente = 0.00
                pago_activo.fecha_cancelacion_pago_cuota = datetime.today().date()
                pago_activo.dias_atraso = (pago_activo.fecha_cancelacion_pago_cuota - pago_activo.fecha_pago).days
                pago_activo.monto_mora = 0.0  # Resetear mora si se completa el pago

            elif monto_abonado_str and Decimal(monto_abonado_str) > 0:
                # Caso 2: Se ha ingresado un monto de abono
                monto_abonado = Decimal(monto_abonado_str)

                # Si el nuevo abono completa o excede el monto pendiente
                if pago_activo.estado == 'Incompleto':
                    monto_total_abonado = pago_activo.monto_pagado + monto_abonado
                else:
                    monto_total_abonado = monto_abonado

                if monto_total_abonado >= monto_cuota:
                    pago_activo.monto_pagado = monto_total_abonado
                    pago_activo.estado = "Pagado"
                    pago_activo.monto_pendiente = 0.00
                    pago_activo.fecha_cancelacion_pago_cuota = datetime.today().date()
                    pago_activo.dias_atraso = (pago_activo.fecha_cancelacion_pago_cuota - pago_activo.fecha_pago).days
                    pago_activo.monto_mora = 0.0
                else:
                    # Si el nuevo abono es parcial
                    pago_activo.monto_pagado = monto_total_abonado
                    pago_activo.estado = "Incompleto"
                    pago_activo.monto_pendiente = monto_cuota - monto_total_abonado
                    pago_activo.fecha_cancelacion_pago_cuota = datetime.today().date()
                    pago_activo.dias_atraso = (pago_activo.fecha_cancelacion_pago_cuota - pago_activo.fecha_pago).days
                    # Lógica para calcular mora, si aplica
                    if pago_activo.dias_atraso > DIAS_RETRASO:
                        monto_mora = pago_activo.monto_pendiente * Decimal(str(INTERES_RETRASO))
                        pago_activo.monto_mora = monto_mora

            # Solo agregar al session si hubo alguna actualización
            if pago_completo_marcado or (monto_abonado_str and Decimal(monto_abonado_str) > 0):
                db.session.add(pago_activo)

        db.session.commit()
        flash('Pagos guardados correctamente.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ocurrió un error al guardar los pagos: {e}', 'error')

    return redirect(url_for('pagos.lista_pagos', grupo_id=grupo_id))
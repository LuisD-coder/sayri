from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from datetime import datetime, date
from flask_login import login_required, current_user 
from models import Pago, PrestamoIndividual, Cliente, Grupo, PrestamoGrupal, PagoParcial 
from models import db
from decimal import Decimal

# Crear un Blueprint para la gestión de pagos
pagos_bp = Blueprint('pagos', __name__)

# ----------------------------------------------------------------------
# CONSTANTES PARA MORA (ACTUALIZADAS)
# ----------------------------------------------------------------------
MORA_POR_DIA = Decimal('7.50')  # S/7.50 por cada día de atraso

# ----------------------------------------------------------------------
# RUTA DE LISTADO DE PAGOS
# ----------------------------------------------------------------------
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

    html_content = render_template(
        'pagos/pagos.html',
        grupos=grupos,
        selected_grupo=selected_grupo,
        prestamos_grupales=prestamos_grupales,
        current_date=current_date
    )
    
    response = make_response(html_content)
    response.headers['Content-Type'] = 'text/html'
    
    return response


# ----------------------------------------------------------------------
# RUTA DE GUARDADO DE PAGOS (Sistema de mora diaria)
# ----------------------------------------------------------------------
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
            
            # 1. Encontrar la cuota activa (Pago)
            pago_activo = Pago.query.filter(
                Pago.prestamo_individual_id == prestamo.id,
                Pago.estado.in_(['Pendiente', 'Incompleto', 'Atrasado']) 
            ).order_by(Pago.fecha_pago).first()

            if not pago_activo:
                continue

            # 2. Capturar y validar el monto abonado desde el formulario
            monto_abonado_str = request.form.get(f'monto_abonado_{prestamo.id}')
            
            try:
                monto_abonado = Decimal(monto_abonado_str or '0.00') 
            except Exception:
                monto_abonado = Decimal('0.00')

            if monto_abonado <= 0:
                continue # No hay abono para procesar en este préstamo

            # 3. Datos clave para el cálculo
            monto_cuota = Decimal(str(prestamo.obtener_numero_cuota()))
            monto_pagado_actual = Decimal(str(pago_activo.monto_pagado))
            
            # 4. Crear el registro de PagoParcial (el abono en sí)
            nuevo_abono = PagoParcial(
                pago_id=pago_activo.id,
                monto_abono=float(monto_abonado),
                fecha_abono=datetime.now(),
                usuario_registro_id=current_user.id,
                observaciones="Abono registrado (Sistema de mora diaria S/7.50)"
            )
            db.session.add(nuevo_abono)

            # 5. Calcular el nuevo estado del Pago (Cuota)
            nuevo_monto_total_pagado = monto_pagado_actual + monto_abonado
            
            # 6. Calcular días de atraso
            fecha_hoy = datetime.today().date()
            dias_atraso = (fecha_hoy - pago_activo.fecha_pago).days
            
            # Si la fecha de pago aún no llega (días_atraso negativo), se considera 0
            if dias_atraso < 0:
                dias_atraso = 0
            
            # 7. Actualizar el objeto Pago
            pago_activo.fecha_cancelacion_pago_cuota = fecha_hoy
            pago_activo.dias_atraso = dias_atraso
            
            if nuevo_monto_total_pagado >= monto_cuota:
                # Pago Completo
                pago_activo.monto_pagado = float(monto_cuota)
                pago_activo.monto_pendiente = 0.00
                pago_activo.estado = "Pagado"
                pago_activo.monto_mora = 0.0  # Al completar el pago, la mora se resetea
                
            else:
                # Abono Parcial (Queda Incompleto)
                pago_activo.monto_pagado = float(nuevo_monto_total_pagado)
                pago_activo.monto_pendiente = float(monto_cuota - nuevo_monto_total_pagado)
                pago_activo.estado = "Incompleto"
                
                # NUEVA LÓGICA DE MORA: S/7.50 por cada día de atraso
                if dias_atraso > 0:
                    monto_mora = MORA_POR_DIA * Decimal(str(dias_atraso))
                    pago_activo.monto_mora = float(monto_mora)
                else:
                    pago_activo.monto_mora = 0.0
            
            db.session.add(pago_activo)

        # 8. Persistir todos los cambios
        db.session.commit()
        flash('Pagos guardados correctamente. Los cambios han sido aplicados.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ocurrió un error crítico al guardar los pagos: {e}', 'error')

    return redirect(url_for('pagos.lista_pagos', grupo_id=grupo_id))
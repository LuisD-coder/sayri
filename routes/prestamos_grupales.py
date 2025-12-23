from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app, Response, send_file
from flask_login import current_user, login_required
from models import db, PrestamoGrupal, Grupo, PrestamoIndividual, Pago, Cliente, Contrato
from datetime import datetime, timedelta
import fitz  # PyMuPDF
import tempfile
import zipfile
from werkzeug.utils import secure_filename
import os
from io import BytesIO
import io
from sqlalchemy import asc, desc
from unidecode import unidecode

prestamos_grupales_bp = Blueprint('prestamos_grupales', __name__, url_prefix='/prestamos_grupales')

def obtener_grupos_permitidos():
    """Devuelve la lista de grupos según el rol del usuario"""
    if current_user.rol.nombre == 'admin':
        return Grupo.query.all()
    else:
        # ✅ CORREGIDO: Usamos .grupos en lugar de .grupos_asignados.all()
        # Como quitamos lazy='dynamic' en el modelo, esto ya devuelve una lista.
        return current_user.grupos

@prestamos_grupales_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_prestamo_grupal():
    # 🚀 NUEVO: Capturar si viene un grupo pre-seleccionado desde la URL (query string)
    preselected_grupo_id = request.args.get('grupo_id', type=int)

    if request.method == 'POST':
        grupo_id = request.form['grupo_id']
        fecha_desembolso_str = request.form['fecha_desembolso']

        # Convierte la fecha de string a un objeto datetime.date
        fecha_desembolso = datetime.strptime(fecha_desembolso_str, '%Y-%m-%d').date()

        # Verifica si el grupo existe
        grupo = Grupo.query.get_or_404(grupo_id)
        
        # ✅ SEGURIDAD: Verificar acceso
        if not grupo.tiene_acceso(current_user):
            flash('No tienes permiso para crear préstamos en este grupo.', 'danger')
            return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

        # Establecer monto_total en 0 al crear el prestamo grupal
        nuevo_prestamo_grupal = PrestamoGrupal(
            grupo_id=grupo_id,
            fecha_desembolso=fecha_desembolso
        )

        # Guarda el nuevo prestamo grupal en la base de datos
        db.session.add(nuevo_prestamo_grupal)
        db.session.commit()

        flash("Prestamo grupal creado exitosamente.", "success")
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales', grupo_id=grupo_id))

    # ✅ SEGURIDAD: Mostrar solo grupos permitidos
    grupos = obtener_grupos_permitidos()
    
    # 🚀 NUEVO: Pasamos 'preselected_grupo_id' a la vista
    return render_template('prestamos_grupales/nuevo_prestamo_grupal.html', 
                           grupos=grupos, 
                           preselected_grupo_id=preselected_grupo_id)


@prestamos_grupales_bp.route('/', methods=['GET'])
@login_required
def lista_prestamos_grupales():
    grupo_id = request.args.get('grupo_id', type=int)

    # ✅ SEGURIDAD: Lista de grupos permitidos para el filtro (buscador)
    grupos = obtener_grupos_permitidos()

    prestamos_grupales = []
    selected_grupo = None
    
    if grupo_id:
        selected_grupo = Grupo.query.get_or_404(grupo_id)
        
        # ✅ SEGURIDAD: Verificar acceso al grupo seleccionado
        if not selected_grupo.tiene_acceso(current_user):
             flash('No tienes acceso a este grupo.', 'danger')
             return redirect(url_for('grupos.lista_grupos'))

        prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id)\
            .order_by(PrestamoGrupal.fecha_desembolso.desc()).all()
    else:
        # ⚡ OPTIMIZACIÓN: Estado inicial limpio
        # No cargamos nada hasta que el usuario busque un grupo específico.
        # Esto hace la carga de la página instantánea.
        prestamos_grupales = []

    return render_template('prestamos_grupales/lista_prestamos_grupales.html',
                           prestamos_grupales=prestamos_grupales,
                           grupos=grupos,
                           selected_grupo=selected_grupo)


@prestamos_grupales_bp.route('/eliminar/<int:prestamo_grupal_id>', methods=['POST'])
@login_required
def eliminar_prestamo_grupal(prestamo_grupal_id):
    prestamo = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    
    # ✅ SEGURIDAD: Verificar acceso
    if not prestamo.grupo.tiene_acceso(current_user):
        abort(403)

    grupo_id = prestamo.grupo_id 

    try:
        db.session.delete(prestamo)
        db.session.commit()
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales', grupo_id=grupo_id)) 
    except Exception as e:
        db.session.rollback()
        return f"Error al eliminar el prestamo grupal: {str(e)}", 500


MONTOS_PAGADOS = {
    500: 151, 600: 181, 700: 211, 800: 241, 900: 271,
    1000: 302, 1100: 331, 1200: 361, 1300: 391, 1400: 421,
    1500: 451
}

# Asignar prestamos individuales a los clientes dentro de un prestamo grupal
@prestamos_grupales_bp.route('/<int:prestamo_grupal_id>/asignar_prestamos_individuales', methods=['GET', 'POST'])
@login_required
def asignar_prestamos_individuales(prestamo_grupal_id):
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    
    # ✅ SEGURIDAD
    if not prestamo_grupal.grupo.tiene_acceso(current_user):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

    clientes = prestamo_grupal.grupo.clientes  

    if request.method == 'POST':
        for cliente_id in request.form.getlist('clientes'):
            prestamo_existente = PrestamoIndividual.query.filter_by(
                prestamo_grupal_id=prestamo_grupal.id, cliente_id=cliente_id
            ).first()
            
            if prestamo_existente:
                continue 

            try:
                monto = float(request.form[f'monto_cliente_{cliente_id}'])
            except ValueError:
                flash(f"El monto para el cliente {cliente_id} no es valido.")
                return redirect(url_for('prestamos_grupales.asignar_prestamos_individuales', prestamo_grupal_id=prestamo_grupal_id))

            monto_pagado = MONTOS_PAGADOS.get(int(monto), 0)

            nuevo_prestamo_individual = PrestamoIndividual(
                prestamo_grupal_id=prestamo_grupal.id,
                cliente_id=cliente_id,
                monto=monto,
                monto_pagado=monto_pagado 
            )
            db.session.add(nuevo_prestamo_individual)
            db.session.commit() 

            # Generar 4 pagos iniciando 15 dias despues de la fecha de desembolso
            fecha_pago = prestamo_grupal.fecha_desembolso + timedelta(days=15) 
            for _ in range(4):
                nuevo_pago = Pago(
                    cliente_id=cliente_id,
                    prestamo_individual_id=nuevo_prestamo_individual.id,  
                    monto_pendiente=0,
                    estado="Pendiente",
                    fecha_pago=fecha_pago  
                )
                db.session.add(nuevo_pago)
                fecha_pago += timedelta(days=15)

        # Actualizar monto_total
        prestamos_individuales = db.session.query(db.func.sum(PrestamoIndividual.monto)).filter_by(prestamo_grupal_id=prestamo_grupal.id).scalar() or 0
        prestamo_grupal.monto_total 

        db.session.commit()
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales', grupo_id=prestamo_grupal.grupo_id))

    return render_template('prestamos_grupales/asignar_prestamos_individuales.html',  
                           prestamo_grupal=prestamo_grupal, clientes=clientes)


@prestamos_grupales_bp.route('/<int:prestamo_grupal_id>/prestamos_individuales')
@login_required
def prestamos_individuales(prestamo_grupal_id):
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    
    # ✅ SEGURIDAD
    if not prestamo_grupal.grupo.tiene_acceso(current_user):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))
    
    prestamos_individuales = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal_id).all()
    
    return render_template('prestamos_grupales/prestamos_individuales.html',  
                           prestamo_grupal=prestamo_grupal,  
                           prestamos_individuales=prestamos_individuales)


@prestamos_grupales_bp.route('/grupo/<int:grupo_id>/prestamos')
@login_required
def prestamos_por_grupo(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    
    # ✅ SEGURIDAD
    if not grupo.tiene_acceso(current_user):
        flash('No tienes permiso para ver este grupo', 'danger')
        return redirect(url_for('grupos.lista_grupos'))
    
    prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id)\
        .order_by(PrestamoGrupal.fecha_desembolso.desc()).all()
    
    # ✅ SEGURIDAD: Grupos permitidos
    grupos = obtener_grupos_permitidos()

    return render_template('prestamos_grupales/lista_prestamos_grupales.html',  
                           prestamos_grupales=prestamos_grupales,  
                           selected_grupo=grupo,
                           grupos=grupos)


# ==============================================================================
# FUNCION PARA DESCARGAR CONTRATO INDIVIDUAL
# ==============================================================================
@prestamos_grupales_bp.route('/descargar_contrato/<int:contrato_id>')
@login_required
def descargar_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)

    # ✅ SEGURIDAD: Validar cadena de propiedad
    try:
        grupo = contrato.prestamo_individual.prestamo_grupal.grupo
        if not grupo.tiene_acceso(current_user):
             abort(403)
    except:
         # Si falta alguna relación, mejor denegar o 404
         abort(404)

    try:
        pdf_bytes = contrato.datos_binarios
        download_filename = secure_filename(unidecode(contrato.nombre_archivo))

        headers = {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{download_filename}"',
            'Content-Length': str(len(pdf_bytes))
        }
        return Response(pdf_bytes, headers=headers)

    except Exception as e:
        current_app.logger.error(f"ERROR: [descargar_contrato] {e}", exc_info=True)
        flash(f"Error al descargar el contrato: {str(e)}", "error")
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))


# ==============================================================================
# FUNCION PARA GENERAR Y DESCARGAR CONTRATOS ZIP
# ==============================================================================
@prestamos_grupales_bp.route('/generar_contrato/<int:prestamo_grupal_id>', methods=['GET'])
@login_required
def generar_contrato(prestamo_grupal_id):
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    
    # ✅ SEGURIDAD
    if not prestamo_grupal.grupo.tiene_acceso(current_user):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

    clientes_asociados = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal.id).all()

    if not clientes_asociados:
        flash('No se encontraron clientes asociados a este prestamo grupal.', 'error')
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

    temp_zip_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=".zip") as temp_zip_file:
            temp_zip_path = temp_zip_file.name

        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for prestamo_individual in clientes_asociados:
                cliente = Cliente.query.get(prestamo_individual.cliente_id)
                if not cliente:
                    continue

                try:
                    pdf_buffer = generar_contrato_logic(cliente.id, prestamo_grupal, return_type='buffer')
                except Exception as e:
                    current_app.logger.error(f"ERROR: [generar_contrato] Excepcion al llamar a generar_contrato_logic para {cliente.nombre}: {str(e)}", exc_info=True)
                    continue

                if isinstance(pdf_buffer, io.BytesIO):
                    pdf_bytes = pdf_buffer.getvalue()
                    pdf_buffer.close()
                else:
                    continue

                monto_cliente = prestamo_individual.monto
                cliente_nombre_limpio = unidecode(cliente.nombre).replace(" ", "_").replace(".", "")
                cliente_apellido_limpio = unidecode(cliente.apellido).replace(" ", "_").replace(".", "")

                nombre_archivo_base_zip = f"Contrato_{cliente_nombre_limpio.upper()}_{cliente_apellido_limpio.upper()}_Monto_{monto_cliente}.pdf"
                nombre_archivo_zip = secure_filename(nombre_archivo_base_zip)

                zipf.writestr(nombre_archivo_zip, pdf_bytes)

        grupo_nombre_limpio = unidecode(prestamo_grupal.grupo.nombre).replace(" ", "_").replace(".", "")
        fecha_desembolso = prestamo_grupal.fecha_desembolso.strftime('%d-%m-%Y')
        download_name_base = f"Contratos_{grupo_nombre_limpio}_Desembolso_{fecha_desembolso}.zip"
        download_name = secure_filename(download_name_base)

        with open(temp_zip_path, 'rb') as f:
            zip_data = f.read()

        headers = {
            'Content-Type': 'application/zip',
            'Content-Disposition': f'attachment; filename="{download_name}"',
            'Content-Length': str(len(zip_data))
        }
        return Response(zip_data, headers=headers)

    except Exception as e:
        flash(f"Error al generar o descargar el archivo ZIP: {str(e)}", "error")
        current_app.logger.critical(f"CRITICAL ERROR: [generar_contrato] {str(e)}", exc_info=True)
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))
    finally:
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
            except Exception as e:
                pass


# ==============================================================================
# FUNCION LOGICA PARA GENERAR UN CONTRATO INDIVIDUAL
# ==============================================================================
def generar_contrato_logic(cliente_id, prestamo_grupal, return_type='response'): 
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Iniciando para cliente_id={cliente_id}, prestamo_grupal_id={prestamo_grupal.id}")

    cliente = Cliente.query.get_or_404(cliente_id)
    prestamo_individual = PrestamoIndividual.query.filter_by(cliente_id=cliente.id, prestamo_grupal_id=prestamo_grupal.id).first()

    if prestamo_individual is None:
        raise ValueError(f"No se encontro el prestamo para el cliente {cliente.nombre} {cliente.apellido} en este prestamo grupal.")

    monto_cliente = round(prestamo_individual.monto)
    contrato_path = os.path.join(current_app.root_path, "static", f"contrato_preformateado{monto_cliente}.pdf")

    if not os.path.exists(contrato_path):
        raise FileNotFoundError(f"No se encontro el archivo de contrato preformateado para el monto {monto_cliente}.")

    try:
        doc = fitz.open(contrato_path)
    except Exception as e:
        current_app.logger.error(f"ERROR: [generar_contrato_logic] Error al abrir el archivo PDF con fitz: {e}", exc_info=True)
        raise ValueError(f"Error al abrir el archivo PDF: {e}")

    pagos = Pago.query.filter_by(cliente_id=cliente.id, prestamo_individual_id=prestamo_individual.id) \
                      .order_by(Pago.fecha_pago).limit(4).all()
    fechas_pago = [pago.fecha_pago.strftime('%d/%m/%Y') for pago in pagos]

    while len(fechas_pago) < 4:
        fechas_pago.append("N/A")

    datos_cliente = {
        "NOMBRE_APELLIDO": f"{cliente.nombre.upper()} {cliente.apellido.upper()}",
        "DNI": cliente.dni,
        "PRESTAMO": f"{monto_cliente}",
        "FECHA_DSB": prestamo_grupal.fecha_desembolso.strftime('%d/%m/%Y'),
        "FECHA_1": fechas_pago[0],
        "FECHA_2": fechas_pago[1],
        "FECHA_3": fechas_pago[2],
        "FECHA_4": fechas_pago[3]
    }

    for page_num, page in enumerate(doc):
        text_instances = []
        for tag, value in datos_cliente.items():
            placeholder = f"{{{{{tag}}}}}"
            for inst in page.search_for(placeholder):
                text_instances.append((inst, value))

        for rect, value in text_instances:
            x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
            rect_fill = fitz.Rect(x0, y0, x1, y1)
            page.draw_rect(
                rect_fill,
                color=(1, 1, 1),
                fill=(1, 1, 1),
                width=0
            )

            page.insert_text(
                (rect.x0, rect.y0 + rect.height * 0.8),
                value,
                fontsize=9,
                color=(0, 0, 0)
            )

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    doc.close()

    cliente_nombre_limpio = unidecode(cliente.nombre).replace(" ", "_").replace(".", "")
    cliente_apellido_limpio = unidecode(cliente.apellido).replace(" ", "_").replace(".", "")
    nombre_archivo_base = f"contrato_{cliente_nombre_limpio.upper()}_{cliente_apellido_limpio.upper()}_Monto_{monto_cliente}.pdf"
    nombre_archivo = secure_filename(nombre_archivo_base)

    contrato_existente = Contrato.query.filter_by(cliente_id=cliente.id, prestamo_individual_id=prestamo_individual.id).first()
    pdf_bytes_para_db = buffer.getvalue()

    if contrato_existente:
        contrato_existente.datos_binarios = pdf_bytes_para_db
        contrato_existente.nombre_archivo = nombre_archivo
    else:
        nuevo_contrato = Contrato(
            nombre_archivo=nombre_archivo,
            datos_binarios=pdf_bytes_para_db,
            cliente_id=cliente.id,
            prestamo_individual_id=prestamo_individual.id
        )
        db.session.add(nuevo_contrato)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"ERROR: [generar_contrato_logic] Error DB: {e}", exc_info=True)
        raise

    if return_type == 'buffer':
        return buffer
    else:
        headers = {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{nombre_archivo}"',
            'Content-Length': str(len(pdf_bytes_para_db))
        }
        return Response(pdf_bytes_para_db, headers=headers)


@prestamos_grupales_bp.route('/<int:prestamo_grupal_id>/reporte_pagos')
@login_required
def reporte_pagos(prestamo_grupal_id):
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    
    # ✅ SEGURIDAD
    if not prestamo_grupal.grupo.tiene_acceso(current_user):
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

    prestamos_individuales = PrestamoIndividual.query.filter_by(
        prestamo_grupal_id=prestamo_grupal_id
    ).all()
    
    clientes_data = {}
    total_pagado = 0
    total_pendiente = 0 
    total_mora = 0
    total_registros = 0
    
    for prestamo_individual in prestamos_individuales:
        cliente = Cliente.query.get(prestamo_individual.cliente_id)
        pagos = Pago.query.filter_by(
            prestamo_individual_id=prestamo_individual.id
        ).order_by(Pago.fecha_pago.desc()).all() 
        
        if cliente.id not in clientes_data:
            clientes_data[cliente.id] = {
                'cliente': cliente,
                'prestamo_individual': prestamo_individual,
                'pagos': []
            }
        
        cliente_total_pagado = 0
        cliente_total_pendiente = 0
        cliente_total_mora = 0
        cliente_pagos_completados = 0
        
        for pago in pagos:
            try:
                from models.pago_parcial import PagoParcial
                tiene_abonos_parciales = PagoParcial.query.filter_by(pago_id=pago.id).count() > 0
                pago.tiene_abonos_parciales = tiene_abonos_parciales
            except:
                pago.tiene_abonos_parciales = False
            
            clientes_data[cliente.id]['pagos'].append(pago)
            
            total_pagado += (pago.monto_pagado or 0)
            total_pendiente += (pago.monto_pendiente or 0)
            total_mora += (pago.monto_mora or 0)
            total_registros += 1
            
            cliente_total_pagado += (pago.monto_pagado or 0)
            cliente_total_pendiente += (pago.monto_pendiente or 0)
            cliente_total_mora += (pago.monto_mora or 0)
            
            if pago.estado == 'Pagado':
                cliente_pagos_completados += 1
        
        clientes_data[cliente.id]['resumen'] = {
            'total_pagado': cliente_total_pagado,
            'total_pendiente': cliente_total_pendiente,
            'total_mora': cliente_total_mora,
            'pagos_completados': cliente_pagos_completados,
            'total_pagos': len(pagos)
        }
    
    clientes_list = list(clientes_data.values())
    clientes_list.sort(key=lambda x: f"{x['cliente'].nombre} {x['cliente'].apellido}")
    
    return render_template(
        'reportes/reporte_pagos.html',
        prestamo_grupal=prestamo_grupal,
        clientes_data=clientes_list,
        total_pagado=total_pagado,
        total_pendiente=total_pendiente,
        total_mora=total_mora,
        total_registros=total_registros
    )


# --- HELPERS PARA VALIDACIÓN SEGURA DE PAGOS ---
def verificar_acceso_pago(pago, usuario):
    """Devuelve True si el usuario tiene acceso al grupo dueño del pago"""
    if usuario.rol.nombre == 'admin':
        return True
    
    # Intentar por Cliente
    if pago.cliente and pago.cliente.grupo:
        return pago.cliente.grupo.tiene_acceso(usuario)
    
    # Intentar por Préstamo Individual
    if pago.prestamo_individual and pago.prestamo_individual.prestamo_grupal and pago.prestamo_individual.prestamo_grupal.grupo:
        return pago.prestamo_individual.prestamo_grupal.grupo.tiene_acceso(usuario)
    
    return False

@prestamos_grupales_bp.route('/pago/<int:pago_id>/datos', methods=['GET'])
@login_required
def obtener_datos_pago(pago_id):
    """Obtener los datos de un pago específico para edición"""
    try:
        pago = Pago.query.get_or_404(pago_id)
        
        # ✅ SEGURIDAD
        if not verificar_acceso_pago(pago, current_user):
             return {'success': False, 'message': 'Acceso denegado'}, 403

        # Formatear las fechas para el formulario HTML
        fecha_pago = pago.fecha_pago.strftime('%Y-%m-%d') if pago.fecha_pago else ''
        fecha_cancelacion = ''
        if pago.fecha_cancelacion_pago_cuota:
            fecha_cancelacion = pago.fecha_cancelacion_pago_cuota.strftime('%Y-%m-%d')
        
        datos_pago = {
            'fecha_pago': fecha_pago,
            'monto_pagado': float(pago.monto_pagado) if pago.monto_pagado is not None else 0.0,
            'monto_pendiente': float(pago.monto_pendiente) if pago.monto_pendiente is not None else 0.0,
            'estado': pago.estado or 'Pendiente',
            'dias_atraso': pago.dias_atraso if pago.dias_atraso is not None else 0,
            'monto_mora': float(pago.monto_mora) if pago.monto_mora is not None else 0.0,
            'fecha_cancelacion_pago_cuota': fecha_cancelacion
        }
        
        return {'success': True, 'pago': datos_pago}
    
    except Exception as e:
        current_app.logger.error(f"Error al obtener datos del pago {pago_id}: {str(e)}")
        return {'success': False, 'message': str(e)}, 500


@prestamos_grupales_bp.route('/pago/<int:pago_id>/editar', methods=['POST'])
@login_required  
def editar_pago(pago_id):
    """Actualizar los datos de un pago"""
    try:
        pago = Pago.query.get_or_404(pago_id)

        # ✅ SEGURIDAD
        if not verificar_acceso_pago(pago, current_user):
             return {'success': False, 'message': 'Acceso denegado'}, 403
        
        # Obtener los datos del formulario
        fecha_pago_str = request.form.get('fecha_pago')
        monto_pagado = request.form.get('monto_pagado')
        monto_pendiente = request.form.get('monto_pendiente') 
        estado = request.form.get('estado')
        dias_atraso = request.form.get('dias_atraso')
        monto_mora = request.form.get('monto_mora')
        fecha_cancelacion_str = request.form.get('fecha_cancelacion_pago_cuota')
        
        # Validar y convertir fecha_pago
        if fecha_pago_str:
            try:
                pago.fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
            except ValueError:
                return {'success': False, 'message': 'Formato de fecha de pago inválido'}, 400
        
        # Validar y convertir monto_pagado
        try:
            pago.monto_pagado = float(monto_pagado) if monto_pagado else 0.0
        except (ValueError, TypeError):
            return {'success': False, 'message': 'Monto pagado inválido'}, 400
        
        # Validar y convertir monto_pendiente
        try:
            pago.monto_pendiente = float(monto_pendiente) if monto_pendiente else 0.0
        except (ValueError, TypeError):
            return {'success': False, 'message': 'Monto pendiente inválido'}, 400
        
        # Actualizar estado
        if estado in ['Pendiente', 'Pagado', 'Incompleto', 'Vencido']:
            pago.estado = estado
        else:
            return {'success': False, 'message': 'Estado inválido'}, 400
        
        # Validar y convertir dias_atraso
        try:
            pago.dias_atraso = int(dias_atraso) if dias_atraso else 0
        except (ValueError, TypeError):
            return {'success': False, 'message': 'Días de atraso inválido'}, 400
        
        # Validar y convertir monto_mora
        try:
            pago.monto_mora = float(monto_mora) if monto_mora else 0.0
        except (ValueError, TypeError):
            return {'success': False, 'message': 'Monto de mora inválido'}, 400
        
        # Validar y convertir fecha_cancelacion
        if fecha_cancelacion_str:
            try:
                pago.fecha_cancelacion_pago_cuota = datetime.strptime(fecha_cancelacion_str, '%Y-%m-%d').date()
            except ValueError:
                return {'success': False, 'message': 'Formato de fecha de cancelación inválido'}, 400
        else:
            pago.fecha_cancelacion_pago_cuota = None
        
        # Guardar cambios
        db.session.commit()
        
        current_app.logger.info(f"Pago {pago_id} actualizado correctamente por el usuario")
        return {'success': True, 'message': 'Pago actualizado correctamente'}
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al actualizar el pago {pago_id}: {str(e)}")
        return {'success': False, 'message': f'Error interno: {str(e)}'}, 500


@prestamos_grupales_bp.route('/pago/<int:pago_id>/eliminar', methods=['DELETE'])
@login_required
def eliminar_pago(pago_id):
    """Eliminar un pago - Solo para administradores"""
    try:
        # Verificar que el usuario actual sea administrador
        if not current_user.rol or current_user.rol.nombre != 'admin':
            return {'success': False, 'message': 'No tienes permisos para realizar esta acción'}, 403
        
        pago = Pago.query.get_or_404(pago_id)
        
        # Obtener información del pago antes de eliminarlo para el log
        cliente = Cliente.query.get(pago.cliente_id)
        
        # Eliminar el pago
        db.session.delete(pago)
        db.session.commit()
        
        current_app.logger.info(f"Pago {pago_id} eliminado correctamente por el usuario {current_user.id} (admin). Cliente: {cliente.nombre if cliente else 'N/A'}")
        return {'success': True, 'message': 'Pago eliminado correctamente'}
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar el pago {pago_id}: {str(e)}")
        return {'success': False, 'message': f'Error interno: {str(e)}'}, 500


@prestamos_grupales_bp.route('/pago/<int:pago_id>/historial_abonos', methods=['GET'])
@login_required
def obtener_historial_abonos(pago_id):
    """Obtener el historial de abonos parciales de un pago específico"""
    try:
        pago = Pago.query.get_or_404(pago_id)
        
        # ✅ SEGURIDAD
        if not verificar_acceso_pago(pago, current_user):
             return {'success': False, 'message': 'Acceso denegado'}, 403

        # Obtener todos los abonos parciales de este pago
        from models.pago_parcial import PagoParcial  # Importar aquí para evitar dependencias circulares
        abonos = PagoParcial.query.filter_by(pago_id=pago_id).order_by(PagoParcial.fecha_abono.desc()).all()
        
        # Obtener información del préstamo individual para calcular monto de cuota
        prestamo_individual = PrestamoIndividual.query.get(pago.prestamo_individual_id)
        monto_cuota = prestamo_individual.obtener_numero_cuota() if prestamo_individual else 0
        
        # Formatear datos de abonos
        abonos_data = []
        for abono in abonos:
            usuario_nombre = "Sistema"
            if abono.usuario_registro_id:
                from models.usuario import Usuario
                usuario = Usuario.query.get(abono.usuario_registro_id)
                if usuario:
                    usuario_nombre = f"{usuario.nombre} {usuario.apellido}"
            
            abonos_data.append({
                'id': abono.id,
                'monto_abono': float(abono.monto_abono),
                'fecha_abono': abono.fecha_abono.strftime('%d/%m/%Y %H:%M') if abono.fecha_abono else '',
                'observaciones': abono.observaciones,
                'usuario': usuario_nombre
            })
        
        return {
            'success': True,
            'abonos': abonos_data,
            'fecha_pago': pago.fecha_pago.strftime('%d/%m/%Y') if pago.fecha_pago else '',
            'monto_cuota': float(monto_cuota),
            'monto_pendiente': float(pago.monto_pendiente) if pago.monto_pendiente is not None else 0.0,
            'estado_pago': pago.estado
        }
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener historial de abonos para pago {pago_id}: {str(e)}")
        return {'success': False, 'message': f'Error interno: {str(e)}'}, 500
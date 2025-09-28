from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from models import db, PrestamoGrupal, Grupo, PrestamoIndividual, Pago, Cliente, Contrato
from datetime import datetime, timedelta
import fitz
import tempfile
import zipfile
from werkzeug.utils import secure_filename
from flask_login import login_required
import os
from io import BytesIO
import io
from flask import send_file, Response, current_app # Asegurate que Response este importado
from sqlalchemy import asc, desc
from unidecode import unidecode



prestamos_grupales_bp = Blueprint('prestamos_grupales', __name__, url_prefix='/prestamos_grupales')

@prestamos_grupales_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_prestamo_grupal():
    if request.method == 'POST':
        grupo_id = request.form['grupo_id']
        fecha_desembolso_str = request.form['fecha_desembolso']

        # Convierte la fecha de string a un objeto datetime.date
        fecha_desembolso = datetime.strptime(fecha_desembolso_str, '%Y-%m-%d').date()

        # Verifica si el grupo existe
        grupo = Grupo.query.get_or_404(grupo_id)

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

    # Obtener todos los grupos para mostrar en la plantilla
    grupos = Grupo.query.all()
    return render_template('prestamos_grupales/nuevo_prestamo_grupal.html', grupos=grupos)



@prestamos_grupales_bp.route('/', methods=['GET'])
@login_required
def lista_prestamos_grupales():
    grupo_id = request.args.get('grupo_id', type=int)

    grupos = Grupo.query.all()

    # Si no se ha seleccionado un grupo, no cargamos prestamos
    prestamos_grupales = []
    if grupo_id:
        prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).all()

    return render_template('prestamos_grupales/lista_prestamos_grupales.html',
                           prestamos_grupales=prestamos_grupales,
                           grupos=grupos,
                           selected_grupo_id=grupo_id)


@prestamos_grupales_bp.route('/eliminar/<int:prestamo_grupal_id>', methods=['POST'])
@login_required
def eliminar_prestamo_grupal(prestamo_grupal_id):
    prestamo = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    grupo_id = prestamo.grupo_id  # Guardamos el grupo seleccionado antes de eliminar

    try:
        db.session.delete(prestamo)
        db.session.commit()
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales', grupo_id=grupo_id))  # Mantiene la seleccion del grupo
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
    clientes = prestamo_grupal.grupo.clientes  

    if request.method == 'POST':
        for cliente_id in request.form.getlist('clientes'):
            prestamo_existente = PrestamoIndividual.query.filter_by(
                prestamo_grupal_id=prestamo_grupal.id, cliente_id=cliente_id
            ).first()
            
            if prestamo_existente:
                continue  # Si el prestamo individual ya existe, se salta

            # Validar que el monto ingresado es un numero valido
            try:
                monto = float(request.form[f'monto_cliente_{cliente_id}'])
            except ValueError:
                flash(f"El monto para el cliente {cliente_id} no es valido.")
                return redirect(url_for('prestamos_grupales.asignar_prestamos_individuales', prestamo_grupal_id=prestamo_grupal_id))

            # Obtener el monto pagado basado en el monto del prestamo
            monto_pagado = MONTOS_PAGADOS.get(int(monto), 0)  # Si no esta en el diccionario, asigna 0

            # Crear el prestamo individual
            nuevo_prestamo_individual = PrestamoIndividual(
                prestamo_grupal_id=prestamo_grupal.id,
                cliente_id=cliente_id,
                monto=monto,
                monto_pagado=monto_pagado  # Asignar el monto pagado
            )
            db.session.add(nuevo_prestamo_individual)
            db.session.commit()  # Commit para obtener el ID del prestamo individual

            # **Generar 4 pagos iniciando 15 dias despues de la fecha de desembolso**
            fecha_pago = prestamo_grupal.fecha_desembolso + timedelta(days=15)  # Primer pago despues de 15 dias
            for _ in range(4):
                nuevo_pago = Pago(
                    cliente_id=cliente_id,
                    prestamo_individual_id=nuevo_prestamo_individual.id,  
                    monto_pendiente=0,
                    monto_pagado=monto_pagado,
                    estado="Pendiente",
                    fecha_pago=fecha_pago  
                )
                db.session.add(nuevo_pago)

                # Sumar 15 dias para el siguiente pago
                fecha_pago += timedelta(days=15)

        # Actualizar monto_total del prestamo grupal
        prestamos_individuales = db.session.query(db.func.sum(PrestamoIndividual.monto)).filter_by(prestamo_grupal_id=prestamo_grupal.id).scalar() or 0
        prestamo_grupal.monto_total  # Solo accede a la propiedad calculada

        db.session.commit()
        
        # Redirigir a la lista de prestamos grupales con el grupo seleccionado
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales', grupo_id=prestamo_grupal.grupo_id))

    return render_template('prestamos_grupales/asignar_prestamos_individuales.html',  
                           prestamo_grupal=prestamo_grupal, clientes=clientes)


@prestamos_grupales_bp.route('/<int:prestamo_grupal_id>/prestamos_individuales')
@login_required
def prestamos_individuales(prestamo_grupal_id):
    # Obtener el prestamo grupal
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    
    # Obtener los prestamos individuales del grupo
    prestamos_individuales = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal_id).all()
    
    # Agregar depuracion
    print(f"DEBUG: [prestamos_individuales] Prestamos Individuales para el grupo {prestamo_grupal_id}: {prestamos_individuales}")
    
    # Si no hay prestamos individuales
    if not prestamos_individuales:
        print("DEBUG: [prestamos_individuales] No se encontraron prestamos individuales para este grupo")
    
    return render_template('prestamos_grupales/prestamos_individuales.html',  
                           prestamo_grupal=prestamo_grupal,  
                           prestamos_individuales=prestamos_individuales)


@prestamos_grupales_bp.route('/grupo/<int:grupo_id>/prestamos')
@login_required
def prestamos_por_grupo(grupo_id):
    # Filtrar los prestamos grupales por el grupo seleccionado
    prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).all()
    
    # Obtener el grupo para mostrar su informacion en la plantilla
    grupo = Grupo.query.get_or_404(grupo_id)
    
    # Obtener la lista completa de grupos
    grupos = Grupo.query.all()

    return render_template('prestamos_grupales/lista_prestamos_grupales.html',  
                           prestamos_grupales=prestamos_grupales,  
                           grupo=grupo,
                           grupos=grupos)  # Aqui se pasa la lista de grupos


# ==============================================================================
# FUNCION PARA DESCARGAR CONTRATO INDIVIDUAL (CORREGIDA)
# ==============================================================================
@prestamos_grupales_bp.route('/descargar_contrato/<int:contrato_id>')
@login_required
def descargar_contrato(contrato_id):
    current_app.logger.debug(f"DEBUG: [descargar_contrato] Intentando descargar contrato ID: {contrato_id}")
    contrato = Contrato.query.get_or_404(contrato_id)
    current_app.logger.debug(f"DEBUG: [descargar_contrato] Contrato encontrado: {contrato.nombre_archivo}")

    try:
        # LÍNEA CORREGIDA: Usar la nueva columna
        pdf_bytes = contrato.datos_binarios
        current_app.logger.debug(f"DEBUG: [descargar_contrato] Bytes del PDF obtenidos de la BD. Tamano: {len(pdf_bytes)} bytes.")

        # --- CAMBIO CLAVE: Normalizar el nombre del archivo para la descarga ---
        # Si el nombre en la DB contiene caracteres como 'ñ', unidecode los convierte (ej. 'ñ' a 'n').
        # secure_filename asegura que sea seguro para nombres de archivo.
        download_filename = secure_filename(unidecode(contrato.nombre_archivo))

        headers = {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{download_filename}"',
            'Content-Length': str(len(pdf_bytes))
        }
        current_app.logger.debug(f"DEBUG: [descargar_contrato] Enviando PDF con Response. Nombre: {download_filename}")
        return Response(pdf_bytes, headers=headers)

    except Exception as e:
        # --- MEJORA EN EL LOG: Usar current_app.logger y exc_info=True ---
        current_app.logger.error(f"ERROR: [descargar_contrato] Excepcion al intentar enviar el archivo: {e}", exc_info=True)
        flash(f"Error al descargar el contrato: {str(e)}", "error")
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))


# ==============================================================================
# FUNCION PARA GENERAR Y DESCARGAR CONTRATOS ZIP (CORREGIDA PARA FILENO Y UNICODE)
# ==============================================================================
@prestamos_grupales_bp.route('/generar_contrato/<int:prestamo_grupal_id>', methods=['GET'])
@login_required
def generar_contrato(prestamo_grupal_id):
    current_app.logger.debug(f"DEBUG: [generar_contrato] Iniciando generacion de ZIP para prestamo_grupal_id={prestamo_grupal_id}")

    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    clientes_asociados = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal.id).all()

    if not clientes_asociados:
        flash('No se encontraron clientes asociados a este prestamo grupal.', 'error')
        current_app.logger.debug(f"DEBUG: [generar_contrato] No se encontraron clientes asociados.")
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

    temp_zip_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=".zip") as temp_zip_file:
            temp_zip_path = temp_zip_file.name

        current_app.logger.debug(f"DEBUG: [generar_contrato] Archivo ZIP temporal creado en: {temp_zip_path}")

        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for prestamo_individual in clientes_asociados:
                cliente = Cliente.query.get(prestamo_individual.cliente_id)
                if not cliente:
                    flash(f'Error: Cliente con ID {prestamo_individual.cliente_id} no encontrado.', 'error')
                    current_app.logger.error(f"ERROR: [generar_contrato] Cliente con ID {prestamo_individual.cliente_id} no encontrado.")
                    continue

                current_app.logger.debug(f"DEBUG: [generar_contrato] Procesando contrato para cliente: {cliente.nombre} {cliente.apellido}")

                try:
                    pdf_buffer = generar_contrato_logic(cliente.id, prestamo_grupal, return_type='buffer')
                except Exception as e:
                    flash(f'Error al generar contrato para {cliente.nombre} {cliente.apellido}: {str(e)}', 'error')
                    # --- MEJORA EN EL LOG: Usar current_app.logger y exc_info=True ---
                    current_app.logger.error(f"ERROR: [generar_contrato] Excepcion al llamar a generar_contrato_logic para {cliente.nombre}: {str(e)}", exc_info=True)
                    continue

                if isinstance(pdf_buffer, io.BytesIO):
                    pdf_bytes = pdf_buffer.getvalue()
                    pdf_buffer.close()
                    current_app.logger.debug(f"DEBUG: [generar_contrato] PDF de {cliente.nombre} obtenido del buffer (tamano: {len(pdf_bytes)} bytes).")
                else:
                    flash(f'Error: La funcion generar_contrato_logic no devolvio un objeto BytesIO valido para {cliente.nombre} {cliente.apellido}. Tipo recibido: {type(pdf_buffer)}', 'error')
                    current_app.logger.error(f"ERROR: [generar_contrato] generar_contrato_logic no devolvio BytesIO para {cliente.nombre} {cliente.apellido}. Tipo recibido: {type(pdf_buffer)}")
                    continue

                monto_cliente = prestamo_individual.monto

                # --- CAMBIO CLAVE: Normalizar los nombres de cliente para el nombre de archivo dentro del ZIP ---
                # unidecode convierte 'ñ' a 'n', 'á' a 'a', etc.
                # .replace() elimina espacios y puntos que secure_filename podría convertir de forma indeseada
                cliente_nombre_limpio = unidecode(cliente.nombre).replace(" ", "_").replace(".", "")
                cliente_apellido_limpio = unidecode(cliente.apellido).replace(" ", "_").replace(".", "")

                # Construye el nombre del archivo con los nombres limpios y luego secure_filename
                nombre_archivo_base_zip = f"Contrato_{cliente_nombre_limpio.upper()}_{cliente_apellido_limpio.upper()}_Monto_{monto_cliente}.pdf"
                nombre_archivo_zip = secure_filename(nombre_archivo_base_zip)

                current_app.logger.debug(f"DEBUG: [generar_contrato] Anadiendo '{nombre_archivo_zip}' al ZIP.")
                zipf.writestr(nombre_archivo_zip, pdf_bytes) # Aquí se pasaba el nombre con 'ñ'

        current_app.logger.debug(f"DEBUG: [generar_contrato] Todos los contratos anadidos al ZIP. Tamano final del ZIP en disco: {os.path.getsize(temp_zip_path)} bytes.")

        # --- CAMBIO CLAVE: Normalizar el nombre del grupo para el nombre del archivo ZIP final ---
        grupo_nombre_limpio = unidecode(prestamo_grupal.grupo.nombre).replace(" ", "_").replace(".", "")
        fecha_desembolso = prestamo_grupal.fecha_desembolso.strftime('%d-%m-%Y')
        download_name_base = f"Contratos_{grupo_nombre_limpio}_Desembolso_{fecha_desembolso}.zip"
        download_name = secure_filename(download_name_base) # secure_filename también es importante aquí

        current_app.logger.debug(f"DEBUG: [generar_contrato] Leyendo el archivo ZIP temporal para enviarlo con Response.")
        with open(temp_zip_path, 'rb') as f:
            zip_data = f.read()

        headers = {
            'Content-Type': 'application/zip',
            'Content-Disposition': f'attachment; filename="{download_name}"',
            'Content-Length': str(len(zip_data))
        }
        current_app.logger.debug(f"DEBUG: [generar_contrato] Enviando ZIP con Response. Nombre: {download_name}, Tamano: {len(zip_data)}")
        return Response(zip_data, headers=headers)

    except Exception as e:
        flash(f"Error al generar o descargar el archivo ZIP: {str(e)}", "error")
        # --- MEJORA EN EL LOG: Usar current_app.logger y exc_info=True ---
        current_app.logger.critical(f"CRITICAL ERROR: [generar_contrato] Excepcion general durante la generacion del ZIP: {str(e)}", exc_info=True)
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))
    finally:
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
                current_app.logger.debug(f"DEBUG: [generar_contrato] Archivo temporal ZIP eliminado: {temp_zip_path}")
            except Exception as e:
                current_app.logger.error(f"ERROR: [generar_contrato] No se pudo eliminar el archivo temporal ZIP {temp_zip_path}: {e}")


# ==============================================================================
# FUNCION LOGICA PARA GENERAR UN CONTRATO INDIVIDUAL (AJUSTADA Y CORREGIDA)
# ==============================================================================
def generar_contrato_logic(cliente_id, prestamo_grupal, return_type='response'): 

    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Iniciando para cliente_id={cliente_id}, prestamo_grupal_id={prestamo_grupal.id}")

    cliente = Cliente.query.get_or_404(cliente_id)
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Cliente encontrado: {cliente.nombre} {cliente.apellido} (DNI: {cliente.dni})")

    prestamo_individual = PrestamoIndividual.query.filter_by(cliente_id=cliente.id, prestamo_grupal_id=prestamo_grupal.id).first()

    if prestamo_individual is None:
        current_app.logger.error(f"ERROR: [generar_contrato_logic] No se encontro el prestamo individual para cliente {cliente.id} y prestamo grupal {prestamo_grupal.id}.")
        raise ValueError(f"No se encontro el prestamo para el cliente {cliente.nombre} {cliente.apellido} en este prestamo grupal.")

    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Prestamo individual encontrado: ID={prestamo_individual.id}, Monto={prestamo_individual.monto}")

    monto_cliente = round(prestamo_individual.monto)
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Monto del cliente redondeado: {monto_cliente}")

    contrato_path = os.path.join(current_app.root_path, "static", f"contrato_preformateado{monto_cliente}.pdf")
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Ruta del contrato preformateado: {contrato_path}")

    if not os.path.exists(contrato_path):
        current_app.logger.error(f"ERROR: [generar_contrato_logic] Archivo no encontrado: {contrato_path}")
        raise FileNotFoundError(f"No se encontro el archivo de contrato preformateado para el monto {monto_cliente}.")
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Archivo preformateado encontrado.")

    try:
        doc = fitz.open(contrato_path)
        current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Documento PDF abierto con exito.")
    except Exception as e:
        # --- MEJORA EN EL LOG: Usar current_app.logger y exc_info=True ---
        current_app.logger.error(f"ERROR: [generar_contrato_logic] Error al abrir el archivo PDF con fitz: {e}", exc_info=True)
        raise ValueError(f"Error al abrir el archivo PDF: {e}")

    pagos = Pago.query.filter_by(cliente_id=cliente.id, prestamo_individual_id=prestamo_individual.id) \
                         .order_by(Pago.fecha_pago).limit(4).all()
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Pagos obtenidos del cliente {cliente.id}: {len(pagos)}")
    fechas_pago = [pago.fecha_pago.strftime('%d/%m/%Y') for pago in pagos]
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Fechas de pago iniciales: {fechas_pago}")

    while len(fechas_pago) < 4:
        fechas_pago.append("N/A")
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Fechas de pago finalizadas (4): {fechas_pago}")

    # Los datos para reemplazar DENTRO del PDF (NOMBRE_APELLIDO, etc.)
    # SÍ pueden contener 'ñ' y acentos, ya que PyMuPDF maneja Unicode internamente en el contenido.
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
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Datos a reemplazar en PDF: {datos_cliente}")

    for page_num, page in enumerate(doc):
        current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Procesando pagina {page_num + 1}...")
        text_instances = []
        for tag, value in datos_cliente.items():
            placeholder = f"{{{{{tag}}}}}"
            for inst in page.search_for(placeholder):
                text_instances.append((inst, value))

        current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Instancias de texto encontradas para reemplazar: {len(text_instances)}")

        for rect, value in text_instances:
            x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
            current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Reemplazando con '{value}' en rect {rect}")

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
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Reemplazo de texto en PDF completado.")

    buffer = io.BytesIO()
    doc.save(buffer)
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] PDF guardado en buffer en memoria. Tamano: {len(buffer.getvalue())} bytes.")
    buffer.seek(0)
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Puntero del buffer reseteado a 0.")
    doc.close()
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Documento PyMuPDF cerrado.")

    # --- CAMBIO CLAVE: Normalizar el nombre de archivo para la DB y descarga individual ---
    # Esto asegura que el nombre guardado en la BD no cause problemas en el futuro y sea compatible.
    cliente_nombre_limpio = unidecode(cliente.nombre).replace(" ", "_").replace(".", "")
    cliente_apellido_limpio = unidecode(cliente.apellido).replace(" ", "_").replace(".", "")

    # Construye el nombre del archivo con los nombres limpios y luego secure_filename
    nombre_archivo_base = f"contrato_{cliente_nombre_limpio.upper()}_{cliente_apellido_limpio.upper()}_Monto_{monto_cliente}.pdf"
    nombre_archivo = secure_filename(nombre_archivo_base)

    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Nombre de archivo para descarga (limpio): {nombre_archivo}")

    contrato_existente = Contrato.query.filter_by(cliente_id=cliente.id, prestamo_individual_id=prestamo_individual.id).first()

    pdf_bytes_para_db = buffer.getvalue()
    current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Bytes del PDF listos para DB. (Tamano: {len(pdf_bytes_para_db)})")

    if contrato_existente:
        current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Contrato existente encontrado. Actualizando...")
        # LÍNEA CORREGIDA: Usar la nueva columna
        contrato_existente.datos_binarios = pdf_bytes_para_db
        contrato_existente.nombre_archivo = nombre_archivo
    else:
        current_app.logger.debug(f"DEBUG: [generar_contrato_logic] No se encontro contrato existente. Creando nuevo...")
        nuevo_contrato = Contrato(
            nombre_archivo=nombre_archivo,
            # LÍNEA CORREGIDA: Usar la nueva columna
            datos_binarios=pdf_bytes_para_db,
            cliente_id=cliente.id,
            prestamo_individual_id=prestamo_individual.id
        )
        db.session.add(nuevo_contrato)

    try:
        db.session.commit()
        current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Cambios en la base de datos (contrato) guardados.")
    except Exception as e:
        db.session.rollback()
        # --- MEJORA EN EL LOG: Usar current_app.logger y exc_info=True ---
        current_app.logger.error(f"ERROR: [generar_contrato_logic] Error al guardar el contrato en la base de datos para cliente {cliente_id}: {e}", exc_info=True)
        raise # Relanza la excepción para que el llamador (generar_contrato) pueda manejarla

    if return_type == 'buffer':
        current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Devolviendo BytesIO (buffer) para uso interno.")
        return buffer
    else:
        current_app.logger.debug(f"DEBUG: [generar_contrato_logic] Preparando Response para descarga directa.")
        headers = {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{nombre_archivo}"',
            'Content-Length': str(len(pdf_bytes_para_db))
        }
        return Response(pdf_bytes_para_db, headers=headers)




@prestamos_grupales_bp.route('/<int:prestamo_grupal_id>/reporte_pagos')
@login_required
def reporte_pagos(prestamo_grupal_id):
    # Obtener el préstamo grupal
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    
    # Obtener todos los préstamos individuales de este préstamo grupal
    prestamos_individuales = PrestamoIndividual.query.filter_by(
        prestamo_grupal_id=prestamo_grupal_id
    ).all()
    
    # Organizar datos por cliente
    clientes_data = {}
    total_pagado = 0
    total_pendiente = 0 
    total_mora = 0
    total_registros = 0
    
    for prestamo_individual in prestamos_individuales:
        cliente = Cliente.query.get(prestamo_individual.cliente_id)
        pagos = Pago.query.filter_by(
            prestamo_individual_id=prestamo_individual.id
        ).order_by(Pago.fecha_pago.desc()).all()  # Orden descendente por fecha
        
        if cliente.id not in clientes_data:
            clientes_data[cliente.id] = {
                'cliente': cliente,
                'prestamo_individual': prestamo_individual,
                'pagos': []
            }
        
        # Agregar pagos y calcular totales
        cliente_total_pagado = 0
        cliente_total_pendiente = 0
        cliente_total_mora = 0
        cliente_pagos_completados = 0
        
        for pago in pagos:
            clientes_data[cliente.id]['pagos'].append(pago)
            
            # Sumar a totales generales
            pago_pagado = pago.monto_pagado or 0
            pago_pendiente = pago.monto_pendiente or 0
            pago_mora = pago.monto_mora or 0
            
            total_pagado += pago_pagado
            total_pendiente += pago_pendiente
            total_mora += pago_mora
            total_registros += 1
            
            # Sumar a totales del cliente
            cliente_total_pagado += pago_pagado
            cliente_total_pendiente += pago_pendiente
            cliente_total_mora += pago_mora
            
            # Contar pagos completados
            if pago.estado == 'Pagado':
                cliente_pagos_completados += 1
        
        # Agregar resúmenes del cliente
        clientes_data[cliente.id]['resumen'] = {
            'total_pagado': cliente_total_pagado,
            'total_pendiente': cliente_total_pendiente,
            'total_mora': cliente_total_mora,
            'pagos_completados': cliente_pagos_completados,
            'total_pagos': len(pagos)
        }
    
    # Convertir a lista y ordenar por nombre de cliente
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

@prestamos_grupales_bp.route('/pago/<int:pago_id>/datos', methods=['GET'])
@login_required
def obtener_datos_pago(pago_id):
    """Obtener los datos de un pago específico para edición"""
    try:
        pago = Pago.query.get_or_404(pago_id)
        
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
        prestamo_individual = PrestamoIndividual.query.get(pago.prestamo_individual_id)
        
        # Eliminar el pago
        db.session.delete(pago)
        db.session.commit()
        
        current_app.logger.info(f"Pago {pago_id} eliminado correctamente por el usuario {current_user.id} (admin). Cliente: {cliente.nombre if cliente else 'N/A'}")
        return {'success': True, 'message': 'Pago eliminado correctamente'}
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar el pago {pago_id}: {str(e)}")
        return {'success': False, 'message': f'Error interno: {str(e)}'}, 500
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, PrestamoGrupal, Grupo, PrestamoIndividual, Pago, Cliente, Contrato
from datetime import datetime, timedelta
import fitz
import zipfile
from werkzeug.utils import secure_filename
from flask_login import login_required
import os
from io import BytesIO
import io
from flask import send_file, Response
from sqlalchemy import asc, desc



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

        # ✅ Establecer monto_total en 0 al crear el préstamo grupal
        nuevo_prestamo_grupal = PrestamoGrupal(
            grupo_id=grupo_id,
            fecha_desembolso=fecha_desembolso
        )

        # Guarda el nuevo préstamo grupal en la base de datos
        db.session.add(nuevo_prestamo_grupal)
        db.session.commit()

        flash("Préstamo grupal creado exitosamente.", "success")
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales', grupo_id=grupo_id))

    # Obtener todos los grupos para mostrar en la plantilla
    grupos = Grupo.query.all()
    return render_template('prestamos_grupales/nuevo_prestamo_grupal.html', grupos=grupos)



@prestamos_grupales_bp.route('/', methods=['GET'])
@login_required
def lista_prestamos_grupales():
    grupo_id = request.args.get('grupo_id', type=int)

    grupos = Grupo.query.all()

    # Si no se ha seleccionado un grupo, no cargamos préstamos
    prestamos_grupales = []
    if grupo_id:
        prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).all()

    return render_template('prestamos_grupales/lista_prestamos_grupales.html',
                           prestamos_grupales=prestamos_grupales,
                           grupos=grupos,
                           selected_grupo_id=grupo_id)




# Asignar préstamos individuales a los clientes dentro de un préstamo grupal
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
                continue  # Si el préstamo individual ya existe, se salta

            # Validar que el monto ingresado es un número válido
            try:
                monto = float(request.form[f'monto_cliente_{cliente_id}'])
            except ValueError:
                flash(f"El monto para el cliente {cliente_id} no es válido.")
                return redirect(url_for('prestamos_grupales.asignar_prestamos_individuales', prestamo_grupal_id=prestamo_grupal_id))

            # Crear el préstamo individual
            nuevo_prestamo_individual = PrestamoIndividual(
                prestamo_grupal_id=prestamo_grupal.id,
                cliente_id=cliente_id,
                monto=monto
            )
            db.session.add(nuevo_prestamo_individual)
            db.session.commit()  # Commit para obtener el ID del préstamo individual

            # **Generar 4 pagos iniciando 15 días después de la fecha de desembolso**
            fecha_pago = prestamo_grupal.fecha_desembolso + timedelta(days=15)  # Primer pago después de 15 días
            for _ in range(4):
                nuevo_pago = Pago(
                    cliente_id=cliente_id,
                    prestamo_individual_id=nuevo_prestamo_individual.id,  
                    monto_pendiente=0,
                    monto_pagado=0,
                    estado="Pendiente",
                    fecha_pago=fecha_pago  
                )
                db.session.add(nuevo_pago)

                # Sumar 15 días para el siguiente pago
                fecha_pago += timedelta(days=15)

        # Actualizar monto_total del préstamo grupal
        prestamos_individuales = db.session.query(db.func.sum(PrestamoIndividual.monto)).filter_by(prestamo_grupal_id=prestamo_grupal.id).scalar() or 0
        # Solo usa la propiedad calculada, sin asignar directamente
        prestamo_grupal.monto_total  # Solo accede, no asignes

        db.session.commit()
        
        # Redirigir a la lista de préstamos grupales con el grupo seleccionado
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales', grupo_id=prestamo_grupal.grupo_id))

    return render_template('prestamos_grupales/asignar_prestamos_individuales.html', 
                           prestamo_grupal=prestamo_grupal, clientes=clientes)




@prestamos_grupales_bp.route('/<int:prestamo_grupal_id>/prestamos_individuales')
@login_required
def prestamos_individuales(prestamo_grupal_id):
    # Obtener el préstamo grupal
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    
    # Obtener los préstamos individuales del grupo
    prestamos_individuales = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal_id).all()
    
    # Agregar depuración
    print(f"Prestamos Individuales para el grupo {prestamo_grupal_id}: {prestamos_individuales}")
    
    # Si no hay préstamos individuales
    if not prestamos_individuales:
        print("No se encontraron préstamos individuales para este grupo")
    
    return render_template('prestamos_grupales/prestamos_individuales.html', 
                           prestamo_grupal=prestamo_grupal, 
                           prestamos_individuales=prestamos_individuales)


@prestamos_grupales_bp.route('/grupo/<int:grupo_id>/prestamos')
@login_required
def prestamos_por_grupo(grupo_id):
    # Filtrar los préstamos grupales por el grupo seleccionado
    prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).all()
    
    # Obtener el grupo para mostrar su información en la plantilla
    grupo = Grupo.query.get_or_404(grupo_id)

    return render_template('prestamos_grupales/lista_prestamos_grupales.html', 
                           prestamos_grupales=prestamos_grupales, 
                           grupo=grupo)


@prestamos_grupales_bp.route('/descargar_contrato/<int:contrato_id>')
@login_required
def descargar_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    
    # Crear un archivo en memoria desde el contenido binario
    archivo = BytesIO(contrato.archivo)
    archivo.seek(0)  # Asegurarse de que el puntero esté al principio del archivo

    # Enviar el archivo como respuesta
    return send_file(archivo, as_attachment=True, download_name=contrato.nombre_archivo, mimetype='application/pdf')



@prestamos_grupales_bp.route('/generar_contrato/<int:prestamo_grupal_id>', methods=['GET'])
@login_required
def generar_contrato(prestamo_grupal_id):
    # Obtener el préstamo grupal
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)

    # Obtener los clientes asociados al préstamo grupal
    clientes_asociados = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal.id).all()

    if not clientes_asociados:
        flash('No se encontraron clientes asociados a este préstamo grupal.', 'error')
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

    # Crear una carpeta temporal en memoria
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for prestamo_individual in clientes_asociados:
            cliente = Cliente.query.get(prestamo_individual.cliente_id)
            if not cliente:
                flash(f'Error: Cliente con ID {prestamo_individual.cliente_id} no encontrado.', 'error')
                continue

            # Generar el contrato (asegurándonos de obtener el contenido binario)
            contrato_response = generar_contrato_logic(cliente.id, prestamo_grupal)

            if isinstance(contrato_response, Response):
                contrato_response.direct_passthrough = False  # 🔹 Desactivar modo passthrough
                contrato_bytes = contrato_response.get_data()
            else:
                flash(f'Error al generar contrato para {cliente.nombre} {cliente.apellido}.', 'error')
                continue

            # Obtener el monto del cliente
            monto_cliente = prestamo_individual.monto  # O el campo adecuado que contenga el monto

            # Crear nombre de archivo con monto incluido
            nombre_archivo = secure_filename(f"Contrato_{cliente.nombre}_{cliente.apellido}_Monto_{monto_cliente}.pdf")

            # Guardar el contrato en el archivo ZIP
            zipf.writestr(nombre_archivo, contrato_bytes)

    # Mover el puntero del buffer al inicio
    zip_buffer.seek(0)

    grupo_nombre = prestamo_grupal.grupo.nombre
    fecha_desembolso = prestamo_grupal.fecha_desembolso.strftime('%d-%m-%Y')

    # Enviar el archivo ZIP para descarga automática
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name=f"Contratos_{grupo_nombre}_Desembolso_{fecha_desembolso}.zip")




def generar_contrato_logic(cliente_id, prestamo_grupal):
    # Obtener el cliente por su ID
    cliente = Cliente.query.get_or_404(cliente_id)

    # Obtener el préstamo individual correcto dentro del préstamo grupal
    prestamo_individual = None  

    for prestamo in prestamo_grupal.prestamos_individuales:
        if prestamo.cliente_id == cliente.id:
            prestamo_individual = prestamo  
            break

    if prestamo_individual is None:
        raise ValueError(f"No se encontró el préstamo para el cliente {cliente.nombre} {cliente.apellido} en este préstamo grupal.")

    monto_cliente = round(prestamo_individual.monto)

    contrato_path = f"static/contrato_preformateado{monto_cliente}.pdf"
    
    if not os.path.exists(contrato_path):
        raise FileNotFoundError(f"No se encontró el archivo de contrato preformateado para el monto {monto_cliente}.")
    
    doc = fitz.open(contrato_path)

    # Obtener las fechas de pago solo del préstamo individual correcto
    pagos = Pago.query.filter_by(cliente_id=cliente.id, prestamo_individual_id=prestamo_individual.id) \
                      .order_by(Pago.fecha_pago).limit(4).all()

    fechas_pago = [pago.fecha_pago.strftime('%d/%m/%Y') for pago in pagos]

    # Asegurar que haya 4 fechas, rellenando con "N/A" si es necesario
    while len(fechas_pago) < 4:
        fechas_pago.append("N/A")

    # Definir los datos a reemplazar
    datos_cliente = {
        "NOMBRE": cliente.nombre.upper(),
        "APELLIDO": cliente.apellido.upper(),
        "DNI": cliente.dni,
        "PRESTAMO": f"{monto_cliente}",
        "FECHA_DSB": prestamo_grupal.fecha_desembolso.strftime('%d/%m/%Y'),
        "FECHA_1": fechas_pago[0],
        "FECHA_2": fechas_pago[1],
        "FECHA_3": fechas_pago[2],
        "FECHA_4": fechas_pago[3]
    }

    # Reemplazo en el documento PDF
    for page in doc:
        text_instances = []
        for tag, value in datos_cliente.items():
            placeholder = f"{{{{{tag}}}}}"
            for inst in page.search_for(placeholder):
                text_instances.append((inst, value))
        
        for rect, value in text_instances:
            x, y, width, height = rect.x0, rect.y0, rect.width, rect.height
            
            # Cubrir el texto original con un rectángulo blanco
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            # Escribir el nuevo texto en la misma posición
            page.insert_text((x, y + height * 0.8), value, fontsize=9, color=(0, 0, 0))

    # Guardar el contrato en memoria y en la base de datos
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    nombre_archivo = f"contrato_{cliente.nombre.upper()}_{cliente.apellido.upper()}_{monto_cliente}.pdf"
    
    nuevo_contrato = Contrato(
        nombre_archivo=nombre_archivo,
        archivo=buffer.getvalue(),
        cliente_id=cliente.id,
        prestamo_individual_id=prestamo_individual.id
    )
    
    db.session.add(nuevo_contrato)
    db.session.commit()

    return send_file(buffer, as_attachment=True, download_name=nombre_archivo, mimetype='application/pdf')

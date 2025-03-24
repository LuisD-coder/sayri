from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, PrestamoGrupal, Grupo, PrestamoIndividual, Pago, Cliente, Contrato
from datetime import datetime, timedelta
import fitz
import os
from io import BytesIO
import io
from flask import send_file
from sqlalchemy import asc, desc



prestamos_grupales_bp = Blueprint('prestamos_grupales', __name__, url_prefix='/prestamos_grupales')

# Crear un nuevo préstamo grupal
@prestamos_grupales_bp.route('/nuevo', methods=['GET', 'POST'])
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
            monto_total=0,  # Se inicia en 0 y se actualizará después al asignar préstamos individuales
            fecha_desembolso=fecha_desembolso
        )

        # Guarda el nuevo préstamo grupal en la base de datos
        db.session.add(nuevo_prestamo_grupal)
        db.session.commit()

        flash("Préstamo grupal creado exitosamente.", "success")
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

    # Obtener todos los grupos para mostrar en la plantilla
    grupos = Grupo.query.all()
    return render_template('prestamos_grupales/nuevo_prestamo_grupal.html', grupos=grupos)



@prestamos_grupales_bp.route('/', methods=['GET'])
def lista_prestamos_grupales():
    # Obtener el valor de la columna de orden (por defecto 'grupo')
    orden_columna = request.args.get('orden', 'grupo')

    # Mapea las columnas válidas para ordenación
    columnas_validas = {
        'grupo': PrestamoGrupal.grupo_id,
        'monto': PrestamoGrupal.monto_total,
        'fecha': PrestamoGrupal.fecha_desembolso
    }

    # Asegúrate de que 'orden_columna' sea una columna válida
    if orden_columna in columnas_validas:
        orden_columna = columnas_validas[orden_columna]
    else:
        orden_columna = PrestamoGrupal.grupo_id  # Valor por defecto

    # Realiza la consulta ordenada
    try:
        prestamos_grupales = PrestamoGrupal.query.order_by(asc(orden_columna)).all()
    except Exception as e:
        # Captura cualquier error que ocurra durante la consulta
        print(f"Error al obtener los préstamos grupales: {e}")
        prestamos_grupales = []

    # Devuelve la plantilla con los datos
    return render_template('prestamos_grupales/lista_prestamos_grupales.html', prestamos_grupales=prestamos_grupales)




# Asignar préstamos individuales a los clientes dentro de un préstamo grupal
@prestamos_grupales_bp.route('/<int:prestamo_grupal_id>/asignar_prestamos_individuales', methods=['GET', 'POST'])
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
        prestamo_grupal.monto_total = prestamos_individuales

        db.session.commit()
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

    return render_template('prestamos_grupales/asignar_prestamos_individuales.html', 
                           prestamo_grupal=prestamo_grupal, clientes=clientes)




@prestamos_grupales_bp.route('/<int:prestamo_grupal_id>/prestamos_individuales')
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
def prestamos_por_grupo(grupo_id):
    # Filtrar los préstamos grupales por el grupo seleccionado
    prestamos_grupales = PrestamoGrupal.query.filter_by(grupo_id=grupo_id).all()
    
    # Obtener el grupo para mostrar su información en la plantilla
    grupo = Grupo.query.get_or_404(grupo_id)

    return render_template('prestamos_grupales/lista_prestamos_grupales.html', 
                           prestamos_grupales=prestamos_grupales, 
                           grupo=grupo)


@prestamos_grupales_bp.route('/descargar_contrato/<int:contrato_id>')
def descargar_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    
    # Crear un archivo en memoria desde el contenido binario
    archivo = BytesIO(contrato.archivo)
    archivo.seek(0)  # Asegurarse de que el puntero esté al principio del archivo

    # Enviar el archivo como respuesta
    return send_file(archivo, as_attachment=True, download_name=contrato.nombre_archivo, mimetype='application/pdf')



@prestamos_grupales_bp.route('/generar_contrato/<int:prestamo_grupal_id>', methods=['GET'])
def generar_contrato(prestamo_grupal_id):
    # Obtener el préstamo grupal por su ID
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)

    # Obtener los clientes asociados a ese préstamo grupal
    clientes_asociados = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal.id).all()

    # Si no hay clientes asociados, mostrar un error
    if not clientes_asociados:
        flash('No se encontraron clientes asociados a este préstamo grupal.', 'error')
        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))

    # Crear una lista para almacenar los archivos generados (si los vas a permitir descargar en conjunto)
    archivos_generados = []

    # Aquí podemos proceder a generar el contrato para cada cliente
    for prestamo_individual in clientes_asociados:
        cliente = Cliente.query.get(prestamo_individual.cliente_id)

        # Generar el contrato específico para el cliente
        contrato_generado = generar_contrato_logic(cliente.id, prestamo_grupal)

        # Aquí, si quieres guardar el contrato generado, puedes añadirlo a la lista de archivos
        # Si se quiere permitir que el usuario descargue los contratos como archivos, por ejemplo:
        archivos_generados.append(contrato_generado)

    # Si deseas hacer algo con los archivos generados, como retornar uno específico, se podría modificar:
    # Por ejemplo, solo retornar el último contrato generado
    # return send_file(archivos_generados[-1], as_attachment=True)  # Si deseas devolver uno específico

    # Si has guardado los contratos y deseas permitir su descarga en el futuro, podrías crear un índice de los mismos
    flash('Los contratos han sido generados exitosamente.', 'success')

    # Redirigir a la lista de préstamos grupales o a cualquier otra página después de la generación
    return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))





def generar_contrato_logic(cliente_id, prestamo_grupal):
    # Obtener el cliente por su ID
    cliente = Cliente.query.get_or_404(cliente_id)

    # Obtener el monto del préstamo individual asignado a este cliente
    monto_cliente = None
    prestamo_individual = None  # Variable para almacenar el prestamo individual

    for prestamo in prestamo_grupal.prestamos_individuales:
        if prestamo.cliente_id == cliente.id:
            monto_cliente = prestamo.monto
            prestamo_individual = prestamo  # Asignamos el prestamo_individual
            break

    if monto_cliente is None or prestamo_individual is None:
        raise ValueError(f"No se encontró el monto de préstamo para el cliente {cliente.nombre} {cliente.apellido}.")

    # Redondear el monto del préstamo para evitar decimales en el nombre del archivo
    monto_cliente = round(monto_cliente)

    contrato_path = f"static/contrato_preformateado{monto_cliente}.pdf"
    
    if not os.path.exists(contrato_path):
        raise FileNotFoundError(f"No se encontró el archivo de contrato preformateado para el monto {monto_cliente}.")
    
    doc = fitz.open(contrato_path)

    # Obtener las primeras 4 fechas de pago del cliente, si existen
    pagos = Pago.query.filter_by(cliente_id=cliente.id).order_by(Pago.fecha_pago).limit(4).all()
    fechas_pago = [pago.fecha_pago.strftime('%d/%m/%Y') for pago in pagos]

    # Asegurarse de que haya 4 fechas, rellenando con "N/A" si es necesario
    while len(fechas_pago) < 4:
        fechas_pago.append("N/A")

    # Definir los datos a reemplazar
    datos_cliente = {
        "NOMBRE": cliente.nombre.upper(),
        "APELLIDO": cliente.apellido.upper(),
        "DNI":cliente.dni,
        "PRESTAMO": f"{monto_cliente} soles",
        "FECHA_DSB": prestamo_grupal.fecha_desembolso.strftime('%d/%m/%Y'),
        "FECHA_1": fechas_pago[0],  # Primer fecha de pago
        "FECHA_2": fechas_pago[1],  # Segunda fecha de pago
        "FECHA_3": fechas_pago[2],  # Tercera fecha de pago
        "FECHA_4": fechas_pago[3]   # Cuarta fecha de pago
    }

    # Reemplazar los marcadores de texto
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
            page.insert_text((x, y + height * 0.8), value, fontsize=10, color=(0, 0, 0))

    # Guardar el contrato modificado en un buffer en lugar de en un archivo
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # Crear una nueva instancia de Contrato y guardar el contrato en la base de datos
    nombre_archivo = f"contrato_{cliente.nombre.upper()}_{cliente.apellido.upper()}_{monto_cliente}.pdf"
    
    nuevo_contrato = Contrato(
        nombre_archivo=nombre_archivo,
        archivo=buffer.getvalue(),
        cliente_id=cliente.id,
        prestamo_individual_id=prestamo_individual.id  # Asignar el prestamo_individual_id
    )
    
    db.session.add(nuevo_contrato)
    db.session.commit()

    # Retornar el archivo generado para que el usuario lo descargue
    return send_file(buffer, as_attachment=True, download_name=nombre_archivo, mimetype='application/pdf')

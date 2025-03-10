from flask import Blueprint, render_template, request, redirect, url_for
from models import db, PrestamoGrupal, Grupo, PrestamoIndividual, Pago
from datetime import datetime, timedelta


prestamos_grupales_bp = Blueprint('prestamos_grupales', __name__, url_prefix='/prestamos_grupales')

# Crear un nuevo préstamo grupal
# Crear un nuevo préstamo grupal
@prestamos_grupales_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_prestamo_grupal():
    if request.method == 'POST':
        grupo_id = request.form['grupo_id']
        fecha_desembolso_str = request.form['fecha_desembolso']

        # Convierte la fecha de string a un objeto datetime
        fecha_desembolso = datetime.strptime(fecha_desembolso_str, '%Y-%m-%d').date()

        # Recupera el grupo seleccionado
        grupo = Grupo.query.get(grupo_id)

        # Calcula el monto total sumando los préstamos individuales de los clientes solo para este grupo
        monto_total = sum(prestamo.monto for prestamo in PrestamoIndividual.query
                          .filter(PrestamoIndividual.prestamo_grupal_id == grupo_id).all())  # Aquí cambiamos de grupo_id a prestamo_grupal_id

        # Crea el préstamo grupal con el monto total calculado
        nuevo_prestamo_grupal = PrestamoGrupal(grupo_id=grupo_id, monto_total=monto_total, fecha_desembolso=fecha_desembolso)

        # Guarda el nuevo préstamo grupal en la base de datos
        db.session.add(nuevo_prestamo_grupal)
        db.session.commit()

        return redirect(url_for('prestamos_grupales.lista_prestamos_grupales'))
    
    grupos = Grupo.query.all()
    return render_template('prestamos_grupales/nuevo_prestamo_grupal.html', grupos=grupos)


# Listar todos los préstamos grupales
@prestamos_grupales_bp.route('/')
def lista_prestamos_grupales():
    prestamos_grupales = PrestamoGrupal.query.all()
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

from flask import Blueprint, render_template, request, redirect, url_for
from models import db, PrestamoGrupal, Grupo, PrestamoIndividual
from datetime import datetime

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
    clientes = prestamo_grupal.grupo.clientes  # Obtener los clientes del grupo

    if request.method == 'POST':
        for cliente_id in request.form.getlist('clientes'):
            # Verificar si el cliente ya tiene un préstamo individual asignado en este préstamo grupal
            prestamo_existente = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal.id, cliente_id=cliente_id).first()
            
            if prestamo_existente:
                print(f"El cliente ID {cliente_id} ya tiene un préstamo asignado en este grupo. No se puede asignar otro préstamo.")
                continue  # Si ya tiene un préstamo, se omite y no se asigna otro
            monto = request.form[f'monto_cliente_{cliente_id}']
            print(f"Guardando préstamo individual para Cliente ID {cliente_id}, Monto: {monto}")  # Mensaje de depuración
        
            nuevo_prestamo_individual = PrestamoIndividual(
                prestamo_grupal_id=prestamo_grupal.id,
                cliente_id=cliente_id,
                monto=monto
            )
            db.session.add(nuevo_prestamo_individual)

        # Actualizar monto_total del préstamo grupal solo con los préstamos del grupo actual
        prestamos_individuales = PrestamoIndividual.query.filter_by(prestamo_grupal_id=prestamo_grupal.id).all()
        
        # Asegurarse de que los montos sean números y calcular el monto total
        monto_total_actualizado = sum(float(prestamo.monto) for prestamo in prestamos_individuales if prestamo.monto)

        # Actualizar el campo monto_total del préstamo grupal
        prestamo_grupal.monto_total = monto_total_actualizado
        
        # Guardar los cambios en la base de datos
        db.session.commit()

        print("Préstamos individuales guardados y monto_total actualizado.")
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

from flask import Blueprint, render_template, request, redirect, url_for
from models import db, PrestamoIndividual, Cliente, PrestamoGrupal
from flask_login import login_required

prestamos_individuales_bp = Blueprint('prestamos_individuales', __name__, url_prefix='/prestamos_individuales')

# Asignar un préstamo individual
@prestamos_individuales_bp.route('/<int:prestamo_grupal_id>/asignar', methods=['GET', 'POST'])
@login_required
def asignar_prestamo_individual(prestamo_grupal_id):
    prestamo_grupal = PrestamoGrupal.query.get_or_404(prestamo_grupal_id)
    clientes = prestamo_grupal.grupo.clientes  # Obtener los clientes del grupo
    
    if request.method == 'POST':
        for cliente_id in request.form.getlist('clientes'):
            monto = request.form[f'monto_cliente_{cliente_id}']
            nuevo_prestamo_individual = PrestamoIndividual(
                prestamo_grupal_id=prestamo_grupal.id,
                cliente_id=cliente_id,
                monto=monto
            )
            db.session.add(nuevo_prestamo_individual)
        db.session.commit()
        
        return redirect(url_for('prestamos_grupales.prestamos_individuales', prestamo_grupal_id=prestamo_grupal.id))
    
    return render_template('prestamos_individuales/asignar_prestamo_individual.html', 
                           prestamo_grupal=prestamo_grupal, 
                           clientes=clientes)

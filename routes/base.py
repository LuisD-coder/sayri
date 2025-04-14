from flask import Blueprint, render_template
from datetime import date
from models import Pago, PrestamoIndividual
from flask_login import login_required

base_bp = Blueprint('base', __name__)

@base_bp.route('/')
@login_required
def home():
    today = date.today()
    pagos_proximos = []
    pagos_vencidos = []
    pagos_pagados = []

    # Obtener todos los préstamos individuales
    prestamos = PrestamoIndividual.query.all()

    for prestamo in prestamos:
        for pago in prestamo.pagos:
            dias_diferencia = (pago.fecha_pago - today).days

            if pago.estado == "Pagado":
                pagos_pagados.append(pago)
            elif pago.estado == "Atrasado":
                pagos_vencidos.append(pago)
            elif 0 <= dias_diferencia <= 5 and pago.estado != "Pagado":
                pagos_proximos.append(pago)

    return render_template(
        'base.html',
        pagos_proximos=pagos_proximos,
        pagos_vencidos=pagos_vencidos,
        pagos_pagados=pagos_pagados
    )

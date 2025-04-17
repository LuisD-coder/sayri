from flask import Blueprint, render_template
from datetime import date
from models import Pago, PrestamoIndividual
from flask_login import login_required

base_bp = Blueprint('base', __name__)

@base_bp.route('/')
@login_required
def home():
    return render_template(
        'base.html',
    )
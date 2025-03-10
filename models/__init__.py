from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.cliente import Cliente
from models.grupo import Grupo
from models.prestamo_grupal import PrestamoGrupal
from models.prestamo_individual import PrestamoIndividual
from models.pago import Pago  # Ahora importado al final

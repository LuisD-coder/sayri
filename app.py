from flask import Flask, render_template
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager  # Importar LoginManager
from models import db, Usuario, Pago  # Asegúrate de importar tu modelo Pago
from routes import register_routes
from utils import inicializar_roles, crear_admin  # Importamos la función
from datetime import date

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    # Inicializar LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)

    # Definir el comportamiento de la ruta de inicio de sesión
    login_manager.login_view = "login.login_view"  # Nombre del blueprint y la ruta de login

    # Definir la función user_loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))  # Asegúrate de que estás obteniendo al usuario de la base de datos

    # Registro de rutas
    register_routes(app)

    # Ruta principal
    @app.route('/')
    def index():
        today = date.today()

        # Obtener pagos
        pagos_proximos = Pago.query.filter(
            Pago.estado == 'Pendiente',
            Pago.fecha_pago >= today
        ).limit(5).all()

        pagos_vencidos = Pago.query.filter(
            Pago.estado == 'Atrasado'
        ).limit(5).all()

        pagos_pagados = Pago.query.filter(
            Pago.estado == 'Pagado'
        ).limit(5).all()


        # Imprimir los pagos para depuración
        print("Pagos próximos:", pagos_proximos)
        print("Pagos vencidos:", pagos_vencidos)
        print("Pagos pagados:", pagos_pagados)

        return render_template(
            'base.html',
            pagos_proximos=pagos_proximos,
            pagos_vencidos=pagos_vencidos,
            pagos_pagados=pagos_pagados
        )

    # Ejecutar la inicialización de roles solo si es necesario
    with app.app_context():
        inicializar_roles()
        #crear_admin()  # Crea un usuario admin si no existe

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

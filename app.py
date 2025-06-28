from flask import Flask, render_template, request, redirect, url_for # Importa request, redirect, url_for
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
from models import db, Usuario, Pago
from routes import register_routes
from utils import inicializar_roles, crear_admin
from datetime import date

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    # --- Configuración del modo mantenimiento ---
    # Lo ideal es que esto venga de config.py o de una variable de entorno
    # Por ahora, lo definimos aquí para el ejemplo.
    # CAMBIA ESTO A TRUE CUANDO QUIERAS ACTIVAR EL MANTENIMIENTO
    app.config['MAINTENANCE_MODE'] = False

    # Opcional: Lista de IPs permitidas para acceder durante el mantenimiento
    # Reemplaza 'TU_DIRECCION_IP_PUBLICA' con tu IP real.
    # Puedes añadir más IPs si es necesario: ['IP_ADMIN1', 'IP_ADMIN2']
    ALLOWED_IPS_DURING_MAINTENANCE = ['192.168.1.5']


    # --- Lógica del before_request para el modo mantenimiento ---
    @app.before_request
    def check_maintenance():
        # Si el modo de mantenimiento está activado
        if app.config.get('MAINTENANCE_MODE'):
            # Permite el acceso a la ruta de la página de mantenimiento
            # para que la página en sí pueda ser mostrada.
            if request.path == url_for('maintenance_page'):
                return None # Continúa con la solicitud normal para esta ruta

            # Permite el acceso a IPs específicas (como la tuya)
            if request.remote_addr in ALLOWED_IPS_DURING_MAINTENANCE:
                return None # Continúa con la solicitud normal para estas IPs

            # Si no es la página de mantenimiento y la IP no está permitida,
            # muestra la página de mantenimiento con código 503.
            return render_template('maintenance.html'), 503


    # --- Definición de la ruta de la página de mantenimiento ---
    # Es crucial que esta ruta exista y que la lógica de before_request
    # permita el acceso a ella para evitar un bucle de redirección.
    @app.route('/maintenance')
    def maintenance_page():
        return render_template('maintenance.html')


    # Inicializar LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login.login_view"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    # Registro de rutas (tus blueprints y otras rutas)
    register_routes(app)

    # Ruta principal (solo se ejecutará si no hay modo de mantenimiento activo)
    @app.route('/')
    def index():
        today = date.today()
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
        #crear_admin()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
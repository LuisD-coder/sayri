from flask import Flask, render_template, request, redirect, url_for
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager, current_user
# ✅ 1. Agregamos 'Comunicado' a los imports
from models import db, Usuario, Pago, Comunicado
from routes import register_routes
# ✅ 2. Importamos el Blueprint de comunicados
from routes.comunicados import comunicados_bp
from utils import inicializar_roles, crear_admin
from datetime import date

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    # --- Configuración del modo mantenimiento ---
    app.config['MAINTENANCE_MODE'] = False
    ALLOWED_IPS_DURING_MAINTENANCE = ['201.218.159.117']

    # --- Lógica del before_request para el modo mantenimiento ---
    @app.before_request
    def check_maintenance():
        if app.config.get('MAINTENANCE_MODE'):
            if request.path == url_for('maintenance_page'):
                return None 

            if request.remote_addr in ALLOWED_IPS_DURING_MAINTENANCE:
                return None 

            return render_template('maintenance.html'), 503

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

    # Registro de rutas existentes
    register_routes(app)
    
    # ✅ 3. REGISTRAR EL NUEVO BLUEPRINT DE COMUNICADOS
    app.register_blueprint(comunicados_bp)

    # ✅ 4. INYECCIÓN GLOBAL (Context Processor)
    # Esto busca si hay un mensaje activo y lo envía a TODAS las plantillas (base.html)
    @app.context_processor
    def inject_comunicado_global():
        # Solo buscamos si el usuario está logueado (opcional, ahorra consultas)
        # o si quieres que se vea en el login, quita el 'if current_user'.
        comunicado = None
        try:
            # Buscamos el comunicado activo más reciente
            comunicado = Comunicado.query.filter_by(activo=True).order_by(Comunicado.fecha_creacion.desc()).first()
        except Exception:
            # Evita errores si la tabla aún no existe (durante migraciones)
            pass
            
        return dict(comunicado_global=comunicado)


    # Ruta principal
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

        return render_template(
            'index.html',
            pagos_proximos=pagos_proximos,
            pagos_vencidos=pagos_vencidos,
            pagos_pagados=pagos_pagados
        )

    # Inicialización de roles
    with app.app_context():
        inicializar_roles()
        #crear_admin()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
from flask import redirect, url_for, render_template
from routes.clientes import clientes_bp
from routes.grupos import grupos_bp
from routes.prestamos_grupales import prestamos_grupales_bp
from routes.prestamos_individuales import prestamos_individuales_bp
from routes.pagos import pagos_bp
from routes.login import login_bp  # Importamos el blueprint de login
from routes.usuarios import usuarios_bp

def register_routes(app):
    app.register_blueprint(clientes_bp, url_prefix='/clientes')
    app.register_blueprint(grupos_bp, url_prefix='/grupos')
    app.register_blueprint(prestamos_grupales_bp, url_prefix='/prestamos_grupales')
    app.register_blueprint(prestamos_individuales_bp, url_prefix='/prestamos_individuales')
    app.register_blueprint(pagos_bp, url_prefix='/pagos')
    app.register_blueprint(login_bp, url_prefix='/')  # Registramos el blueprint del login
    app.register_blueprint(usuarios_bp, url_prefix='/admin')
    

    @app.route('/')
    def index():
        return render_template('base.html')

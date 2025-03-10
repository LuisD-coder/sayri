from flask import redirect, url_for, render_template
from routes.clientes import clientes_bp
from routes.grupos import grupos_bp
from routes.prestamos_grupales import prestamos_grupales_bp
from routes.prestamos_individuales import prestamos_individuales_bp

def register_routes(app):
    app.register_blueprint(clientes_bp, url_prefix='/clientes')
    app.register_blueprint(grupos_bp, url_prefix='/grupos')
    app.register_blueprint(prestamos_grupales_bp, url_prefix='/prestamos_grupales')
    app.register_blueprint(prestamos_individuales_bp, url_prefix='/prestamos_individuales')

    @app.route('/')
    def index():
        return render_template('base.html')

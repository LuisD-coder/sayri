from flask import redirect, url_for, render_template
from routes.clientes import clientes_bp
from routes.grupos import grupos_bp
from routes.prestamos_grupales import prestamos_grupales_bp
from routes.prestamos_individuales import prestamos_individuales_bp
from routes.pagos import pagos_bp
from routes.login import login_bp  
from routes.usuarios import usuarios_bp
from routes.base import base_bp  
from routes.reportes import reportes_bp

def register_routes(app):
    app.register_blueprint(clientes_bp, url_prefix='/clientes')
    app.register_blueprint(grupos_bp, url_prefix='/grupos')
    app.register_blueprint(prestamos_grupales_bp, url_prefix='/prestamos_grupales')
    app.register_blueprint(prestamos_individuales_bp, url_prefix='/prestamos_individuales')
    app.register_blueprint(pagos_bp, url_prefix='/pagos')
    app.register_blueprint(login_bp, url_prefix='/auth')  # Registramos el blueprint del login
    app.register_blueprint(usuarios_bp, url_prefix='/admin')
    app.register_blueprint(reportes_bp, url_prefix='/reportes')
    app.register_blueprint(base_bp)
    

    #@app.route('/')
    #def index():
    #    return render_template('base.html')

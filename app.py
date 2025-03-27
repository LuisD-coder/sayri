from flask import Flask
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager  # Importar LoginManager
from models import db, Usuario  # Asegúrate de importar tu modelo Usuario
from routes import register_routes
from utils import inicializar_roles, crear_admin  # Importamos la función

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
        return Usuario.query.get(int(user_id))  # Asegúrate de que estás obteniendo al usuario de la base de datos

    register_routes(app)

    # Ejecutar la inicialización de roles solo si es necesario
    with app.app_context():
        inicializar_roles()
        crear_admin()  # Crea un usuario admin si no existe

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

from flask import Flask, flash, redirect, url_for
from flask_migrate import Migrate
from config import Config
from models import db
from routes import register_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    register_routes(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
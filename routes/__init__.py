from flask import redirect, url_for, render_template

def register_routes(app):

    @app.route('/')
    def index():
        return render_template('base.html')

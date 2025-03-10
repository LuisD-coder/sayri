from models import db

class PrestamoIndividual(db.Model):
    __tablename__ = 'prestamoindividual'  # Nombre de la tabla en la base de datos
    id = db.Column(db.Integer, primary_key=True)
    prestamo_grupal_id = db.Column(db.Integer, db.ForeignKey('prestamogrupal.id'), nullable=False)  # Referencia correcta
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)

    pagos = db.relationship('Pago', backref='prestamo_individual', lazy=True)

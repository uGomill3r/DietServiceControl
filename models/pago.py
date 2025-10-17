from . import db

class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date)
    tipo = db.Column(db.String(20))
    monto = db.Column(db.Float)
    cantidad = db.Column(db.Integer)
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclos_pago.id'))

    def __repr__(self):
        return f"<Pago {self.fecha} | {self.tipo} x {self.monto}>"


class CicloPago(db.Model):
    __tablename__ = 'ciclos_pago'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'almuerzo' o 'cena'
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)  # se cierra al registrar el siguiente pago

    pagos = db.relationship('Pago', backref='ciclo', lazy=True)

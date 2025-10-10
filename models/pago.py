from . import db

class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date)
    tipo = db.Column(db.String(20))
    monto = db.Column(db.Float)
    cantidad = db.Column(db.Integer)

    def __repr__(self):
        return f"<Pago {self.fecha} | {self.tipo} x {self.monto}>"

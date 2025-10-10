from . import db

class Entrega(db.Model):
    __tablename__ = 'entregas'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, db.ForeignKey('pedidos.fecha'))
    entregado_almuerzo = db.Column(db.Integer)
    entregado_cena = db.Column(db.Integer)
    observaciones = db.Column(db.Text)

    pedido = db.relationship('Pedido', backref='entregas')

    def __repr__(self):
        return f"<Entrega {self.fecha} | Almuerzo: {self.entregado_almuerzo}, Cena: {self.entregado_cena}>"

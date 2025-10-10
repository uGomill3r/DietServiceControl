from . import db

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    fecha = db.Column(db.Date, primary_key=True)
    semana = db.Column(db.Integer)
    almuerzo = db.Column(db.Integer, default=1)
    cena = db.Column(db.Integer)
    feriado = db.Column(db.Boolean, default=False)
    entrada = db.Column(db.Text)
    fondo = db.Column(db.Text)
    plato_cena = db.Column(db.Text)
    observaciones = db.Column(db.Text)

    def __repr__(self):
        return f"<Pedido {self.fecha} | Almuerzo: {self.almuerzo}, Cena: {self.cena}>"

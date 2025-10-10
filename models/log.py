from . import db

class Log(db.Model):
    __tablename__ = 'log'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    accion = db.Column(db.String(100))
    detalle = db.Column(db.Text)

    def __repr__(self):
        return f"<Log {self.timestamp} | {self.accion}>"

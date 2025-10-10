from . import db

class Credencial(db.Model):
    __tablename__ = 'credenciales'
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True)
    contraseña = db.Column(db.String(100))
    actualizado = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Credencial {self.usuario}>"

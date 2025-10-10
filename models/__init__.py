from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .pedido import Pedido
from .entrega import Entrega
from .pago import Pago
from .log import Log
from .credencial import Credencial

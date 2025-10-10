from .auth import auth_bp
from .dashboard import dashboard_bp
from .semana import semana_bp
from .dia import dia_bp
from .pagos import pagos_bp
from .reportes import reportes_bp
from .log import log_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(semana_bp)
    app.register_blueprint(dia_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(log_bp)

import os
from dotenv import load_dotenv

# Carga el entorno desde la variable DOTENV_PATH o por defecto .env
# Ejemplo:
# export FLASK_APP=app.py
# export FLASK_ENV=production
# export DOTENV_PATH=.env.prod

load_dotenv(dotenv_path=os.getenv("DOTENV_PATH", ".env"), override=True)

from flask import Flask
from config import DevelopmentConfig, TestingConfig, ProductionConfig
from models import db
from flask_migrate import Migrate
from blueprints import register_blueprints

def create_app():
    app = Flask(__name__)

    env = os.getenv("FLASK_ENV", "production")
    if env == "development":
        app.config.from_object(DevelopmentConfig)
    elif env == "testing":
        app.config.from_object(TestingConfig)
    else:
        app.config.from_object(ProductionConfig)

    db.init_app(app)
    Migrate(app, db)
    register_blueprints(app)

    return app

app = create_app()

# Depuración
print("Entorno:", os.getenv("FLASK_ENV"))
print("Archivo de entorno:", os.getenv("DOTENV_PATH"))
print("DB conectada:", app.config["SQLALCHEMY_DATABASE_URI"])

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)

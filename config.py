import os

def build_uri():
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"

class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-por-defecto")

class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = build_uri()

class TestingConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = build_uri()
    TESTING = True

class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = build_uri()

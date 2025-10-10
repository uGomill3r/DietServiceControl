from flask_sqlalchemy import SQLAlchemy
import psycopg2
from config import build_uri  # reutiliza tu constructor editorial

db = SQLAlchemy()

def get_connection():
    uri = build_uri()
    print("🔗 Conectando con URI:", uri)
    return psycopg2.connect(uri)

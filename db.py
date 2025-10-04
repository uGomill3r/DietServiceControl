# db.py
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def get_connection():
    db_name = os.environ['DB_NAME']
    db_user = os.environ['DB_USER']
    db_password = os.environ['DB_PASSWORD']
    db_host = os.environ['DB_HOST']
    db_port = os.environ.get('DB_PORT', '5432')  # usa 5432 por defecto

    conn_str = f"dbname={db_name} user={db_user} password={db_password} host={db_host} port={db_port} sslmode=require"
    return psycopg2.connect(conn_str)

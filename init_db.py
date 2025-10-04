import sqlite3
from datetime import datetime

DB_NAME = 'dietservice.db'

# Lista de feriados iniciales
feriados_iniciales = [
    '2025-10-08',
    '2025-12-25',
    '2026-01-01'
]

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Crear tablas
cursor.execute('''
CREATE TABLE IF NOT EXISTS pagos (
    fecha TEXT,
    monto REAL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS pedidos (
    fecha TEXT,
    semana INTEGER,
    almuerzo INTEGER DEFAULT 1,
    cena INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS entregas (
    fecha TEXT,
    entregado_almuerzo INTEGER,
    entregado_cena INTEGER,
    observaciones TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS feriados (
    fecha TEXT PRIMARY KEY
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS log (
    timestamp TEXT,
    accion TEXT,
    detalle TEXT
)
''')

# Poblar feriados
for fecha in feriados_iniciales:
    cursor.execute("INSERT OR IGNORE INTO feriados (fecha) VALUES (?)", (fecha,))

# Registrar acción en changelog
cursor.execute("INSERT INTO log (timestamp, accion, detalle) VALUES (?, ?, ?)",
               (datetime.now().isoformat(), 'Inicialización', 'Base de datos creada y feriados cargados'))

conn.commit()
conn.close()

print("Base de datos dietservice.db inicializada correctamente.")

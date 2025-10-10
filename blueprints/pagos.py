from flask import Blueprint, render_template, request, redirect
from db import get_connection
from datetime import datetime
from utils import formatear_fecha
from decoradores import protegido

pagos_bp = Blueprint('pagos', __name__)

@pagos_bp.route('/pagos', methods=['GET', 'POST'])
@protegido
def pagos():
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        fecha_form = request.form['fecha']
        fecha_iso = request.form['fecha']
        tipo = request.form['tipo']
        monto = float(request.form['monto'])
        cantidad = int(request.form['cantidad'])

        cursor.execute("INSERT INTO pagos (fecha, tipo, monto, cantidad) VALUES (%s, %s, %s, %s)",
                       (fecha_iso, tipo, monto, cantidad))

        detalle = f"{fecha_form} | {tipo} x {monto}"
        cursor.execute("INSERT INTO log (timestamp, accion, detalle) VALUES (%s, %s, %s)",
                       (datetime.now().isoformat(), 'Pago registrado', detalle))

        conn.commit()
        return redirect('/pagos')

    cursor.execute("SELECT fecha, tipo, monto FROM pagos ORDER BY fecha DESC")
    pagos_raw = cursor.fetchall()
    pagos = [(formatear_fecha(p[0]), p[1], p[2]) for p in pagos_raw]

    cursor.execute("SELECT tipo, SUM(monto) FROM pagos GROUP BY tipo")
    totales = dict(cursor.fetchall())

    cursor.close()
    conn.close()
    return render_template('pagos.html',
                           pagos=pagos,
                           totales=totales)

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
        fecha_iso = request.form['fecha']
        tipo = request.form['tipo']
        monto = float(request.form['monto'])
        cantidad = int(request.form['cantidad'])

        # Verificar si hay ciclo abierto para el tipo
        cursor.execute("""
            SELECT id, fecha_inicio
            FROM ciclos_pago
            WHERE tipo = %s AND fecha_fin IS NULL
            ORDER BY fecha_inicio DESC LIMIT 1
        """, (tipo,))
        ciclo_abierto = cursor.fetchone()

        cerrar_ciclo = False
        if ciclo_abierto:
            ciclo_id_anterior, fecha_inicio_anterior = ciclo_abierto
            if fecha_iso > fecha_inicio_anterior.isoformat():
                cerrar_ciclo = True

        if cerrar_ciclo:
            # Buscar último pedido dentro del ciclo abierto
            cursor.execute(f"""
                SELECT MAX(fecha)
                FROM pedidos
                WHERE {tipo} > 0 AND fecha >= %s AND fecha < %s
            """, (fecha_inicio_anterior, fecha_iso))
            fecha_ultimo_pedido = cursor.fetchone()[0] or fecha_iso
            cursor.execute("""
                UPDATE ciclos_pago
                SET fecha_fin = %s
                WHERE id = %s
            """, (fecha_ultimo_pedido, ciclo_id_anterior))

        # Crear nuevo ciclo
        cursor.execute("""
            INSERT INTO ciclos_pago (tipo, fecha_inicio)
            VALUES (%s, %s)
            RETURNING id
        """, (tipo, fecha_iso))
        nuevo_ciclo_id = cursor.fetchone()[0]

        # Registrar pago asociado al nuevo ciclo
        cursor.execute("""
            INSERT INTO pagos (fecha, tipo, monto, cantidad, ciclo_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (fecha_iso, tipo, monto, cantidad, nuevo_ciclo_id))

        detalle = f"{fecha_iso} | {tipo} x {monto} (ciclo {nuevo_ciclo_id})"
        cursor.execute("INSERT INTO log (timestamp, accion, detalle) VALUES (%s, %s, %s)",
                       (datetime.now().isoformat(), 'Pago registrado', detalle))

        conn.commit()
        return redirect('/pagos')

    # Mostrar pagos con ciclo asociado
    cursor.execute("""
        SELECT p.id, p.fecha, p.tipo, p.monto, c.fecha_inicio
        FROM pagos p
        LEFT JOIN ciclos_pago c ON p.ciclo_id = c.id
        ORDER BY p.fecha DESC
    """)
    pagos_raw = cursor.fetchall()
    pagos = [
        (p[0], formatear_fecha(p[1]), p[2], p[3], formatear_fecha(p[4]) if p[4] else "—")
        for p in pagos_raw
    ]

    cursor.execute("SELECT tipo, SUM(monto) FROM pagos GROUP BY tipo")
    totales = dict(cursor.fetchall())

    cursor.close()
    conn.close()
    return render_template('pagos.html',
                           pagos=pagos,
                           totales=totales)


@pagos_bp.route('/pagos/editar/<int:id>', methods=['GET', 'POST'])
@protegido
def editar_pago(id):
    conn = get_connection()
    cursor = conn.cursor()

    # Obtener ciclos disponibles
    cursor.execute("SELECT id, tipo, fecha_inicio FROM ciclos_pago ORDER BY fecha_inicio DESC")
    ciclos_raw = cursor.fetchall()
    ciclos = [(c[0], f"{c[1].capitalize()} desde {formatear_fecha(c[2])}") for c in ciclos_raw]

    if request.method == 'POST':
        nueva_fecha = request.form['fecha']
        nuevo_tipo = request.form['tipo']
        nuevo_monto = float(request.form['monto'])
        nueva_cantidad = int(request.form['cantidad'])

        # Obtener datos originales del pago
        cursor.execute("SELECT fecha, tipo, ciclo_id FROM pagos WHERE id = %s", (id,))
        original = cursor.fetchone()
        fecha_original, tipo_original, ciclo_id_original = original

        # Si tipo o fecha cambian, cerrar ciclo anterior si está abierto
        if tipo_original != nuevo_tipo or fecha_original != nueva_fecha:
            # Verificar si el ciclo anterior está abierto
            cursor.execute("""
                SELECT fecha_fin FROM ciclos_pago WHERE id = %s
            """, (ciclo_id_original,))
            ciclo_anterior = cursor.fetchone()
            if ciclo_anterior and ciclo_anterior[0] is None:
                # Buscar último pedido del tipo original
                cursor.execute(f"""
                    SELECT MAX(fecha)
                    FROM pedidos
                    WHERE {tipo_original} > 0
                """)
                fecha_ultimo_pedido = cursor.fetchone()[0] or fecha_original
                # Cerrar ciclo anterior
                cursor.execute("""
                    UPDATE ciclos_pago
                    SET fecha_fin = %s
                    WHERE id = %s
                """, (fecha_ultimo_pedido, ciclo_id_original))

        # Verificar si hay ciclo abierto para el nuevo tipo
        cursor.execute("""
            SELECT id FROM ciclos_pago
            WHERE tipo = %s AND fecha_fin IS NULL
            ORDER BY fecha_inicio DESC LIMIT 1
        """, (nuevo_tipo,))
        ciclo_abierto = cursor.fetchone()

        if ciclo_abierto:
            nuevo_ciclo_id = ciclo_abierto[0]
        else:
            # Crear nuevo ciclo
            cursor.execute("""
                INSERT INTO ciclos_pago (tipo, fecha_inicio)
                VALUES (%s, %s)
                RETURNING id
            """, (nuevo_tipo, nueva_fecha))
            nuevo_ciclo_id = cursor.fetchone()[0]

        # Actualizar pago
        cursor.execute("""
            UPDATE pagos
            SET fecha = %s, tipo = %s, monto = %s, cantidad = %s, ciclo_id = %s
            WHERE id = %s
        """, (nueva_fecha, nuevo_tipo, nuevo_monto, nueva_cantidad, nuevo_ciclo_id, id))

        detalle = f"Editado pago {id}: {nueva_fecha} | {nuevo_tipo} x {nuevo_monto} (ciclo {nuevo_ciclo_id})"
        cursor.execute("INSERT INTO log (timestamp, accion, detalle) VALUES (%s, %s, %s)",
                       (datetime.now().isoformat(), 'Pago editado', detalle))

        conn.commit()
        return redirect('/pagos')

    # Obtener datos del pago
    cursor.execute("SELECT fecha, tipo, monto, cantidad, ciclo_id FROM pagos WHERE id = %s", (id,))
    pago = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('editar_pago.html',
                           pago=pago,
                           pago_id=id,
                           ciclos=ciclos)

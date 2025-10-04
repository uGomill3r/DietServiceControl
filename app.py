from flask import Flask, render_template, request, redirect
from datetime import datetime, timedelta
import csv, re
from db import get_connection

app = Flask(__name__)

# Archivos
LOG = 'changelog/log.md'

# Utilidades
def obtener_fechas_semana(numero_semana, año=datetime.now().year):
    lunes = datetime.strptime(f'{año}-W{int(numero_semana)}-1', "%Y-W%W-%w")
    dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie']
    fechas = [(lunes + timedelta(days=i)).strftime('%d-%m-%Y') for i in range(5)]
    return dias, fechas


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pagos', methods=['GET', 'POST'])
def pagos():
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        fecha_form = request.form['fecha']  # dd-mm-aaaa
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

    # Mostrar pagos anteriores
    cursor.execute("SELECT fecha, tipo, monto FROM pagos ORDER BY fecha DESC")
    pagos_raw = cursor.fetchall()
    pagos = [(datetime.strptime(p[0], "%Y-%m-%d").strftime("%d-%m-%Y"), p[1], p[2]) for p in pagos_raw]

    # Totales por tipo
    cursor.execute("SELECT tipo, SUM(monto) FROM pagos GROUP BY tipo")
    totales = dict(cursor.fetchall())

    cursor.close()
    conn.close()
    return render_template('pagos.html',
                           pagos=pagos,
                           totales=totales)

@app.route('/planificar', methods=['GET', 'POST'])
def planificar():
    conn = get_connection()
    cursor = conn.cursor()

    # Calcular semana actual desde GET o POST
    if request.method == 'POST':
        semana_actual = int(request.form['semana'])
    else:
        semana_actual = int(request.args.get('semana', datetime.now().isocalendar().week))

    dias, fechas = obtener_fechas_semana(semana_actual)  # dd-mm-aaaa
    feriados = set(row[0] for row in cursor.execute("SELECT fecha FROM feriados").fetchall())

    if request.method == 'POST':
        for i in range(5):
            fecha_form = request.form[f'fecha{i}']  # dd-mm-aaaa
            fecha_iso = datetime.strptime(fecha_form, "%d-%m-%Y").strftime("%Y-%m-%d")
            almuerzo = 1 if request.form.get(f'almuerzo{i}') == 'on' else 0
            cena = 1 if request.form.get(f'cena{i}') == 'on' else 0
            if fecha_iso not in feriados:
                cursor.execute("INSERT INTO pedidos (fecha, semana, almuerzo, cena) VALUES (%s, %s, %s, %s)",
                               (fecha_iso, semana_actual, almuerzo, cena))
                cursor.execute("INSERT INTO log (timestamp, accion, detalle) VALUES (%s, %s, %s)",
                               (datetime.now().isoformat(), 'Pedido', f'{fecha_form} | A:{almuerzo} C:{cena}'))
        conn.commit()

    # Obtener pedidos guardados para esa semana
    cursor.execute("SELECT fecha, almuerzo, cena FROM pedidos WHERE semana = %s", (semana_actual,))
    pedidos_guardados = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    cursor.close()
    conn.close()
    return render_template('planificar.html',
                           semana=semana_actual,
                           dias=dias,
                           fechas=fechas,
                           pedidos_guardados=pedidos_guardados)

@app.route('/planificar_editar', methods=['GET', 'POST'])
def planificar_editar():
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        fecha_form = request.form['fecha']  # dd-mm-aaaa
        fecha_iso = datetime.strptime(fecha_form, "%d-%m-%Y").strftime("%Y-%m-%d")
        almuerzo = 1 if request.form.get('almuerzo') == 'on' else 0
        cena = 1 if request.form.get('cena') == 'on' else 0

        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE fecha = %s", (fecha_iso,))
        existe = cursor.fetchone()[0]

        if existe:
            cursor.execute("""
                UPDATE pedidos
                SET almuerzo = %s, cena = %s
                WHERE fecha = %s
            """, (almuerzo, cena, fecha_iso))
            accion = "Pedido editado"
        else:
            semana = datetime.strptime(fecha_iso, "%Y-%m-%d").isocalendar().week
            cursor.execute("""
                INSERT INTO pedidos (fecha, semana, almuerzo, cena)
                VALUES (%s, %s, %s, %s)
            """, (fecha_iso, semana, almuerzo, cena))
            accion = "Pedido registrado"

        detalle = f"{fecha_form} | A:{almuerzo} C:{cena}"
        cursor.execute("INSERT INTO log (timestamp, accion, detalle) VALUES (%s, %s, %s)",
                       (datetime.now().isoformat(), accion, detalle))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/planificar_editar')

    # GET: mostrar pedidos existentes
    cursor.execute("SELECT fecha, almuerzo, cena FROM pedidos ORDER BY fecha DESC")
    pedidos_raw = cursor.fetchall()
    pedidos = [(datetime.strptime(p[0], "%Y-%m-%d").strftime("%d-%m-%Y"), p[1], p[2]) for p in pedidos_raw]

    cursor.close()
    conn.close()
    return render_template('planificar_editar.html', pedidos=pedidos)

@app.route('/entregas', methods=['GET', 'POST'])
def entregas():
    conn = get_connection()
    cursor = conn.cursor()

    # Día actual o recibido por GET
    fecha_form = request.args.get('fecha')
    if fecha_form:
        fecha_iso = datetime.strptime(fecha_form, "%d-%m-%Y").strftime("%Y-%m-%d")
    else:
        hoy = datetime.now()
        fecha_iso = hoy.strftime("%Y-%m-%d")
        fecha_form = hoy.strftime("%d-%m-%Y")

    # Validar si es sábado (5) o domingo (6)
    dia_semana = datetime.strptime(fecha_iso, "%Y-%m-%d").weekday()
    bloqueado = dia_semana >= 5

    if request.method == 'POST' and not bloqueado:
        fecha_form = request.form['fecha']
        fecha_iso = datetime.strptime(fecha_form, "%d-%m-%Y").strftime("%Y-%m-%d")

        entregado_almuerzo = 1 if request.form.get('entregado_almuerzo') == 'on' else 0
        entregado_cena = 1 if request.form.get('entregado_cena') == 'on' else 0
        observaciones = request.form['observaciones']

        cursor.execute("SELECT COUNT(*) FROM entregas WHERE fecha = %s", (fecha_iso,))
        existe = cursor.fetchone()[0]

        if existe:
            cursor.execute("""
                UPDATE entregas
                SET entregado_almuerzo = %s, entregado_cena = %s, observaciones = %s
                WHERE fecha = %s
            """, (entregado_almuerzo, entregado_cena, observaciones, fecha_iso))
            accion = "Entrega editada"
        else:
            cursor.execute("""
                INSERT INTO entregas (fecha, entregado_almuerzo, entregado_cena, observaciones)
                VALUES (%s, %s, %s, %s)
            """, (fecha_iso, entregado_almuerzo, entregado_cena, observaciones))
            accion = "Entrega registrada"

        detalle = f"{fecha_form} | A:{entregado_almuerzo} C:{entregado_cena} | Obs:{observaciones}"
        cursor.execute("INSERT INTO log (timestamp, accion, detalle) VALUES (%s, %s, %s)",
                       (datetime.now().isoformat(), accion, detalle))
        cursor.close()
        conn.commit()
        return redirect(f'/entregas?fecha={fecha_form}')

    # Obtener entrega registrada (si existe)
    entrega = (0, 0, '')
    pedido = (0, 0)

    if not bloqueado:
        cursor.execute("SELECT entregado_almuerzo, entregado_cena, observaciones FROM entregas WHERE fecha = %s", (fecha_iso,))
        entrega = cursor.fetchone() or (0, 0, '')

        cursor.execute("SELECT almuerzo, cena FROM pedidos WHERE fecha = %s", (fecha_iso,))
        pedido = cursor.fetchone() or (0, 0)

    actual_dt = datetime.strptime(fecha_iso, "%Y-%m-%d")

    # Día anterior hábil
    anterior_dt = actual_dt - timedelta(days=1)
    while anterior_dt.weekday() >= 5:
        anterior_dt -= timedelta(days=1)
    anterior_form = anterior_dt.strftime("%d-%m-%Y")

    # Día siguiente hábil
    siguiente_dt = actual_dt + timedelta(days=1)
    while siguiente_dt.weekday() >= 5:
        siguiente_dt += timedelta(days=1)
    siguiente_form = siguiente_dt.strftime("%d-%m-%Y")

    cursor.close()
    conn.close()
    return render_template('entregas.html',
                           fecha=fecha_form,
                           entrega=entrega,
                           pedido=pedido,
                           bloqueado=bloqueado,
                           anterior=anterior_form,
                           siguiente=siguiente_form)

@app.route('/entregas_editar', methods=['GET', 'POST'])
def entregas_editar():
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        fecha_form = request.form['fecha']  # dd-mm-aaaa
        fecha_iso = datetime.strptime(fecha_form, "%d-%m-%Y").strftime("%Y-%m-%d")
        entregado_almuerzo = 1 if request.form.get('entregado_almuerzo') == 'on' else 0
        entregado_cena = 1 if request.form.get('entregado_cena') == 'on' else 0
        observaciones = request.form['observaciones']

        cursor.execute("SELECT COUNT(*) FROM entregas WHERE fecha = %s", (fecha_iso,))
        existe = cursor.fetchone()[0]

        if existe:
            cursor.execute("""
                UPDATE entregas
                SET entregado_almuerzo = %s, entregado_cena = %s, observaciones = %s
                WHERE fecha = %s
            """, (entregado_almuerzo, entregado_cena, observaciones, fecha_iso))
            accion = "Entrega editada"
        else:
            cursor.execute("""
                INSERT INTO entregas (fecha, entregado_almuerzo, entregado_cena, observaciones)
                VALUES (%s, %s, %s, %s)
            """, (fecha_iso, entregado_almuerzo, entregado_cena, observaciones))
            accion = "Entrega registrada"

        detalle = f"{fecha_form} | A:{entregado_almuerzo} C:{entregado_cena} | Obs:{observaciones}"
        cursor.execute("INSERT INTO log (timestamp, accion, detalle) VALUES (%s, %s, %s)",
                       (datetime.now().isoformat(), accion, detalle))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/entregas_editar')

    # GET: mostrar entregas existentes
    cursor.execute("SELECT fecha, entregado_almuerzo, entregado_cena, observaciones FROM entregas ORDER BY fecha DESC")
    entregas_raw = cursor.fetchall()
    entregas = [(datetime.strptime(e[0], "%Y-%m-%d").strftime("%d-%m-%Y"), e[1], e[2], e[3]) for e in entregas_raw]

    cursor.close()
    conn.close()
    return render_template('entregas_editar.html', entregas=entregas)

@app.route('/entregas_pendientes')
def entregas_pendientes():
    conn = get_connection()
    cursor = conn.cursor()

    hoy_iso = datetime.now().strftime("%Y-%m-%d")

    # Obtener todos los pedidos hasta hoy
    cursor.execute("""
        SELECT fecha, almuerzo, cena
        FROM pedidos
        WHERE fecha <= %s
        ORDER BY fecha ASC
    """, (hoy_iso,))
    pedidos = cursor.fetchall()

    # Obtener entregas registradas
    cursor.execute("SELECT fecha, entregado_almuerzo, entregado_cena FROM entregas")
    entregas = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    pendientes = []
    for fecha_iso, a_pedido, c_pedido in pedidos:
        a_entregado, c_entregado = entregas.get(fecha_iso, (0, 0))
        if (a_pedido and not a_entregado) or (c_pedido and not c_entregado):
            fecha_fmt = datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d-%m-%Y")
            pendientes.append((fecha_fmt, a_pedido, c_pedido, a_entregado, c_entregado))

    cursor.close()
    conn.close()
    return render_template('entregas_pendientes.html', pendientes=pendientes)

@app.route('/dashboard')
def dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    # Todos los pedidos
    cursor.execute("SELECT fecha, almuerzo, cena FROM pedidos")
    pedidos_raw = cursor.fetchall()

    # Todas las entregas
    cursor.execute("SELECT fecha, entregado_almuerzo, entregado_cena FROM entregas")
    entregas = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    hoy_iso = datetime.now().strftime("%Y-%m-%d")

    alm_por_entregar = 0
    cen_por_entregar = 0

    for fecha_iso, a_pedido, c_pedido in pedidos_raw:
        if fecha_iso >= hoy_iso:
            a_entregado, c_entregado = entregas.get(fecha_iso, (0, 0))
            if a_pedido and not a_entregado:
                alm_por_entregar += 1
            if c_pedido and not c_entregado:
                cen_por_entregar += 1

    # Pagos acumulados
    cursor.execute("SELECT tipo, SUM(cantidad) FROM pagos GROUP BY tipo")
    pagos_raw = dict(cursor.fetchall())
    alm_pagados = pagos_raw.get('almuerzo', 0)
    cen_pagados = pagos_raw.get('cena', 0)

    # Último pago
    cursor.execute("SELECT fecha FROM pagos ORDER BY fecha DESC LIMIT 1")
    ultimo_pago = cursor.fetchone()
    fecha_ultimo_pago = datetime.strptime(ultimo_pago[0], "%Y-%m-%d").strftime("%d-%m-%Y") if ultimo_pago else "—"

    # Totales
    alm_pedidos = sum(p[1] for p in pedidos_raw)
    cen_pedidos = sum(p[2] for p in pedidos_raw)
    alm_entregados = sum(entregas.get(p[0], (0, 0))[0] for p in pedidos_raw)
    cen_entregados = sum(entregas.get(p[0], (0, 0))[1] for p in pedidos_raw)

    alm_saldo = alm_pagados - alm_entregados - alm_por_entregar
    cen_saldo = cen_pagados - cen_entregados - cen_por_entregar

    errores = []
    for p in pedidos_raw:
        fecha_iso, a_pedido, c_pedido = p
        fecha_fmt = datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d-%m-%Y")
        a_entregado, c_entregado = entregas.get(fecha_iso, (0, 0))
        if a_pedido and not a_entregado:
            errores.append(f"{fecha_fmt}: Almuerzo pedido no entregado")
        if c_pedido and not c_entregado:
            errores.append(f"{fecha_fmt}: Cena pedida no entregada")
        if a_entregado and not a_pedido:
            errores.append(f"{fecha_fmt}: Almuerzo entregado sin pedido")
        if c_entregado and not c_pedido:
            errores.append(f"{fecha_fmt}: Cena entregada sin pedido")

    cursor.close()
    conn.close()

    return render_template('dashboard.html',
                           alm_pagados=alm_pagados,
                           cen_pagados=cen_pagados,
                           alm_pedidos=alm_pedidos,
                           cen_pedidos=cen_pedidos,
                           alm_entregados=alm_entregados,
                           cen_entregados=cen_entregados,
                           alm_por_entregar=alm_por_entregar,
                           cen_por_entregar=cen_por_entregar,
                           alm_saldo=alm_saldo,
                           cen_saldo=cen_saldo,
                           fecha_ultimo_pago=fecha_ultimo_pago,
                           errores=errores
                           )

@app.route('/log')
def log():
    with open(LOG) as f:
        contenido = f.read()

    # Reemplazar fechas ISO por dd-mm-aaaa
    contenido = re.sub(r'(\d{4})-(\d{2})-(\d{2})', r'\3-\2-\1', contenido)

    return render_template('log.html', contenido=contenido)

@app.route('/log_exportado', methods=['GET'])
def log_exportado():
    desde_form = request.args.get('desde')  # dd-mm-aaaa
    hasta_form = request.args.get('hasta')  # dd-mm-aaaa

    conn = get_connection()
    cursor = conn.cursor()

    if desde_form and hasta_form:
        # Convertir a formato ISO para la consulta
        desde_iso = datetime.strptime(desde_form, "%d-%m-%Y").strftime("%Y-%m-%d")
        hasta_iso = datetime.strptime(hasta_form, "%d-%m-%Y").strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT timestamp, accion, detalle
            FROM log
            WHERE DATE(timestamp) BETWEEN %s AND %s
            ORDER BY timestamp ASC
        """, (desde_iso, hasta_iso))
        registros_raw = cursor.fetchall()

        # Convertir timestamp a formato legible
        registros = [
            (datetime.strptime(r[0], "%Y-%m-%dT%H:%M:%S.%f").strftime("%d-%m-%Y %H:%M:%S"), r[1], r[2])
            for r in registros_raw
        ]
    else:
        registros = []

    cursor.close()
    conn.close()
    return render_template('log_exportado.html',
                           registros=registros,
                           desde=desde_form,
                           hasta=hasta_form)

if __name__ == '__main__':
    app.run(debug=True)

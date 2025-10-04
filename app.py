from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, date, timedelta
from collections import defaultdict
import re
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

def normalizar_fecha(fecha):
    if isinstance(fecha, date):
        return fecha
    if isinstance(fecha, datetime):
        return fecha.date()
    if isinstance(fecha, str):
        try:
            return datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Fecha en formato incorrecto para normalizar_fecha: {fecha}")
    raise ValueError(f"Tipo de fecha no reconocido: {type(fecha)}")

def formatear_fecha(fecha):
    """
    Convierte una fecha en str o datetime a formato dd-mm-aaaa para visualización.
    """
    fecha_date = normalizar_fecha(fecha)
    return fecha_date.strftime("%d-%m-%Y")

def normalizar_fecha_ddmmaaaa(fecha_str):
    """
    Convierte una fecha en formato dd-mm-aaaa a objeto date.
    """
    return datetime.strptime(fecha_str, "%d-%m-%Y").date()

def estado_textual(fecha_obj, pedido, entrega, feriado):
    if feriado:
        return "Feriado"
    if pedido == (0, 0):
        return "Sin pedido registrado"

    a_pedido, c_pedido = pedido
    a_entregado, c_entregado = entrega

    pendientes = []
    if a_pedido and not a_entregado:
        pendientes.append("almuerzo")
    if c_pedido and not c_entregado:
        pendientes.append("cena")

    if pendientes and fecha_obj < datetime.now().date():
        return f"Entrega pendiente: {', '.join(pendientes)}"
    if not pendientes:
        return "Entregado"

    return ""

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/semana', methods=['GET'])
def vista_semanal():
    def fecha_iso(fecha):
        return normalizar_fecha(fecha).strftime("%Y-%m-%d")

    def clave_fecha(fecha):
        return normalizar_fecha(fecha)

    conn = get_connection()
    cursor = conn.cursor()

    semana_actual = int(request.args.get('semana', datetime.now().isocalendar().week))
    dias, fechas = obtener_fechas_semana(semana_actual)

    # Pedidos por fecha (incluye feriado)
    fecha_inicio = normalizar_fecha_ddmmaaaa(fechas[0]).strftime("%Y-%m-%d")
    fecha_fin = normalizar_fecha_ddmmaaaa(fechas[-1]).strftime("%Y-%m-%d")
    cursor.execute("SELECT fecha, almuerzo, cena, feriado FROM pedidos WHERE fecha BETWEEN %s AND %s",
                   (fecha_inicio, fecha_fin))
    pedidos_raw = cursor.fetchall()
    pedidos = {}
    for row in pedidos_raw:
        fecha = normalizar_fecha(row[0])  # clave consistente con fechas
        pedidos[fecha] = {
            'almuerzo': row[1],
            'cena': row[2],
            'feriado': row[3]
        }

    # Entregas por fecha
    cursor.execute("SELECT fecha, entregado_almuerzo, entregado_cena FROM entregas")
    entregas = {normalizar_fecha(row[0]): (row[1], row[2]) for row in cursor.fetchall()}

    semana_data = []
    hoy = datetime.now().date()

    for i, fecha_str in enumerate(fechas):
        fecha_obj = normalizar_fecha_ddmmaaaa(fecha_str)

        pedido = pedidos.get(fecha_obj, {'almuerzo': 0, 'cena': 0, 'feriado': False})
        entrega = entregas.get(fecha_obj, (0, 0))

        estado = {}
        for comida, p, e in zip(['almuerzo', 'cena'], [pedido['almuerzo'], pedido['cena']], entrega):
            if p == 0:
                color = 'light'
            elif e == 1:
                color = 'success'
            elif fecha_obj < hoy:
                color = 'danger'
            else:
                color = 'warning'
            estado[comida] = color

        texto_estado = estado_textual(fecha_obj, (pedido['almuerzo'], pedido['cena']), entrega, pedido['feriado'])

        semana_data.append({
            'dia': dias[i],
            'fecha': fecha_str,
            'estado': estado,
            'feriado': pedido['feriado'],
            'texto_estado': texto_estado
        })

    cursor.close()
    conn.close()
    return render_template('semana.html',
                           semana=semana_actual,
                           semana_data=semana_data)

@app.route('/editar_dia', methods=['GET', 'POST'])
def editar_dia():
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        fecha_form = request.form['fecha']
        fecha_iso = datetime.strptime(fecha_form, "%d-%m-%Y").strftime("%Y-%m-%d")

        almuerzo = 1 if request.form.get('almuerzo') == 'on' else 0
        cena = 1 if request.form.get('cena') == 'on' else 0
        obs_pedido = request.form.get('obs_pedido', '')

        entregado_almuerzo = 1 if request.form.get('entregado_almuerzo') == 'on' else 0
        entregado_cena = 1 if request.form.get('entregado_cena') == 'on' else 0
        obs_entrega = request.form.get('obs_entrega', '')

        feriado = request.form.get('feriado') == 'on'

        # Pedido
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE fecha = %s", (fecha_iso,))
        if cursor.fetchone()[0]:
            cursor.execute("UPDATE pedidos SET almuerzo = %s, cena = %s, feriado = %s WHERE fecha = %s",
                           (almuerzo, cena, feriado, fecha_iso))
        else:
            semana = normalizar_fecha(fecha_iso).isocalendar().week
            cursor.execute("INSERT INTO pedidos (fecha, semana, almuerzo, cena, feriado) VALUES (%s, %s, %s, %s, %s)",
                           (fecha_iso, semana, almuerzo, cena, feriado))
            print (f"Feriado activado para {fecha_form}")

        # Entrega
        cursor.execute("SELECT COUNT(*) FROM entregas WHERE fecha = %s", (fecha_iso,))
        if cursor.fetchone()[0]:
            cursor.execute("UPDATE entregas SET entregado_almuerzo = %s, entregado_cena = %s, observaciones = %s WHERE fecha = %s",
                           (entregado_almuerzo, entregado_cena, obs_entrega, fecha_iso))
        else:
            cursor.execute("INSERT INTO entregas (fecha, entregado_almuerzo, entregado_cena, observaciones) VALUES (%s, %s, %s, %s)",
                           (fecha_iso, entregado_almuerzo, entregado_cena, obs_entrega))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/semana')

    # GET
    fecha_form = request.args.get('fecha')
    fecha_iso = datetime.strptime(fecha_form, "%d-%m-%Y").strftime("%Y-%m-%d")

    cursor.execute("SELECT almuerzo, cena, feriado FROM pedidos WHERE fecha = %s", (fecha_iso,))
    row = cursor.fetchone()
    if row:
        pedido = (row[0], row[1])
        feriado = row[2]
    else:
        pedido = (0, 0)
        feriado = False

    cursor.execute("SELECT entregado_almuerzo, entregado_cena, observaciones FROM entregas WHERE fecha = %s", (fecha_iso,))
    entrega = cursor.fetchone() or (0, 0, '')

    cursor.close()
    conn.close()
    return render_template('editar_dia.html',
                           fecha=fecha_form,
                           pedido=pedido,
                           entrega=entrega,
                           feriado=feriado)

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
    pagos = [(formatear_fecha(p[0]), p[1], p[2]) for p in pagos_raw]

    # Totales por tipo
    cursor.execute("SELECT tipo, SUM(monto) FROM pagos GROUP BY tipo")
    totales = dict(cursor.fetchall())

    cursor.close()
    conn.close()
    return render_template('pagos.html',
                           pagos=pagos,
                           totales=totales)

@app.route('/dashboard')
def dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    # Todos los pedidos
    cursor.execute("SELECT fecha, almuerzo, cena FROM pedidos")
    pedidos_raw = cursor.fetchall()

    # Todas las entregas
    cursor.execute("SELECT fecha, entregado_almuerzo, entregado_cena FROM entregas")
    entregas_raw = cursor.fetchall()
    entregas = {normalizar_fecha(row[0]): (row[1], row[2]) for row in entregas_raw}

    hoy_date = datetime.now().date()

    alm_por_entregar = 0
    cen_por_entregar = 0

    for fecha_iso, a_pedido, c_pedido in pedidos_raw:
        fecha_date = normalizar_fecha(fecha_iso)
        if fecha_date >= hoy_date:
            a_entregado, c_entregado = entregas.get(fecha_date, (0, 0))
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
    fecha_ultimo_pago = formatear_fecha(ultimo_pago[0]) if ultimo_pago else "—"

    # Totales
    alm_pedidos = sum(p[1] for p in pedidos_raw)
    cen_pedidos = sum(p[2] for p in pedidos_raw)
    alm_entregados = sum(entregas.get(normalizar_fecha(p[0]), (0, 0))[0] for p in pedidos_raw)
    cen_entregados = sum(entregas.get(normalizar_fecha(p[0]), (0, 0))[1] for p in pedidos_raw)

    alm_saldo = alm_pagados - alm_entregados - alm_por_entregar
    cen_saldo = cen_pagados - cen_entregados - cen_por_entregar

    errores_pendientes = defaultdict(list)
    errores_inconsistencias = defaultdict(list)

    for fecha_iso, a_pedido, c_pedido in pedidos_raw:
        fecha_date = normalizar_fecha(fecha_iso)
        fecha_fmt = formatear_fecha(fecha_date)
        a_entregado, c_entregado = entregas.get(fecha_date, (0, 0))

        if a_pedido and not a_entregado:
            if fecha_date >= hoy_date:
                errores_pendientes[fecha_fmt].append('almuerzo')
            else:
                errores_inconsistencias[fecha_fmt].append('almuerzo')
        if c_pedido and not c_entregado:
            if fecha_date >= hoy_date:
                errores_pendientes[fecha_fmt].append('cena')
            else:
                errores_inconsistencias[fecha_fmt].append('cena')

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
                           errores_pendientes=errores_pendientes,
                           errores_inconsistencias=errores_inconsistencias)

@app.route('/log')
def log():
    with open(LOG) as f:
        contenido = f.read()

    # Reemplazar fechas ISO por dd-mm-aaaa
    contenido = re.sub(r'(\d{4})-(\d{2})-(\d{2})', r'\3-\2-\1', contenido)

    return render_template('log.html', contenido=contenido)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
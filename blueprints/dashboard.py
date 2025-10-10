from flask import Blueprint, render_template, redirect, url_for, session
from db import get_connection
from datetime import datetime
from collections import defaultdict
from utils import normalizar_fecha, formatear_fecha, formatear_fecha_con_dia
from decoradores import protegido

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    if not session.get('autenticado'):
        return redirect(url_for('auth.login'))
    if session.get('clave_temporal'):
        return redirect(url_for('auth.cambiar_clave'))
    return redirect(url_for('dashboard.dashboard'))


@dashboard_bp.route('/dashboard')
@protegido
def dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT fecha, almuerzo, cena FROM pedidos")
    pedidos_raw = cursor.fetchall()

    cursor.execute("SELECT fecha, entregado_almuerzo, entregado_cena FROM entregas")
    entregas_raw = cursor.fetchall()
    entregas = {normalizar_fecha(row[0]): (row[1], row[2]) for row in entregas_raw}

    hoy_date = datetime.now().date()
    alm_por_entregar = cen_por_entregar = 0

    for fecha_iso, a_pedido, c_pedido in pedidos_raw:
        fecha_date = normalizar_fecha(fecha_iso)
        if fecha_date >= hoy_date:
            a_entregado, c_entregado = entregas.get(fecha_date, (0, 0))
            if a_pedido and not a_entregado:
                alm_por_entregar += 1
            if c_pedido and not c_entregado:
                cen_por_entregar += 1

    cursor.execute("SELECT tipo, SUM(cantidad) FROM pagos GROUP BY tipo")
    pagos_raw = dict(cursor.fetchall())
    alm_pagados = pagos_raw.get('almuerzo', 0)
    cen_pagados = pagos_raw.get('cena', 0)

    cursor.execute("SELECT fecha FROM pagos ORDER BY fecha DESC LIMIT 1")
    ultimo_pago = cursor.fetchone()
    fecha_ultimo_pago = formatear_fecha(ultimo_pago[0]) if ultimo_pago else "—"

    alm_pedidos = sum(p[1] for p in pedidos_raw)
    cen_pedidos = sum(p[2] for p in pedidos_raw)
    alm_entregados = sum(entregas.get(normalizar_fecha(p[0]), (0, 0))[0] for p in pedidos_raw)
    cen_entregados = sum(entregas.get(normalizar_fecha(p[0]), (0, 0))[1] for p in pedidos_raw)

    alm_saldo = alm_pagados - alm_entregados - alm_por_entregar
    cen_saldo = cen_pagados - cen_entregados - cen_por_entregar

    pedidos_pendientes_raw = []
    pedidos_por_validar_raw = []

    for fecha_iso, a_pedido, c_pedido in pedidos_raw:
        fecha_date = normalizar_fecha(fecha_iso)
        a_entregado, c_entregado = entregas.get(fecha_date, (0, 0))
        errores = []
        if a_pedido and not a_entregado:
            errores.append('almuerzo')
        if c_pedido and not c_entregado:
            errores.append('cena')
        if errores:
            if fecha_date >= hoy_date:
                pedidos_pendientes_raw.append((fecha_date, errores))
            else:
                pedidos_por_validar_raw.append((fecha_date, errores))

    # Ordenar por fecha ascendente y tomar los 5 más cercanos
    pedidos_pendientes = [
        (f.strftime('%d-%m-%Y'), formatear_fecha_con_dia(f), e)
        for f, e in sorted(pedidos_pendientes_raw, key=lambda x: x[0])[:5]
    ]

    pedidos_por_validar = [
        (f.strftime('%d-%m-%Y'), formatear_fecha_con_dia(f), e)
        for f, e in sorted(pedidos_por_validar_raw, key=lambda x: x[0])[:5]
    ]

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
                           pedidos_pendientes=pedidos_pendientes,
                           pedidos_por_validar=pedidos_por_validar)

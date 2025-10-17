from flask import Blueprint, render_template, redirect, url_for, session
from db import get_connection
from datetime import datetime
from utils import normalizar_fecha, formatear_fecha_con_dia
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

    # Obtener fecha de inicio del último ciclo por tipo
    cursor.execute("""
        SELECT tipo, MAX(fecha_inicio)
        FROM ciclos_pago
        GROUP BY tipo
    """)
    ciclos = dict(cursor.fetchall())
    alm_ciclo = ciclos.get('almuerzo', datetime.min.date())
    cen_ciclo = ciclos.get('cena', datetime.min.date())

    # Obtener pagos desde el inicio del ciclo
    cursor.execute("""
        SELECT tipo, SUM(cantidad)
        FROM pagos
        WHERE (tipo = 'almuerzo' AND fecha >= %s)
           OR (tipo = 'cena' AND fecha >= %s)
        GROUP BY tipo
    """, (alm_ciclo, cen_ciclo))
    pagos_raw = dict(cursor.fetchall())
    alm_pagados = pagos_raw.get('almuerzo', 0)
    cen_pagados = pagos_raw.get('cena', 0)

    # Obtener pedidos y entregas
    cursor.execute("SELECT fecha, almuerzo, cena FROM pedidos")
    pedidos_raw = cursor.fetchall()

    cursor.execute("SELECT fecha, entregado_almuerzo, entregado_cena FROM entregas")
    entregas_raw = cursor.fetchall()
    entregas = {normalizar_fecha(row[0]): (row[1], row[2]) for row in entregas_raw}

    hoy_date = datetime.now().date()
    alm_pedidos = alm_entregados = alm_por_entregar = 0
    cen_pedidos = cen_entregados = cen_por_entregar = 0

    pedidos_pendientes_raw = []
    pedidos_por_validar_raw = []

    for fecha_iso, a_pedido, c_pedido in pedidos_raw:
        fecha_date = normalizar_fecha(fecha_iso)
        a_entregado, c_entregado = entregas.get(fecha_date, (0, 0))

        # Almuerzo
        if fecha_date >= alm_ciclo:
            alm_pedidos += a_pedido
            alm_entregados += a_entregado
            if a_pedido and not a_entregado and fecha_date >= hoy_date:
                alm_por_entregar += 1

        # Cena
        if fecha_date >= cen_ciclo:
            cen_pedidos += c_pedido
            cen_entregados += c_entregado
            if c_pedido and not c_entregado and fecha_date >= hoy_date:
                cen_por_entregar += 1

        # Errores
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

    # Ordenar y formatear
    pedidos_pendientes = [
        (f.strftime('%d-%m-%Y'), formatear_fecha_con_dia(f), e)
        for f, e in sorted(pedidos_pendientes_raw, key=lambda x: x[0])[:5]
    ]
    pedidos_por_validar = [
        (f.strftime('%d-%m-%Y'), formatear_fecha_con_dia(f), e)
        for f, e in sorted(pedidos_por_validar_raw, key=lambda x: x[0])[:5]
    ]

    # Saldos
    alm_saldo = alm_pagados - alm_entregados - alm_por_entregar
    cen_saldo = cen_pagados - cen_entregados - cen_por_entregar

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
                           fecha_ultimo_pago=alm_ciclo.strftime('%d-%m-%Y'),
                           pedidos_pendientes=pedidos_pendientes,
                           pedidos_por_validar=pedidos_por_validar)

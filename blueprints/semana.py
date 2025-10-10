from flask import Blueprint, render_template, request
from db import get_connection
from datetime import datetime
from utils import obtener_fechas_semana, normalizar_fecha, normalizar_fecha_ddmmaaaa, estado_textual
from decoradores import protegido

semana_bp = Blueprint('semana', __name__)

@semana_bp.route('/semana', methods=['GET'])
@protegido
def vista_semanal():
    conn = get_connection()
    cursor = conn.cursor()

    semana_actual = int(request.args.get('semana', datetime.now().isocalendar().week))
    dias, fechas = obtener_fechas_semana(semana_actual)

    fecha_inicio = normalizar_fecha_ddmmaaaa(fechas[0]).strftime("%Y-%m-%d")
    fecha_fin = normalizar_fecha_ddmmaaaa(fechas[-1]).strftime("%Y-%m-%d")
    cursor.execute("SELECT fecha, almuerzo, cena, feriado FROM pedidos WHERE fecha BETWEEN %s AND %s",
                   (fecha_inicio, fecha_fin))
    pedidos_raw = cursor.fetchall()
    pedidos = {normalizar_fecha(row[0]): {'almuerzo': row[1], 'cena': row[2], 'feriado': row[3]} for row in pedidos_raw}

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

from flask import Blueprint, render_template, request, send_file
from db import get_connection
import pandas as pd
from io import BytesIO
from datetime import datetime
from decoradores import protegido
from utils import formatear_fecha_con_dia

reportes_bp = Blueprint('reportes', __name__)


@reportes_bp.route('/entregados', methods=['GET', 'POST'])
@protegido
def entregados():
    conn = get_connection()
    cursor = conn.cursor()

    # Obtener tipo desde GET o POST
    tipo = request.values.get('tipo', 'almuerzo')
    if tipo not in ['almuerzo', 'cena']:
        tipo = 'almuerzo'

    # Obtener fechas de pagos por tipo
    cursor.execute("SELECT fecha FROM pagos WHERE tipo = %s ORDER BY fecha DESC", (tipo,))
    fechas_pago = [r[0] for r in cursor.fetchall()]

    registros = []
    fecha_seleccionada = None
    pago_info = None

    # Solo procesar si hay fecha válida
    if request.method == 'POST':
        fecha_str = request.form.get('fecha')
        if fecha_str:
            fecha_seleccionada = datetime.strptime(fecha_str, "%Y-%m-%d").date()

            # Obtener info del pago primero
            cursor.execute("""
                SELECT fecha, tipo, monto, cantidad
                FROM pagos
                WHERE fecha = %s AND tipo = %s
            """, (fecha_seleccionada, tipo))
            pago_info = cursor.fetchone()
            cantidad_pagada = pago_info[3] if pago_info else 0

            # Luego obtener entregas
            campo_entregado = 'e.entregado_almuerzo' if tipo == 'almuerzo' else 'e.entregado_cena'
            cursor.execute(f"""
                SELECT p.fecha
                FROM pedidos p
                JOIN entregas e ON p.fecha = e.fecha
                WHERE p.fecha >= %s AND {campo_entregado} = 1
                ORDER BY p.fecha ASC
            """, (fecha_seleccionada,))
            fechas_entregadas = [r[0] for r in cursor.fetchall()]

            registros = []
            for i, fecha in enumerate(fechas_entregadas):
                texto = formatear_fecha_con_dia(fecha)
                excedido = i >= cantidad_pagada
                registros.append({
                    'fecha': texto,
                    'excedido': excedido
                })

    cursor.close()
    conn.close()

    return render_template('entregados.html',
                           tipo=tipo,
                           fechas_pago=fechas_pago,
                           registros=registros,
                           fecha_seleccionada=fecha_seleccionada,
                           pago_info=pago_info)


@reportes_bp.route('/entregados_excel')
@protegido
def validados_excel():
    tipo = request.args.get('tipo')
    fecha_str = request.args.get('desde')

    if not fecha_str:
        return "Fecha no proporcionada", 400
    if tipo not in ['almuerzo', 'cena']:
        return "Tipo inválido", 400

    fecha_base = datetime.strptime(fecha_str, "%Y-%m-%d").date()

    conn = get_connection()
    cursor = conn.cursor()

    # Obtener info del pago
    cursor.execute("""
        SELECT fecha, tipo, monto, cantidad
        FROM pagos
        WHERE fecha = %s AND tipo = %s
    """, (fecha_base, tipo))
    pago_info = cursor.fetchone()
    cantidad_pagada = pago_info[3] if pago_info else 0

    # Obtener entregas según tipo
    campo_entregado = 'e.entregado_almuerzo' if tipo == 'almuerzo' else 'e.entregado_cena'
    cursor.execute(f"""
        SELECT p.fecha
        FROM pedidos p
        JOIN entregas e ON p.fecha = e.fecha
        WHERE p.fecha >= %s AND {campo_entregado} = 1
        ORDER BY p.fecha ASC
    """, (fecha_base,))
    fechas_entregadas = [r[0] for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    # Preparar registros
    registros = []
    for i, fecha in enumerate(fechas_entregadas):
        texto = formatear_fecha_con_dia(fecha)
        excedido = i >= cantidad_pagada
        registros.append({
            'Fecha': texto,
            'Excedido': 'Sí' if excedido else ''
        })

    df = pd.DataFrame(registros)
    df.index += 1
    df.reset_index(inplace=True)
    df.rename(columns={'index': '#'}, inplace=True)

    # Generar Excel con formato
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        sheet_name = f'Entregas {tipo.capitalize()}'
        df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=4)

        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # Escribir resumen del pago si existe
        if pago_info:
            resumen = pd.DataFrame([{
                'Fecha de pago': pago_info[0].strftime('%d-%m-%Y'),
                'Tipo': pago_info[1].capitalize(),
                'Monto': f"S/. {pago_info[2]:.2f}",
                'Entregas cubiertas': cantidad_pagada,
                'Valor por unidad': f"S/. {pago_info[2] / cantidad_pagada:.2f}"
            }])
            resumen.to_excel(writer, index=False, sheet_name=sheet_name, startrow=0)

        # Aplicar formato amarillo a filas con "Sí" en columna Excedido
        formato_excedido = workbook.add_format({'bg_color': '#FFF3CD'})  # amarillo suave
        worksheet.conditional_format(f'E5:E{len(df)+4}', {
            'type': 'text',
            'criteria': 'containing',
            'value': 'Sí',
            'format': formato_excedido
        })

    output.seek(0)
    return send_file(output,
                     download_name=f'entregas_{tipo}_{fecha_str}.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')



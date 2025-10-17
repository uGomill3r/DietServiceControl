from flask import Blueprint, render_template, request, send_file
from db import get_connection
import pandas as pd
from io import BytesIO
from datetime import datetime
from decoradores import protegido
from utils import formatear_fecha_con_dia

reportes_bp = Blueprint('reportes', __name__)


@reportes_bp.route('/reporte_ciclo', methods=['GET', 'POST'])
@protegido
def reporte_ciclo():
    conn = get_connection()
    cursor = conn.cursor()

    tipo = request.values.get('tipo', 'almuerzo')
    if tipo not in ['almuerzo', 'cena']:
        tipo = 'almuerzo'

    # Obtener ciclos por tipo
    cursor.execute("""
        SELECT id, fecha_inicio, fecha_fin
        FROM ciclos_pago
        WHERE tipo = %s
        ORDER BY fecha_inicio DESC
    """, (tipo,))
    ciclos_raw = cursor.fetchall()

    registros = []
    ciclo_seleccionado = None
    ciclo_info = None
    cantidad_pagada = 0

    if request.method == 'POST':
        fecha_str = request.form.get('fecha')
        if fecha_str:
            fecha_inicio = datetime.strptime(fecha_str, "%Y-%m-%d").date()

            # Buscar ciclo por fecha de inicio
            ciclo = next((c for c in ciclos_raw if c[1] == fecha_inicio), None)
            if ciclo:
                ciclo_id, fecha_inicio, fecha_fin = ciclo
                ciclo_seleccionado = fecha_inicio
                ciclo_info = (fecha_inicio, fecha_fin)

                # Obtener pagos dentro del ciclo
                cursor.execute("""
                    SELECT SUM(cantidad)
                    FROM pagos
                    WHERE tipo = %s AND ciclo_id = %s
                """, (tipo, ciclo_id))
                cantidad_pagada = cursor.fetchone()[0] or 0

                # Obtener entregas dentro del ciclo
                campo_entregado = 'e.entregado_almuerzo' if tipo == 'almuerzo' else 'e.entregado_cena'
                cursor.execute(f"""
                    SELECT p.fecha
                    FROM pedidos p
                    JOIN entregas e ON p.fecha = e.fecha
                    WHERE p.fecha >= %s AND p.fecha <= %s AND {campo_entregado} = 1
                    ORDER BY p.fecha ASC
                """, (fecha_inicio, fecha_fin or datetime.now().date()))
                fechas_entregadas = [r[0] for r in cursor.fetchall()]

                for i, fecha in enumerate(fechas_entregadas):
                    texto = formatear_fecha_con_dia(fecha)
                    excedido = i >= cantidad_pagada
                    registros.append({
                        'fecha': texto,
                        'excedido': excedido
                    })

    cursor.close()
    conn.close()

    return render_template('reporte_ciclo.html',
                           tipo=tipo,
                           ciclos=ciclos_raw,
                           registros=registros,
                           ciclo_seleccionado=ciclo_seleccionado,
                           ciclo_info=ciclo_info,
                           cantidad_pagada=cantidad_pagada)


@reportes_bp.route('/ciclo_excel')
@protegido
def ciclo_excel():
    tipo = request.args.get('tipo')
    fecha_str = request.args.get('desde')

    if not fecha_str:
        return "Fecha no proporcionada", 400
    if tipo not in ['almuerzo', 'cena']:
        return "Tipo inválido", 400

    fecha_inicio = datetime.strptime(fecha_str, "%Y-%m-%d").date()

    conn = get_connection()
    cursor = conn.cursor()

    # Buscar ciclo por tipo y fecha de inicio
    cursor.execute("""
        SELECT id, fecha_inicio, fecha_fin
        FROM ciclos_pago
        WHERE tipo = %s AND fecha_inicio = %s
    """, (tipo, fecha_inicio))
    ciclo = cursor.fetchone()
    if not ciclo:
        return "Ciclo no encontrado", 404

    ciclo_id, fecha_inicio, fecha_fin = ciclo

    # Obtener cantidad pagada dentro del ciclo
    cursor.execute("""
        SELECT SUM(cantidad)
        FROM pagos
        WHERE tipo = %s AND ciclo_id = %s
    """, (tipo, ciclo_id))
    cantidad_pagada = cursor.fetchone()[0] or 0

    # Obtener entregas dentro del ciclo
    campo_entregado = 'e.entregado_almuerzo' if tipo == 'almuerzo' else 'e.entregado_cena'
    cursor.execute(f"""
        SELECT p.fecha
        FROM pedidos p
        JOIN entregas e ON p.fecha = e.fecha
        WHERE p.fecha >= %s AND p.fecha <= %s AND {campo_entregado} = 1
        ORDER BY p.fecha ASC
    """, (fecha_inicio, fecha_fin or datetime.now().date()))
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
        sheet_name = f'Ciclo {tipo.capitalize()}'
        df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=4)

        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # Escribir resumen del ciclo
        resumen = pd.DataFrame([{
            'Inicio del ciclo': fecha_inicio.strftime('%d-%m-%Y'),
            'Fin del ciclo': fecha_fin.strftime('%d-%m-%Y') if fecha_fin else '—',
            'Tipo': tipo.capitalize(),
            'Entregas cubiertas': cantidad_pagada
        }])
        resumen.to_excel(writer, index=False, sheet_name=sheet_name, startrow=0)

        # Formato condicional para excedidos
        formato_excedido = workbook.add_format({'bg_color': '#FFF3CD'})
        worksheet.conditional_format(f'E5:E{len(df)+4}', {
            'type': 'text',
            'criteria': 'containing',
            'value': 'Sí',
            'format': formato_excedido
        })

    output.seek(0)
    return send_file(output,
                     download_name=f'ciclo_{tipo}_{fecha_str}.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')




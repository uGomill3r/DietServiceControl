from flask import Blueprint, render_template, request, send_file
from db import get_connection
import pandas as pd
from io import BytesIO
from datetime import datetime
from decoradores import protegido

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

            campo_entregado = 'e.entregado_almuerzo' if tipo == 'almuerzo' else 'e.entregado_cena'
            cursor.execute(f"""
                SELECT p.fecha, p.almuerzo, p.cena, {campo_entregado}
                FROM pedidos p
                JOIN entregas e ON p.fecha = e.fecha
                WHERE p.fecha >= %s AND {campo_entregado} = 1
                ORDER BY p.fecha ASC
            """, (fecha_seleccionada,))
            registros = cursor.fetchall()

            cursor.execute("""
                SELECT fecha, tipo, monto, cantidad
                FROM pagos
                WHERE fecha = %s AND tipo = %s
            """, (fecha_seleccionada, tipo))
            pago_info = cursor.fetchone()

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

    # Obtener entregas según tipo
    campo_entregado = 'e.entregado_almuerzo' if tipo == 'almuerzo' else 'e.entregado_cena'
    cursor.execute(f"""
        SELECT p.fecha, p.almuerzo, p.cena, {campo_entregado}
        FROM pedidos p
        JOIN entregas e ON p.fecha = e.fecha
        WHERE p.fecha >= %s AND {campo_entregado} = 1
        ORDER BY p.fecha ASC
    """, (fecha_base,))
    registros = cursor.fetchall()

    cursor.close()
    conn.close()

    # Preparar DataFrame
    df = pd.DataFrame(registros, columns=[
        'Fecha', 'Almuerzo', 'Cena', 'Entregado'
    ])
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['Fecha'] = df['Fecha'].dt.strftime('%d-%m-%Y')
    df['Pedido'] = df['Almuerzo'] if tipo == 'almuerzo' else df['Cena']
    df['Pedido'] = df['Pedido'].replace({1: 'Sí', 0: 'No'})
    df['Entregado'] = df['Entregado'].replace({1: 'Sí', 0: 'No'})
    df = df[['Fecha', 'Pedido', 'Entregado']]
    df.index += 1
    df.reset_index(inplace=True)
    df.rename(columns={'index': '#'}, inplace=True)

    # Generar Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        sheet_name = f'Entregas {tipo.capitalize()}'

        # Escribir resumen del pago si existe
        if pago_info:
            resumen = pd.DataFrame([{
                'Fecha de pago': pago_info[0].strftime('%d-%m-%Y'),
                'Tipo': pago_info[1].capitalize(),
                'Monto': f"S/. {pago_info[2]:.2f}",
                'Entregas cubiertas': pago_info[3],
                'Valor por unidad': f"S/. {pago_info[2] / pago_info[3]:.2f}"
            }])
            resumen.to_excel(writer, index=False, sheet_name=sheet_name, startrow=0)
            df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=4)
        else:
            df.to_excel(writer, index=False, sheet_name=sheet_name)

    output.seek(0)
    return send_file(output,
                     download_name=f'entregas_{tipo}_{fecha_str}.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')



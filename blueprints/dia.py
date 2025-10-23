from flask import Blueprint, request, redirect, url_for, render_template, session, jsonify
from datetime import datetime, timedelta
from db import get_connection
from decoradores import protegido
from utils import normalizar_fecha, buscar_platos_similares

dia_bp = Blueprint('dia', __name__)

def siguiente_dia_habil(fecha):
    siguiente = fecha + timedelta(days=1)
    while siguiente.weekday() > 4:
        siguiente += timedelta(days=1)
    return siguiente

def anterior_dia_habil(fecha):
    anterior = fecha - timedelta(days=1)
    while anterior.weekday() > 4:
        anterior -= timedelta(days=1)
    return anterior

def cargar_datos_dia(fecha_form):
    conn = get_connection()
    cursor = conn.cursor()

    fecha_iso = datetime.strptime(fecha_form, "%d-%m-%Y").strftime("%Y-%m-%d")
    fecha_obj = datetime.strptime(fecha_form, "%d-%m-%Y")
    dias_abreviados = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    dia_semana = dias_abreviados[fecha_obj.weekday()]
    fecha_con_dia = f"{dia_semana} {fecha_form}"

    cursor.execute("""
        SELECT almuerzo, cena, feriado, observaciones, entrada, fondo, plato_cena
        FROM pedidos WHERE fecha = %s
    """, (fecha_iso,))
    row = cursor.fetchone()
    if row:
        pedido = (row[0], row[1])
        feriado = row[2]
        obs_pedido = row[3] or ''
        entrada = row[4] or ''
        fondo = row[5] or ''
        plato_cena = row[6] or ''
    else:
        pedido = (0, 0)
        feriado = False
        obs_pedido = ''
        entrada = ''
        fondo = ''
        plato_cena = ''

    cursor.execute("""
        SELECT entregado_almuerzo, entregado_cena, observaciones
        FROM entregas WHERE fecha = %s
    """, (fecha_iso,))
    entrega = cursor.fetchone() or (0, 0, '')

    cursor.close()
    conn.close()

    fecha_ant = anterior_dia_habil(fecha_obj).strftime("%d-%m-%Y")
    fecha_sig = siguiente_dia_habil(fecha_obj).strftime("%d-%m-%Y")

    return {
        'fecha': fecha_form,
        'fecha_con_dia': fecha_con_dia,
        'pedido': pedido,
        'entrega': entrega,
        'feriado': feriado,
        'obs_pedido': obs_pedido,
        'entrada': entrada,
        'fondo': fondo,
        'plato_cena': plato_cena,
        'fecha_ant': fecha_ant,
        'fecha_sig': fecha_sig
    }

@dia_bp.route('/ver_dia')
@protegido
def ver_dia():
    fecha_form = request.args.get('fecha')
    contexto = cargar_datos_dia(fecha_form)
    return render_template('editar_dia.html', solo_lectura=True, **contexto)

@dia_bp.route('/editar_dia', methods=['GET', 'POST'])
@protegido
def editar_dia():
    if request.method == 'POST':
        conn = get_connection()
        cursor = conn.cursor()

        fecha_form = request.form['fecha']
        fecha_iso = datetime.strptime(fecha_form, "%d-%m-%Y").strftime("%Y-%m-%d")

        almuerzo = 1 if request.form.get('almuerzo') == 'on' else 0
        cena = 1 if request.form.get('cena') == 'on' else 0
        entrada = request.form.get('entrada', '')
        fondo = request.form.get('fondo', '')
        plato_cena = request.form.get('plato_cena', '')
        obs_pedido = request.form.get('obs_pedido', '')

        entregado_almuerzo = 1 if request.form.get('entregado_almuerzo') == 'on' else 0
        entregado_cena = 1 if request.form.get('entregado_cena') == 'on' else 0
        obs_entrega = request.form.get('obs_entrega', '')

        feriado = request.form.get('feriado') == 'on'

        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE fecha = %s", (fecha_iso,))
        if cursor.fetchone()[0]:
            cursor.execute("""
                UPDATE pedidos
                SET almuerzo = %s, cena = %s, feriado = %s,
                    observaciones = %s, entrada = %s, fondo = %s, plato_cena = %s
                WHERE fecha = %s
            """, (almuerzo, cena, feriado, obs_pedido, entrada, fondo, plato_cena, fecha_iso))
        else:
            semana = normalizar_fecha(fecha_iso).isocalendar().week
            cursor.execute("""
                INSERT INTO pedidos (fecha, semana, almuerzo, cena, feriado,
                                     observaciones, entrada, fondo, plato_cena)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (fecha_iso, semana, almuerzo, cena, feriado,
                  obs_pedido, entrada, fondo, plato_cena))

        cursor.execute("SELECT COUNT(*) FROM entregas WHERE fecha = %s", (fecha_iso,))
        if cursor.fetchone()[0]:
            cursor.execute("""
                UPDATE entregas
                SET entregado_almuerzo = %s, entregado_cena = %s, observaciones = %s
                WHERE fecha = %s
            """, (entregado_almuerzo, entregado_cena, obs_entrega, fecha_iso))
        else:
            cursor.execute("""
                INSERT INTO entregas (fecha, entregado_almuerzo, entregado_cena, observaciones)
                VALUES (%s, %s, %s, %s)
            """, (fecha_iso, entregado_almuerzo, entregado_cena, obs_entrega))

        conn.commit()
        cursor.close()
        conn.close()

        accion = request.form.get('accion')
        if accion == 'guardar_siguiente':
            fecha_actual = datetime.strptime(fecha_form, "%d-%m-%Y")
            siguiente = siguiente_dia_habil(fecha_actual)
            siguiente_str = siguiente.strftime("%d-%m-%Y")
            return redirect(url_for('dia.editar_dia', fecha=siguiente_str))

        return redirect('/semana')

    # GET
    fecha_form = request.args.get('fecha')
    contexto = cargar_datos_dia(fecha_form)
    return render_template('editar_dia.html', solo_lectura=False, **contexto)

@dia_bp.route('/sugerencias_plato')
@protegido
def sugerencias_plato():
    termino = request.args.get('q', '')
    if not termino:
        return jsonify([])

    resultados = buscar_platos_similares(termino)
    platos = set()
    for entrada, fondo, cena in resultados:
        for plato in [entrada, fondo, cena]:
            if plato and termino.lower() in plato.lower():
                platos.add(plato)

    return jsonify(sorted(platos))

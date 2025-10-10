from datetime import datetime, date, timedelta
from db import get_connection

def obtener_fechas_semana(numero_semana, año=None):
    if año is None:
        año = datetime.now().isocalendar().year
    lunes = datetime.strptime(f'{año}-W{int(numero_semana):02}-1', "%G-W%V-%u")
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
            raise ValueError(f"Fecha en formato incorrecto: {fecha}")
    raise ValueError(f"Tipo de fecha no reconocido: {type(fecha)}")

def normalizar_fecha_ddmmaaaa(fecha_str):
    return datetime.strptime(fecha_str, "%d-%m-%Y").date()

def formatear_fecha(fecha):
    return normalizar_fecha(fecha).strftime("%d-%m-%Y")

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

def buscar_platos_similares(nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT entrada, fondo, plato_cena
        FROM pedidos
        WHERE entrada ILIKE %s OR fondo ILIKE %s OR plato_cena ILIKE %s
        LIMIT 10
    """, (f"%{nombre}%", f"%{nombre}%", f"%{nombre}%"))
    resultados = cursor.fetchall()
    cursor.close()
    conn.close()
    return resultados

def formatear_fecha_con_dia(fecha: date) -> str:
    dias_abreviados = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    dia = dias_abreviados[fecha.weekday()]
    return f"{dia} {fecha.strftime('%d-%m-%Y')}"

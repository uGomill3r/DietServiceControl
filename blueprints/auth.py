from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_connection
import os

auth_bp = Blueprint('auth', __name__)

def credencial_valida(usuario, clave):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT contraseña FROM credenciales WHERE usuario = %s", (usuario,))
    fila = cursor.fetchone()
    conn.close()
    if fila:
        return clave == fila[0]
    return usuario == os.getenv("APP_USER") and clave == os.getenv("APP_PASSWORD")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']
        if credencial_valida(usuario, clave):
            session['autenticado'] = True
            if clave == os.getenv("APP_PASSWORD"):
                session['clave_temporal'] = True
            return redirect(url_for('dashboard.dashboard'))
        flash('Credenciales incorrectas')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO credenciales (usuario, contraseña)
            VALUES (%s, %s)
            ON CONFLICT (usuario) DO UPDATE SET contraseña = EXCLUDED.contraseña, actualizado = CURRENT_TIMESTAMP
        """, (os.getenv("APP_USER"), os.getenv("APP_PASSWORD")))
        conn.commit()
        conn.close()
        flash('Contraseña restaurada. Por favor inicia sesión y cámbiala.')
        return redirect(url_for('auth.login'))
    return render_template('recuperar.html')

@auth_bp.route('/cambiar_clave', methods=['GET', 'POST'])
def cambiar_clave():
    if not session.get('autenticado'):
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        nueva = request.form['nueva_clave']
        if nueva == os.getenv("APP_PASSWORD"):
            flash('La nueva contraseña no puede ser igual a la inicial.')
            return render_template('cambiar_clave.html')
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE credenciales SET contraseña = %s, actualizado = CURRENT_TIMESTAMP
            WHERE usuario = %s
        """, (nueva, os.getenv("APP_USER")))
        conn.commit()
        conn.close()
        session.pop('clave_temporal', None)
        flash('Contraseña actualizada correctamente.')
        return redirect(url_for('dashboard.dashboard'))
    return render_template('cambiar_clave.html')

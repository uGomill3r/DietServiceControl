# decoradores.py
from functools import wraps
from flask import session, redirect, url_for

def protegido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('autenticado'):
            return redirect(url_for('auth.login'))
        if session.get('clave_temporal'):
            return redirect(url_for('auth.cambiar_clave'))
        return f(*args, **kwargs)
    return wrapper


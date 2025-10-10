from flask import Blueprint, render_template
from decoradores import protegido
import re
import os

log_bp = Blueprint('log', __name__)
LOG = 'changelog/log.md'

@log_bp.route('/log')
@protegido
def log():
    with open(LOG) as f:
        contenido = f.read()
    contenido = re.sub(r'(\d{4})-(\d{2})-(\d{2})', r'\3-\2-\1', contenido)
    return render_template('log.html', contenido=contenido)

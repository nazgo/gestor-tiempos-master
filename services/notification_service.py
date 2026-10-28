"""Notificaciones de solicitudes de acceso por Resend."""
import json
import logging
import os
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

def notificar_nueva_solicitud(nombre, email, ruta_admin):
    api_key = os.environ.get('RESEND_API_KEY', '').strip()
    remitente = os.environ.get('MAIL_FROM', '').strip()
    destinatarios = [v.strip() for v in os.environ.get('ADMIN_NOTIFICATION_EMAIL', '').split(',') if v.strip()]
    base = os.environ.get('APP_BASE_URL', '').strip()
    if not all((api_key, remitente, destinatarios, base)):
        logger.warning('Resend sin configurar: no se envió aviso de solicitud')
        return False
    enlace = urljoin(base.rstrip('/') + '/', ruta_admin.lstrip('/'))
    contenido = (
        '<h2>Nueva solicitud de acceso</h2>'
        '<p>Se ha recibido una solicitud de registro en ÑM Performance.</p>'
        '<p><strong>Nombre:</strong> ' + escape(str(nombre or '')) + '</p>'
        '<p><strong>Correo:</strong> ' + escape(str(email or '')) + '</p>'
        '<p><a href="' + escape(enlace, quote=True) + '">Revisar solicitudes pendientes</a></p>'
        '<p>Verifica la identidad del solicitante antes de aprobar.</p>'
    )
    payload = {
        'from': remitente,
        'to': destinatarios,
        'subject': 'ÑM Performance: nueva solicitud de acceso',
        'html': contenido,
    }
    peticion = Request(
        'https://api.resend.com/emails',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urlopen(peticion, timeout=8) as respuesta:
            if respuesta.status in (200, 201, 202):
                return True
            logger.error('Resend devolvió HTTP %s', respuesta.status)
    except HTTPError as error:
        logger.error('Resend rechazó el correo: HTTP %s', error.code)
    except (URLError, TimeoutError, OSError):
        logger.exception('Error de conexión con Resend')
    return False

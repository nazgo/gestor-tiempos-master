"""Avisos de registro y resolución de solicitudes mediante Resend."""
import json
import logging
import os
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def _enviar(destinatarios, asunto, contenido):
    api_key = os.environ.get('RESEND_API_KEY', '').strip()
    remitente = os.environ.get('MAIL_FROM', '').strip()
    if not (api_key and remitente and destinatarios):
        logger.warning('Resend sin configurar: aviso no enviado')
        return False
    payload = {'from': remitente, 'to': destinatarios, 'subject': asunto, 'html': contenido}
    peticion = Request(
        'https://api.resend.com/emails',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': 'Bearer ' + api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'NM-Performance/1.0',
        },
        method='POST',
    )
    try:
        with urlopen(peticion, timeout=8) as respuesta:
            return respuesta.status in (200, 201, 202)
    except HTTPError as error:
        detalle = error.read().decode('utf-8', errors='replace')[:500]
        logger.error('Resend rechazó el correo: HTTP %s - %s', error.code, detalle)
    except (URLError, TimeoutError, OSError):
        logger.exception('Error de conexión con Resend')
    return False


def notificar_nueva_solicitud(nombre, email, ruta_admin):
    destinatarios = [v.strip() for v in os.environ.get('ADMIN_NOTIFICATION_EMAIL', '').split(',') if v.strip()]
    base = os.environ.get('APP_BASE_URL', '').strip()
    if not base:
        logger.warning('APP_BASE_URL sin configurar')
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
    return _enviar(destinatarios, 'ÑM Performance: nueva solicitud de acceso', contenido)


def notificar_resolucion_solicitud(nombre, email, accion):
    if accion not in ('aprobar', 'rechazar'):
        raise ValueError('Acción de solicitud no válida')
    base = os.environ.get('APP_BASE_URL', '').strip()
    if not base:
        logger.warning('APP_BASE_URL sin configurar')
        return False
    nombre_seguro = escape(str(nombre or ''))
    if accion == 'aprobar':
        asunto = 'ÑM Performance: tu solicitud fue aprobada'
        enlace = urljoin(base.rstrip('/') + '/', 'login')
        contenido = (
            '<h2>¡Tu acceso fue aprobado!</h2>'
            '<p>Hola ' + nombre_seguro + ',</p>'
            '<p>Tu solicitud de acceso a ÑM Performance ha sido aprobada.</p>'
            '<p>Ya puedes ingresar con el correo y la contraseña que elegiste al registrarte.</p>'
            '<p><a href="' + escape(enlace, quote=True) + '">Iniciar sesión</a></p>'
            '<p>Equipo Ñuñoa Master</p>'
        )
    else:
        asunto = 'ÑM Performance: resultado de tu solicitud de acceso'
        contenido = (
            '<h2>Actualización de tu solicitud</h2>'
            '<p>Hola ' + nombre_seguro + ',</p>'
            '<p>Tu solicitud de acceso a ÑM Performance no fue aprobada.</p>'
            '<p>Si consideras que hubo un error, comunícate con la administración del club.</p>'
            '<p>Equipo Ñuñoa Master</p>'
        )
    return _enviar([str(email).strip()], asunto, contenido)

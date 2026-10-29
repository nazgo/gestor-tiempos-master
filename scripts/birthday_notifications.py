"""ÑM Performance: avisos de cumpleaños. Ejecutar mediante Render Cron Job cada hora."""
import json
import logging
import os
from datetime import datetime, date
from html import escape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import psycopg

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('cumpleanos')
TZ = ZoneInfo('America/Santiago')


def enviar(destinatario, asunto, contenido):
    payload = {'from': os.environ['MAIL_FROM'], 'to': [destinatario], 'subject': asunto, 'html': contenido}
    request = Request('https://api.resend.com/emails', data=json.dumps(payload).encode(),
                      headers={'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'],
                               'Content-Type': 'application/json', 'User-Agent': 'NM-Performance/1.0'}, method='POST')
    try:
        with urlopen(request, timeout=15) as response:
            return response.status in (200, 201, 202)
    except HTTPError as exc:
        log.error('Resend HTTP %s para destinatario %s', exc.code, destinatario)
    except (URLError, TimeoutError, OSError):
        log.exception('Error enviando correo a %s', destinatario)
    return False


def plantilla(titulo, cuerpo):
    return ('<div style="font-family:Arial,sans-serif;max-width:580px;margin:auto;color:#172238">'
            '<h2 style="color:#542a86">' + escape(titulo) + '</h2>' + cuerpo +
            '<p style="color:#666">Club Natación Ñuñoa Master · ÑM Performance</p></div>')


def main():
    for key in ('DATABASE_URL', 'RESEND_API_KEY', 'MAIL_FROM', 'ADMIN_NOTIFICATION_EMAIL', 'BIRTHDAY_NOTIFICATION_EMAIL'):
        if not os.environ.get(key, '').strip():
            raise RuntimeError('Variable de entorno requerida: ' + key)
    now = datetime.now(TZ)
    if now.hour != 9 and os.environ.get('BIRTHDAY_FORCE_RUN') != '1':
        log.info('Hora Chile: %s. Se omite ejecución; programado a las 09:00.', now.isoformat())
        return
    today = now.date()
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS birthday_notification_log (
                nadador_id INTEGER NOT NULL,
                fecha DATE NOT NULL,
                tipo TEXT NOT NULL,
                destinatario TEXT NOT NULL,
                enviado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (nadador_id, fecha, tipo, destinatario)
            )''')
            cur.execute('''SELECT n.id, n.nombre, n.apellido, n.fecha_nacimiento,
                                  u.email
                           FROM nadadores n
                           LEFT JOIN usuarios u ON u.nadador_id = n.id
                               AND u.estado = 'activo'
                               AND u.email IS NOT NULL AND TRIM(u.email) <> ''
                           WHERE n.activo = TRUE
                             AND EXTRACT(MONTH FROM n.fecha_nacimiento) = %s
                             AND EXTRACT(DAY FROM n.fecha_nacimiento) = %s
                           ORDER BY n.apellido, n.nombre''', (today.month, today.day))
            cumpleaneros = cur.fetchall()
            log.info('Cumpleañeros activos hoy: %d', len(cumpleaneros))
            for nadador_id, nombre, apellido, fecha_nac, email in cumpleaneros:
                completo = f'{nombre} {apellido}'.strip()
                safe = escape(completo)
                mensajes = []
                if email:
                    mensajes.append(('nadador', email.strip(),
                        '¡Feliz cumpleaños! 🎉 | ÑM Performance',
                        plantilla('¡Feliz cumpleaños, ' + nombre + '! 🎉',
                            '<p>¡Hoy celebramos contigo! Te deseamos mucha salud, alegría, grandes momentos '
                            'y nuevas marcas personales en la piscina.</p><p>¡Un abrazo de todo Ñuñoa Master! 🏊‍♂️💜</p>')))
                else:
                    log.info('Sin correo de usuario activo vinculado: nadador ID %s', nadador_id)
                texto = f'<p>Hoy está de cumpleaños <strong>{safe}</strong>.</p><p>¡No olvidemos saludarle! 🎂</p>'
                for addr in os.environ['ADMIN_NOTIFICATION_EMAIL'].split(','):
                    if addr.strip():
                        mensajes.append(('administrador', addr.strip(), 'Cumpleaños de hoy | ÑM Performance', plantilla('Cumpleaños del club 🎂', texto)))
                for addr in os.environ['BIRTHDAY_NOTIFICATION_EMAIL'].split(','):
                    if addr.strip():
                        mensajes.append(('encargado', addr.strip(), 'Cumpleaños de hoy | ÑM Performance', plantilla('Cumpleaños del club 🎂', texto)))
                for tipo, destinatario, asunto, html in mensajes:
                    # La llave única y el bloqueo transaccional impiden duplicados en ejecuciones concurrentes.
                    cur.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (f'birthday:{nadador_id}:{today}:{tipo}:{destinatario.lower()}',))
                    cur.execute('SELECT 1 FROM birthday_notification_log WHERE nadador_id=%s AND fecha=%s AND tipo=%s AND destinatario=%s',
                                (nadador_id, today, tipo, destinatario.lower()))
                    if cur.fetchone():
                        continue
                    if enviar(destinatario, asunto, html):
                        cur.execute('INSERT INTO birthday_notification_log (nadador_id,fecha,tipo,destinatario) VALUES (%s,%s,%s,%s)',
                                    (nadador_id, today, tipo, destinatario.lower()))
                        conn.commit()
                        log.info('Enviado %s a %s (nadador ID %s)', tipo, destinatario, nadador_id)
                    else:
                        log.warning('No enviado %s a %s (nadador ID %s); reintentará', tipo, destinatario, nadador_id)
    log.info('Proceso finalizado')


if __name__ == '__main__':
    main()

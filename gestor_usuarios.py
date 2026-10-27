import os
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import psycopg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class GestorUsuarios:
    def __init__(self, db_path="nadadores_master_competitivos.db"):
        self.db_path = db_path
        self.conn = None
        self.connect()
        self.crear_tabla()
        self.migrar_registro()

    def connect(self):
        db_url = os.environ.get('DATABASE_URL')
        print("DEBUG usuarios - DATABASE_URL:", bool(db_url))
        
        if db_url and 'postgresql' in db_url and POSTGRES_AVAILABLE:
            try:
                print("🔗 Conectando a Neon PostgreSQL para usuarios...")
                self.conn = psycopg.connect(db_url)
                self.conn.autocommit = True
                print("✅ Conexión PostgreSQL exitosa!")
                return
            except Exception as e:
                print("❌ Error PostgreSQL usuarios:", e)
        
        if db_url and 'postgresql' in db_url:
            raise RuntimeError('No se pudo conectar a PostgreSQL: se cancela el inicio para evitar SQLite accidental')
        print("🔗 Usando SQLite local para usuarios...")
        import sqlite3
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def _execute(self, query, params=None, commit=True):
    
        try:
            self.conn.cursor()
        except Exception:
            print("Reconectando a PostgreSQL...")
            self.connect()
    
        cursor = self.conn.cursor()
    
        if params:
            if 'postgresql' in str(os.environ.get('DATABASE_URL', '')):
                query = query.replace('?', '%s')
            cursor.execute(query, params)
        else:
            cursor.execute(query)
    
        if commit:
            self.conn.commit()
    
        return cursor

    def crear_tabla(self):
        self._execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'viewer',
                nombre TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''', commit=False)

        # Nunca crear credenciales administrativas predeterminadas.

    def migrar_registro(self):
        postgres = 'postgresql' in str(os.environ.get('DATABASE_URL', ''))
        columns = [('rut', 'TEXT'), ('email', 'TEXT'), ('estado', "TEXT DEFAULT 'activo'"), ('nadador_id', 'INTEGER'), ('fecha_aprobacion', 'TIMESTAMP'), ('aprobado_por', 'INTEGER')]
        for name, kind in columns:
            if postgres:
                self._execute(f'ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS {name} {kind}')
            else:
                try:
                    self._execute(f'ALTER TABLE usuarios ADD COLUMN {name} {kind}')
                except Exception as e:
                    if 'duplicate column' not in str(e).lower():
                        raise
        self._execute("UPDATE usuarios SET estado='activo' WHERE estado IS NULL")
        self._execute("UPDATE usuarios SET rol='entrenador' WHERE rol='editor'")
        self._execute("UPDATE usuarios SET rol='delegado' WHERE rol='viewer'")
        self._execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_email ON usuarios (LOWER(email))')
        self._execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_rut ON usuarios (rut)')
        self._execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_nadador ON usuarios (nadador_id)')

    def solicitar_registro(self, nombre, rut, email, password):
        import re
        rut = rut.upper().replace('.', '').replace('-', '').replace(' ', '')
        if not re.fullmatch(r'[0-9]{7,8}[0-9K]', rut):
            raise ValueError('RUT inválido')
        body, dv = rut[:-1], rut[-1]
        total = sum(int(n) * (2 + i % 6) for i, n in enumerate(reversed(body)))
        expected = '0' if total % 11 == 0 else 'K' if 11 - total % 11 == 10 else str(11 - total % 11)
        if dv != expected:
            raise ValueError('Dígito verificador del RUT incorrecto')
        email = email.strip().lower()
        nombre = ' '.join(nombre.split())
        if len(nombre) < 4 or len(nombre) > 150 or len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValueError('Nombre o correo inválidos')
        if len(password) < 12 or len(password) > 256:
            raise ValueError('La contraseña debe tener entre 12 y 256 caracteres')
        if self._execute('SELECT id FROM usuarios WHERE rut=? OR LOWER(email)=?', (rut, email), False).fetchone():
            raise ValueError('Ya existe una solicitud o cuenta asociada a esos datos')
        username = email
        self._execute('''INSERT INTO usuarios (username, password_hash, rol, nombre, rut, email, estado)
                         VALUES (?, ?, 'pendiente', ?, ?, ?, 'pendiente')''',
                      (username, generate_password_hash(password), nombre, rut, email))

    def listar_pendientes(self):
        cursor = self._execute("SELECT id, nombre, rut, email, created_at FROM usuarios WHERE estado='pendiente' ORDER BY created_at", commit=False)
        return [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]

    def resolver_solicitud(self, user_id, accion, rol, nadador_id, admin_id):
        if accion not in ('aprobar', 'rechazar'):
            raise ValueError('Acción no válida')
        if rol not in ('admin', 'entrenador', 'delegado', 'nadador'):
            raise ValueError('Rol no válido')
        row = self._execute("SELECT rut FROM usuarios WHERE id=? AND estado='pendiente'", (user_id,), False).fetchone()
        if not row:
            raise ValueError('La solicitud ya fue resuelta o no existe')
        if accion == 'rechazar':
            self._execute("UPDATE usuarios SET estado='rechazado' WHERE id=? AND estado='pendiente'", (user_id,))
            return
        if rol == 'nadador' and not nadador_id:
            raise ValueError('El rol Nadador requiere una ficha vinculada')
        if nadador_id:
            n = self._execute('SELECT rut FROM nadadores WHERE id=?', (nadador_id,), False).fetchone()
            if not n:
                raise ValueError('Ficha inexistente')
            # El RUT debe coincidir; si no coincide, corregir los datos antes de aprobar.
            normalize = lambda x: str(x or '').upper().replace('.', '').replace('-', '').replace(' ', '')
            if normalize(n[0]) != normalize(row[0]):
                raise ValueError('El RUT de la ficha no coincide con el del solicitante')
        self._execute('''UPDATE usuarios SET rol=?, estado='activo', nadador_id=?,
                         aprobado_por=?, fecha_aprobacion=CURRENT_TIMESTAMP
                         WHERE id=? AND estado='pendiente' ''', (rol, nadador_id, admin_id, user_id))

    def crear_usuario(self, username, password, rol="viewer", nombre=""):
        password_hash = generate_password_hash(password)
        self._execute('''
            INSERT INTO usuarios (username, password_hash, rol, nombre)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, rol, nombre))

    def obtener_usuario(self, username):
            cursor = self._execute('SELECT * FROM usuarios WHERE username = ?', (username,), commit=False)
            row = cursor.fetchone()
            if not row:
                return None
            # Conversión segura
            if hasattr(row, '_asdict'):  # psycopg
                return dict(row._asdict())
            elif hasattr(row, 'keys'):   # sqlite Row
                return dict(row)
            else:  # fallback
                return dict(zip([desc[0] for desc in cursor.description], row))

    def obtener_usuario_por_id(self, user_id):
        cursor = self._execute('SELECT * FROM usuarios WHERE id = ?', (user_id,), commit=False)
        row = cursor.fetchone()
        if not row:
            return None
        return dict(zip([c[0] for c in cursor.description], row))

    def verificar_login(self, username, password):
        usuario = self.obtener_usuario(username)
        if usuario and usuario.get('estado', 'activo') == 'activo' and check_password_hash(usuario['password_hash'], password):
            return dict(usuario)
        return None

    def listar_usuarios(self):
            cursor = self._execute('SELECT id, username, rol, nombre, created_at FROM usuarios', commit=False)
            rows = cursor.fetchall()
            result = []
            for row in rows:
                if row:
                    if hasattr(row, '_asdict'):
                        result.append(dict(row._asdict()))
                    elif hasattr(row, 'keys'):
                        result.append(dict(row))
                    else:
                        result.append(dict(zip([desc[0] for desc in cursor.description], row)))
            return result

    def cambiar_rol(self, user_id, nuevo_rol):
        self._execute('UPDATE usuarios SET rol = ? WHERE id = ?', (nuevo_rol, user_id))

    def cambiar_password(self, user_id, new_password):
        password_hash = generate_password_hash(new_password)
        self._execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', (password_hash, user_id))

    def eliminar_usuario(self, user_id):
        if user_id == 1:
            return False
        self._execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
        return True
        
    def cerrar_conexion(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass  # Ignorar si ya estaba cerrada

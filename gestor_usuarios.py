import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class GestorUsuarios:
    def __init__(self, db_path="nadadores_master_competitivos.db"):
        self.db_path = db_path
        self.conn = None
        self.connect()
        self.crear_tabla()

    def connect(self):
        """Conecta a PostgreSQL (Neon) o SQLite local."""
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('postgres') and POSTGRES_AVAILABLE:
            print("🔗 Conectando a PostgreSQL (Neon) para usuarios...")
            self.conn = psycopg2.connect(db_url)
            self.conn.autocommit = True
        else:
            print("🔗 Usando SQLite local para usuarios...")
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

    def _execute(self, query: str, params=None, commit=True):
        """Método helper para manejar diferencias entre SQLite y PostgreSQL."""
        cursor = self.conn.cursor()
        if params is not None:
            # Convertir placeholders según el motor
            if hasattr(self.conn, 'autocommit'):  # PostgreSQL
                query = query.replace('?', '%s')
            else:  # SQLite
                query = query.replace('%s', '?')
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if commit and hasattr(self.conn, 'commit'):
            self.conn.commit()
        return cursor

    def crear_tabla(self):
        """Crea la tabla de usuarios si no existe."""
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

        # Usuario admin por defecto
        if not self.obtener_usuario("admin"):
            self.crear_usuario("admin", "admin123", "admin", "Administrador")

    def crear_usuario(self, username, password, rol="viewer", nombre=""):
        password_hash = generate_password_hash(password)
        self._execute('''
            INSERT INTO usuarios (username, password_hash, rol, nombre)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, rol, nombre))

    def verificar_login(self, username, password):
        usuario = self.obtener_usuario(username)
        if usuario and check_password_hash(usuario['password_hash'], password):
            return dict(usuario)
        return None

    def obtener_usuario(self, username):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def listar_usuarios(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, username, rol, nombre, created_at FROM usuarios')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def cambiar_rol(self, user_id, nuevo_rol):
        self._execute('UPDATE usuarios SET rol = ? WHERE id = ?', (nuevo_rol, user_id))

    def cambiar_password(self, user_id, new_password):
        password_hash = generate_password_hash(new_password)
        self._execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', (password_hash, user_id))

    def eliminar_usuario(self, user_id):
        if user_id == 1:  # Proteger admin principal
            return False
        self._execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
        return True

    def cerrar_conexion(self):
        """Cierra la conexión (útil para limpieza)."""
        if self.conn:
            self.conn.close()

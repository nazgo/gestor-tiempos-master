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
        
        print("🔗 Usando SQLite local para usuarios...")
        import sqlite3
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def _execute(self, query, params=None, commit=True):
        cursor = self.conn.cursor()
        if params:
            if 'postgresql' in str(os.environ.get('DATABASE_URL', '')):
                query = query.replace('?', '%s')
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if commit and hasattr(self.conn, 'commit'):
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

        if not self.obtener_usuario("admin"):
            self.crear_usuario("admin", "admin123", "admin", "Administrador")

    def crear_usuario(self, username, password, rol="viewer", nombre=""):
        password_hash = generate_password_hash(password)
        self._execute('''
            INSERT INTO usuarios (username, password_hash, rol, nombre)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, rol, nombre))

    def obtener_usuario(self, username):
        cursor = self._execute('SELECT * FROM usuarios WHERE username = ?', (username,), commit=False)
        row = cursor.fetchone()
        if row:
            return dict(row) if hasattr(row, '_asdict') else dict(row)
        return None

    def verificar_login(self, username, password):
        usuario = self.obtener_usuario(username)
        if usuario and check_password_hash(usuario['password_hash'], password):
            return dict(usuario)
        return None

    def listar_usuarios(self):
        cursor = self._execute('SELECT id, username, rol, nombre, created_at FROM usuarios', commit=False)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            if row:
                result.append(dict(row) if hasattr(row, '_asdict') else dict(row))
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

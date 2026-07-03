import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

class GestorUsuarios:
    def __init__(self, db_path="nadadores_master_competitivos.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.crear_tabla()

    def crear_tabla(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'viewer',
                nombre TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Usuario admin por defecto
        if not self.obtener_usuario("admin"):
            self.crear_usuario("admin", "admin123", "admin", "Administrador")
        self.conn.commit()

    def crear_usuario(self, username, password, rol="viewer", nombre=""):
        password_hash = generate_password_hash(password)
        self.conn.execute('''
            INSERT INTO usuarios (username, password_hash, rol, nombre)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, rol, nombre))
        self.conn.commit()

    def verificar_login(self, username, password):
        usuario = self.obtener_usuario(username)
        if usuario and check_password_hash(usuario['password_hash'], password):
            return dict(usuario)
        return None

    def obtener_usuario(self, username):
        cursor = self.conn.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def listar_usuarios(self):
        cursor = self.conn.execute('SELECT id, username, rol, nombre, created_at FROM usuarios')
        return [dict(row) for row in cursor.fetchall()]

    def cambiar_rol(self, user_id, nuevo_rol):
        self.conn.execute('UPDATE usuarios SET rol = ? WHERE id = ?', (nuevo_rol, user_id))
        self.conn.commit()

    def cambiar_password(self, user_id, new_password):
        password_hash = generate_password_hash(new_password)
        self.conn.execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        self.conn.commit()

    def eliminar_nadador(self, nadador_id):
        """Elimina un nadador y sus tiempos asociados."""
        cursor = self.conn.cursor()
        # Elimina primero los tiempos
        cursor.execute('DELETE FROM tiempos WHERE LOWER(nombre_nadador) = LOWER((SELECT nombre || " " || apellido FROM nadadores WHERE id = ?))', (nadador_id,))
        # Elimina el nadador
        cursor.execute('DELETE FROM nadadores WHERE id = ?', (nadador_id,))
        self.conn.commit()

    def eliminar_usuario(self, user_id):
        if user_id == 1:  # Proteger admin principal
            return False
        self.conn.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
        self.conn.commit()
        return True

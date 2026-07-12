from datetime import datetime, date
import sqlite3
import os

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class GestorNadadores:
    def __init__(self, db_path="nadadores_master_competitivos.db"):
        self.db_path = db_path
        self.conn = None
        self.connect()
        self.crear_tabla()

    def connect(self):
        """Conecta a PostgreSQL (Neon) o SQLite."""
        db_url = os.environ.get('DATABASE_URL')
        print("DEBUG - DATABASE_URL:", bool(db_url))
        
        if db_url and 'postgresql' in db_url:
            try:
                import psycopg
                print("🔗 Conectando a Neon PostgreSQL con psycopg...")
                self.conn = psycopg.connect(db_url)
                self.conn.autocommit = True
                print("✅ Conexión PostgreSQL exitosa!")
                return
            except Exception as e:
                print("❌ Error conectando a PostgreSQL:", e)
        
        print("⚠️  Usando SQLite local.")
        import sqlite3
        self.conn = sqlite3.connect("nadadores_master_competitivos.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Fallback a SQLite
        print("⚠️  Usando SQLite local.")
        import sqlite3
        self.conn = sqlite3.connect("nadadores_master_competitivos.db", check_same_thread=False)
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
            CREATE TABLE IF NOT EXISTS nadadores (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                fecha_nacimiento DATE NOT NULL,
                rut TEXT UNIQUE,
                genero TEXT,
                categoria_master TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''', commit=False)

    def calcular_categoria_master(self, fecha_nac):
        """Calcula categoría Master según edad al 31 de diciembre del año actual"""
        if not fecha_nac:
            return "Sin categoría"
        ano_actual = datetime.now().year
        fecha_corte = date(ano_actual, 12, 31)
        edad = fecha_corte.year - fecha_nac.year - ((fecha_corte.month, fecha_corte.day) < (fecha_nac.month, fecha_nac.day))
        
        if edad < 18:
            return "Juvenil"
        elif edad <= 24:
            return f"Master {18}-{24}"
        elif edad <= 29:
            return f"Master {25}-{29}"
        elif edad <= 34:
            return f"Master {30}-{34}"
        elif edad <= 39:
            return f"Master {35}-{39}"
        elif edad <= 44:
            return f"Master {40}-{44}"
        elif edad <= 49:
            return f"Master {45}-{49}"
        elif edad <= 54:
            return f"Master {50}-{54}"
        elif edad <= 59:
            return f"Master {55}-{59}"
        elif edad <= 64:
            return f"Master {60}-{64}"
        elif edad <= 69:
            return f"Master {65}-{69}"
        elif edad <= 74:
            return f"Master {70}-{74}"
        elif edad <= 79:
            return f"Master {75}-{79}"
        elif edad <= 84:
            return f"Master {80}-{84}"
        elif edad <= 89:
            return f"Master {85}-{89}"
        else:
            return f"Master 90+"

    def agregar_nadador(self, nombre, apellido, fecha_nacimiento, rut=None, genero=None):
        categoria = self.calcular_categoria_master(fecha_nacimiento)
        self._execute('''
            INSERT INTO nadadores (nombre, apellido, fecha_nacimiento, rut, genero, categoria_master)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, apellido, fecha_nacimiento, rut, genero, categoria))

    def listar_nadadores(self):
        cursor = self._execute('SELECT * FROM nadadores ORDER BY apellido, nombre', commit=False)
        rows = cursor.fetchall()
        return [dict(row) if hasattr(row, '_asdict') else dict(row) for row in rows]

    def obtener_nadador(self, nadador_id):
        cursor = self._execute('SELECT * FROM nadadores WHERE id = ?', (nadador_id,), commit=False)
        row = cursor.fetchone()
        return dict(row) if row else None

    def actualizar_nadador(self, nadador_id, nombre, apellido, fecha_nacimiento, rut=None, genero=None):
        categoria = self.calcular_categoria_master(fecha_nacimiento)
        self._execute('''
            UPDATE nadadores 
            SET nombre = ?, apellido = ?, fecha_nacimiento = ?, rut = ?, genero = ?, categoria_master = ?
            WHERE id = ?
        ''', (nombre, apellido, fecha_nacimiento, rut, genero, categoria, nadador_id))

    def eliminar_nadador(self, nadador_id):
        """Elimina un nadador y sus tiempos asociados."""
        # Elimina primero los tiempos
        self._execute('''
            DELETE FROM tiempos 
            WHERE LOWER(nombre_nadador) = LOWER(
                (SELECT nombre || ' ' || apellido FROM nadadores WHERE id = ? LIMIT 1)
            )
        ''', (nadador_id,))
        
        # Elimina el nadador
        self._execute('DELETE FROM nadadores WHERE id = ?', (nadador_id,))

    def cerrar_conexion(self):
        if self.conn:
            self.conn.close()

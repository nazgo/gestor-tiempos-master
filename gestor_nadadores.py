from datetime import datetime, date
import sqlite3

class GestorNadadores:
    def __init__(self, db_path="nadadores_master_competitivos.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.crear_tabla()

    def crear_tabla(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS nadadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                fecha_nacimiento DATE NOT NULL,
                rut TEXT UNIQUE,
                genero TEXT,
                categoria_master TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

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
        self.conn.execute('''
            INSERT INTO nadadores (nombre, apellido, fecha_nacimiento, rut, genero, categoria_master)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, apellido, fecha_nacimiento, rut, genero, categoria))
        self.conn.commit()

    def listar_nadadores(self):
        cursor = self.conn.execute('SELECT * FROM nadadores ORDER BY apellido, nombre')
        return [dict(row) for row in cursor.fetchall()]

    def obtener_nadador(self, nadador_id):
        cursor = self.conn.execute('SELECT * FROM nadadores WHERE id = ?', (nadador_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def actualizar_nadador(self, nadador_id, nombre, apellido, fecha_nacimiento, rut=None, genero=None):
        categoria = self.calcular_categoria_master(fecha_nacimiento)
        self.conn.execute('''
            UPDATE nadadores 
            SET nombre = ?, apellido = ?, fecha_nacimiento = ?, rut = ?, genero = ?, categoria_master = ?
            WHERE id = ?
        ''', (nombre, apellido, fecha_nacimiento, rut, genero, categoria, nadador_id))
        self.conn.commit()

    def eliminar_nadador(self, nadador_id):
        """Elimina un nadador y sus tiempos asociados."""
        cursor = self.conn.cursor()
        # Elimina primero los tiempos
        cursor.execute('DELETE FROM tiempos WHERE LOWER(nombre_nadador) = LOWER((SELECT nombre || " " || apellido FROM nadadores WHERE id = ? LIMIT 1))', (nadador_id,))
        # Elimina el nadador
        cursor.execute('DELETE FROM nadadores WHERE id = ?', (nadador_id,))
        self.conn.commit()

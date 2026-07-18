from datetime import datetime, date
import os

try:
    import psycopg
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
        db_url = os.environ.get('DATABASE_URL')
        print("DEBUG nadadores - DATABASE_URL:", bool(db_url))
        
        if db_url and 'postgresql' in db_url and POSTGRES_AVAILABLE:
            try:
                print("🔗 Conectando a Neon PostgreSQL para nadadores...")
                self.conn = psycopg.connect(db_url)
                self.conn.autocommit = True
                print("✅ Conexión PostgreSQL exitosa!")
                return
            except Exception as e:
                print("❌ Error PostgreSQL nadadores:", e)
        
        print("🔗 Usando SQLite local para nadadores...")
        import sqlite3
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def ensure_connection(self):
        if not self.conn or getattr(self.conn, 'closed', True):
            print("🔄 Reconectando a la base de datos...")
            self.connect()
        return self.conn

    def _execute(self, query, params=None, commit=True):
        self.ensure_connection()
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

    def _row_to_dict(self, row, cursor=None):
        if not row:
            return None
        if hasattr(row, '_asdict'):
            return dict(row._asdict())
        elif hasattr(row, 'keys'):
            return dict(row)
        elif cursor and hasattr(cursor, 'description'):
            return dict(zip([desc[0] for desc in cursor.description], row))
        else:
            return dict(row) if hasattr(row, '__iter__') else {}

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
        result = []
        for row in rows:
            if row:
                result.append(self._row_to_dict(row, cursor))
        return result

    def obtener_nadador(self, nadador_id):
        cursor = self._execute('SELECT * FROM nadadores WHERE id = ?', (nadador_id,), commit=False)
        row = cursor.fetchone()
        return self._row_to_dict(row, cursor)

    def actualizar_nadador(self, nadador_id, nombre, apellido, fecha_nacimiento, rut=None, genero=None):
        categoria = self.calcular_categoria_master(fecha_nacimiento)
        self._execute('''
            UPDATE nadadores 
            SET nombre = ?, apellido = ?, fecha_nacimiento = ?, rut = ?, genero = ?, categoria_master = ?
            WHERE id = ?
        ''', (nombre, apellido, fecha_nacimiento, rut, genero, categoria, nadador_id))

    def eliminar_nadador(self, nadador_id):
        self._execute('''
            DELETE FROM tiempos 
            WHERE LOWER(nombre_nadador) = LOWER(
                (SELECT nombre || ' ' || apellido FROM nadadores WHERE id = ? LIMIT 1)
            )
        ''', (nadador_id,))
        self._execute('DELETE FROM nadadores WHERE id = ?', (nadador_id,))

    def importar_csv(self, file):
        import csv
        import io
        from datetime import datetime
    
        contenido = file.read()
    
        if isinstance(contenido, bytes):
            try:
                contenido = contenido.decode("utf-8-sig")
            except UnicodeDecodeError:
                contenido = contenido.decode("latin-1")
    
        importados = 0
        omitidos = 0
        errores = []
    
        # Tus datos están separados por comas.
        # No usamos Sniffer porque estaba detectando incorrectamente
        # el separador del archivo.
        lector = csv.reader(
            io.StringIO(contenido),
            delimiter=","
        )
    
        for numero_fila, fila in enumerate(lector, start=1):
            try:
                # Eliminar espacios y columnas vacías sobrantes
                fila = [
                    str(celda).strip()
                    for celda in fila
                ]
    
                while fila and fila[-1] == "":
                    fila.pop()
    
                if not fila:
                    continue
    
                # Respaldo: si todo quedó dentro de la primera celda,
                # volver a separar esa celda por comas.
                if len(fila) == 1 and "," in fila[0]:
                    fila = [
                        celda.strip()
                        for celda in fila[0].split(",")
                    ]
    
                if len(fila) < 5:
                    raise ValueError(
                        f"Se esperaban 5 columnas y llegaron "
                        f"{len(fila)}: {fila}"
                    )
    
                # Orden real del archivo:
                # Nombre, Apellido, RUT, Fecha Nacimiento, Genero
                nombre = fila[0].strip()
                apellido = fila[1].strip()
                rut = fila[2].strip()
                fecha_csv = fila[3].strip()
                genero = fila[4].strip()
    
                # Ignorar encabezado
                if numero_fila == 1 and nombre.lower() in {
                    "nombre",
                    "nombres"
                }:
                    continue
    
                if not nombre:
                    raise ValueError(
                        "El nombre está vacío"
                    )
    
                if not apellido:
                    raise ValueError(
                        "El apellido está vacío"
                    )
    
                # Normalizar género
                genero_normalizado = genero.lower()
    
                if genero_normalizado in {
                    "masculino",
                    "m",
                    "hombre"
                }:
                    genero = "Masculino"
    
                elif genero_normalizado in {
                    "femenino",
                    "f",
                    "mujer"
                }:
                    genero = "Femenino"
    
                else:
                    raise ValueError(
                        f"Género inválido: {genero}"
                    )
    
                # Convertir fecha
                fecha_nacimiento = None
    
                formatos_fecha = [
                    "%d-%m-%Y",
                    "%d/%m/%Y",
                    "%Y-%m-%d"
                ]
    
                for formato in formatos_fecha:
                    try:
                        fecha_nacimiento = datetime.strptime(
                            fecha_csv,
                            formato
                        ).date()
                        break
                    except ValueError:
                        continue
    
                if fecha_nacimiento is None:
                    raise ValueError(
                        f"Fecha inválida: {fecha_csv}. "
                        "Use DD-MM-AAAA."
                    )
    
                # Normalizar RUT
                rut = rut.replace(".", "").strip()
    
                if not rut:
                    rut = None
    
                categoria = self.calcular_categoria_master(
                    fecha_nacimiento
                )
    
                # Buscar duplicado por RUT
                if rut:
                    cursor_rut = self._execute("""
                        SELECT id
                        FROM nadadores
                        WHERE LOWER(TRIM(rut)) =
                              LOWER(TRIM(?))
                        LIMIT 1
                    """, (
                        rut,
                    ), commit=False)
    
                    if cursor_rut.fetchone():
                        omitidos += 1
    
                        print(
                            f"Fila {numero_fila} omitida: "
                            f"ya existe el RUT {rut}"
                        )
                        continue
    
                # Buscar duplicado por nombre, apellido y fecha
                cursor_duplicado = self._execute("""
                    SELECT id
                    FROM nadadores
                    WHERE LOWER(TRIM(nombre)) =
                          LOWER(TRIM(?))
                      AND LOWER(TRIM(apellido)) =
                          LOWER(TRIM(?))
                      AND fecha_nacimiento = ?
                    LIMIT 1
                """, (
                    nombre,
                    apellido,
                    fecha_nacimiento
                ), commit=False)
    
                if cursor_duplicado.fetchone():
                    omitidos += 1
    
                    print(
                        f"Fila {numero_fila} omitida: "
                        f"{nombre} {apellido} ya existe"
                    )
                    continue
    
                self._execute("""
                    INSERT INTO nadadores (
                        nombre,
                        apellido,
                        fecha_nacimiento,
                        rut,
                        genero,
                        categoria_master
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    nombre,
                    apellido,
                    fecha_nacimiento,
                    rut,
                    genero,
                    categoria
                ))
    
                importados += 1
    
            except Exception as e:
                mensaje = (
                    f"Fila {numero_fila}: {str(e)}"
                )
    
                errores.append(mensaje)
    
                print(
                    f"Error importando nadador, "
                    f"fila {numero_fila} {fila}: {e}"
                )
    
        print(
            f"Importación de nadadores terminada: "
            f"{importados} importados, "
            f"{omitidos} omitidos, "
            f"{len(errores)} errores."
        )
    
        if errores:
            print("Primeros errores:")
    
            for error in errores[:10]:
                print(f"- {error}")
    
        if importados == 0 and errores:
            raise ValueError(
                "No se importó ningún nadador. "
                "Primeros errores: "
                + "; ".join(errores[:5])
            )
    
        return {
            "importados": importados,
            "omitidos": omitidos,
            "errores": errores
        }

    def cerrar_conexion(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass

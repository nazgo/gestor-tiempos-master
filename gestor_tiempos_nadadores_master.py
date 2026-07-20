#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Gestión de Tiempos para Nadadores Master de Nivel Competitivo
"""

import os
import csv
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any

try:
    import psycopg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class GestorTiemposMaster:
    ESTILOS = ['Mariposa', 'Espalda', 'Pecho', 'Crol', 'Combinado']
    DISTANCIAS = [50, 100, 200, 400, 800, 1500]

    def __init__(self):
        self.conn = None
        self.connect()
        self.crear_tabla()

    def connect(self):
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
        
        print("⚠️ Usando SQLite local.")
        import sqlite3
        self.conn = sqlite3.connect("nadadores_master_competitivos.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def ensure_connection(self):
        """Asegura que la conexión esté abierta."""
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

    def crear_tabla(self) -> None:
        cursor = self.conn.cursor()
        self._execute('''
            CREATE TABLE IF NOT EXISTS tiempos (
                id SERIAL PRIMARY KEY,
                nombre_nadador TEXT NOT NULL,
                estilo TEXT NOT NULL,
                distancia INTEGER NOT NULL,
                piscina TEXT DEFAULT '25 metros',
                tiempo TEXT NOT NULL,
                tiempo_segundos REAL NOT NULL,
                fecha DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self._execute("""
            ALTER TABLE tiempos
            ADD COLUMN IF NOT EXISTS genero VARCHAR(20)
        """)
        
        self._execute("""
            ALTER TABLE tiempos
            ADD COLUMN IF NOT EXISTS categoria VARCHAR(30)
        """)

        self._execute("""
            ALTER TABLE tiempos
            ADD COLUMN IF NOT EXISTS competencia_id INTEGER
        """)
        
        self._execute('''
            CREATE INDEX IF NOT EXISTS idx_nombre_estilo_dist ON tiempos(nombre_nadador, estilo, distancia)
        ''')
        self._execute('CREATE INDEX IF NOT EXISTS idx_fecha ON tiempos(fecha)')

        self._execute("""
            CREATE TABLE IF NOT EXISTS asistencia_competencias (
                id SERIAL PRIMARY KEY,
                nadador_id INTEGER NOT NULL,
                competencia_id INTEGER NOT NULL,
                estado VARCHAR(20) DEFAULT 'SIN_REGISTRO',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (nadador_id, competencia_id)
            )
        """)

        self._execute("""
        CREATE TABLE IF NOT EXISTS competencias (
            id SERIAL PRIMARY KEY,
            fecha DATE NOT NULL,
            mes VARCHAR(20),
            lugar VARCHAR(100),
            organiza VARCHAR(100),
            nombre VARCHAR(200),
            tipo_piscina VARCHAR(50),
            estado VARCHAR(20) DEFAULT 'NO REALIZADO'
        )
        """)

        self._execute("""
            ALTER TABLE competencias
            ADD COLUMN IF NOT EXISTS fecha DATE
        """)
        
        self._execute("""
            ALTER TABLE competencias
            ADD COLUMN IF NOT EXISTS mes VARCHAR(20)
        """)
        
        self._execute("""
            ALTER TABLE competencias
            ADD COLUMN IF NOT EXISTS lugar VARCHAR(100)
        """)
        
        self._execute("""
            ALTER TABLE competencias
            ADD COLUMN IF NOT EXISTS organiza VARCHAR(100)
        """)
        
        self._execute("""
            ALTER TABLE competencias
            ADD COLUMN IF NOT EXISTS nombre VARCHAR(200)
        """)
        
        self._execute("""
            ALTER TABLE competencias
            ADD COLUMN IF NOT EXISTS tipo_piscina VARCHAR(50)
        """)
        
        self._execute("""
            ALTER TABLE competencias
            ADD COLUMN IF NOT EXISTS estado VARCHAR(20)
            DEFAULT 'NO REALIZADO'
        """)

        self._execute("""
            ALTER TABLE competencias
            ALTER COLUMN mes TYPE VARCHAR(20)
            USING mes::VARCHAR
        """)

        self.inicializar_competencias()
    
        self.conn.commit()

    def cerrar_conexion(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass

    def inicializar_competencias(self):
    
        cursor = self._execute(
            "SELECT COUNT(*) FROM competencias",
            commit=False
        )
    
        row = cursor.fetchone()
    
        # Compatible con PostgreSQL y SQLite
        if hasattr(row, "_asdict"):
            total = list(row._asdict().values())[0]
        elif hasattr(row, "keys"):
            total = list(dict(row).values())[0]
        else:
            total = row[0]
    
        if total > 0:
            print(f"✅ Ya existen {total} competencias.")
            return
    
        print("📅 Cargando competencias iniciales...")

        competencias = [
        
            ("2026-03-14", "MARZO", "Santiago", "FCHMN",
             "II Copa Cordillera de los Andes (CHI)",
             "50 metros (cubierta)", "REALIZADO"),
        
            ("2026-03-28", "MARZO", "Mendoza", "TyC MASTER ARGENTINA",
             "II Copa Cordillera de los Andes (ARG)",
             "25 metros (cubierta)", "REALIZADO"),
        
            ("2026-03-28", "MARZO", "Santiago", "Stadio Italiano",
             "XXII Copa Italia Master",
             "50 metros (abierta)", "REALIZADO"),
        
            ("2026-04-13", "ABRIL", "Recife-BRA", "CONSA DA",
             "XIV Campeonato Sudamericano Master",
             "25 metros (abierta)", "REALIZADO"),
        
            ("2026-05-16", "MAYO", "Santiago", "Peñalolén Master",
             "XIII Copa Peñalolen Master",
             "25 metros (cubierta)", "REALIZADO"),
        
            ("2026-05-31", "MAYO", "Santiago", "Smart Swim Team",
             "VII Copa Smart Swim",
             "50 metros (cubierta)", "REALIZADO"),
        
            ("2026-06-20", "JUNIO", "Santiago", "Santiago Deporte",
             "VI Copa Santiago Deportes",
             "50 metros (cubierta)", "REALIZADO"),
        
            ("2026-07-04", "JULIO", "Santiago", "Master San Bernardo",
             "X Copa Master San Bernardo",
             "25 metros (cubierta)", "REALIZADO"),
        
            ("2026-07-18", "JULIO", "Santiago", "Ñuñoa Master",
             "III Copa Ñuñoa Master",
             "50 metros (cubierta)", "NO REALIZADO"),
        
            ("2026-08-08", "AGOSTO", "Talca", "FCHMN",
             "IV Copa del Maule",
             "25 metros (cubierta)", "NO REALIZADO"),
        
            ("2026-08-22", "AGOSTO", "Santiago", "LQBLO",
             "VI Copa Master LQBLO",
             "50 metros (cubierta)", "NO REALIZADO"),
        
            ("2026-09-05", "SEPTIEMBRE", "Temuco", "Master del Ñielol",
             "VII Copa Araucania de Natación Master",
             "25 metros (cubierta)", "NO REALIZADO"),
        
            ("2026-10-03", "OCTUBRE", "Santiago", "Estadio Español",
             "XVI Copa España Master",
             "25 metros (cubierta)", "NO REALIZADO"),
        
            ("2026-10-17", "OCTUBRE", "Por definir", "Aguas Abiertas Chile",
             "9ª Versión Aguas Abiertas",
             "Por definir", "NO REALIZADO"),
        
            ("2026-10-21", "OCTUBRE", "Buenos Aires - Argentina", "UANA",
             "Campeonato Panamericano Master",
             "50 metros (cubierta)", "NO REALIZADO"),
        
            ("2026-10-24", "OCTUBRE", "Santiago", "Master Providencia",
             "XIV Copa 4 Estilos Master Providencia",
             "25 metros (cubierta)", "NO REALIZADO"),
        
            ("2026-11-07", "NOVIEMBRE", "Santiago", "U. Católica Master",
             "V Copa UC Master",
             "50 metros (cubierta)", "NO REALIZADO"),
        
            ("2026-12-04", "DICIEMBRE", "Arica", "Mantarrayas de Arica",
             "Natación Sin Fronteras",
             "50 metros (abierta)", "NO REALIZADO"),
        
            ("2026-12-12", "DICIEMBRE", "Santiago", "Natación Recoleta",
             "XII Copa Natación Recoleta",
             "25 metros (abierta)", "NO REALIZADO"),
        
            ("2027-01-06", "ENERO", "Por definir", "FCHMN",
             "XXI Cto. Nacional de Natación Master",
             "Por definir", "NO REALIZADO")
        
        ]

        for competencia in competencias:
            self._execute("""
                INSERT INTO competencias
                (
                    fecha,
                    mes,
                    lugar,
                    organiza,
                    nombre,
                    tipo_piscina,
                    estado
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, competencia)
    
        print(f"✅ Se cargaron {len(competencias)} competencias.")

    # ====================== MÉTODOS ESTÁTICOS ======================
    @staticmethod
    def _validar_tiempo(tiempo_str: str) -> bool:
        if not tiempo_str or not isinstance(tiempo_str, str):
            return False
        tiempo_str = tiempo_str.strip().upper()
        if tiempo_str in ['DQ', 'DNS', 'DNF']:
            return True
        # Acepta cualquier cosa que tenga : y .
        return ':' in tiempo_str and '.' in tiempo_str
    
    @staticmethod
    def convertir_tiempo_a_segundos(self, tiempo):
        if tiempo is None:
            raise ValueError("El tiempo no puede estar vacío")
    
        tiempo = str(tiempo).strip().replace(",", ".")
    
        try:
            if ":" in tiempo:
                partes = tiempo.split(":")
    
                if len(partes) != 2:
                    raise ValueError(
                        "Formato inválido. Use MM:SS.cc"
                    )
    
                minutos = int(partes[0])
                segundos = float(partes[1])
    
                if minutos < 0:
                    raise ValueError(
                        "Los minutos no pueden ser negativos"
                    )
    
                if segundos < 0 or segundos >= 60:
                    raise ValueError(
                        "Los segundos deben estar entre 0 y 59.99"
                    )
    
                return round(
                    minutos * 60 + segundos,
                    2
                )
    
            segundos = float(tiempo)
    
            if segundos < 0:
                raise ValueError(
                    "El tiempo no puede ser negativo"
                )
    
            return round(segundos, 2)
    
        except ValueError as e:
            mensajes_controlados = {
                "Formato inválido. Use MM:SS.cc",
                "Los minutos no pueden ser negativos",
                "Los segundos deben estar entre 0 y 59.99",
                "El tiempo no puede ser negativo"
            }
    
            if str(e) in mensajes_controlados:
                raise
    
            raise ValueError(
                "Formato de tiempo inválido. "
                "Debe ser MM:SS.cc, por ejemplo 01:23.45"
            )

    # ====================== CRUD BÁSICO ======================
    def agregar_tiempo(self, nombre, estilo, distancia, tiempo, fecha=None, piscina="25 metros", competencia_id=None):
        """Agrega un nuevo registro de tiempo."""
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del nadador no puede estar vacío.")
        if estilo not in self.ESTILOS:
            raise ValueError(f"Estilo inválido. Opciones: {', '.join(self.ESTILOS)}")
        
        # Aceptar distancias de 25m y 50m
        distancias_validas = [25, 50, 100, 200, 400, 800, 1500]
        if distancia not in distancias_validas:
            raise ValueError(f"Distancia inválida. Opciones: {distancias_validas}")

        if fecha is None:
            fecha = date.today()

        # Manejo de tiempos especiales (DQ, DNS, DNF)
        if str(tiempo).upper() in ['DQ', 'DNS', 'DNF']:
            tiempo_str = str(tiempo).upper()
            tiempo_segundos = 9999.99
        else:
            if not self._validar_tiempo(tiempo):
                raise ValueError("Formato de tiempo inválido. Debe ser MM:SS.cc (ej: 01:23.45)")
            tiempo_str = tiempo
            tiempo_segundos = self._convertir_a_segundos(tiempo)

        self._execute('''
            INSERT INTO tiempos
            (nombre_nadador, estilo, distancia, piscina, tiempo, tiempo_segundos, fecha, competencia_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nombre.title(), estilo, distancia, piscina, tiempo_str, tiempo_segundos, fecha.isoformat(), competencia_id))

    def convertir_tiempo_a_segundos(self, tiempo):
        """
        Convierte tiempos en formato MM:SS.cc o SS.cc a segundos.
        Ejemplos:
        01:23.45 -> 83.45
        59.32 -> 59.32
        """
        if tiempo is None:
            raise ValueError("El tiempo no puede estar vacío")
    
        tiempo = str(tiempo).strip().replace(",", ".")
    
        try:
            if ":" in tiempo:
                partes = tiempo.split(":")
    
                if len(partes) != 2:
                    raise ValueError(
                        "Formato inválido. Use MM:SS.cc"
                    )
    
                minutos = int(partes[0])
                segundos = float(partes[1])
    
                if minutos < 0 or segundos < 0 or segundos >= 60:
                    raise ValueError(
                        "Minutos o segundos fuera de rango"
                    )
    
                return round((minutos * 60) + segundos, 2)
    
            segundos = float(tiempo)
    
            if segundos < 0:
                raise ValueError(
                    "El tiempo no puede ser negativo"
                )
    
            return round(segundos, 2)
    
        except ValueError as e:
            if str(e) in (
                "Formato inválido. Use MM:SS.cc",
                "Minutos o segundos fuera de rango",
                "El tiempo no puede ser negativo"
            ):
                raise
    
            raise ValueError(
                "Formato de tiempo inválido. Use MM:SS.cc, por ejemplo 01:23.45"
            )

    def marcar_asistencia_desde_tiempo(
        self,
        nadador_id,
        competencia_id
    ):
        if not nadador_id or not competencia_id:
            return
    
        self._execute("""
            INSERT INTO asistencia_competencias (
                nadador_id,
                competencia_id,
                estado,
                updated_at
            )
            VALUES (?, ?, 'PRESENTE', CURRENT_TIMESTAMP)
            ON CONFLICT (nadador_id, competencia_id)
            DO UPDATE SET
                estado = 'PRESENTE',
                updated_at = CURRENT_TIMESTAMP
        """, (
            nadador_id,
            competencia_id
        ))

    def obtener_tiempo_por_id(self, tiempo_id):
        cursor = self._execute('SELECT * FROM tiempos WHERE id = ?', (tiempo_id,), commit=False)
        row = cursor.fetchone()
        return self._row_to_dict(row, cursor)

    def actualizar_tiempo(self, tiempo_id, nombre, estilo, distancia, piscina, tiempo, fecha):
        tiempo_segundos = self._convertir_a_segundos(tiempo)
        self._execute('''
            UPDATE tiempos 
            SET nombre_nadador = ?, estilo = ?, distancia = ?, piscina = ?, 
                tiempo = ?, tiempo_segundos = ?, fecha = ?
            WHERE id = ?
        ''', (nombre, estilo, distancia, piscina, tiempo, tiempo_segundos, fecha, tiempo_id))

    def eliminar_tiempo(self, tiempo_id):
        self._execute('DELETE FROM tiempos WHERE id = ?', (tiempo_id,))

    # ====================== CONSULTAS AVANZADAS ======================
    def obtener_season_best(self, nadador_id):
        """
        Devuelve el mejor tiempo de cada combinación:
        estilo + distancia + piscina para un nadador.
        """
    
        cursor = self._execute("""
            SELECT DISTINCT ON (
                LOWER(t.estilo),
                t.distancia,
                LOWER(t.piscina)
            )
                t.id,
                t.fecha,
                t.estilo,
                t.distancia,
                t.piscina,
                t.tiempo,
                t.tiempo_segundos
            FROM tiempos t
            WHERE LOWER(t.nombre_nadador) = LOWER(
                (
                    SELECT nombre || ' ' || apellido
                    FROM nadadores
                    WHERE id = ?
                    LIMIT 1
                )
            )
            ORDER BY
                LOWER(t.estilo),
                t.distancia,
                LOWER(t.piscina),
                t.tiempo_segundos ASC,
                t.fecha ASC
        """, (nadador_id,), commit=False)
    
        filas = cursor.fetchall()
        columnas = [
            columna[0]
            for columna in cursor.description
        ]
    
        resultado = []
    
        for fila in filas:
            if hasattr(fila, "_asdict"):
                resultado.append(dict(fila._asdict()))
            elif hasattr(fila, "keys"):
                resultado.append(dict(fila))
            else:
                resultado.append(
                    dict(zip(columnas, fila))
                )
    
        return resultado

    def obtener_season_best_avanzado(self, nombre=None, estilo=None, distancia=None, categoria=None, year=None):
        if year is None:
            year = datetime.now().year

        query = '''
            SELECT t.*, n.categoria_master 
            FROM tiempos t
            LEFT JOIN nadadores n ON LOWER(t.nombre_nadador) = LOWER(n.nombre || ' ' || n.apellido)
            WHERE EXTRACT(YEAR FROM t.fecha) = ?
        '''
        params = [year]

        if nombre:
            query += " AND LOWER(t.nombre_nadador) LIKE LOWER(?)"
            params.append(f"%{nombre}%")
        if estilo:
            query += " AND t.estilo = ?"
            params.append(estilo)
        if distancia:
            query += " AND t.distancia = ?"
            params.append(int(distancia))
        if categoria:
            query += " AND n.categoria_master = ?"
            params.append(categoria)

        query += " ORDER BY t.tiempo_segundos ASC LIMIT 1"

        cursor = self._execute(query, params, commit=False)
        row = cursor.fetchone()
        return self._row_to_dict(row, cursor)

    def obtener_todos_los_tiempos(self, nombre_filtro: Optional[str] = None) -> List[Dict[str, Any]]:
        if nombre_filtro:
            cursor = self._execute('''
                SELECT * FROM tiempos 
                WHERE LOWER(nombre_nadador) LIKE LOWER(?)
                ORDER BY fecha DESC, tiempo_segundos ASC
            ''', (f"%{nombre_filtro.strip()}%",), commit=False)
        else:
            cursor = self._execute('''
                SELECT * FROM tiempos 
                ORDER BY fecha DESC, nombre_nadador, estilo, distancia
            ''', commit=False)
        
        return [self._row_to_dict(row, cursor) for row in cursor.fetchall() if row]

    def obtener_tiempos_nadador(self, nombre_completo):
        cursor = self._execute('''
            SELECT * FROM tiempos 
            WHERE LOWER(nombre_nadador) = LOWER(?)
            ORDER BY fecha ASC, tiempo_segundos ASC
        ''', (nombre_completo,), commit=False)
        return [self._row_to_dict(row, cursor) for row in cursor.fetchall() if row]

    # ====================== ESTADÍSTICAS ======================
    def obtener_estadisticas_nadador(self, nombre: str) -> Dict[str, Any]:
        tiempos = self.obtener_todos_los_tiempos(nombre)
        if not tiempos:
            return {"total_registros": 0}
        return {
            "total_registros": len(tiempos),
            "pruebas_unicas": len(set(f"{t['estilo']}_{t['distancia']}" for t in tiempos)),
            "mejor_tiempo_general": min(t['tiempo_segundos'] for t in tiempos),
            "primera_fecha": min(t['fecha'] for t in tiempos),
            "ultima_fecha": max(t['fecha'] for t in tiempos)
        }

    def obtener_estadisticas_club(self):
        año_actual = datetime.now().year

        cursor = self._execute('''
            SELECT COUNT(*) as total_tiempos, 
                   COUNT(DISTINCT nombre_nadador) as total_nadadores 
            FROM tiempos
        ''', commit=False)
        row = cursor.fetchone()
        general = self._row_to_dict(row, cursor) or {}

        cursor = self._execute('''
            SELECT COUNT(DISTINCT nombre_nadador) as activos_este_año
            FROM tiempos 
            WHERE EXTRACT(YEAR FROM fecha) = ?
        ''', (año_actual,), commit=False)
        row = cursor.fetchone()
        activos = self._row_to_dict(row, cursor)['activos_este_año'] if row else 0

        cursor = self._execute("SELECT DISTINCT EXTRACT(YEAR FROM fecha) as ano FROM tiempos WHERE fecha IS NOT NULL", commit=False)
        años = cursor.fetchall()
        temporadas = len(años)

        cursor = self._execute('''
            SELECT nombre_nadador, COUNT(*) as total_tiempos
            FROM tiempos 
            WHERE EXTRACT(YEAR FROM fecha) = ?
            GROUP BY nombre_nadador 
            ORDER BY total_tiempos DESC 
            LIMIT 10
        ''', (año_actual,), commit=False)
        mas_activos = [self._row_to_dict(row, cursor) for row in cursor.fetchall() if row]

        cursor = self._execute('''
            SELECT nombre_nadador, estilo, distancia, tiempo, fecha
            FROM tiempos
            ORDER BY tiempo_segundos ASC
            LIMIT 10
        ''', commit=False)
        por_prueba = [self._row_to_dict(row, cursor) for row in cursor.fetchall() if row]

        return {
            'general': general,
            'activos_este_año': activos,
            'temporadas': temporadas,
            'mas_activos': mas_activos,
            'por_prueba': por_prueba
        }

    def obtener_top_4_por_categoria_genero_estilo(
        self,
        piscina="50 metros",
        anio=2026
    ):
        cursor = self._execute("""
            WITH ranking AS (
                SELECT
                    COALESCE(
                        t.categoria,
                        n.categoria_master,
                        'Sin categoría'
                    ) AS categoria_master,
    
                    COALESCE(
                        t.genero,
                        n.genero,
                        'Sin género'
                    ) AS genero,
    
                    t.estilo,
                    t.distancia,
                    t.tiempo,
                    t.tiempo_segundos,
                    t.fecha,
                    t.nombre_nadador,
    
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            COALESCE(
                                t.categoria,
                                n.categoria_master,
                                'Sin categoría'
                            ),
                            COALESCE(
                                t.genero,
                                n.genero,
                                'Sin género'
                            ),
                            t.estilo,
                            t.distancia
                        ORDER BY
                            t.tiempo_segundos ASC,
                            t.fecha ASC
                    ) AS posicion
    
                FROM tiempos t
    
                LEFT JOIN nadadores n
                    ON LOWER(TRIM(t.nombre_nadador)) =
                       LOWER(TRIM(n.nombre || ' ' || n.apellido))
    
                WHERE LOWER(TRIM(t.piscina)) = LOWER(TRIM(?))
                  AND EXTRACT(YEAR FROM t.fecha) = ?
                  AND t.distancia IN (50, 100)
                  AND NOT (
                      LOWER(TRIM(t.estilo)) = 'combinado'
                      AND t.distancia = 100
                  )
            )
    
            SELECT
                categoria_master,
                genero,
                estilo,
                distancia,
                tiempo,
                fecha,
                nombre_nadador,
                posicion
    
            FROM ranking
    
            WHERE posicion <= 4
    
            ORDER BY
                categoria_master,
                genero,
                distancia,
                estilo,
                posicion
        """, (
            piscina,
            anio
        ), commit=False)
    
        filas = cursor.fetchall()
    
        return [
            self._row_to_dict(fila, cursor)
            for fila in filas
            if fila
        ]

    # ====================== EXPORTACIONES ======================
    def exportar_a_csv(self, filepath: Optional[str] = None) -> str:
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"export_tiempos_master_{timestamp}.csv"

        registros = self.obtener_todos_los_tiempos()
        if not registros:
            raise ValueError("No hay datos para exportar.")

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['ID', 'Nombre Nadador', 'Estilo', 'Distancia (m)', 
                         'Tiempo (MM:SS.cc)', 'Tiempo (segundos)', 'Fecha', 'Fecha Creación']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for reg in registros:
                writer.writerow({
                    'ID': reg['id'],
                    'Nombre Nadador': reg['nombre_nadador'],
                    'Estilo': reg['estilo'],
                    'Distancia (m)': reg['distancia'],
                    'Tiempo (MM:SS.cc)': reg['tiempo'],
                    'Tiempo (segundos)': round(reg['tiempo_segundos'], 2),
                    'Fecha': reg['fecha'],
                    'Fecha Creación': reg.get('created_at')
                })
        return filepath

    def exportar_a_pdf(self, tiempos):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet

        pdf_path = "tiempos_export.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()

        data = [['Nadador', 'Prueba', 'Tiempo', 'Fecha']]
        for t in tiempos:
            data.append([
                t['nombre_nadador'],
                f"{t['estilo']} {t['distancia']}m",
                t['tiempo'],
                t['fecha']
            ])

        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        doc.build([Paragraph("Reporte de Tiempos - Natación Ñuñoa Master", styles['Title']), table])
        return pdf_path

    def importar_csv(self, file):
        import csv
        import io
        from datetime import datetime
    
        contenido = file.read()
    
        # Decodificar el archivo
        if isinstance(contenido, bytes):
            try:
                contenido = contenido.decode("utf-8-sig")
            except UnicodeDecodeError:
                contenido = contenido.decode("latin-1")
    
        # Detectar automáticamente si usa coma o punto y coma
        muestra = contenido[:2048]
    
        try:
            dialecto = csv.Sniffer().sniff(
                muestra,
                delimiters=",;"
            )
    
            lector = csv.reader(
                io.StringIO(contenido),
                dialecto
            )
    
        except csv.Error:
            lector = csv.reader(
                io.StringIO(contenido),
                delimiter=","
            )
    
        importados = 0
        omitidos = 0
        errores = []
    
        for numero_fila, fila in enumerate(lector, start=1):
            try:
                # Ignorar filas completamente vacías
                if not fila or not any(
                    str(celda).strip()
                    for celda in fila
                ):
                    continue
    
                # Se permiten:
                # 8 columnas: sin competencia
                # 9 columnas: con competencia
                if len(fila) not in (8, 9):
                    raise ValueError(
                        f"Se esperaban 8 o 9 columnas y llegaron "
                        f"{len(fila)}."
                    )
    
                nombre = fila[0].strip()
                genero = fila[1].strip()
                estilo = fila[2].strip()
                piscina_csv = fila[3].strip()
                distancia_csv = fila[4].strip()
                categoria = fila[5].strip()
                tiempo = fila[6].strip()
                fecha_csv = fila[7].strip()
    
                competencia_csv = (
                    fila[8].strip()
                    if len(fila) >= 9
                    else ""
                )
    
                # Ignorar encabezado
                if numero_fila == 1 and nombre.lower() in {
                    "nombre",
                    "nadador",
                    "nombre_nadador",
                    "nombre nadador"
                }:
                    continue
    
                # Validaciones básicas
                if not nombre:
                    raise ValueError(
                        "El nombre del nadador está vacío"
                    )
    
                if not estilo:
                    raise ValueError(
                        "El estilo está vacío"
                    )
    
                genero_normalizado = genero.lower()
    
                if genero_normalizado == "masculino":
                    genero = "Masculino"
    
                elif genero_normalizado == "femenino":
                    genero = "Femenino"
    
                else:
                    raise ValueError(
                        f"Género inválido: {genero}"
                    )
    
                if not categoria:
                    raise ValueError(
                        "La categoría está vacía"
                    )
    
                try:
                    distancia = int(distancia_csv)
                except ValueError:
                    raise ValueError(
                        f"Distancia inválida: {distancia_csv}"
                    )
    
                # Normalizar piscina
                piscina_normalizada = piscina_csv.lower().strip()
    
                if piscina_normalizada in {
                    "25",
                    "25m",
                    "25 m",
                    "25 metros"
                }:
                    piscina = "25 metros"
    
                elif piscina_normalizada in {
                    "50",
                    "50m",
                    "50 m",
                    "50 metros"
                }:
                    piscina = "50 metros"
    
                else:
                    raise ValueError(
                        f"Piscina inválida: {piscina_csv}"
                    )
    
                # Omitir resultados no válidos como tiempos
                if tiempo.upper() in {
                    "DQ",
                    "DSQ",
                    "DNS",
                    "DNF",
                    "NP",
                    "-"
                }:
                    omitidos += 1
    
                    print(
                        f"Fila {numero_fila} omitida: "
                        f"{nombre} tiene resultado {tiempo}"
                    )
    
                    continue
    
                # Normalizar y convertir el tiempo
                tiempo = tiempo.replace(",", ".").strip()
    
                tiempo_segundos = (
                    self.convertir_tiempo_a_segundos(
                        tiempo
                    )
                )
    
                # Convertir fecha
                fecha = None
    
                formatos_fecha = [
                    "%d-%m-%Y",
                    "%d/%m/%Y",
                    "%Y-%m-%d"
                ]
    
                for formato in formatos_fecha:
                    try:
                        fecha = datetime.strptime(
                            fecha_csv,
                            formato
                        ).date()
    
                        break
    
                    except ValueError:
                        continue
    
                if fecha is None:
                    raise ValueError(
                        f"Fecha inválida: {fecha_csv}. "
                        "Use DD-MM-AAAA."
                    )
    
                # Buscar la competencia por ID o nombre
                competencia_id = None
    
                if competencia_csv:
                    if competencia_csv.isdigit():
                        cursor_competencia = self._execute("""
                            SELECT id
                            FROM competencias
                            WHERE id = ?
                            LIMIT 1
                        """, (
                            int(competencia_csv),
                        ), commit=False)
    
                    else:
                        cursor_competencia = self._execute("""
                            SELECT id
                            FROM competencias
                            WHERE LOWER(TRIM(nombre)) =
                                  LOWER(TRIM(?))
                            LIMIT 1
                        """, (
                            competencia_csv,
                        ), commit=False)
    
                    fila_competencia = (
                        cursor_competencia.fetchone()
                    )
    
                    if not fila_competencia:
                        raise ValueError(
                            "Competencia no encontrada: "
                            f"{competencia_csv}"
                        )
    
                    if hasattr(fila_competencia, "_asdict"):
                        competencia_id = (
                            fila_competencia
                            ._asdict()["id"]
                        )
    
                    elif hasattr(fila_competencia, "keys"):
                        competencia_id = dict(
                            fila_competencia
                        )["id"]
    
                    else:
                        competencia_id = (
                            fila_competencia[0]
                        )
    
                # Buscar el nadador solamente para marcar asistencia
                cursor_nadador = self._execute("""
                    SELECT id
                    FROM nadadores
                    WHERE LOWER(
                        TRIM(nombre || ' ' || apellido)
                    ) = LOWER(TRIM(?))
                    LIMIT 1
                """, (
                    nombre,
                ), commit=False)
    
                fila_nadador = cursor_nadador.fetchone()
                nadador_id = None
    
                if fila_nadador:
                    if hasattr(fila_nadador, "_asdict"):
                        nadador_id = (
                            fila_nadador
                            ._asdict()["id"]
                        )
    
                    elif hasattr(fila_nadador, "keys"):
                        nadador_id = dict(
                            fila_nadador
                        )["id"]
    
                    else:
                        nadador_id = fila_nadador[0]
    
                # Insertar el tiempo
                # La tabla tiempos no tiene nadador_id,
                # por eso se guarda nombre_nadador.
                self._execute("""
                    INSERT INTO tiempos (
                        nombre_nadador,
                        genero,
                        categoria,
                        estilo,
                        distancia,
                        piscina,
                        tiempo,
                        tiempo_segundos,
                        fecha,
                        competencia_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nombre,
                    genero,
                    categoria,
                    estilo,
                    distancia,
                    piscina,
                    tiempo,
                    tiempo_segundos,
                    fecha,
                    competencia_id
                ))
    
                # Marcar asistencia solamente cuando:
                # 1. El nadador existe en nadadores.
                # 2. La competencia está asociada.
                if nadador_id and competencia_id:
                    self.marcar_asistencia_desde_tiempo(
                        nadador_id,
                        competencia_id
                    )
    
                elif competencia_id and not nadador_id:
                    print(
                        f"Advertencia fila {numero_fila}: "
                        f"se importó el tiempo de {nombre}, "
                        "pero no se marcó asistencia porque "
                        "el nadador no existe en la tabla nadadores."
                    )
    
                importados += 1
    
            except Exception as e:
                mensaje = (
                    f"Fila {numero_fila}: {str(e)}"
                )
    
                errores.append(mensaje)
    
                print(
                    f"Error al importar fila "
                    f"{numero_fila} {fila}: {e}"
                )
    
        print(
            f"Importación terminada: "
            f"{importados} importados, "
            f"{omitidos} omitidos, "
            f"{len(errores)} errores."
        )
    
        if errores:
            print("Primeros errores encontrados:")
    
            for error in errores[:10]:
                print(f"- {error}")
    
        if importados == 0 and errores:
            raise ValueError(
                "No se importó ningún tiempo. "
                "Primeros errores: "
                + "; ".join(errores[:5])
            )
    
        return importados

    def __del__(self):
        self.cerrar_conexion()


    def listar_competencias(self):
    
        cursor = self._execute("""
            SELECT *
            FROM competencias
            ORDER BY fecha
        """, commit=False)
    
        rows = cursor.fetchall()
    
        competencias = []
    
        for row in rows:
    
            if hasattr(row, "_asdict"):
                competencias.append(dict(row._asdict()))
    
            elif hasattr(row, "keys"):
                competencias.append(dict(row))
    
            else:
                competencias.append(
                    dict(zip([d[0] for d in cursor.description], row))
                )
    
        return competencias

    def obtener_tabla_asistencia(self, anio):
        cursor_nadadores = self._execute("""
            SELECT
                id,
                nombre,
                apellido
            FROM nadadores
            ORDER BY apellido ASC, nombre ASC
        """, commit=False)
    
        filas_nadadores = cursor_nadadores.fetchall()
    
        nadadores = [
            self._row_to_dict(
                fila,
                cursor_nadadores
            )
            for fila in filas_nadadores
            if fila
        ]
    
        cursor_competencias = self._execute("""
            SELECT
                id,
                fecha,
                nombre
            FROM competencias
            WHERE EXTRACT(YEAR FROM fecha) = ?
            ORDER BY fecha ASC, id ASC
        """, (
            anio,
        ), commit=False)
    
        filas_competencias = (
            cursor_competencias.fetchall()
        )
    
        competencias = [
            self._row_to_dict(
                fila,
                cursor_competencias
            )
            for fila in filas_competencias
            if fila
        ]
    
        ids_competencias = [
            competencia['id']
            for competencia in competencias
        ]
    
        asistencias = {}
    
        if ids_competencias:
            placeholders = ", ".join(
                ["?"] * len(ids_competencias)
            )
    
            cursor_asistencias = self._execute(
                f"""
                SELECT
                    nadador_id,
                    competencia_id,
                    estado
                FROM asistencia_competencias
                WHERE competencia_id IN (
                    {placeholders}
                )
                """,
                tuple(ids_competencias),
                commit=False
            )
    
            for fila in cursor_asistencias.fetchall():
                registro = self._row_to_dict(
                    fila,
                    cursor_asistencias
                )
    
                clave = (
                    registro['nadador_id'],
                    registro['competencia_id']
                )
    
                asistencias[clave] = (
                    registro['estado']
                )
    
        return {
            'nadadores': nadadores,
            'competencias': competencias,
            'asistencias': asistencias
        }

    def actualizar_asistencia(
        self,
        nadador_id,
        competencia_id,
        estado
    ):
        estados_validos = {
            "PRESENTE",
            "AUSENTE",
            "NO_APLICA",
            "SIN_REGISTRO"
        }
    
        if estado not in estados_validos:
            raise ValueError("Estado de asistencia no válido")
    
        cursor = self._execute("""
            SELECT id
            FROM asistencia_competencias
            WHERE nadador_id = ?
              AND competencia_id = ?
        """, (
            nadador_id,
            competencia_id
        ), commit=False)
    
        existente = cursor.fetchone()
    
        if existente:
            self._execute("""
                UPDATE asistencia_competencias
                SET estado = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE nadador_id = ?
                  AND competencia_id = ?
            """, (
                estado,
                nadador_id,
                competencia_id
            ))
        else:
            self._execute("""
                INSERT INTO asistencia_competencias (
                    nadador_id,
                    competencia_id,
                    estado
                )
                VALUES (?, ?, ?)
            """, (
                nadador_id,
                competencia_id,
                estado
            ))

    def actualizar_estado_competencia(self, id_competencia, estado):
    
        self._execute("""
            UPDATE competencias
            SET estado = ?
            WHERE id = ?
        """, (estado, id_competencia))


    def _obtener_mes_competencia(self, fecha):
        """Devuelve el nombre del mes en español."""
        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
    
        meses = [
            "ENERO", "FEBRERO", "MARZO", "ABRIL",
            "MAYO", "JUNIO", "JULIO", "AGOSTO",
            "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
        ]
    
        return meses[fecha.month - 1]
    
    
    def agregar_competencia(
        self,
        fecha,
        lugar,
        organiza,
        nombre,
        tipo_piscina,
        estado="NO REALIZADO"
    ):
        mes = self._obtener_mes_competencia(fecha)
    
        self._execute("""
            INSERT INTO competencias (
                fecha,
                mes,
                lugar,
                organiza,
                nombre,
                tipo_piscina,
                estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            fecha,
            mes,
            lugar,
            organiza,
            nombre,
            tipo_piscina,
            estado
        ))
    
    
    def obtener_competencia(self, competencia_id):
        cursor = self._execute("""
            SELECT *
            FROM competencias
            WHERE id = ?
        """, (competencia_id,), commit=False)
    
        row = cursor.fetchone()
    
        if not row:
            return None
    
        if hasattr(row, "_asdict"):
            return dict(row._asdict())
    
        if hasattr(row, "keys"):
            return dict(row)
    
        columnas = [columna[0] for columna in cursor.description]
        return dict(zip(columnas, row))
    
    
    def editar_competencia(
        self,
        competencia_id,
        fecha,
        lugar,
        organiza,
        nombre,
        tipo_piscina,
        estado
    ):
        mes = self._obtener_mes_competencia(fecha)
    
        self._execute("""
            UPDATE competencias
            SET fecha = ?,
                mes = ?,
                lugar = ?,
                organiza = ?,
                nombre = ?,
                tipo_piscina = ?,
                estado = ?
            WHERE id = ?
        """, (
            fecha,
            mes,
            lugar,
            organiza,
            nombre,
            tipo_piscina,
            estado,
            competencia_id
        ))
    
    
    def eliminar_competencia(self, competencia_id):
        self._execute("""
            DELETE FROM competencias
            WHERE id = ?
        """, (competencia_id,))
    
    
    def actualizar_estado_competencia(self, competencia_id, estado):
        estados_validos = ("REALIZADO", "NO REALIZADO")
    
        if estado not in estados_validos:
            raise ValueError("Estado de competencia no válido")
    
        self._execute("""
            UPDATE competencias
            SET estado = ?
            WHERE id = ?
        """, (estado, competencia_id))

    def comparacion_nadador_25_50(self, nadador_id):
        """
        Compara los mejores tiempos de un nadador en piscinas de 25 y 50 metros.
        Devuelve una lista agrupada por estilo y distancia.
        """
    
        cursor = self._execute("""
            SELECT
                estilo,
                distancia,
                piscina,
                MIN(tiempo_segundos) AS mejor_tiempo_segundos
            FROM tiempos
            WHERE nombre_nadador = (
                SELECT nombre || ' ' || apellido
                FROM nadadores
                WHERE id = ?
            )
            AND piscina IN ('25 metros', '50 metros')
            GROUP BY estilo, distancia, piscina
            ORDER BY distancia, estilo, piscina
        """, (nadador_id,), commit=False)
    
        filas = cursor.fetchall()
        columnas = [col[0] for col in cursor.description]
    
        registros = [
            dict(zip(columnas, fila))
            for fila in filas
        ]
    
        comparacion = {}
    
        for registro in registros:
            clave = (
                registro["estilo"],
                registro["distancia"]
            )
    
            if clave not in comparacion:
                comparacion[clave] = {
                    "estilo": registro["estilo"],
                    "distancia": registro["distancia"],
                    "tiempo_25": None,
                    "tiempo_50": None,
                    "diferencia_segundos": None
                }
    
            piscina = str(registro["piscina"]).lower()
            tiempo = registro["mejor_tiempo_segundos"]
    
            if "25" in piscina:
                comparacion[clave]["tiempo_25"] = tiempo
    
            elif "50" in piscina:
                comparacion[clave]["tiempo_50"] = tiempo
    
        resultado = []
    
        for item in comparacion.values():
            tiempo_25 = item["tiempo_25"]
            tiempo_50 = item["tiempo_50"]
    
            if tiempo_25 is not None and tiempo_50 is not None:
                item["diferencia_segundos"] = round(
                    float(tiempo_50) - float(tiempo_25),
                    2
                )
    
            resultado.append(item)
    
        return resultado

    def obtener_progreso_nadador(
        self,
        nadador_id,
        estilo,
        distancia,
        piscina
    ):
        cursor = self._execute("""
            SELECT
                t.fecha,
                t.tiempo,
                t.tiempo_segundos
            FROM tiempos t
            WHERE LOWER(t.nombre_nadador) = LOWER(
                (
                    SELECT nombre || ' ' || apellido
                    FROM nadadores
                    WHERE id = ?
                    LIMIT 1
                )
            )
            AND LOWER(t.estilo) = LOWER(?)
            AND t.distancia = ?
            AND LOWER(t.piscina) = LOWER(?)
            ORDER BY t.fecha ASC, t.id ASC
        """, (
            nadador_id,
            estilo,
            distancia,
            piscina
        ), commit=False)
    
        filas = cursor.fetchall()
        columnas = [columna[0] for columna in cursor.description]
    
        historial = []
        tiempo_anterior = None
    
        for fila in filas:
            if hasattr(fila, '_asdict'):
                registro = dict(fila._asdict())
            elif hasattr(fila, 'keys'):
                registro = dict(fila)
            else:
                registro = dict(zip(columnas, fila))
    
            tiempo_actual = float(registro['tiempo_segundos'])
    
            if tiempo_anterior is None:
                registro['diferencia'] = None
            else:
                registro['diferencia'] = round(
                    tiempo_actual - tiempo_anterior,
                    2
                )
    
            historial.append(registro)
            tiempo_anterior = tiempo_actual
    
        return historial

    def obtener_tiempo_por_id(self, tiempo_id):
        cursor = self._execute("""
            SELECT *
            FROM tiempos
            WHERE id = ?
        """, (tiempo_id,), commit=False)
    
        fila = cursor.fetchone()
    
        if not fila:
            return None
    
        columnas = [col[0] for col in cursor.description]
    
        if hasattr(fila, "_asdict"):
            return dict(fila._asdict())
    
        if hasattr(fila, "keys"):
            return dict(fila)
    
        return dict(zip(columnas, fila))
    
    def editar_tiempo(
        self,
        tiempo_id,
        estilo,
        distancia,
        tiempo,
        fecha,
        piscina,
        competencia_id=None,
        categoria=None
    ):
        tiempo_segundos = self.convertir_tiempo_a_segundos(tiempo)
    
        self._execute("""
            UPDATE tiempos
            SET estilo = ?,
                distancia = ?,
                tiempo = ?,
                tiempo_segundos = ?,
                fecha = ?,
                piscina = ?,
                competencia_id = ?,
                categoria = ?
            WHERE id = ?
        """, (
            estilo,
            distancia,
            tiempo,
            tiempo_segundos,
            fecha,
            piscina,
            competencia_id,
            categoria,
            tiempo_id
        ))

    def eliminar_tiempo(self, tiempo_id):
        self._execute("""
            DELETE FROM tiempos
            WHERE id = ?
        """, (tiempo_id,))

if __name__ == "__main__":
    gestor = GestorTiemposMaster()
    print("Gestor de Tiempos Master inicializado correctamente.")
    gestor.cerrar_conexion()

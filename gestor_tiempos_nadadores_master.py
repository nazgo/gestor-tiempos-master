#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Gestión de Tiempos para Nadadores Master de Nivel Competitivo
"""

import os
import csv
import re
from datetime import datetime, date, timedelta
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

        # Define si la competencia forma parte del porcentaje oficial anual.
        # Las competencias especiales siguen registrando participación, pero
        # no afectan el porcentaje de asistencia.
        self._execute("""
            ALTER TABLE competencias
            ADD COLUMN IF NOT EXISTS considera_asistencia BOOLEAN DEFAULT TRUE
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

        # Resumen general
        cursor = self._execute("""
            SELECT
                COUNT(*) AS total_tiempos,
                COUNT(DISTINCT nombre_nadador) AS total_nadadores
            FROM tiempos
        """, commit=False)

        row = cursor.fetchone()
        general = self._row_to_dict(row, cursor) or {}

        # Nadadores activos en el año actual
        cursor = self._execute("""
            SELECT
                COUNT(DISTINCT nombre_nadador) AS activos_este_año
            FROM tiempos
            WHERE EXTRACT(YEAR FROM fecha) = ?
        """, (
            año_actual,
        ), commit=False)

        row = cursor.fetchone()

        activos = (
            self._row_to_dict(row, cursor).get(
                'activos_este_año',
                0
            )
            if row
            else 0
        )

        # Número de temporadas
        cursor = self._execute("""
            SELECT DISTINCT
                EXTRACT(YEAR FROM fecha) AS ano
            FROM tiempos
            WHERE fecha IS NOT NULL
        """, commit=False)

        años = cursor.fetchall()
        temporadas = len(años)

        # Los 12 nadadores más activos del año,
        # incluyendo su categoría
        cursor = self._execute("""
            SELECT
                t.nombre_nadador,

                COALESCE(
                    MAX(t.categoria),
                    MAX(n.categoria_master),
                    'Sin categoría'
                ) AS categoria_master,

                COUNT(*) AS total_tiempos

            FROM tiempos t

            LEFT JOIN nadadores n
                ON LOWER(TRIM(t.nombre_nadador)) =
                   LOWER(TRIM(n.nombre || ' ' || n.apellido))

            WHERE EXTRACT(YEAR FROM t.fecha) = ?

            GROUP BY
                t.nombre_nadador

            ORDER BY
                total_tiempos DESC,
                t.nombre_nadador ASC

            LIMIT 12
        """, (
            año_actual,
        ), commit=False)

        mas_activos = [
            self._row_to_dict(row, cursor)
            for row in cursor.fetchall()
            if row
        ]

        # Top 3 de cada estilo en 50 metros,
        # sin repetir nadador dentro del mismo estilo
        cursor = self._execute("""
            WITH mejores_por_nadador AS (
                SELECT
                    nombre_nadador,
                    estilo,
                    distancia,
                    piscina,
                    tiempo,
                    tiempo_segundos,
                    fecha,

                    ROW_NUMBER() OVER (
                        PARTITION BY
                            LOWER(TRIM(nombre_nadador)),
                            LOWER(TRIM(estilo))
                        ORDER BY
                            tiempo_segundos ASC,
                            fecha ASC
                    ) AS puesto_nadador

                FROM tiempos
        
                WHERE distancia = 50
                  AND LOWER(TRIM(piscina)) IN (
                      '25 metros',
                      '50 metros'
                  )
                  AND nombre_nadador IS NOT NULL
                  AND TRIM(nombre_nadador) <> ''
                  AND estilo IS NOT NULL
                  AND TRIM(estilo) <> ''
                  AND tiempo_segundos IS NOT NULL
            ),

            ranking_por_estilo AS (
                SELECT
                    nombre_nadador,
                    estilo,
                    distancia,
                    piscina,
                    tiempo,
                    tiempo_segundos,
                    fecha,

                    ROW_NUMBER() OVER (
                        PARTITION BY LOWER(TRIM(estilo))
                        ORDER BY
                            tiempo_segundos ASC,
                            fecha ASC,
                            nombre_nadador ASC
                    ) AS posicion

                FROM mejores_por_nadador

                WHERE puesto_nadador = 1
            )

            SELECT
                nombre_nadador,
                estilo,
                distancia,
                piscina,
                tiempo,
                tiempo_segundos,
                fecha,
                posicion

            FROM ranking_por_estilo

            WHERE posicion <= 3

            ORDER BY
                LOWER(TRIM(estilo)) ASC,
                posicion ASC
        """, commit=False)

        por_prueba = [
            self._row_to_dict(row, cursor)
            for row in cursor.fetchall()
            if row
        ]

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
        """Construye la matriz anual, porcentaje oficial y reconocimientos."""
        hoy = date.today()

        cursor_nadadores = self._execute("""
            SELECT id, nombre, apellido, categoria_master
            FROM nadadores
            ORDER BY apellido ASC, nombre ASC
        """, commit=False)
        nadadores = [
            self._row_to_dict(fila, cursor_nadadores)
            for fila in cursor_nadadores.fetchall() if fila
        ]

        cursor_competencias = self._execute("""
            SELECT
                id, fecha, nombre, lugar,
                COALESCE(considera_asistencia, TRUE) AS considera_asistencia
            FROM competencias
            WHERE EXTRACT(YEAR FROM fecha) = ?
            ORDER BY fecha ASC, id ASC
        """, (anio,), commit=False)
        competencias = [
            self._row_to_dict(fila, cursor_competencias)
            for fila in cursor_competencias.fetchall() if fila
        ]

        for competencia in competencias:
            fecha_competencia = competencia.get('fecha')
            if isinstance(fecha_competencia, datetime):
                fecha_competencia = fecha_competencia.date()
            elif isinstance(fecha_competencia, str):
                try:
                    fecha_competencia = datetime.strptime(
                        fecha_competencia[:10], '%Y-%m-%d'
                    ).date()
                except (TypeError, ValueError):
                    fecha_competencia = None
            competencia['transcurrida'] = bool(
                fecha_competencia and fecha_competencia <= hoy
            )
            competencia['considera_asistencia'] = bool(
                competencia.get('considera_asistencia', True)
            )
            competencia['es_especial'] = not competencia['considera_asistencia']

        ids_competencias = [c['id'] for c in competencias]
        asistencias = {}
        if ids_competencias:
            placeholders = ', '.join(['?'] * len(ids_competencias))
            cursor_asistencias = self._execute(f"""
                SELECT nadador_id, competencia_id, estado
                FROM asistencia_competencias
                WHERE competencia_id IN ({placeholders})
            """, tuple(ids_competencias), commit=False)
            for fila in cursor_asistencias.fetchall():
                registro = self._row_to_dict(fila, cursor_asistencias)
                asistencias[(registro['nadador_id'], registro['competencia_id'])] = (
                    registro.get('estado') or 'SIN_REGISTRO'
                )

        oficiales_transcurridas = [
            c for c in competencias
            if c['transcurrida'] and c['considera_asistencia']
        ]
        especiales_transcurridas = [
            c for c in competencias
            if c['transcurrida'] and not c['considera_asistencia']
        ]

        porcentajes_validos = []
        asistencia_completa = 0
        asistencia_baja = 0
        participaciones_especiales_total = 0
        nadadores_con_especial = 0

        for nadador in nadadores:
            presentes = ausentes = pendientes = aplicables = 0
            reconocimientos = []

            for competencia in oficiales_transcurridas:
                estado = asistencias.get(
                    (nadador['id'], competencia['id']), 'SIN_REGISTRO'
                )
                if estado == 'NO_APLICA':
                    continue
                aplicables += 1
                if estado == 'PRESENTE': presentes += 1
                elif estado == 'AUSENTE': ausentes += 1
                else: pendientes += 1

            for competencia in especiales_transcurridas:
                estado = asistencias.get(
                    (nadador['id'], competencia['id']), 'SIN_REGISTRO'
                )
                if estado == 'PRESENTE':
                    reconocimientos.append({
                        'id': competencia['id'],
                        'nombre': competencia.get('nombre') or 'Competencia especial',
                        'lugar': competencia.get('lugar') or '',
                        'fecha': competencia.get('fecha'),
                    })

            porcentaje = round((presentes / aplicables) * 100) if aplicables else 0
            nadador.update({
                'asistencias_presentes': presentes,
                'asistencias_ausentes': ausentes,
                'asistencias_pendientes': pendientes,
                'competencias_aplicables': aplicables,
                'porcentaje_asistencia': porcentaje,
                'reconocimientos_especiales': reconocimientos,
                'participaciones_especiales': len(reconocimientos),
            })

            participaciones_especiales_total += len(reconocimientos)
            if reconocimientos:
                nadadores_con_especial += 1
            if aplicables:
                porcentajes_validos.append(porcentaje)
                if porcentaje == 100: asistencia_completa += 1
                if porcentaje < 50: asistencia_baja += 1

        promedio = round(sum(porcentajes_validos) / len(porcentajes_validos)) if porcentajes_validos else 0
        resumen = {
            'competencias_transcurridas': len(oficiales_transcurridas),
            'competencias_oficiales': len(oficiales_transcurridas),
            'competencias_especiales': len(especiales_transcurridas),
            'asistencia_promedio': promedio,
            'asistencia_completa': asistencia_completa,
            'asistencia_baja': asistencia_baja,
            'participaciones_especiales': participaciones_especiales_total,
            'nadadores_con_especial': nadadores_con_especial,
        }
        return {
            'nadadores': nadadores,
            'competencias': competencias,
            'asistencias': asistencias,
            'resumen': resumen,
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
        estado="NO REALIZADO",
        considera_asistencia=True,
        mes=None
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
                estado,
                considera_asistencia
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fecha,
            mes,
            lugar,
            organiza,
            nombre,
            tipo_piscina,
            estado,
            bool(considera_asistencia)
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
        estado,
        mes=None,
        considera_asistencia=True
    ):
        """
        Edita una competencia existente.
    
        Si no se recibe el mes, se calcula automáticamente a partir de la fecha.
        """
    
        if mes is None:
            mes = self._obtener_mes_competencia(fecha)
    
        self._execute("""
            UPDATE competencias
            SET
                fecha = ?,
                mes = ?,
                lugar = ?,
                organiza = ?,
                nombre = ?,
                tipo_piscina = ?,
                estado = ?,
                considera_asistencia = ?
            WHERE id = ?
        """, (
            fecha,
            mes,
            lugar,
            organiza,
            nombre,
            tipo_piscina,
            estado,
            bool(considera_asistencia),
            competencia_id
        ))
    
        return True    
    
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

    def listar_competencias_por_anio(self, anio):
        cursor = self._execute("""
            SELECT
                id,
                fecha,
                mes,
                lugar,
                organiza,
                nombre,
                tipo_piscina,
                estado,
                COALESCE(considera_asistencia, TRUE) AS considera_asistencia
            FROM competencias
            WHERE EXTRACT(YEAR FROM fecha) = ?
            ORDER BY fecha ASC, id ASC
        """, (
            anio,
        ), commit=False)
    
        filas = cursor.fetchall()
    
        return [
            self._row_to_dict(fila, cursor)
            for fila in filas
            if fila
        ]

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

    def agregar_competencia(
        self,
        fecha,
        mes,
        lugar,
        organiza,
        nombre,
        tipo_piscina,
        estado="NO REALIZADO",
        considera_asistencia=True
    ):
        self._execute("""
            INSERT INTO competencias (
                fecha,
                mes,
                lugar,
                organiza,
                nombre,
                tipo_piscina,
                estado,
                considera_asistencia
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fecha,
            mes,
            lugar,
            organiza,
            nombre,
            tipo_piscina,
            estado,
            bool(considera_asistencia)
        ))

    def obtener_dashboard_inicio(self):
        """Datos resumidos y alertas inteligentes para la portada ejecutiva."""
        hoy = date.today()
        anio_actual = hoy.year

        def una_fila(query, params=()):
            cursor = self._execute(query, params, commit=False)
            fila = cursor.fetchone()
            return self._row_to_dict(fila, cursor) or {}

        def varias_filas(query, params=()):
            cursor = self._execute(query, params, commit=False)
            return [
                self._row_to_dict(fila, cursor)
                for fila in cursor.fetchall()
                if fila
            ]

        resumen_tiempos = una_fila("""
            SELECT
                COUNT(*) AS total_tiempos,
                COUNT(DISTINCT nombre_nadador) AS nadadores_con_tiempos
            FROM tiempos
        """)

        resumen_nadadores = una_fila("""
            SELECT COUNT(*) AS total_nadadores
            FROM nadadores
        """)

        resumen_competencias = una_fila("""
            SELECT
                COUNT(*) AS total_competencias,
                COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM fecha) = ?) AS competencias_anio,
                COUNT(*) FILTER (WHERE fecha >= CURRENT_DATE) AS proximas_competencias
            FROM competencias
        """, (anio_actual,))

        activos = una_fila("""
            SELECT COUNT(DISTINCT nombre_nadador) AS total
            FROM tiempos
            WHERE EXTRACT(YEAR FROM fecha) = ?
        """, (anio_actual,)).get('total', 0) or 0

        total_nadadores = resumen_nadadores.get('total_nadadores', 0) or 0
        inactivos = max(total_nadadores - activos, 0)

        registros_temporada = varias_filas("""
            SELECT EXTRACT(YEAR FROM fecha)::INTEGER AS anio, COUNT(*) AS total
            FROM tiempos
            WHERE fecha IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM fecha)
            ORDER BY anio ASC
        """)

        registros_mes_raw = varias_filas("""
            SELECT EXTRACT(MONTH FROM fecha)::INTEGER AS mes, COUNT(*) AS total
            FROM tiempos
            WHERE EXTRACT(YEAR FROM fecha) = ?
            GROUP BY EXTRACT(MONTH FROM fecha)
            ORDER BY mes
        """, (anio_actual,))

        registros_por_mes = {int(f['mes']): int(f['total']) for f in registros_mes_raw}
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        estilos = varias_filas("""
            SELECT COALESCE(NULLIF(TRIM(estilo), ''), 'Sin estilo') AS estilo, COUNT(*) AS total
            FROM tiempos
            GROUP BY COALESCE(NULLIF(TRIM(estilo), ''), 'Sin estilo')
            ORDER BY total DESC
            LIMIT 6
        """)

        ultimos_tiempos = varias_filas("""
            SELECT id, nombre_nadador, estilo, distancia, piscina, tiempo, fecha
            FROM tiempos
            ORDER BY fecha DESC, id DESC
            LIMIT 7
        """)

        proximas_competencias = varias_filas("""
            SELECT id, nombre, fecha, lugar, tipo_piscina, estado
            FROM competencias
            WHERE fecha >= CURRENT_DATE
            ORDER BY fecha ASC
            LIMIT 5
        """)

        top_nadadores = varias_filas("""
            SELECT TRIM(nombre_nadador) AS nombre_nadador, COUNT(*)::INTEGER AS total_tiempos
            FROM tiempos
            WHERE fecha IS NOT NULL
              AND EXTRACT(YEAR FROM fecha) = ?
              AND nombre_nadador IS NOT NULL
              AND TRIM(nombre_nadador) <> ''
            GROUP BY TRIM(nombre_nadador)
            ORDER BY total_tiempos DESC, nombre_nadador ASC
            LIMIT 8
        """, (anio_actual,))

        # Cumpleaños: se calculan en Python para manejar correctamente el cambio de año.
        nadadores_cumple = varias_filas("""
            SELECT id, nombre, apellido, fecha_nacimiento
            FROM nadadores
            ORDER BY apellido, nombre
        """)
        proximos_cumpleanos = []
        cumpleanos_hoy = []
        for nadador in nadadores_cumple:
            fecha_nacimiento = nadador.get('fecha_nacimiento')
            if not fecha_nacimiento:
                continue
            if isinstance(fecha_nacimiento, str):
                try:
                    fecha_nacimiento = datetime.strptime(fecha_nacimiento[:10], '%Y-%m-%d').date()
                except ValueError:
                    continue
            try:
                proximo = date(hoy.year, fecha_nacimiento.month, fecha_nacimiento.day)
            except ValueError:
                proximo = date(hoy.year, 2, 28)
            if proximo < hoy:
                try:
                    proximo = date(hoy.year + 1, fecha_nacimiento.month, fecha_nacimiento.day)
                except ValueError:
                    proximo = date(hoy.year + 1, 2, 28)
            dias = (proximo - hoy).days
            edad = proximo.year - fecha_nacimiento.year
            item = {
                'id': nadador.get('id'),
                'nombre': f"{nadador.get('nombre', '')} {nadador.get('apellido', '')}".strip(),
                'fecha': proximo,
                'dias': dias,
                'edad': edad,
            }
            if dias == 0:
                cumpleanos_hoy.append(item)
            if dias <= 30:
                proximos_cumpleanos.append(item)
        proximos_cumpleanos.sort(key=lambda item: (item['dias'], item['nombre']))
        proximos_cumpleanos = proximos_cumpleanos[:6]

        # Alertas operativas del club.
        sin_fecha_nacimiento = una_fila("""
            SELECT COUNT(*) AS total
            FROM nadadores
            WHERE fecha_nacimiento IS NULL
        """).get('total', 0) or 0

        sin_actividad_90 = una_fila("""
            SELECT COUNT(*) AS total
            FROM nadadores n
            LEFT JOIN (
                SELECT TRIM(nombre_nadador) AS nombre_nadador, MAX(fecha) AS ultima_fecha
                FROM tiempos
                GROUP BY TRIM(nombre_nadador)
            ) t ON LOWER(TRIM(n.nombre || ' ' || n.apellido)) = LOWER(t.nombre_nadador)
            WHERE t.ultima_fecha IS NULL OR t.ultima_fecha < CURRENT_DATE - INTERVAL '90 days'
        """).get('total', 0) or 0

        competencias_incompletas = una_fila("""
            SELECT COUNT(*) AS total
            FROM competencias
            WHERE COALESCE(TRIM(nombre), '') = ''
               OR COALESCE(TRIM(lugar), '') = ''
               OR COALESCE(TRIM(tipo_piscina), '') = ''
        """).get('total', 0) or 0

        asistencias_pendientes = una_fila("""
            SELECT COUNT(*) AS total
            FROM competencias c
            WHERE UPPER(COALESCE(c.estado, '')) = 'REALIZADO'
              AND NOT EXISTS (
                  SELECT 1
                  FROM asistencia_competencias a
                  WHERE a.competencia_id = c.id
              )
        """).get('total', 0) or 0

        alertas = []
        if sin_actividad_90:
            alertas.append({'tipo': 'warning', 'icono': 'fa-user-clock', 'titulo': 'Nadadores sin actividad', 'detalle': f'{sin_actividad_90} sin tiempos en los últimos 90 días', 'valor': sin_actividad_90})
        if asistencias_pendientes:
            alertas.append({'tipo': 'danger', 'icono': 'fa-clipboard-question', 'titulo': 'Asistencias pendientes', 'detalle': f'{asistencias_pendientes} competencias realizadas sin asistencia', 'valor': asistencias_pendientes})
        if competencias_incompletas:
            alertas.append({'tipo': 'info', 'icono': 'fa-calendar-xmark', 'titulo': 'Competencias incompletas', 'detalle': f'{competencias_incompletas} con datos por completar', 'valor': competencias_incompletas})
        if sin_fecha_nacimiento:
            alertas.append({'tipo': 'info', 'icono': 'fa-cake-candles', 'titulo': 'Fechas de nacimiento', 'detalle': f'{sin_fecha_nacimiento} perfiles sin fecha registrada', 'valor': sin_fecha_nacimiento})

        # Actividad de los últimos 7 días.
        actividad_semana = una_fila("""
            SELECT COUNT(*) AS tiempos, COUNT(DISTINCT nombre_nadador) AS nadadores
            FROM tiempos
            WHERE fecha >= CURRENT_DATE - INTERVAL '6 days'
        """)

        # PB recientes: una marca es PB si mejora todas las anteriores de la misma prueba.
        pb_recientes = varias_filas("""
            WITH marcas AS (
                SELECT
                    id, nombre_nadador, estilo, distancia, piscina, tiempo,
                    tiempo_segundos, fecha,
                    MIN(tiempo_segundos) OVER (
                        PARTITION BY nombre_nadador, estilo, distancia, piscina
                        ORDER BY fecha, id
                        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                    ) AS mejor_anterior
                FROM tiempos
            )
            SELECT id, nombre_nadador, estilo, distancia, piscina, tiempo, fecha
            FROM marcas
            WHERE mejor_anterior IS NOT NULL
              AND tiempo_segundos < mejor_anterior
              AND fecha >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY fecha DESC, id DESC
            LIMIT 5
        """)

        proxima_destacada = proximas_competencias[0] if proximas_competencias else None
        if proxima_destacada and proxima_destacada.get('fecha'):
            fecha_comp = proxima_destacada['fecha']
            if isinstance(fecha_comp, str):
                try:
                    fecha_comp = datetime.strptime(fecha_comp[:10], '%Y-%m-%d').date()
                except ValueError:
                    fecha_comp = None
            proxima_destacada['dias_restantes'] = (fecha_comp - hoy).days if fecha_comp else None

        return {
            'anio_actual': anio_actual,
            'metricas': {
                'total_nadadores': total_nadadores,
                'activos': activos,
                'inactivos': inactivos,
                'total_tiempos': resumen_tiempos.get('total_tiempos', 0) or 0,
                'competencias_anio': resumen_competencias.get('competencias_anio', 0) or 0,
                'proximas_competencias': resumen_competencias.get('proximas_competencias', 0) or 0,
            },
            'graficos': {
                'temporadas': {'labels': [str(f['anio']) for f in registros_temporada], 'values': [int(f['total']) for f in registros_temporada]},
                'meses': {'labels': meses, 'values': [registros_por_mes.get(i, 0) for i in range(1, 13)]},
                'estilos': {'labels': [f['estilo'] for f in estilos], 'values': [int(f['total']) for f in estilos]},
                'actividad': {'labels': ['Activos', 'Inactivos'], 'values': [activos, inactivos]},
                'top_nadadores': {'labels': [f['nombre_nadador'] for f in top_nadadores], 'values': [int(f.get('total_tiempos') or 0) for f in top_nadadores]},
            },
            'ultimos_tiempos': ultimos_tiempos,
            'proximas_competencias_lista': proximas_competencias,
            'proxima_competencia_destacada': proxima_destacada,
            'proximos_cumpleanos': proximos_cumpleanos,
            'cumpleanos_hoy': cumpleanos_hoy,
            'alertas': alertas,
            'actividad_semana': {
                'tiempos': int(actividad_semana.get('tiempos', 0) or 0),
                'nadadores': int(actividad_semana.get('nadadores', 0) or 0),
                'pb': len(pb_recientes),
            },
            'pb_recientes': pb_recientes,
        }


    def obtener_registros_por_temporada(self):
        cursor = self._execute("""
            SELECT
                EXTRACT(YEAR FROM fecha)::INTEGER AS anio,
                COUNT(*) AS total
            FROM tiempos
            WHERE fecha IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM fecha)
            ORDER BY anio DESC
        """, commit=False)
    
        filas = cursor.fetchall()
    
        return [
            self._row_to_dict(fila, cursor)
            for fila in filas
            if fila
        ]

    def obtener_estado_nadadores_por_anio(self, anio):
        cursor = self._execute("""
            SELECT
                n.id,
                n.nombre,
                n.apellido,
                n.genero,
                n.categoria_master,
    
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM tiempos t
                        WHERE LOWER(TRIM(t.nombre_nadador)) =
                              LOWER(TRIM(n.nombre || ' ' || n.apellido))
                          AND EXTRACT(YEAR FROM t.fecha) = ?
                    )
                    THEN 'ACTIVO'
                    ELSE 'INACTIVO'
                END AS estado,
    
                (
                    SELECT COUNT(*)
                    FROM tiempos t
                    WHERE LOWER(TRIM(t.nombre_nadador)) =
                          LOWER(TRIM(n.nombre || ' ' || n.apellido))
                      AND EXTRACT(YEAR FROM t.fecha) = ?
                ) AS total_tiempos
    
            FROM nadadores n
    
            ORDER BY
                estado ASC,
                n.apellido ASC,
                n.nombre ASC
        """, (
            anio,
            anio
        ), commit=False)
    
        filas = cursor.fetchall()
    
        return [
            self._row_to_dict(fila, cursor)
            for fila in filas
            if fila
        ]

    def obtener_todos_los_tiempos(self, filtro_nombre=None):
        """
        Obtiene todos los tiempos registrados.
    
        Si se recibe filtro_nombre, filtra los resultados
        por el nombre del nadador.
        """
    
        if filtro_nombre:
            filtro_nombre = filtro_nombre.strip()
    
            return self._fetchall(
                """
                SELECT
                    id,
                    nadador,
                    genero,
                    estilo,
                    piscina,
                    distancia,
                    categoria,
                    tiempo,
                    tiempo_segundos,
                    fecha,
                    competencia_id
                FROM tiempos
                WHERE LOWER(nadador) LIKE LOWER(?)
                ORDER BY fecha DESC, id DESC
                """,
                (
                    f'%{filtro_nombre}%',
                )
            )
    
        return self._fetchall(
            """
            SELECT
                id,
                nadador,
                genero,
                estilo,
                piscina,
                distancia,
                categoria,
                tiempo,
                tiempo_segundos,
                fecha,
                competencia_id
            FROM tiempos
            ORDER BY fecha DESC, id DESC
            """
        )



 # ====================== Todos los Tiempos Registrados ======================
    def obtener_historial_tiempos(
        self,
        busqueda="",
        anio=None,
        piscina="",
        estilo="",
        distancia=None,
        columna_orden="fecha",
        direccion="desc",
        pagina=1,
        por_pagina=20
    ):
        """
        Retorna los tiempos filtrados y paginados.
    
        orden:
            desc = fecha más reciente primero
            asc  = fecha más antigua primero
        """
    
        try:
            pagina = max(int(pagina), 1)
        except (TypeError, ValueError):
            pagina = 1
    
        try:
            por_pagina = int(por_pagina)
        except (TypeError, ValueError):
            por_pagina = 20
    
        if por_pagina not in (20, 50, 100000):
            por_pagina = 20
    
        columnas_permitidas = {
            "fecha": "fecha",
            "nombre": "LOWER(TRIM(nombre_nadador))",
            "categoria": "LOWER(TRIM(categoria))",
            "genero": "LOWER(TRIM(genero))",
            "estilo": "LOWER(TRIM(estilo))",
            "distancia": "distancia",
            "piscina": "LOWER(TRIM(piscina))",
            "tiempo": "tiempo_segundos"
        }
        
        columna_sql = columnas_permitidas.get(
            columna_orden,
            "fecha"
        )
        
        direccion_sql = (
            "ASC"
            if direccion == "asc"
            else "DESC"
        )
    
        condiciones = []
        parametros = []
    
        # Búsqueda por nombre
        if busqueda:
            condiciones.append("""
                LOWER(TRIM(nombre_nadador))
                LIKE LOWER(?)
            """)
            parametros.append(
                f"%{busqueda.strip()}%"
            )
    
        # Año
        if anio:
            condiciones.append("""
                EXTRACT(YEAR FROM fecha) = ?
            """)
            parametros.append(int(anio))
    
        # Piscina
        if piscina:
            condiciones.append("""
                LOWER(TRIM(piscina)) = LOWER(TRIM(?))
            """)
            parametros.append(piscina)
    
        # Estilo
        if estilo:
            condiciones.append("""
                LOWER(TRIM(estilo)) = LOWER(TRIM(?))
            """)
            parametros.append(estilo)
    
        # Distancia
        if distancia:
            condiciones.append("""
                distancia = ?
            """)
            parametros.append(int(distancia))
    
        where_sql = ""
    
        if condiciones:
            where_sql = (
                "WHERE " +
                " AND ".join(condiciones)
            )
    
        # Contar resultados
        cursor_total = self._execute(
            f"""
            SELECT COUNT(*) AS total
            FROM tiempos
            {where_sql}
            """,
            tuple(parametros),
            commit=False
        )
    
        fila_total = cursor_total.fetchone()
    
        if fila_total:
            registro_total = self._row_to_dict(
                fila_total,
                cursor_total
            )
            total = int(
                registro_total.get("total", 0)
            )
        else:
            total = 0
    
        total_paginas = max(
            (total + por_pagina - 1)
            // por_pagina,
            1
        )
    
        if pagina > total_paginas:
            pagina = total_paginas
    
        offset = (
            pagina - 1
        ) * por_pagina
    
        # Obtener página solicitada
        parametros_pagina = (
            parametros +
            [por_pagina, offset]
        )
    
        cursor = self._execute(
            f"""
            SELECT
                id,
                nombre_nadador,
                categoria,
                genero,
                estilo,
                distancia,
                piscina,
                tiempo,
                tiempo_segundos,
                fecha,
                competencia_id
            FROM tiempos
            {where_sql}
            ORDER BY
                {columna_sql} {direccion_sql},
                fecha DESC,
                LOWER(TRIM(nombre_nadador)) ASC,
                id ASC
            LIMIT ?
            OFFSET ?
            """,
            tuple(parametros_pagina),
            commit=False
        )
    
        tiempos = [
            self._row_to_dict(fila, cursor)
            for fila in cursor.fetchall()
            if fila
        ]
    
        return {
            "tiempos": tiempos,
            "total": total,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_paginas": total_paginas,
            "desde": (
                offset + 1
                if total > 0
                else 0
            ),
            "hasta": min(
                offset + por_pagina,
                total
            )
        }

    def obtener_opciones_historial(self):
        # Años
        cursor_anios = self._execute("""
            SELECT DISTINCT
                CAST(
                    EXTRACT(YEAR FROM fecha)
                    AS INTEGER
                ) AS anio
            FROM tiempos
            WHERE fecha IS NOT NULL
            ORDER BY anio DESC
        """, commit=False)
    
        anios = []
    
        for fila in cursor_anios.fetchall():
            registro = self._row_to_dict(
                fila,
                cursor_anios
            )
    
            if registro and registro.get("anio"):
                anios.append(
                    registro["anio"]
                )
    
        # Piscinas
        cursor_piscinas = self._execute("""
            SELECT DISTINCT piscina
            FROM tiempos
            WHERE piscina IS NOT NULL
              AND TRIM(piscina) <> ''
            ORDER BY piscina
        """, commit=False)
    
        piscinas = []
    
        for fila in cursor_piscinas.fetchall():
            registro = self._row_to_dict(
                fila,
                cursor_piscinas
            )
    
            if registro:
                piscinas.append(
                    registro["piscina"]
                )
    
        # Estilos
        cursor_estilos = self._execute("""
            SELECT DISTINCT estilo
            FROM tiempos
            WHERE estilo IS NOT NULL
              AND TRIM(estilo) <> ''
            ORDER BY estilo
        """, commit=False)
    
        estilos = []
    
        for fila in cursor_estilos.fetchall():
            registro = self._row_to_dict(
                fila,
                cursor_estilos
            )
    
            if registro:
                estilos.append(
                    registro["estilo"]
                )
    
        # Distancias
        cursor_distancias = self._execute("""
            SELECT DISTINCT distancia
            FROM tiempos
            WHERE distancia IS NOT NULL
            ORDER BY distancia
        """, commit=False)
    
        distancias = []
    
        for fila in cursor_distancias.fetchall():
            registro = self._row_to_dict(
                fila,
                cursor_distancias
            )
    
            if registro:
                distancias.append(
                    registro["distancia"]
                )
    
        return {
            "anios": anios,
            "piscinas": piscinas,
            "estilos": estilos,
            "distancias": distancias
        }


     # ====================== FICHA NADADOR ======================

    def obtener_ficha_nadador(self, nombre_completo):
        nombre_completo = nombre_completo.strip()
    
        # Total de tiempos
        cursor = self._execute("""
            SELECT
                COUNT(*) AS total_tiempos,
                COUNT(DISTINCT competencia_id)
                    FILTER (WHERE competencia_id IS NOT NULL)
                    AS total_competencias,
                MIN(fecha) AS primer_registro,
                MAX(fecha) AS ultimo_registro
            FROM tiempos
            WHERE LOWER(TRIM(nombre_nadador)) =
                  LOWER(TRIM(?))
        """, (
            nombre_completo,
        ), commit=False)
    
        fila = cursor.fetchone()
    
        resumen = (
            self._row_to_dict(fila, cursor)
            if fila
            else {}
        )
    
        # Mejores marcas: una por estilo, distancia y piscina
        cursor = self._execute("""
            WITH ranking AS (
                SELECT
                    id,
                    estilo,
                    distancia,
                    piscina,
                    tiempo,
                    tiempo_segundos,
                    fecha,
                    competencia_id,
    
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            LOWER(TRIM(estilo)),
                            distancia,
                            LOWER(TRIM(piscina))
                        ORDER BY
                            tiempo_segundos ASC,
                            fecha ASC,
                            id ASC
                    ) AS posicion
    
                FROM tiempos
    
                WHERE LOWER(TRIM(nombre_nadador)) =
                      LOWER(TRIM(?))
                  AND tiempo_segundos IS NOT NULL
            )
    
            SELECT
                id,
                estilo,
                distancia,
                piscina,
                tiempo,
                tiempo_segundos,
                fecha,
                competencia_id
    
            FROM ranking
    
            WHERE posicion = 1
    
            ORDER BY
                distancia ASC,
                estilo ASC,
                piscina ASC
        """, (
            nombre_completo,
        ), commit=False)
    
        mejores_marcas = [
            self._row_to_dict(fila, cursor)
            for fila in cursor.fetchall()
            if fila
        ]
    
        # Últimos 10 tiempos
        cursor = self._execute("""
            SELECT
                id,
                estilo,
                distancia,
                piscina,
                tiempo,
                tiempo_segundos,
                fecha,
                categoria,
                genero,
                competencia_id
            FROM tiempos
            WHERE LOWER(TRIM(nombre_nadador)) =
                  LOWER(TRIM(?))
            ORDER BY
                fecha DESC,
                id DESC
            LIMIT 10
        """, (
            nombre_completo,
        ), commit=False)
    
        ultimos_tiempos = [
            self._row_to_dict(fila, cursor)
            for fila in cursor.fetchall()
            if fila
        ]
    
        # Cantidad de registros por temporada
        cursor = self._execute("""
            SELECT
                CAST(
                    EXTRACT(YEAR FROM fecha)
                    AS INTEGER
                ) AS anio,
                COUNT(*) AS total
            FROM tiempos
            WHERE LOWER(TRIM(nombre_nadador)) =
                  LOWER(TRIM(?))
              AND fecha IS NOT NULL
            GROUP BY
                EXTRACT(YEAR FROM fecha)
            ORDER BY
                anio DESC
        """, (
            nombre_completo,
        ), commit=False)
    
        temporadas = [
            self._row_to_dict(fila, cursor)
            for fila in cursor.fetchall()
            if fila
        ]
    
        return {
            'resumen': resumen or {},
            'mejores_marcas': mejores_marcas,
            'ultimos_tiempos': ultimos_tiempos,
            'temporadas': temporadas
        }

if __name__ == "__main__":
    gestor = GestorTiemposMaster()
    print("Gestor de Tiempos Master inicializado correctamente.")
    gestor.cerrar_conexion()

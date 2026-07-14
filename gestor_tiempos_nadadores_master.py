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
        cursor.execute('''
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
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_nombre_estilo_dist ON tiempos(nombre_nadador, estilo, distancia)
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fecha ON tiempos(fecha)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competencias (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                fecha DATE,
                mes INTEGER,
                estado TEXT DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def cerrar_conexion(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass

    # ====================== MÉTODOS ESTÁTICOS ======================
    @staticmethod
    def _validar_tiempo(tiempo_str: str) -> bool:
        if not isinstance(tiempo_str, str):
            return False
        patron = r'^\d{1,2}:\d{2}\.\d{2}$'
        if not re.match(patron, tiempo_str):
            return False
        try:
            mm_str, ss_cc = tiempo_str.split(':')
            ss_str, cc_str = ss_cc.split('.')
            mm = int(mm_str)
            ss = int(ss_str)
            cc = int(cc_str)
            return 0 <= mm <= 99 and 0 <= ss <= 59 and 0 <= cc <= 99
        except (ValueError, IndexError, AttributeError):
            return False

    @staticmethod
    def _convertir_a_segundos(tiempo_str: str) -> float:
        mm_str, ss_cc = tiempo_str.split(':')
        ss_str, cc_str = ss_cc.split('.')
        mm = int(mm_str)
        ss = int(ss_str)
        cc = int(cc_str)
        return (mm * 60) + ss + (cc / 100.0)

    # ====================== CRUD BÁSICO ======================
    def agregar_tiempo(self, nombre, estilo, distancia, tiempo, fecha=None, piscina="25 metros"):
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del nadador no puede estar vacío.")
        if estilo not in self.ESTILOS:
            raise ValueError(f"Estilo inválido. Opciones: {', '.join(self.ESTILOS)}")
        if distancia not in self.DISTANCIAS:
            raise ValueError(f"Distancia inválida. Opciones: {self.DISTANCIAS}")
        if not self._validar_tiempo(tiempo):
            raise ValueError("Formato de tiempo inválido. Debe ser MM:SS.cc (ej: 01:23.45)")
        if fecha is None:
            fecha = date.today()

        tiempo_segundos = self._convertir_a_segundos(tiempo)
        self._execute('''
            INSERT INTO tiempos 
            (nombre_nadador, estilo, distancia, piscina, tiempo, tiempo_segundos, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nombre.title(), estilo, distancia, piscina, tiempo, tiempo_segundos, fecha.isoformat()))

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
    def obtener_season_best(self, nombre: str, estilo: str, distancia: int, year: Optional[int] = None):
        if year is None:
            year = datetime.now().year
        cursor = self._execute('''
            SELECT * FROM tiempos
            WHERE LOWER(nombre_nadador) LIKE LOWER(?)
              AND estilo = ?
              AND distancia = ?
              AND EXTRACT(YEAR FROM fecha) = ?
            ORDER BY tiempo_segundos ASC
            LIMIT 1
        ''', (f"%{nombre.strip()}%", estilo, distancia, year), commit=False)
        row = cursor.fetchone()
        return self._row_to_dict(row, cursor)

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

    def obtener_top_5_por_categoria_estilo(self):
        cursor = self._execute('''
            SELECT 
                n.categoria_master,
                n.genero,
                t.estilo,
                t.distancia,
                t.tiempo,
                t.fecha,
                t.nombre_nadador
            FROM tiempos t
            LEFT JOIN nadadores n ON LOWER(t.nombre_nadador) = LOWER(n.nombre || ' ' || n.apellido)
            ORDER BY t.tiempo_segundos ASC
            LIMIT 50
        ''', commit=False)
        return [self._row_to_dict(row, cursor) for row in cursor.fetchall() if row]

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

    def __del__(self):
        self.cerrar_conexion()


    def listar_competencias(self):
        """Lista todas las competencias."""
        cursor = self._execute('SELECT * FROM competencias ORDER BY mes, fecha', commit=False)
        return [self._row_to_dict(row, cursor) for row in cursor.fetchall() if row]

    def actualizar_estado_competencia(self, competencia_id, estado):
        """Actualiza el estado de una competencia."""
        self._execute('UPDATE competencias SET estado = ? WHERE id = ?', (estado, competencia_id))

if __name__ == "__main__":
    gestor = GestorTiemposMaster()
    print("Gestor de Tiempos Master inicializado correctamente.")
    gestor.cerrar_conexion()

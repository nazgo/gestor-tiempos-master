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
    import psycopg2
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

    def crear_tabla(self) -> None:
        """Crea las tablas si no existen."""
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
        self.conn.commit()

    def cerrar_conexion(self) -> None:
        """Cierra la conexión a la base de datos de forma segura."""
        if self.conn:
            self.conn.close()

    # ====================== MÉTODOS ESTÁTICOS =======================
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
        """Agrega un nuevo registro de tiempo."""
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

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO tiempos 
            (nombre_nadador, estilo, distancia, piscina, tiempo, tiempo_segundos, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            nombre.title(),
            estilo,
            distancia,
            piscina,
            tiempo,
            tiempo_segundos,
            fecha.isoformat()
        ))
        self.conn.commit()
        return cursor.lastrowid

    def obtener_tiempo_por_id(self, tiempo_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tiempos WHERE id = ?', (tiempo_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def actualizar_tiempo(self, tiempo_id, nombre, estilo, distancia, piscina, tiempo, fecha):
        """Actualiza un tiempo existente."""
        tiempo_segundos = self._convertir_a_segundos(tiempo)
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE tiempos 
            SET nombre_nadador = ?, estilo = ?, distancia = ?, piscina = ?, 
                tiempo = ?, tiempo_segundos = ?, fecha = ?
            WHERE id = ?
        ''', (nombre, estilo, distancia, piscina, tiempo, tiempo_segundos, fecha, tiempo_id))
        self.conn.commit()

    def eliminar_tiempo(self, tiempo_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM tiempos WHERE id = ?', (tiempo_id,))
        self.conn.commit()

    # ====================== CONSULTAS AVANZADAS ======================
    def obtener_season_best(self, nombre: str, estilo: str, distancia: int, year: Optional[int] = None):
        if year is None:
            year = datetime.now().year

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tiempos
            WHERE LOWER(nombre_nadador) LIKE LOWER(?)
              AND estilo = ?
              AND distancia = ?
              AND strftime('%Y', fecha) = ?
            ORDER BY tiempo_segundos ASC
            LIMIT 1
        ''', (f"%{nombre.strip()}%", estilo, distancia, str(year)))
        
        row = cursor.fetchone()
        return dict(row) if row else None

    def obtener_season_best_avanzado(self, nombre=None, estilo=None, distancia=None, categoria=None, year=None):
        if year is None:
            year = datetime.now().year

        query = '''
            SELECT t.*, n.categoria_master 
            FROM tiempos t
            LEFT JOIN nadadores n ON LOWER(t.nombre_nadador) = LOWER(n.nombre || ' ' || n.apellido)
            WHERE strftime('%Y', t.fecha) = ?
        '''
        params = [str(year)]

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

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def obtener_todos_los_tiempos(self, nombre_filtro: Optional[str] = None) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        
        if nombre_filtro:
            cursor.execute('''
                SELECT * FROM tiempos 
                WHERE LOWER(nombre_nadador) LIKE LOWER(?)
                ORDER BY fecha DESC, tiempo_segundos ASC
            ''', (f"%{nombre_filtro.strip()}%",))
        else:
            cursor.execute('''
                SELECT * FROM tiempos 
                ORDER BY fecha DESC, nombre_nadador, estilo, distancia
            ''')
        
        return [dict(row) for row in cursor.fetchall()]

    def obtener_tiempos_nadador(self, nombre_completo):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tiempos 
            WHERE LOWER(nombre_nadador) = LOWER(?)
            ORDER BY fecha ASC, tiempo_segundos ASC
        ''', (nombre_completo,))
        return [dict(row) for row in cursor.fetchall()]

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
        """Obtiene estadísticas generales del club."""
        cursor = self.conn.cursor()
        año_actual = datetime.now().year

        # Total general
        cursor = self._execute('''
            SELECT COUNT(*) as total_tiempos, 
                   COUNT(DISTINCT nombre_nadador) as total_nadadores 
            FROM tiempos
        ''', commit=False)
        general = dict(cursor.fetchone()) if cursor.fetchone() else {}

        # Nadadores activos este año
        cursor = self._execute('''
            SELECT COUNT(DISTINCT nombre_nadador) as activos_este_año
            FROM tiempos 
            WHERE strftime('%Y', fecha) = %s
        ''', (str(año_actual),), commit=False)
        activos_row = cursor.fetchone()
        activos = dict(activos_row)['activos_este_año'] if activos_row else 0

        # Temporadas
        cursor = self._execute("SELECT DISTINCT strftime('%Y', fecha) as ano FROM tiempos WHERE fecha IS NOT NULL", commit=False)
        años = cursor.fetchall()
        temporadas = len(años)

        # Nadadores más activos
        cursor = self._execute('''
            SELECT nombre_nadador, COUNT(*) as total_tiempos
            FROM tiempos 
            WHERE strftime('%Y', fecha) = %s
            GROUP BY nombre_nadador 
            ORDER BY total_tiempos DESC 
            LIMIT 10
        ''', (str(año_actual),), commit=False)
        mas_activos = [dict(row) if hasattr(row, '_asdict') else dict(row) for row in cursor.fetchall()]

        # Mejores tiempos
        cursor = self._execute('''
            SELECT nombre_nadador, estilo, distancia, tiempo, fecha
            FROM tiempos
            ORDER BY tiempo_segundos ASC
            LIMIT 10
        ''', commit=False)
        por_prueba = [dict(row) if hasattr(row, '_asdict') else dict(row) for row in cursor.fetchall()]
    
        return {
            'general': general,
            'activos_este_año': activos,
            'temporadas': temporadas,
            'mas_activos': mas_activos,
            'por_prueba': por_prueba
        }

    def obtener_top_5_por_categoria_estilo(self):
        """Obtiene los mejores tiempos por categoría."""
        cursor = self.conn.cursor()
        cursor.execute('''
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
        ''')
        return [dict(row) for row in cursor.fetchall()]

    # ====================== OTRAS FUNCIONALIDADES ======================
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
        """Exporta los tiempos a un PDF."""
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

    # ... (puedes agregar aquí los demás métodos como importar_csv, comparaciones, etc.)

    def __del__(self):
        self.cerrar_conexion()


# ====================== EJECUCIÓN DIRECTA ======================
if __name__ == "__main__":
    gestor = GestorTiemposMaster()
    print("Gestor de Tiempos Master inicializado correctamente.")
    gestor.cerrar_conexion()

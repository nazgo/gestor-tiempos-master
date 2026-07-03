#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Gestión de Tiempos para Nadadores Master de Nivel Competitivo
"""

import sqlite3
import csv
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any


class GestorTiemposMaster:
    ESTILOS = ['Mariposa', 'Espalda', 'Pecho', 'Crol', 'Combinado']
    DISTANCIAS = [50, 100, 200, 400, 800, 1500]

    def __init__(self, db_path: str = "nadadores_master_competitivos.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.crear_tabla()

    def crear_tabla(self) -> None:
        """Crea la tabla principal y los índices optimizados para consultas frecuentes."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tiempos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            CREATE INDEX IF NOT EXISTS idx_nombre_estilo_dist
            ON tiempos(nombre_nadador, estilo, distancia)
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fecha ON tiempos(fecha)')
        self.conn.commit()

        # Tabla de Competencias
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mes TEXT,
                fecha TEXT,
                etapas TEXT,
                lugar TEXT,
                organiza TEXT,
                nombre_torneo TEXT,
                tipo_piscina TEXT,
                estado TEXT DEFAULT '1'
            )
        ''')
        self.conn.commit()

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
            if not (0 <= mm <= 99 and 0 <= ss <= 59 and 0 <= cc <= 99):
                return False
            return True
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

    def agregar_tiempo(self, nombre, estilo, distancia, tiempo, fecha=None, piscina="25 metros"):
        """Agrega un nuevo registro de tiempo al sistema."""
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del nadador no puede estar vacío.")

        if estilo not in self.ESTILOS:
            raise ValueError(f"Estilo inválido. Opciones válidas: {', '.join(self.ESTILOS)}")

        if distancia not in self.DISTANCIAS:
            raise ValueError(f"Distancia inválida. Opciones válidas: {self.DISTANCIAS}")

        if not self._validar_tiempo(tiempo):
            raise ValueError(
                "Formato de tiempo inválido. Debe ser MM:SS.cc con dos dígitos "
                "en las centésimas (ejemplo correcto: 01:23.45 o 00:58.72)"
            )

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

    # ... (el resto del archivo se mantiene igual)
    def obtener_season_best(
        self, 
        nombre: str, 
        estilo: str, 
        distancia: int, 
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene el Season Best (mejor tiempo de la temporada) para un nadador 
        y una prueba específica (estilo + distancia).
        
        Args:
            year: Año de la temporada. Si es None, usa el año actual.
        
        Returns:
            dict con los datos del mejor tiempo o None si no existe registro.
        """
        if year is None:
            year = datetime.now().year

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, nombre_nadador, estilo, distancia, tiempo, 
                   tiempo_segundos, fecha, created_at
            FROM tiempos
            WHERE LOWER(nombre_nadador) LIKE LOWER(?)
              AND estilo = ?
              AND distancia = ?
              AND strftime('%Y', fecha) = ?
            ORDER BY tiempo_segundos ASC
            LIMIT 1
        ''', (f"%{nombre.strip()}%", estilo, distancia, str(year)))
        
        row = cursor.fetchone()
        return dict(row) if row else None

    def obtener_todos_los_tiempos(
        self, 
        nombre_filtro: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna todos los tiempos registrados.
        Si se proporciona nombre_filtro, filtra por nadador (búsqueda parcial case-insensitive).
        """
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

    def exportar_a_csv(self, filepath: Optional[str] = None) -> str:
        """
        Exporta todos los registros a un archivo CSV compatible con Excel.
        
        Usa codificación UTF-8 con BOM (utf-8-sig) para que Excel muestre 
        correctamente los acentos y caracteres especiales.
        
        Returns:
            str: Ruta absoluta del archivo generado.
        """
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"export_tiempos_master_{timestamp}.csv"

        registros = self.obtener_todos_los_tiempos()
        if not registros:
            raise ValueError("No hay datos para exportar. Agregue algunos tiempos primero.")

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = [
                'ID', 'Nombre Nadador', 'Estilo', 'Distancia (m)', 
                'Tiempo (MM:SS.cc)', 'Tiempo (segundos)', 'Fecha', 'Fecha Creación'
            ]
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
                    'Fecha Creación': reg['created_at']
                })

        return filepath

    def obtener_estadisticas_nadador(self, nombre: str) -> Dict[str, Any]:
        """
        Método bonus (no requerido pero útil) para estadísticas básicas.
        Facilita la migración futura a dashboards.
        """
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

    def cerrar_conexion(self) -> None:
        """Cierra la conexión a la base de datos de forma segura."""
        if self.conn:
            self.conn.close()

    def obtener_tiempo_por_id(self, tiempo_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tiempos WHERE id = ?', (tiempo_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def actualizar_tiempo(self, tiempo_id, nombre, estilo, distancia, piscina, tiempo, fecha):
        """Actualiza un tiempo existente."""
        tiempo_segundos = self._convertir_a_segundos(tiempo)
        self.conn.execute('''
            UPDATE tiempos 
            SET nombre_nadador = ?, estilo = ?, distancia = ?, piscina = ?, 
                tiempo = ?, tiempo_segundos = ?, fecha = ?
            WHERE id = ?
        ''', (nombre, estilo, distancia, piscina, tiempo, tiempo_segundos, fecha, tiempo_id))
        self.conn.commit()

    def eliminar_tiempo(self, tiempo_id):
        self.conn.execute('DELETE FROM tiempos WHERE id = ?', (tiempo_id,))
        self.conn.commit()

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



    def obtener_estadisticas_club(self):
        """Obtiene estadísticas generales del club."""
        cursor = self.conn.cursor()
        año_actual = datetime.now().year

        # Total general
        cursor.execute('''
            SELECT COUNT(*) as total_tiempos, 
                   COUNT(DISTINCT nombre_nadador) as total_nadadores 
            FROM tiempos
        ''')
        general = dict(cursor.fetchone())

        # Nadadores activos este año
        cursor.execute('''
            SELECT COUNT(DISTINCT nombre_nadador) as activos_este_año
            FROM tiempos 
            WHERE strftime('%Y', fecha) = ?
        ''', (str(año_actual),))
        activos_row = cursor.fetchone()
        activos = dict(activos_row)['activos_este_año'] if activos_row else 0

        # Número de temporadas (años distintos) - versión simplificada
        cursor.execute("SELECT DISTINCT strftime('%Y', fecha) as ano FROM tiempos WHERE fecha IS NOT NULL")
        años = cursor.fetchall()
        temporadas = len(años)

        # Si sigue 0, contar manualmente
        if temporadas == 0:
            cursor.execute("SELECT DISTINCT strftime('%Y', fecha) FROM tiempos")
            años = cursor.fetchall()
            temporadas = len(años)

        # Nadadores más activos este año
        cursor.execute('''
            SELECT nombre_nadador, COUNT(*) as total_tiempos
            FROM tiempos 
            WHERE strftime('%Y', fecha) = ?
            GROUP BY nombre_nadador 
            ORDER BY total_tiempos DESC 
            LIMIT 10
        ''', (str(año_actual),))
        mas_activos = [dict(row) for row in cursor.fetchall()]

	# Mejores Tiempos (versión ultra simple)
        cursor.execute('''
            SELECT nombre_nadador, estilo, distancia, tiempo, fecha
            FROM tiempos
            ORDER BY tiempo_segundos ASC
            LIMIT 10
        ''')
        por_prueba = [dict(row) for row in cursor.fetchall()]
    
        return {
            'general': general,
            'activos_este_año': activos,
            'temporadas': temporadas,
            'mas_activos': mas_activos,
            'por_prueba': por_prueba
        }

    def obtener_tiempos_nadador(self, nombre_completo):
        """Obtiene todos los tiempos de un nadador por su nombre completo."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tiempos 
            WHERE LOWER(nombre_nadador) = LOWER(?)
            ORDER BY fecha ASC, tiempo_segundos ASC
        ''', (nombre_completo,))
        return [dict(row) for row in cursor.fetchall()]


    def comparacion_25_vs_50(self):
        """Compara tiempos en 25m vs 50m para cada nadador y estilo."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT
                nombre_nadador,
                estilo,
                MAX(CASE WHEN distancia = 25 THEN tiempo END) as tiempo_25,
                MAX(CASE WHEN distancia = 50 THEN tiempo END) as tiempo_50,
                COUNT(CASE WHEN distancia = 25 THEN 1 END) as registros_25,
                COUNT(CASE WHEN distancia = 50 THEN 1 END) as registros_50
            FROM tiempos
            WHERE distancia IN (25, 50)
            GROUP BY nombre_nadador, estilo
            HAVING COUNT(DISTINCT distancia) = 2
            ORDER BY nombre_nadador, estilo
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def comparacion_nadador_25_50(self, nadador_id):
        """Compara tiempos 25m vs 50m de un nadador específico."""
        cursor = self.conn.cursor()
        
        # Obtener nombre del nadador
        cursor.execute('SELECT nombre, apellido FROM nadadores WHERE id = ?', (nadador_id,))
        row = cursor.fetchone()
        if not row:
            return []
        
        nombre_completo = f"{row['nombre']} {row['apellido']}"
        print("DEBUG - Nombre completo:", nombre_completo)
        cursor.execute("SELECT DISTINCT nombre_nadador FROM tiempos")
        print("DEBUG - Nombres en tiempos:", [row[0] for row in cursor.fetchall()])

        # Búsqueda muy flexible
        cursor.execute('''
            SELECT estilo, distancia, tiempo, fecha
            FROM tiempos
            WHERE LOWER(nombre_nadador) LIKE LOWER(?)
            ORDER BY fecha DESC
        ''', (f"%{nombre_completo}%",))
        return [dict(row) for row in cursor.fetchall()]

    def listar_competencias(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM competencias ORDER BY mes, fecha')
        return [dict(row) for row in cursor.fetchall()]

    def actualizar_estado_competencia(self, competencia_id, estado):
        self.conn.execute('UPDATE competencias SET estado = ? WHERE id = ?', (estado, competencia_id))
        self.conn.commit()

    def importar_csv(self, file):
        """Importa tiempos desde un archivo CSV."""
        import csv
        from io import StringIO
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        next(csv_input)  # Skip header
        for row in csv_input:
            if len(row) >= 5:
                nombre = row[0]
                estilo = row[1]
                distancia = int(row[2])
                tiempo = row[3]
                fecha = datetime.strptime(row[4], '%Y-%m-%d').date() if len(row) > 4 else date.today()
                self.agregar_tiempo(nombre, estilo, distancia, tiempo, fecha)

    def exportar_a_pdf(self, tiempos):
        """Exporta los tiempos a un PDF bonito."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        import os

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


# =============================================================================
#                    INTERFAZ DE LÍNEA DE COMANDOS (CLI)
# =============================================================================
# Esta sección es temporal. En una migración a web/GUI, reemplazar por
# controladores o vistas que llamen a los métodos de GestorTiemposMaster.

def mostrar_menu_principal() -> None:
    """Muestra el menú principal con formato limpio y profesional."""
    print("\n" + "═" * 68)
    print("🏊  SISTEMA DE GESTIÓN DE TIEMPOS - NADADORES MASTER COMPETITIVOS")
    print("═" * 68)
    print("  1. ➕  Agregar nuevo tiempo de entrenamiento o competencia")
    print("  2. 🏆  Consultar Season Best (mejor tiempo de la temporada)")
    print("  3. 📋  Listar todos los tiempos registrados")
    print("  4. 📤  Exportar todos los datos a CSV (compatible con Excel)")
    print("  5. 📊  Ver estadísticas rápidas de un nadador")
    print("  6. ❌  Salir del sistema")
    print("═" * 68)


def seleccionar_opcion_lista(opciones: List[Any], prompt: str) -> Any:
    """
    Helper reutilizable para seleccionar elementos de una lista numerada.
    Usado para estilos y distancias.
    """
    print(f"\n{prompt}")
    for idx, opcion in enumerate(opciones, 1):
        print(f"   {idx}. {opcion}")
    
    while True:
        try:
            eleccion = int(input("\n   Seleccione una opción (número): ").strip())
            if 1 <= eleccion <= len(opciones):
                return opciones[eleccion - 1]
            print("   ⚠️  Número fuera de rango. Intente nuevamente.")
        except ValueError:
            print("   ⚠️  Entrada inválida. Por favor ingrese un número.")


def solicitar_tiempo_valido() -> str:
    """
    Solicita el tiempo al usuario con validación en tiempo real.
    Rechaza cualquier formato que no cumpla MM:SS.cc con dos dígitos en centésimas.
    """
    print("\n   Formato requerido: MM:SS.cc  (ejemplos: 00:58.72, 01:15.30, 02:45.00)")
    while True:
        tiempo_input = input("   Ingrese el tiempo: ").strip()
        if GestorTiemposMaster._validar_tiempo(tiempo_input):
            return tiempo_input
        print("   ❌ Formato inválido. Asegúrese de usar dos dígitos para segundos y centésimas.")
        print("      Ejemplo correcto: 01:23.45   |   Incorrecto: 1:23.4 o 01:23.5")


def main() -> None:
    """
    Función principal que ejecuta la interfaz CLI.
    Orquesta las llamadas a la clase GestorTiemposMaster.
    """
    print("\n🚀 Iniciando Sistema de Gestión de Tiempos Master...")
    gestor = GestorTiemposMaster("nadadores_master_competitivos.db")
    print("✅ Base de datos SQLite lista y operativa.\n")

    try:
        while True:
            mostrar_menu_principal()
            opcion = input("Seleccione una opción (1-6): ").strip()

            # ──────────────────────────────────────────────────────────────
            # 1. AGREGAR NUEVO TIEMPO
            # ──────────────────────────────────────────────────────────────
            if opcion == "1":
                print("\n" + "─" * 50)
                print("➕  AGREGAR NUEVO REGISTRO DE TIEMPO")
                print("─" * 50)
                
                nombre = input("   Nombre completo del nadador: ").strip()
                if not nombre:
                    print("   ❌ El nombre no puede estar vacío.")
                    continue

                estilo = seleccionar_opcion_lista(
                    gestor.ESTILOS, 
                    "Seleccione el estilo de nado:"
                )
                distancia = seleccionar_opcion_lista(
                    gestor.DISTANCIAS, 
                    "Seleccione la distancia (en metros):"
                )
                tiempo = solicitar_tiempo_valido()

                # Fecha opcional
                fecha_input = input(
                    "   Fecha de la prueba (YYYY-MM-DD) o Enter para usar hoy: "
                ).strip()
                
                if fecha_input:
                    try:
                        fecha = datetime.strptime(fecha_input, "%Y-%m-%d").date()
                    except ValueError:
                        print("   ⚠️  Formato de fecha inválido. Usando fecha actual.")
                        fecha = date.today()
                else:
                    fecha = date.today()

                try:
                    nuevo_id = gestor.agregar_tiempo(nombre, estilo, distancia, tiempo, fecha)
                    print(f"\n   ✅ ¡Registro exitoso! ID asignado: {nuevo_id}")
                    print(f"      {nombre.title()} | {estilo} {distancia}m | {tiempo} | {fecha}")
                except ValueError as err:
                    print(f"   ❌ Error de validación: {err}")

            # ──────────────────────────────────────────────────────────────
            # 2. CONSULTAR SEASON BEST
            # ──────────────────────────────────────────────────────────────
            elif opcion == "2":
                print("\n" + "─" * 50)
                print("🏆  CONSULTAR SEASON BEST (MEJOR TIEMPO DE LA TEMPORADA)")
                print("─" * 50)
                
                nombre = input("   Nombre del nadador (puede ser parcial): ").strip()
                if not nombre:
                    print("   ❌ Debe ingresar al menos parte del nombre.")
                    continue

                estilo = seleccionar_opcion_lista(
                    gestor.ESTILOS, 
                    "Seleccione el estilo de la prueba:"
                )
                distancia = seleccionar_opcion_lista(
                    gestor.DISTANCIAS, 
                    "Seleccione la distancia de la prueba:"
                )
                
                year_input = input(
                    f"   Año de la temporada (Enter = año actual {datetime.now().year}): "
                ).strip()
                year = int(year_input) if year_input.isdigit() else None

                best = gestor.obtener_season_best(nombre, estilo, distancia, year)
                
                if best:
                    temporada = best['fecha'][:4]
                    print(f"\n   🏆 SEASON BEST - {best['nombre_nadador']}")
                    print(f"      Prueba: {best['estilo']} {best['distancia']}m")
                    print(f"      ⏱️  Tiempo: {best['tiempo']}   ({best['tiempo_segundos']:.2f} segundos)")
                    print(f"      📅 Fecha del récord: {best['fecha']}")
                    print(f"      📆 Temporada: {temporada}")
                else:
                    temporada_str = year or datetime.now().year
                    print(f"\n   ⚠️  No se encontraron tiempos para '{nombre}' en {estilo} {distancia}m durante {temporada_str}.")

            # ──────────────────────────────────────────────────────────────
            # 3. LISTAR TIEMPOS
            # ──────────────────────────────────────────────────────────────
            elif opcion == "3":
                print("\n" + "─" * 50)
                print("📋  LISTADO DE TIEMPOS REGISTRADOS")
                print("─" * 50)
                
                filtro = input("   Filtrar por nombre (Enter = mostrar todos): ").strip() or None
                tiempos = gestor.obtener_todos_los_tiempos(filtro)

                if not tiempos:
                    print("   ℹ️  No hay registros que coincidan con el criterio.")
                    continue

                print(f"\n   Total de registros encontrados: {len(tiempos)}")
                print("   " + "─" * 85)
                print(f"   {'ID':<4} │ {'Nadador':<22} │ {'Prueba':<18} │ {'Tiempo':<9} │ {'Fecha':<11}")
                print("   " + "─" * 85)
                
                for t in tiempos:
                    prueba_str = f"{t['estilo']} {t['distancia']}m"
                    print(
                        f"   {t['id']:<4} │ {t['nombre_nadador']:<22} │ {prueba_str:<18} │ "
                        f"{t['tiempo']:<9} │ {t['fecha']:<11}"
                    )
                print("   " + "─" * 85)

            # ──────────────────────────────────────────────────────────────
            # 4. EXPORTAR A CSV
            # ──────────────────────────────────────────────────────────────
            elif opcion == "4":
                print("\n" + "─" * 50)
                print("📤  EXPORTAR DATOS A ARCHIVO CSV")
                print("─" * 50)
                
                try:
                    ruta_archivo = gestor.exportar_a_csv()
                    print(f"\n   ✅ Exportación completada exitosamente.")
                    print(f"   📁 Archivo generado: {ruta_archivo}")
                    print("   ℹ️  El archivo usa codificación UTF-8 con BOM para correcta visualización en Excel.")
                except ValueError as err:
                    print(f"   ❌ {err}")
                except Exception as err:
                    print(f"   ❌ Error inesperado durante la exportación: {err}")

            # ──────────────────────────────────────────────────────────────
            # 5. ESTADÍSTICAS RÁPIDAS (BONUS)
            # ──────────────────────────────────────────────────────────────
            elif opcion == "5":
                print("\n" + "─" * 50)
                print("📊  ESTADÍSTICAS RÁPIDAS DEL NADADOR")
                print("─" * 50)
                
                nombre = input("   Nombre del nadador: ").strip()
                if not nombre:
                    print("   ❌ Nombre requerido.")
                    continue
                
                stats = gestor.obtener_estadisticas_nadador(nombre)
                if stats["total_registros"] == 0:
                    print(f"   ℹ️  No hay registros para '{nombre}'.")
                    continue
                
                print(f"\n   Nadador: {nombre.title()}")
                print(f"   Total de registros: {stats['total_registros']}")
                print(f"   Pruebas únicas registradas: {stats['pruebas_unicas']}")
                print(f"   Mejor tiempo general: {stats['mejor_tiempo_general']:.2f} segundos")
                print(f"   Primera marca: {stats['primera_fecha']}")
                print(f"   Última marca: {stats['ultima_fecha']}")

            # ──────────────────────────────────────────────────────────────
            # 6. SALIR
            # ──────────────────────────────────────────────────────────────
            elif opcion == "6":
                print("\n👋  ¡Gracias por usar el Sistema de Gestión de Tiempos Master!")
                print("   Que tengas una gran temporada competitiva.\n")
                break

            else:
                print("   ⚠️  Opción inválida. Por favor seleccione un número del 1 al 6.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Programa interrumpido por el usuario (Ctrl+C).")
    except Exception as err:
        print(f"\n❌ Error inesperado en la aplicación: {err}")
        import traceback
        traceback.print_exc()
    finally:
        gestor.cerrar_conexion()
        print("✅ Conexión a base de datos cerrada correctamente.")


if __name__ == "__main__":
    main()

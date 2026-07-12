from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from functools import wraps
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_super_secreta_master_nadadores_2026')

# ==================== DEBUG DE VARIABLES ====================
print("=== DEBUG ENVIRONMENT VARIABLES ===")
print("DATABASE_URL existe?", bool(os.environ.get('DATABASE_URL')))
db_url = os.environ.get('DATABASE_URL')
print("Valor de DATABASE_URL:", db_url[:80] + "..." if db_url else "NO ENCONTRADA")
if db_url:
    print("Empieza con 'postgresql'?", db_url.startswith('postgresql'))
print("==================================")
# =======================================================

# Importa los gestores
from gestor_tiempos_nadadores_master import GestorTiemposMaster
from gestor_nadadores import GestorNadadores
from gestor_usuarios import GestorUsuarios

# Instancias
gestor_tiempos = GestorTiemposMaster()
gestor_nadadores = GestorNadadores()
gestor_usuarios = GestorUsuarios()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != 'admin':
            flash('No tienes permisos de administrador', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def editor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') not in ['admin', 'editor']:
            flash('No tienes permisos para editar', 'danger')
            return redirect(request.referrer or url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== RUTAS ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    # TODO: Implementar login real cuando tengas GestorUsuarios
    if request.method == 'POST':
        flash('Sistema de login en desarrollo. Usa modo demo por ahora.', 'info')
        session['user_id'] = 1
        session['username'] = 'admin'
        session['rol'] = 'admin'
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return render_template('index.html')


# ==================== GESTIÓN DE NADADORES ====================
@app.route('/nadadores')
@login_required
def nadadores():
    nadadores_list = gestor_nadadores.listar_nadadores()
    return render_template('nadadores.html', nadadores=nadadores_list)


@app.route('/nadadores/agregar', methods=['GET', 'POST'])
@login_required
@editor_required
def agregar_nadador():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre'].strip()
            apellido = request.form['apellido'].strip()
            fecha_nac_str = request.form['fecha_nacimiento']
            rut = request.form.get('rut', '').strip()
            genero = request.form.get('genero')

            fecha_nac = datetime.strptime(fecha_nac_str, '%Y-%m-%d').date()
            
            gestor_nadadores.agregar_nadador(nombre, apellido, fecha_nac, rut, genero)
            flash('✅ Nadador agregado correctamente', 'success')
            return redirect(url_for('nadadores'))
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'danger')
    
    return render_template('agregar_nadador.html')


@app.route('/nadador/<int:nadador_id>/editar', methods=['GET', 'POST'])
@login_required
@editor_required
def editar_nadador(nadador_id):
    nadador = gestor_nadadores.obtener_nadador(nadador_id)
    if not nadador:
        flash('Nadador no encontrado', 'danger')
        return redirect(url_for('nadadores'))

    if request.method == 'POST':
        try:
            nombre = request.form['nombre'].strip()
            apellido = request.form['apellido'].strip()
            fecha_nac = datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d').date()
            rut = request.form.get('rut', '').strip()
            genero = request.form.get('genero')

            gestor_nadadores.actualizar_nadador(nadador_id, nombre, apellido, fecha_nac, rut, genero)
            flash('✅ Nadador actualizado correctamente', 'success')
            return redirect(url_for('nadadores'))
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'danger')

    return render_template('editar_nadador.html', nadador=nadador)


@app.route('/nadador/<int:nadador_id>/eliminar', methods=['POST'])
@login_required
@editor_required
def eliminar_nadador(nadador_id):
    try:
        gestor_nadadores.eliminar_nadador(nadador_id)
        flash('✅ Nadador eliminado correctamente', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    return redirect(url_for('nadadores'))


# ==================== GESTIÓN DE TIEMPOS ====================
@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre'].strip()
            estilo = request.form['estilo']
            distancia = int(request.form['distancia'])
            piscina = request.form.get('piscina', '25 metros')
            tiempo = request.form['tiempo'].strip()
            fecha_str = request.form.get('fecha')

            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else None

            gestor_tiempos.agregar_tiempo(nombre, estilo, distancia, tiempo, fecha, piscina)
            flash('✅ Tiempo registrado correctamente', 'success')
            return redirect(url_for('listar_tiempos'))
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'danger')

    return render_template('agregar.html', 
                         estilos=gestor_tiempos.ESTILOS, 
                         distancias=gestor_tiempos.DISTANCIAS)


@app.route('/listar')
@login_required
def listar_tiempos():
    filtro_nombre = request.args.get('filtro', '')
    tiempos = gestor_tiempos.obtener_todos_los_tiempos(filtro_nombre)
    return render_template('listar_tiempos.html', tiempos=tiempos, filtro=filtro_nombre)


@app.route('/tiempo/<int:tiempo_id>/editar', methods=['GET', 'POST'])
@login_required
@editor_required
def editar_tiempo(tiempo_id):
    tiempo = gestor_tiempos.obtener_tiempo_por_id(tiempo_id)
    if not tiempo:
        flash('Tiempo no encontrado', 'danger')
        return redirect(url_for('listar_tiempos'))

    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            estilo = request.form['estilo']
            distancia = int(request.form['distancia'])
            piscina = request.form.get('piscina', '25 metros')
            tiempo_str = request.form['tiempo']
            fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d').date()

            gestor_tiempos.actualizar_tiempo(tiempo_id, nombre, estilo, distancia, piscina, tiempo_str, fecha)
            flash('✅ Tiempo actualizado correctamente', 'success')
            return redirect(url_for('listar_tiempos'))
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'danger')

    return render_template('editar_tiempo.html', tiempo=tiempo, 
                         estilos=gestor_tiempos.ESTILOS, 
                         distancias=gestor_tiempos.DISTANCIAS)


@app.route('/tiempo/<int:tiempo_id>/eliminar', methods=['POST'])
@login_required
@editor_required
def eliminar_tiempo(tiempo_id):
    try:
        gestor_tiempos.eliminar_tiempo(tiempo_id)
        flash('✅ Tiempo eliminado correctamente', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    return redirect(url_for('listar_tiempos'))


@app.route('/estadisticas')
@login_required
def estadisticas_club():
    stats = gestor_tiempos.obtener_estadisticas_club()
    return render_template('estadisticas.html', 
                         stats=stats, 
                         año_actual=datetime.now().year)

@app.route('/nadador/<int:nadador_id>/progreso')
@login_required
def progreso_nadador(nadador_id):
    nadador = gestor_nadadores.obtener_nadador(nadador_id)
    if not nadador:
        flash('Nadador no encontrado', 'danger')
        return redirect(url_for('nadadores'))
    
    nombre_completo = f"{nadador['nombre']} {nadador['apellido']}"
    tiempos = gestor_tiempos.obtener_tiempos_nadador(nombre_completo)
    
    return render_template('progreso_nadador.html', nadador=nadador, tiempos=tiempos)

@app.route('/comparacion_25_50')
@login_required
def comparacion_25_50():
    nadadores = gestor_nadadores.listar_nadadores()
    return render_template('comparacion_25_50.html', nadadores=nadadores)

@app.route('/comparacion_25_50_resultado', methods=['POST'])
@login_required
def comparacion_resultado():
    nadador_id = request.form.get('nadador_id')
    if not nadador_id:
        flash('Debe seleccionar un nadador', 'danger')
        return redirect(url_for('comparacion_25_50'))
    
    comparacion = gestor_tiempos.comparacion_nadador_25_50(nadador_id)
    nadador = gestor_nadadores.obtener_nadador(nadador_id)
    
    return render_template('comparacion_resultado.html', nadador=nadador, comparacion=comparacion)

@app.route('/calendario')
@login_required
def calendario_competencias():
    competencias = gestor_tiempos.listar_competencias()
    return render_template('calendario.html', competencias=competencias)

@app.route('/calendario/actualizar_estado', methods=['POST'])
@login_required
@editor_required
def actualizar_estado():
    competencia_id = request.form.get('id')
    estado = request.form.get('estado')
    gestor_tiempos.actualizar_estado_competencia(competencia_id, estado)
    flash('Estado actualizado correctamente', 'success')
    return redirect(url_for('calendario_competencias'))


@app.route('/import_export')
@login_required
def import_export():
    return render_template('import_export.html')
    

@app.route('/importar', methods=['GET', 'POST'])
@login_required
@editor_required
def importar_tiempos():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No se seleccionó archivo', 'danger')
            return redirect(url_for('importar_tiempos'))
        file = request.files['file']
        if file.filename == '':
            flash('No se seleccionó archivo', 'danger')
            return redirect(url_for('importar_tiempos'))
        if file and file.filename.endswith('.csv'):
            gestor_tiempos.importar_csv(file)
            flash('✅ Tiempos importados correctamente', 'success')
            return redirect(url_for('listar_tiempos'))
        else:
            flash('Solo se permiten archivos CSV', 'danger')
    return render_template('importar.html')

@app.route('/exportar_pdf')
@login_required
def exportar_pdf():
    tiempos = gestor_tiempos.obtener_todos_los_tiempos()
    pdf_path = gestor_tiempos.exportar_a_pdf(tiempos)
    return send_file(pdf_path, as_attachment=True, download_name='tiempos.pdf')

@app.route('/descargar_plantilla')
@login_required
def descargar_plantilla():
    from flask import send_file
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nombre', 'genero', 'estilo', 'distancia', 'piscina', 'tiempo', 'fecha'])
    writer.writerow(['Carlos Gomez', 'Masculino', 'Mariposa', '50', '25 metros', '00:37.02', '2026-04-02'])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='plantilla_tiempos.csv'
    )

@app.route('/mejores_tiempos')
@login_required
def mejores_tiempos():
    top_tiempos = gestor_tiempos.obtener_top_5_por_categoria_estilo()
    return render_template('mejores_tiempos.html', top_tiempos=top_tiempos)


# ==================== OTRAS RUTAS (puedes ir agregando) ====================
@app.route('/season_best', methods=['GET', 'POST'])
@login_required
def season_best():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        estilo = request.form.get('estilo')
        distancia = request.form.get('distancia')
        categoria = request.form.get('categoria')
        year = request.form.get('year')

        best = gestor_tiempos.obtener_season_best_avanzado(nombre, estilo, distancia, categoria, year)
        return render_template('season_best.html', best=best, nombre=nombre, 
                             estilo=estilo, distancia=distancia, categoria=categoria)
    
    return render_template('season_best_form.html', 
                         estilos=gestor_tiempos.ESTILOS, 
                         distancias=gestor_tiempos.DISTANCIAS)

@app.teardown_appcontext
def shutdown_session(exception=None):
    for gestor in [gestor_tiempos, gestor_nadadores, gestor_usuarios]:
        try:
            if hasattr(gestor, 'cerrar_conexion'):
                gestor.cerrar_conexion()
        except:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

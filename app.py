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

# ==================== ADMINISTRACIÓN ====================
@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    usuarios = gestor_usuarios.listar_usuarios()
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin/crear_usuario', methods=['POST'])
@admin_required
def crear_usuario():
    username = request.form['username']
    password = request.form['password']
    rol = request.form['rol']
    nombre = request.form.get('nombre', '')
    try:
        gestor_usuarios.crear_usuario(username, password, rol, nombre)
        flash('Usuario creado correctamente', 'success')
    except Exception as e:
        flash(f'Error al crear usuario: {e}', 'danger')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/cambiar_rol/<int:user_id>', methods=['POST'])
@admin_required
def cambiar_rol(user_id):
    nuevo_rol = request.form['rol']
    gestor_usuarios.cambiar_rol(user_id, nuevo_rol)
    flash('Rol actualizado', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/cambiar_password/<int:user_id>', methods=['POST'])
@admin_required
def cambiar_password(user_id):
    new_pass = request.form['new_password']
    gestor_usuarios.cambiar_password(user_id, new_pass)
    flash('Contraseña actualizada correctamente', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/eliminar_usuario/<int:user_id>', methods=['POST'])
@admin_required
def eliminar_usuario(user_id):
    if gestor_usuarios.eliminar_usuario(user_id):
        flash('Usuario eliminado correctamente', 'success')
    else:
        flash('No se puede eliminar el usuario administrador principal', 'danger')
    return redirect(url_for('admin_usuarios'))


# ==================== RUTAS ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        usuario = gestor_usuarios.verificar_login(username, password)
        if usuario:
            session['user_id'] = usuario['id']
            session['username'] = usuario['username']
            session['rol'] = usuario['rol']
            flash(f'Bienvenido, {usuario["username"]}', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
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

    competencias = gestor_tiempos.listar_competencias()
    nadadores = gestor_nadadores.listar_nadadores()

    categorias = [
        'Juvenil',
        'Master 18-24',
        'Master 25-29',
        'Master 30-34',
        'Master 35-39',
        'Master 40-44',
        'Master 45-49',
        'Master 50-54',
        'Master 55-59',
        'Master 60-64',
        'Master 65-69',
        'Master 70-74',
        'Master 75-79',
        'Master 80-84',
        'Master 85-89',
        'Master 90+'
    ]

    if request.method == 'POST':
        try:
            nombre = request.form['nombre'].strip()
            estilo = request.form['estilo']
            distancia = int(request.form['distancia'])
            piscina = request.form.get(
                'piscina',
                '25 metros'
            )

            categoria = request.form.get(
                'categoria',
                ''
            ).strip()

            tiempo = request.form['tiempo'].strip()
            fecha_str = request.form.get('fecha')

            competencia_id = request.form.get(
                'competencia_id',
                type=int
            )

            if not categoria:
                raise ValueError(
                    'Debe seleccionar una categoría'
                )

            fecha = (
                datetime.strptime(
                    fecha_str,
                    '%Y-%m-%d'
                ).date()
                if fecha_str
                else None
            )

            nadador_id = None

            for nadador in nadadores:
                nombre_completo = (
                    f"{nadador['nombre']} "
                    f"{nadador['apellido']}"
                ).strip()

                if nombre_completo.lower() == nombre.lower():
                    nadador_id = nadador['id']
                    break

            if not nadador_id:
                flash(
                    '❌ Nadador no encontrado',
                    'danger'
                )

                return render_template(
                    'agregar.html',
                    estilos=gestor_tiempos.ESTILOS,
                    distancias=gestor_tiempos.DISTANCIAS,
                    competencias=competencias,
                    nadadores=nadadores,
                    categorias=categorias
                )

            gestor_tiempos.agregar_tiempo(
                nombre,
                estilo,
                distancia,
                tiempo,
                fecha,
                piscina,
                competencia_id
            )

            if competencia_id:
                gestor_tiempos.marcar_asistencia_desde_tiempo(
                    nadador_id,
                    competencia_id
                )

            flash(
                '✅ Tiempo registrado correctamente',
                'success'
            )

            return redirect(
                url_for('listar_tiempos')
            )

        except Exception as e:
            print("Error registrando tiempo:", e)
            flash(
                f'❌ Error: {str(e)}',
                'danger'
            )

    return render_template(
        'agregar.html',
        estilos=gestor_tiempos.ESTILOS,
        distancias=gestor_tiempos.DISTANCIAS,
        competencias=competencias,
        nadadores=nadadores,
        categorias=categorias
    )


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
    tiempo_registro = gestor_tiempos.obtener_tiempo_por_id(
        tiempo_id
    )

    if not tiempo_registro:
        flash('Tiempo no encontrado.', 'danger')
        return redirect(url_for('listar_tiempos'))

    competencias = gestor_tiempos.listar_competencias()

    categorias = [
        'Juvenil',
        'Master 18-24',
        'Master 25-29',
        'Master 30-34',
        'Master 35-39',
        'Master 40-44',
        'Master 45-49',
        'Master 50-54',
        'Master 55-59',
        'Master 60-64',
        'Master 65-69',
        'Master 70-74',
        'Master 75-79',
        'Master 80-84',
        'Master 85-89',
        'Master 90+'
    ]

    if request.method == 'POST':
        try:
            estilo = request.form['estilo']
            distancia = int(request.form['distancia'])
            tiempo = request.form['tiempo'].strip()

            piscina = request.form.get(
                'piscina',
                '25 metros'
            )

            categoria = request.form.get(
                'categoria',
                ''
            ).strip()

            competencia_id = request.form.get(
                'competencia_id',
                type=int
            )

            fecha_str = request.form.get('fecha')

            fecha = (
                datetime.strptime(
                    fecha_str,
                    '%Y-%m-%d'
                ).date()
                if fecha_str
                else None
            )

            if not categoria:
                raise ValueError(
                    'Debe seleccionar una categoría.'
                )

            gestor_tiempos.editar_tiempo(
                tiempo_id=tiempo_id,
                estilo=estilo,
                distancia=distancia,
                tiempo=tiempo,
                fecha=fecha,
                piscina=piscina,
                competencia_id=competencia_id,
                categoria=categoria
            )

            flash(
                'Tiempo actualizado correctamente.',
                'success'
            )

            return redirect(
                url_for('listar_tiempos')
            )

        except Exception as e:
            print("Error editando tiempo:", e)

            flash(
                f'Error al editar el tiempo: {e}',
                'danger'
            )

    return render_template(
        'editar_tiempo.html',
        tiempo=tiempo_registro,
        estilos=gestor_tiempos.ESTILOS,
        distancias=gestor_tiempos.DISTANCIAS,
        competencias=competencias,
        categorias=categorias
    )


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
def progreso_nadador1(nadador_id):
    nadador = gestor_nadadores.obtener_nadador(nadador_id)
    if not nadador:
        flash('Nadador no encontrado', 'danger')
        return redirect(url_for('nadadores'))
    
    nombre_completo = f"{nadador.get('nombre', '')} {nadador.get('apellido', '')}".strip()
    tiempos = gestor_tiempos.obtener_tiempos_nadador(nombre_completo)
    
    return render_template('progreso_nadador1.html', nadador=nadador, tiempos=tiempos)

@app.route('/progreso_nadador', methods=['GET', 'POST'])
@login_required
def progreso_nadador():
    nadadores = gestor_nadadores.listar_nadadores()

    estilos = [
        'Crol',
        'Espalda',
        'Pecho',
        'Mariposa',
        'Combinado'
    ]

    distancias = [25, 50, 100, 200, 400, 800, 1500]

    filtros = {
        'nadador_id': None,
        'estilo': '',
        'distancia': '',
        'piscina': '50 metros'
    }

    nadador = None
    historial = []
    etiquetas = []
    tiempos_grafico = []
    consulta_realizada = False

    if request.method == 'POST':
        consulta_realizada = True

        filtros['nadador_id'] = request.form.get(
            'nadador_id',
            type=int
        )
        filtros['estilo'] = request.form.get(
            'estilo',
            ''
        ).strip()
        filtros['distancia'] = request.form.get(
            'distancia',
            type=int
        )
        filtros['piscina'] = request.form.get(
            'piscina',
            '50 metros'
        ).strip()

        if (
            not filtros['nadador_id']
            or not filtros['estilo']
            or not filtros['distancia']
        ):
            flash(
                'Debe completar todos los filtros.',
                'danger'
            )
        else:
            nadador = gestor_nadadores.obtener_nadador(
                filtros['nadador_id']
            )

            if not nadador:
                flash('Nadador no encontrado.', 'danger')
            else:
                historial = gestor_tiempos.obtener_progreso_nadador(
                    filtros['nadador_id'],
                    filtros['estilo'],
                    filtros['distancia'],
                    filtros['piscina']
                )

                etiquetas = [
                    registro['fecha'].strftime('%d %b %Y')
                    if hasattr(registro['fecha'], 'strftime')
                    else str(registro['fecha'])
                    for registro in historial
                ]

                tiempos_grafico = [
                    float(registro['tiempo_segundos'])
                    for registro in historial
                ]

    return render_template(
        'progreso_nadador.html',
        nadadores=nadadores,
        estilos=estilos,
        distancias=distancias,
        filtros=filtros,
        nadador=nadador,
        historial=historial,
        etiquetas=etiquetas,
        tiempos_grafico=tiempos_grafico,
        consulta_realizada=consulta_realizada
    )

@app.route('/comparacion_25_50', methods=['GET', 'POST'])
@login_required
def comparacion_25_50():
    nadadores = gestor_nadadores.listar_nadadores()

    nadador = None
    comparacion = []

    if request.method == 'POST':
        nadador_id = request.form.get('nadador_id', type=int)

        if not nadador_id:
            flash('Debe seleccionar un nadador', 'danger')
        else:
            nadador = gestor_nadadores.obtener_nadador(nadador_id)

            if not nadador:
                flash('Nadador no encontrado', 'danger')
            else:
                comparacion = gestor_tiempos.comparacion_nadador_25_50(
                    nadador_id
                )

    return render_template(
        'comparacion_25_50.html',
        nadadores=nadadores,
        nadador=nadador,
        comparacion=comparacion
    )

@app.route('/nadador/<int:nadador_id>/tiempos')
@login_required
def tiempos_nadador(nadador_id):
    nadador = gestor_nadadores.obtener_nadador(nadador_id)
    if not nadador:
        flash('Nadador no encontrado', 'danger')
        return redirect(url_for('nadadores'))
    
    nombre_completo = f"{nadador.get('nombre', '')} {nadador.get('apellido', '')}".strip()
    tiempos = gestor_tiempos.obtener_tiempos_nadador(nombre_completo)
    
    return render_template('tiempos_nadador.html', nadador=nadador, tiempos=tiempos)

@app.route('/calendario')
@login_required
def calendario_competencias():

    competencias = gestor_tiempos.listar_competencias()

    print(competencias)   # <-- solo para depuración

    return render_template(
        "calendario.html",
        competencias=competencias
    )

@app.route('/calendario/actualizar_estado', methods=['POST'])
@login_required
@editor_required
def actualizar_estado():
    competencia_id = request.form.get('id')
    estado = request.form.get('estado')

    if not competencia_id or estado not in (
        'REALIZADO',
        'NO REALIZADO'
    ):
        flash('Datos inválidos para actualizar el estado.', 'danger')
        return redirect(url_for('calendario_competencias'))

    try:
        gestor_tiempos.actualizar_estado_competencia(
            competencia_id,
            estado
        )

        flash('Estado actualizado correctamente.', 'success')

    except Exception as e:
        print("Error actualizando estado:", e)
        flash('No fue posible actualizar el estado.', 'danger')

    return redirect(url_for('calendario_competencias'))

@app.route('/competencias/nueva', methods=['GET', 'POST'])
@login_required
@editor_required
def nueva_competencia():
    if request.method == 'POST':
        fecha = request.form.get('fecha', '').strip()
        lugar = request.form.get('lugar', '').strip()
        organiza = request.form.get('organiza', '').strip()
        nombre = request.form.get('nombre', '').strip()
        tipo_piscina = request.form.get('tipo_piscina', '').strip()
        estado = request.form.get('estado', 'NO REALIZADO').strip()

        if not fecha or not lugar or not nombre:
            flash(
                'Fecha, lugar y nombre del torneo son obligatorios.',
                'danger'
            )
            return render_template(
                'competencia_form.html',
                competencia=request.form,
                titulo='Nueva competencia'
            )

        try:
            gestor_tiempos.agregar_competencia(
                fecha=fecha,
                lugar=lugar,
                organiza=organiza,
                nombre=nombre,
                tipo_piscina=tipo_piscina,
                estado=estado
            )

            flash('Competencia creada correctamente.', 'success')
            return redirect(url_for('calendario_competencias'))

        except Exception as e:
            print("Error creando competencia:", e)
            flash('No fue posible crear la competencia.', 'danger')

    return render_template(
        'competencia_form.html',
        competencia=None,
        titulo='Nueva competencia'
    )

@app.route(
    '/competencias/<int:competencia_id>/editar',
    methods=['GET', 'POST']
)
@login_required
@editor_required
def editar_competencia(competencia_id):
    competencia = gestor_tiempos.obtener_competencia(competencia_id)

    if not competencia:
        flash('Competencia no encontrada.', 'danger')
        return redirect(url_for('calendario_competencias'))

    if request.method == 'POST':
        fecha = request.form.get('fecha', '').strip()
        lugar = request.form.get('lugar', '').strip()
        organiza = request.form.get('organiza', '').strip()
        nombre = request.form.get('nombre', '').strip()
        tipo_piscina = request.form.get('tipo_piscina', '').strip()
        estado = request.form.get('estado', 'NO REALIZADO').strip()

        if not fecha or not lugar or not nombre:
            flash(
                'Fecha, lugar y nombre del torneo son obligatorios.',
                'danger'
            )
        else:
            try:
                gestor_tiempos.editar_competencia(
                    competencia_id=competencia_id,
                    fecha=fecha,
                    lugar=lugar,
                    organiza=organiza,
                    nombre=nombre,
                    tipo_piscina=tipo_piscina,
                    estado=estado
                )

                flash('Competencia actualizada correctamente.', 'success')
                return redirect(url_for('calendario_competencias'))

            except Exception as e:
                print("Error editando competencia:", e)
                flash('No fue posible editar la competencia.', 'danger')

    return render_template(
        'competencia_form.html',
        competencia=competencia,
        titulo='Editar competencia'
    )

@app.route(
    '/competencias/<int:competencia_id>/eliminar',
    methods=['POST']
)
@login_required
@editor_required
def eliminar_competencia(competencia_id):
    competencia = gestor_tiempos.obtener_competencia(competencia_id)

    if not competencia:
        flash('Competencia no encontrada.', 'danger')
        return redirect(url_for('calendario_competencias'))

    try:
        gestor_tiempos.eliminar_competencia(competencia_id)
        flash('Competencia eliminada correctamente.', 'success')

    except Exception as e:
        print("Error eliminando competencia:", e)
        flash('No fue posible eliminar la competencia.', 'danger')

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

        if file and file.filename.lower().endswith('.csv'):
            try:
                count = gestor_tiempos.importar_csv(file)

                flash(
                    f'✅ {count} tiempos importados correctamente',
                    'success'
                )

                return redirect(url_for('listar_tiempos'))

            except Exception as e:
                print("❌ ERROR COMPLETO AL IMPORTAR:", repr(e))

                flash(
                    f'❌ Error al importar: {str(e)}',
                    'danger'
                )
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


@app.route('/asistencias')
@login_required
def tabla_asistencias():
    datos = gestor_tiempos.obtener_tabla_asistencia()

    return render_template(
        'asistencias.html',
        nadadores=datos['nadadores'],
        competencias=datos['competencias'],
        asistencias=datos['asistencias']
    )


@app.route('/asistencias/actualizar', methods=['POST'])
@login_required
@editor_required
def actualizar_asistencia():
    nadador_id = request.form.get(
        'nadador_id',
        type=int
    )

    competencia_id = request.form.get(
        'competencia_id',
        type=int
    )

    estado = request.form.get(
        'estado',
        ''
    ).strip()

    if not nadador_id or not competencia_id:
        flash('Datos de asistencia incompletos.', 'danger')
        return redirect(url_for('tabla_asistencias'))

    try:
        gestor_tiempos.actualizar_asistencia(
            nadador_id,
            competencia_id,
            estado
        )

        flash(
            'Asistencia actualizada correctamente.',
            'success'
        )

    except Exception as e:
        print("Error actualizando asistencia:", e)
        flash(
            'No fue posible actualizar la asistencia.',
            'danger'
        )

    return redirect(url_for('tabla_asistencias'))


@app.route('/tiempo/<int:tiempo_id>/editar', methods=['GET', 'POST'])
@login_required
@editor_required
def editar_tiempo_nadador(tiempo_id):
    tiempo_registro = gestor_tiempos.obtener_tiempo_por_id(
        tiempo_id
    )

    if not tiempo_registro:
        flash('Tiempo no encontrado.', 'danger')
        return redirect(url_for('listar_tiempos'))

    competencias = gestor_tiempos.listar_competencias()

    if request.method == 'POST':
        try:
            estilo = request.form['estilo']
            distancia = int(request.form['distancia'])
            tiempo = request.form['tiempo'].strip()
            piscina = request.form.get(
                'piscina',
                '25 metros'
            )
            fecha_str = request.form.get('fecha')
            competencia_id = request.form.get(
                'competencia_id',
                type=int
            )

            fecha = (
                datetime.strptime(
                    fecha_str,
                    '%Y-%m-%d'
                ).date()
                if fecha_str
                else None
            )

            gestor_tiempos.editar_tiempo(
                tiempo_id=tiempo_id,
                estilo=estilo,
                distancia=distancia,
                tiempo=tiempo,
                fecha=fecha,
                piscina=piscina,
                competencia_id=competencia_id
            )

            flash(
                'Tiempo actualizado correctamente.',
                'success'
            )

            return redirect(
                url_for('listar_tiempos')
            )

        except Exception as e:
            print("Error editando tiempo:", e)
            flash(
                f'Error al editar el tiempo: {e}',
                'danger'
            )

    return render_template(
        'editar_tiempo.html',
        tiempo=tiempo_registro,
        estilos=gestor_tiempos.ESTILOS,
        distancias=gestor_tiempos.DISTANCIAS,
        competencias=competencias
    )


@app.route('/tiempo/<int:tiempo_id>/eliminar', methods=['POST'])
@login_required
@editor_required
def eliminar_tiempo_nadador(tiempo_id):
    tiempo_registro = gestor_tiempos.obtener_tiempo_por_id(
        tiempo_id
    )

    if not tiempo_registro:
        flash('Tiempo no encontrado.', 'danger')
        return redirect(url_for('listar_tiempos'))

    try:
        gestor_tiempos.eliminar_tiempo(tiempo_id)

        flash(
            'Tiempo eliminado correctamente.',
            'success'
        )

    except Exception as e:
        print("Error eliminando tiempo:", e)
        flash(
            'No fue posible eliminar el tiempo.',
            'danger'
        )

    return redirect(url_for('listar_tiempos'))

@app.route(
    '/nadadores/importar',
    methods=['GET', 'POST']
)
@login_required
@editor_required
def importar_nadadores():
    if request.method == 'POST':

        if 'file' not in request.files:
            flash(
                'No se seleccionó archivo.',
                'danger'
            )

            return redirect(
                url_for('importar_nadadores')
            )

        file = request.files['file']

        if file.filename == '':
            flash(
                'No se seleccionó archivo.',
                'danger'
            )

            return redirect(
                url_for('importar_nadadores')
            )

        if not file.filename.lower().endswith('.csv'):
            flash(
                'Solo se permiten archivos CSV.',
                'danger'
            )

            return redirect(
                url_for('importar_nadadores')
            )

        try:
            resultado = gestor_nadadores.importar_csv(
                file
            )

            importados = resultado['importados']
            omitidos = resultado['omitidos']
            errores = resultado['errores']

            if errores:
                flash(
                    f'Importación terminada: '
                    f'{importados} importados, '
                    f'{omitidos} omitidos y '
                    f'{len(errores)} errores.',
                    'warning'
                )
            else:
                flash(
                    f'✅ {importados} nadadores '
                    f'importados correctamente. '
                    f'{omitidos} duplicados omitidos.',
                    'success'
                )

            return redirect(
                url_for('nadadores')
            )

        except Exception as e:
            print(
                "Error importando nadadores:",
                repr(e)
            )

            flash(
                f'❌ Error al importar: {str(e)}',
                'danger'
            )

    return render_template(
        'importar_nadadores.html'
    )

# ==================== OTRAS RUTAS (puedes ir agregando) ====================
@app.route('/season_best', methods=['GET', 'POST'])
@login_required
def season_best():
    nadadores = gestor_nadadores.listar_nadadores()

    nadador = None
    mejores_tiempos = []
    consulta_realizada = False

    if request.method == 'POST':
        consulta_realizada = True

        nadador_id = request.form.get(
            'nadador_id',
            type=int
        )

        if not nadador_id:
            flash(
                'Debe seleccionar un nadador.',
                'danger'
            )
        else:
            nadador = gestor_nadadores.obtener_nadador(
                nadador_id
            )

            if not nadador:
                flash(
                    'Nadador no encontrado.',
                    'danger'
                )
            else:
                mejores_tiempos = (
                    gestor_tiempos.obtener_season_best(
                        nadador_id
                    )
                )

    return render_template(
        'season_best.html',
        nadadores=nadadores,
        nadador=nadador,
        mejores_tiempos=mejores_tiempos,
        consulta_realizada=consulta_realizada
    )

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

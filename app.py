from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import json
import pdfkit
from flask import Response


app = Flask(__name__)
app.config['SECRET_KEY'] = '123456'  # Puedes cambiar 'your_secret_key' a cualquier valor aleatorio

# Establece la conexión con la base de datos
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Inicializa la base de datos con la tabla necesaria
def init_db():
    with app.app_context():
        db = get_db_connection()
        cursor = db.cursor()
        
        # Crear tabla de órdenes si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion TEXT NOT NULL,
                conductor TEXT NOT NULL,
                numero_maquina TEXT NOT NULL,
                patente_maquina TEXT NOT NULL,
                falla_reportada TEXT NOT NULL,
                fecha_entrega_programada TEXT NOT NULL,
                necesita_repuestos INTEGER NOT NULL,
                estado_ot TEXT NOT NULL
            )
        ''')
        # Verificar si la columna repuestos existe
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]
        if "repuestos" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN repuestos TEXT")

        db.commit()

def init_users_table():
    with app.app_context():
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        db.commit()


# Ruta principal, simplemente para verificar que todo está funcionando
@app.route('/')
def index():
    try:
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders')
            orders = cursor.fetchall()
    except sqlite3.Error as e:
        print(e)
        orders = []
    return render_template('index.html', ordenes=orders)



# Añade aquí tus rutas y funciones adicionales, como agregar, eliminar, actualizar órdenes, etc.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Login exitoso!', 'success')
            return redirect(url_for('index'))
        flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar si el usuario ya existe
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if user:
            flash('El nombre de usuario ya existe. Por favor, elige otro.', 'danger')
            return redirect(url_for('register'))
        
        # Si el usuario no existe, insertarlo en la base de datos
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, generate_password_hash(password)))
        conn.commit()
        conn.close()

        flash('Usuario registrado con éxito. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Has cerrado sesión', 'success')
    return redirect(url_for('login'))

@app.route('/ordenes')
def listar_ordenes():
    conn = get_db_connection()
    ordenes = conn.execute('SELECT * FROM orders').fetchall()
    conn.close()
    return render_template('index.html', ordenes=ordenes)

@app.route('/crear_orden', methods=['GET', 'POST'])
def crear_orden():
    if request.method == 'POST':
        descripcion = request.form['descripcion']
        conductor = request.form['conductor']
        numero_maquina = request.form['numero_maquina']
        patente_maquina = request.form['patente_maquina']
        falla_reportada = request.form['falla_reportada']
        fecha_entrega_programada = request.form['fecha_entrega_programada']
        necesita_repuestos = int(request.form['necesita_repuestos'])
        estado_ot = request.form['estado_ot']
        repuestos_data = {
        "Aceite Motor": int(request.form['repuesto_Aceite_Motor']),
        "Foco Delantero": int(request.form['repuesto_Foco_Delantero']),
        "Botón Timbre": int(request.form['repuesto_Boton_Timbre']),
        "Válvula Accionamiento": int(request.form['repuesto_Valvula_Accionamiento']),
        "Rodamiento Embrague": int(request.form['repuesto_Rodamiento_Embrague']),
        "Motor Partida": int(request.form['repuesto_Motor_Partida']),
            }
        repuestos = json.dumps(repuestos_data)

        conn = get_db_connection()
        conn.execute('INSERT INTO orders (descripcion, conductor, numero_maquina,patente_maquina,falla_reportada,fecha_entrega_programada, necesita_repuestos, estado_ot, repuestos) VALUES (?, ?, ?, ?, ?, ? , ?, ?, ?)', (descripcion, conductor, numero_maquina,patente_maquina,falla_reportada,fecha_entrega_programada, necesita_repuestos,estado_ot,repuestos))
        conn.commit()
        conn.close()

        flash('Orden creada con éxito', 'success')
        return redirect(url_for('listar_ordenes'))
    return render_template('crear_orden.html')

@app.route('/eliminar_orden/<int:id>', methods=['GET'])
def eliminar_orden(id):
    try:
        with sqlite3.connect("database.db") as conn:
            conn.execute('DELETE FROM orders WHERE id = ?', (id,))
            conn.commit()
            flash('Orden eliminada con éxito!', 'success')
    except sqlite3.Error as e:
        flash('Hubo un error al eliminar: ' + str(e), 'danger')
    return redirect(url_for('index'))


@app.route('/editar_orden/<int:id>', methods=['GET', 'POST'])
def editar_orden(id):
    db = get_db_connection()  # <-- Aquí está el cambio
    cursor = db.cursor()

    # Consultar la orden específica por ID
    cursor.execute('SELECT * FROM orders WHERE id = ?', (id,))
    orden = cursor.fetchone()
    # Si deseas usar la información de repuestos en el template o en algún otro lugar de esta función:
    repuestos_data = json.loads(orden['repuestos'] or '{}')

    # Verificar si la orden existe
    if not orden:
        flash('La orden no existe', 'error')
        return redirect(url_for('listar_ordenes'))  # Asumiendo que tienes una función que muestra la lista de órdenes

    if request.method == 'POST':
        # Recoger los datos del formulario
        descripcion = request.form['descripcion']
        conductor = request.form['conductor']
        numero_maquina = request.form['numero_maquina']
        patente_maquina = request.form['patente_maquina']
        falla_reportada = request.form['falla_reportada']
        fecha_entrega_programada = request.form['fecha_entrega_programada']
        necesita_repuestos = int(request.form['necesita_repuestos'])
        estado_ot = request.form['estado_ot']
        repuestos_actualizados = {
        "Aceite Motor": int(request.form.get('repuesto_Aceite_Motor', 0)),
        "Foco Delantero": int(request.form.get('repuesto_Foco_Delantero', 0)),
        "Botón Timbre": int(request.form.get('repuesto_Boton_Timbre', 0)),
        "Válvula Accionamiento": int(request.form.get('repuesto_Valvula_Accionamiento', 0)),
        "Rodamiento Embrague": int(request.form.get('repuesto_Rodamiento_Embrague', 0)),
        "Motor Partida": int(request.form.get('repuesto_Motor_Partida', 0)),
            }
        repuestos = json.dumps(repuestos_actualizados)

        # Actualizar la orden en la base de datos
        cursor.execute('''
            UPDATE orders
            SET descripcion = ?, conductor = ?, numero_maquina = ?, patente_maquina = ?, falla_reportada = ?, fecha_entrega_programada = ?, necesita_repuestos = ?, estado_ot = ?, repuestos = ?
            WHERE id = ?
        ''', (descripcion, conductor, numero_maquina, patente_maquina, falla_reportada, fecha_entrega_programada, necesita_repuestos, estado_ot, repuestos, id))
        db.commit()

        flash('Orden actualizada con éxito', 'success')
        return redirect(url_for('listar_ordenes'))

    # Mostrar el formulario de edición con los datos actuales de la orden
    return render_template('editar_orden.html', orden=orden, repuestos=repuestos_data)

@app.route('/generate_pdf/<int:id>')
def generate_pdf(id):

    # Obtener la orden específica por ID
    conn = get_db_connection()
    orden = conn.execute('SELECT * FROM orders WHERE id = ?', (id,)).fetchone()
    
    # Deserializar el JSON de repuestos
    repuestos_data = json.loads(orden['repuestos'] or '{}')

    # Calcular el total de los repuestos
    total = sum(cantidad * PRECIO_DEL_REPUESTO[repuesto] for repuesto, cantidad in repuestos_data.items())

    # Renderizar la plantilla HTML pasando la orden, los repuestos, los precios y el total
    html_str = render_template('factura.html', orden=orden, repuestos=repuestos_data, precios=PRECIO_DEL_REPUESTO, total=total)

    # Configuración de pdfkit
    config = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
    
    # Convertir el HTML a PDF
    pdf = pdfkit.from_string(html_str, False, configuration=config)
    
    # Devolver el PDF como respuesta
    response = Response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=factura.pdf'
    
    return response


PRECIO_DEL_REPUESTO = {
    "Aceite Motor": 4000,        # Precio de ejemplo
    "Foco Delantero": 12000,       # Precio de ejemplo
    "Botón Timbre": 5000,         # Precio de ejemplo
    "Válvula Accionamiento": 20000,   # Precio de ejemplo
    "Rodamiento Embrague": 40000,     # Precio de ejemplo
    "Motor Partida": 370000       # Precio de ejemplo
}


# Añade aquí tus rutas y funciones adicionales, como agregar, eliminar, actualizar órdenes, etc.

if __name__ == '__main__':
    init_db()
    init_users_table()
    app.run(debug=True)

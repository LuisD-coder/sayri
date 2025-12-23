from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify, flash
from models import db, Cliente, Grupo, PrestamoGrupal, PrestamoIndividual, Contrato, Pago, FotoCliente
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
import os
from PIL import Image
from io import BytesIO

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')
fotos = db.relationship('FotoCliente', backref='cliente', lazy=True, cascade='all, delete-orphan', order_by='FotoCliente.orden')

# --- HELPER: Obtener grupos permitidos (SEGURIDAD) ---
def obtener_grupos_permitidos():
    """Devuelve la lista de grupos segun el rol del usuario"""
    if current_user.rol.nombre == 'admin':
        return Grupo.query.all()
    else:
        # Usamos .grupos (la relación Many-to-Many corregida)
        return current_user.grupos

def verificar_acceso_cliente(cliente):
    """Verifica si el usuario actual tiene permiso para ver a este cliente"""
    if current_user.rol.nombre == 'admin':
        return True
    
    # Si el cliente tiene grupo, verificamos si el usuario pertenece a ese grupo
    if cliente.grupo:
        return cliente.grupo in current_user.grupos
    
    # Si el cliente NO tiene grupo (es huérfano), decidimos la política:
    # Opción A: Solo Admin los ve (Retornar False)
    # Opción B: Todos los ven (Retornar True) -> Usaremos False por seguridad estricta
    return False

# ----------------------------------------------------------------------
# CREAR NUEVO CLIENTE
# ----------------------------------------------------------------------
@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_cliente():
    # ✅ SEGURIDAD: Solo mostramos grupos permitidos en el select
    grupos = obtener_grupos_permitidos()
    
    if request.method == 'POST':
        nombre = ' '.join(word.capitalize() for word in request.form['nombre'].strip().split())
        apellido = ' '.join(word.capitalize() for word in request.form['apellido'].strip().split())
        dni = request.form['dni'].strip()
        celular = request.form['celular'].strip()
        operadora = request.form['operadora'].strip().capitalize()
        banco = request.form['banco'].strip().upper()
        numero_cuenta = request.form['numero_cuenta'].strip()
        grupo_id = request.form['grupo_id'].strip()
        
        # ✅ SEGURIDAD: Validar que el grupo seleccionado sea válido para este usuario
        grupo_seleccionado = Grupo.query.get(grupo_id)
        if not grupo_seleccionado:
             flash('Grupo no valido.', 'danger')
             return render_template('clientes/nuevo_cliente.html', grupos=grupos)
             
        if current_user.rol.nombre != 'admin' and grupo_seleccionado not in current_user.grupos:
             flash('No tienes permiso para asignar clientes a este grupo.', 'danger')
             return render_template('clientes/nuevo_cliente.html', grupos=grupos)

        # --- NUEVOS CAMPOS ---
        email = request.form.get('email', '').strip()
        direccion = request.form.get('direccion', '').strip()
        referencia = request.form.get('referencia', '').strip()
        latitud = request.form.get('latitud', '').strip()
        longitud = request.form.get('longitud', '').strip()
        
        nuevo_cliente = Cliente(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            celular=celular,
            operadora=operadora,
            banco=banco,
            numero_cuenta=numero_cuenta,
            grupo_id=grupo_id,
            email=email,
            direccion=direccion,
            referencia=referencia,
            latitud=latitud,
            longitud=longitud
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        flash('Cliente registrado exitosamente.', 'success')
        return redirect(url_for('clientes.lista_clientes'))

    return render_template('clientes/nuevo_cliente.html', grupos=grupos)


# ----------------------------------------------------------------------
# LISTAR CLIENTES (FILTRADO)
# ----------------------------------------------------------------------
@clientes_bp.route('/')
@login_required
def lista_clientes():
    page = request.args.get('page', 1, type=int)
    grupo_id = request.args.get('grupo_id', type=int)
    search = request.args.get('search', '').strip()

    # ✅ SEGURIDAD: Obtener los grupos permitidos para el filtro y la validación
    grupos_permitidos = obtener_grupos_permitidos()
    ids_grupos_permitidos = [g.id for g in grupos_permitidos]

    # Construcción de la consulta base
    query = Cliente.query

    # ✅ FILTRO DE SEGURIDAD: Si no es admin, filtrar clientes por los grupos permitidos
    if current_user.rol.nombre != 'admin':
        if not ids_grupos_permitidos:
            # Si el asesor no tiene grupos, no ve nada
            query = query.filter(db.false())
        else:
            query = query.filter(Cliente.grupo_id.in_(ids_grupos_permitidos))

    # Filtros opcionales del usuario
    if grupo_id:
        # Verificar que el usuario tenga acceso al grupo que está filtrando
        if current_user.rol.nombre != 'admin' and grupo_id not in ids_grupos_permitidos:
            flash('Acceso denegado al grupo solicitado.', 'danger')
            return redirect(url_for('clientes.lista_clientes'))
        query = query.filter_by(grupo_id=grupo_id)

    if search:
        query = query.filter(
            Cliente.nombre.ilike(f"%{search}%") | Cliente.dni.ilike(f"%{search}%")
        )

    # Ordenar por fecha de registro descendente
    query = query.order_by(Cliente.fecha_registro.desc())

    clientes = query.paginate(page=page, per_page=10)

    return render_template('clientes/lista_clientes.html', 
                           clientes=clientes, 
                           grupos=grupos_permitidos, # Pasamos solo los permitidos al select
                           selected_grupo=grupo_id)


# ----------------------------------------------------------------------
# DETALLE CLIENTE
# ----------------------------------------------------------------------
@clientes_bp.route('/<int:cliente_id>')
@login_required
def detalle_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # ✅ SEGURIDAD
    if not verificar_acceso_cliente(cliente):
        flash('No tienes permiso para ver este cliente.', 'danger')
        return redirect(url_for('clientes.lista_clientes'))
    
    prestamos = cliente.prestamos_individuales
    contratos = cliente.contratos
    pagos = cliente.pagos
    prestamos_grupales = PrestamoGrupal.query.join(PrestamoIndividual).filter(PrestamoIndividual.cliente_id == cliente.id).all()
    
    return render_template('clientes/detalle_cliente.html', cliente=cliente, prestamos=prestamos, contratos=contratos, pagos=pagos, prestamos_grupales=prestamos_grupales)


# ----------------------------------------------------------------------
# ELIMINAR CLIENTE
# ----------------------------------------------------------------------
@clientes_bp.route('/eliminar/<int:cliente_id>', methods=['POST'])
@login_required
def eliminar_cliente(cliente_id):
    # Solo admin puede eliminar, o manager
    if not current_user.is_authenticated or current_user.rol.nombre not in ['admin', 'manager']:
        abort(403)

    cliente = Cliente.query.get_or_404(cliente_id)
    
    # ✅ SEGURIDAD (Opcional: ¿Un admin puede borrar cualquier cliente? Sí. ¿Un manager? Quizás solo los suyos)
    # Por ahora mantenemos la restricción por rol superior
    
    try:
        PrestamoIndividual.query.filter_by(cliente_id=cliente.id).delete()
        Contrato.query.filter_by(cliente_id=cliente.id).delete()
        Pago.query.filter_by(cliente_id=cliente.id).delete()
        
        db.session.delete(cliente)
        db.session.commit()
        flash('Cliente eliminado correctamente.', 'success')
        return redirect(url_for('clientes.lista_clientes'))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el cliente: {str(e)}", 'error')
        return redirect(url_for('clientes.lista_clientes'))


# ----------------------------------------------------------------------
# EDITAR CLIENTE
# ----------------------------------------------------------------------
@clientes_bp.route('/editar/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def actualizar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # ✅ SEGURIDAD
    if not verificar_acceso_cliente(cliente):
        flash('No tienes permiso para editar este cliente.', 'danger')
        return redirect(url_for('clientes.lista_clientes'))

    # Para el formulario, solo mostrar grupos permitidos
    grupos = obtener_grupos_permitidos()

    if request.method == 'POST':
        try:
            # Validar el grupo destino
            nuevo_grupo_id = int(request.form['grupo_id'].strip())
            
            # Verificar si el usuario tiene permiso sobre el NUEVO grupo
            grupo_destino = Grupo.query.get(nuevo_grupo_id)
            if current_user.rol.nombre != 'admin' and grupo_destino not in current_user.grupos:
                 flash('No puedes mover al cliente a un grupo que no te pertenece.', 'danger')
                 return render_template('clientes/editar_cliente.html', cliente=cliente, grupos=grupos)

            cliente.nombre = ' '.join(word.capitalize() for word in request.form['nombre'].strip().split())
            cliente.apellido = ' '.join(word.capitalize() for word in request.form['apellido'].strip().split())
            cliente.dni = request.form['dni'].strip()
            cliente.celular = request.form['celular'].strip()
            cliente.operadora = request.form['operadora'].strip().capitalize()
            cliente.banco = request.form['banco'].strip().upper()
            cliente.numero_cuenta = request.form['numero_cuenta'].strip()
            cliente.grupo_id = nuevo_grupo_id

            # --- ACTUALIZAR NUEVOS CAMPOS ---
            cliente.email = request.form.get('email', '').strip()
            cliente.direccion = request.form.get('direccion', '').strip()
            cliente.referencia = request.form.get('referencia', '').strip()
            
            new_lat = request.form.get('latitud', '').strip()
            new_lon = request.form.get('longitud', '').strip()
            if new_lat and new_lon:
                cliente.latitud = new_lat
                cliente.longitud = new_lon

            db.session.commit()
            flash('Datos del cliente actualizados.', 'success')
            return redirect(url_for('clientes.detalle_cliente', cliente_id=cliente.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar el cliente: {str(e)}", 'error')

    return render_template('clientes/editar_cliente.html', cliente=cliente, grupos=grupos)


UPLOAD_FOLDER = 'static/uploads/clientes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FOTOS_POR_CLIENTE = 3

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@clientes_bp.route('/<int:cliente_id>/fotos', methods=['GET'])
@login_required
def obtener_fotos(cliente_id):
    from models.foto_cliente import FotoCliente
    cliente = Cliente.query.get_or_404(cliente_id)
    if not verificar_acceso_cliente(cliente):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    fotos = FotoCliente.query.filter_by(cliente_id=cliente_id).order_by(FotoCliente.orden).all()
    return jsonify({
        'success': True,
        'fotos': [foto.to_dict() for foto in fotos]
    })

@clientes_bp.route('/<int:cliente_id>/subir_foto', methods=['POST'])
@login_required
def subir_foto(cliente_id):
    from models.foto_cliente import FotoCliente
    cliente = Cliente.query.get_or_404(cliente_id)
    
    if not verificar_acceso_cliente(cliente):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    num_fotos = FotoCliente.query.filter_by(cliente_id=cliente_id).count()
    if num_fotos >= MAX_FOTOS_POR_CLIENTE:
        return jsonify({
            'success': False,
            'error': f'El cliente ya tiene {MAX_FOTOS_POR_CLIENTE} fotos. Elimina una antes de agregar otra.'
        }), 400
    
    if 'foto' not in request.files:
        return jsonify({'success': False, 'error': 'No se envio archivo'}), 400
    
    foto = request.files['foto']
    if foto.filename == '':
        return jsonify({'success': False, 'error': 'Archivo vacio'}), 400
    
    if not allowed_file(foto.filename):
        return jsonify({'success': False, 'error': 'Formato no permitido'}), 400
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = secure_filename(f"cliente_{cliente_id}_{timestamp}_{foto.filename}")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    try:
        img = Image.open(foto)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        max_width = 1280
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        img.save(filepath, optimize=True, quality=80)
    except Exception as e:
        print(f"Error al comprimir imagen: {e}")
        foto.save(filepath)
    
    nueva_foto = FotoCliente(
        cliente_id=cliente_id,
        url=f'/static/uploads/clientes/{filename}',
        orden=num_fotos
    )
    db.session.add(nueva_foto)
    db.session.commit()
    
    return jsonify({'success': True, 'foto': nueva_foto.to_dict()})


@clientes_bp.route('/<int:cliente_id>/fotos/<int:foto_id>', methods=['DELETE'])
@login_required
def eliminar_foto(cliente_id, foto_id):
    from models.foto_cliente import FotoCliente
    
    # Verificar acceso al cliente primero
    cliente = Cliente.query.get_or_404(cliente_id)
    if not verificar_acceso_cliente(cliente):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    foto = FotoCliente.query.filter_by(id=foto_id, cliente_id=cliente_id).first_or_404()
    try:
        filepath = foto.url.lstrip('/')
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error al eliminar archivo: {e}")
    db.session.delete(foto)
    db.session.commit()
    return jsonify({'success': True})
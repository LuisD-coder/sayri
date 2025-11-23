from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify
from models import db, Cliente, Grupo, PrestamoGrupal, PrestamoIndividual,Contrato, Pago, FotoCliente
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
import os
from PIL import Image
from io import BytesIO

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')
fotos = db.relationship('FotoCliente', backref='cliente', lazy=True, cascade='all, delete-orphan', order_by='FotoCliente.orden')

# Crear un nuevo cliente
@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_cliente():
    grupos = Grupo.query.all()
    
    if request.method == 'POST':
        nombre = ' '.join(word.capitalize() for word in request.form['nombre'].strip().split())
        apellido = ' '.join(word.capitalize() for word in request.form['apellido'].strip().split())
        dni = request.form['dni'].strip()
        celular = request.form['celular'].strip()
        operadora = request.form['operadora'].strip().capitalize()
        banco = request.form['banco'].strip().upper()  # Los nombres de bancos suelen ir en mayúsculas
        numero_cuenta = request.form['numero_cuenta'].strip()
        grupo_id = request.form['grupo_id'].strip()
        
        nuevo_cliente = Cliente(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            celular=celular,
            operadora=operadora,
            banco=banco,
            numero_cuenta=numero_cuenta,
            grupo_id=grupo_id
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        return redirect(url_for('clientes.lista_clientes'))

    return render_template('clientes/nuevo_cliente.html', grupos=grupos)



@clientes_bp.route('/')
@login_required
def lista_clientes():
    page = request.args.get('page', 1, type=int)
    grupo_id = request.args.get('grupo_id', type=int)
    search = request.args.get('search', '').strip()

    # Si no hay filtros seleccionados, no ejecutar la consulta
    if not grupo_id and not search:
        return render_template('clientes/lista_clientes.html', clientes=None, grupos=Grupo.query.all(), selected_grupo=None)

    query = Cliente.query
    if grupo_id:
        query = query.filter_by(grupo_id=grupo_id)
    if search:
        query = query.filter(
            Cliente.nombre.ilike(f"%{search}%") | Cliente.dni.ilike(f"%{search}%")
        )

    clientes = query.paginate(page=page, per_page=10)  # 10 clientes por página
    grupos = Grupo.query.all()  # Obtener todos los grupos

    return render_template('clientes/lista_clientes.html', clientes=clientes, grupos=grupos, selected_grupo=grupo_id)

    page = request.args.get('page', 1, type=int)
    grupo_id = request.args.get('grupo_id', type=int)
    search = request.args.get('search', '').strip()

    query = Cliente.query
    if grupo_id:
        query = query.filter_by(grupo_id=grupo_id)
    if search:
        query = query.filter(
            Cliente.nombre.ilike(f"%{search}%") | Cliente.dni.ilike(f"%{search}%")
        )

    clientes = query.paginate(page=page, per_page=10)  # 10 clientes por página
    grupos = Grupo.query.all()  # Obtener todos los grupos

    return render_template('clientes/lista_clientes.html', clientes=clientes, grupos=grupos, selected_grupo=grupo_id)




@clientes_bp.route('/<int:cliente_id>')
@login_required
def detalle_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Obtener los préstamos individuales, contratos, pagos y préstamos grupales relacionados con el cliente
    prestamos = cliente.prestamos_individuales  # Relación con los préstamos individuales
    contratos = cliente.contratos  # Relación con los contratos
    pagos = cliente.pagos  # Relación con los pagos
    prestamos_grupales = PrestamoGrupal.query.join(PrestamoIndividual).filter(PrestamoIndividual.cliente_id == cliente.id).all()  # Obtener préstamos grupales del cliente
    
    return render_template('clientes/detalle_cliente.html', cliente=cliente, prestamos=prestamos, contratos=contratos, pagos=pagos, prestamos_grupales=prestamos_grupales)



@clientes_bp.route('/eliminar/<int:cliente_id>', methods=['POST'])
@login_required
def eliminar_cliente(cliente_id):


    # Verificar si el usuario tiene los roles permitidos
    if not current_user.is_authenticated or current_user.rol.nombre not in ['admin', 'manager']:
        print(f"Acceso denegado. Rol encontrado: {getattr(current_user.rol, 'nombre', 'Sin rol')}")
        abort(403)  # Denegar acceso (403 Forbidden)

    cliente = Cliente.query.get_or_404(cliente_id)  # Obtener el cliente
    
    try:
        # Eliminar todos los préstamos individuales relacionados con el cliente
        PrestamoIndividual.query.filter_by(cliente_id=cliente.id).delete()
        # Eliminar los contratos asociados
        Contrato.query.filter_by(cliente_id=cliente.id).delete()
        # Eliminar todos los pagos relacionados con el cliente
        Pago.query.filter_by(cliente_id=cliente.id).delete()
        
        
        # Ahora eliminar el cliente
        db.session.delete(cliente)
        db.session.commit()
        return redirect(url_for('clientes.lista_clientes'))
    except Exception as e:
        db.session.rollback()
        return f"Error al eliminar el cliente: {str(e)}", 500


@clientes_bp.route('/editar/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def actualizar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)  # Obtener el cliente por su ID
    grupos = Grupo.query.all()  # Listar los grupos disponibles

    if request.method == 'POST':
        try:
            # Actualizar los datos del cliente con los valores del formulario
            cliente.nombre = ' '.join(word.capitalize() for word in request.form['nombre'].strip().split())
            cliente.apellido = ' '.join(word.capitalize() for word in request.form['apellido'].strip().split())
            cliente.dni = request.form['dni'].strip()
            cliente.celular = request.form['celular'].strip()
            cliente.operadora = request.form['operadora'].strip().capitalize()
            cliente.banco = request.form['banco'].strip().upper()
            cliente.numero_cuenta = request.form['numero_cuenta'].strip()
            cliente.grupo_id = request.form['grupo_id'].strip()

            db.session.commit()  # Guardar los cambios en la base de datos
            return redirect(url_for('clientes.detalle_cliente', cliente_id=cliente.id))
        except Exception as e:
            db.session.rollback()  # Revertir los cambios en caso de error
            return f"Error al actualizar el cliente: {str(e)}", 500

    # En caso de GET, renderizar el formulario de edición con los datos existentes
    return render_template('clientes/editar_cliente.html', cliente=cliente, grupos=grupos)



UPLOAD_FOLDER = 'static/uploads/clientes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FOTOS_POR_CLIENTE = 3

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@clientes_bp.route('/<int:cliente_id>/fotos', methods=['GET'])
@login_required
def obtener_fotos(cliente_id):
    """Obtener todas las fotos de un cliente"""
    from models.cliente import Cliente
    from models.foto_cliente import FotoCliente
    
    cliente = Cliente.query.get_or_404(cliente_id)
    fotos = FotoCliente.query.filter_by(cliente_id=cliente_id).order_by(FotoCliente.orden).all()
    
    return jsonify({
        'success': True,
        'fotos': [foto.to_dict() for foto in fotos]
    })

@clientes_bp.route('/<int:cliente_id>/subir_foto', methods=['POST'])
@login_required
def subir_foto(cliente_id):
    """Subir y comprimir una nueva foto para el cliente"""
    from models.cliente import Cliente
    from models.foto_cliente import FotoCliente
    from models import db
    
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Verificar número de fotos existentes
    num_fotos = FotoCliente.query.filter_by(cliente_id=cliente_id).count()
    if num_fotos >= MAX_FOTOS_POR_CLIENTE:
        return jsonify({
            'success': False,
            'error': f'El cliente ya tiene {MAX_FOTOS_POR_CLIENTE} fotos. Elimina una antes de agregar otra.'
        }), 400
    
    # Validar archivo
    if 'foto' not in request.files:
        return jsonify({'success': False, 'error': 'No se envió archivo'}), 400
    
    foto = request.files['foto']
    
    if foto.filename == '':
        return jsonify({'success': False, 'error': 'Archivo vacío'}), 400
    
    if not allowed_file(foto.filename):
        return jsonify({'success': False, 'error': 'Formato no permitido'}), 400
    
    # Crear directorio si no existe
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Generar nombre único
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = secure_filename(f"cliente_{cliente_id}_{timestamp}_{foto.filename}")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    # 🧠 COMPRIMIR imagen antes de guardar
    try:
        # Abrir la imagen con Pillow
        img = Image.open(foto)
        
        # Convertir a RGB (para evitar errores con PNG con transparencia)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Redimensionar si es muy grande (opcional, mejora rendimiento)
        max_width = 1280  # puedes ajustar el tamaño máximo
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        
        # Guardar comprimida con calidad reducida (80 = buena calidad)
        img.save(filepath, optimize=True, quality=80)
    
    except Exception as e:
        print(f"Error al comprimir imagen: {e}")
        foto.save(filepath)  # Si falla, guardar original como respaldo
    
    # Guardar referencia en base de datos
    nueva_foto = FotoCliente(
        cliente_id=cliente_id,
        url=f'/static/uploads/clientes/{filename}',
        orden=num_fotos  # La nueva foto va al final
    )
    db.session.add(nueva_foto)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'foto': nueva_foto.to_dict()
    })


@clientes_bp.route('/<int:cliente_id>/fotos/<int:foto_id>', methods=['DELETE'])
@login_required
def eliminar_foto(cliente_id, foto_id):
    """Eliminar una foto del cliente"""
    from models.foto_cliente import FotoCliente
    from models import db
    
    foto = FotoCliente.query.filter_by(id=foto_id, cliente_id=cliente_id).first_or_404()
    
    # Eliminar archivo físico
    try:
        filepath = foto.url.lstrip('/')
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error al eliminar archivo: {e}")
    
    # Eliminar de base de datos
    db.session.delete(foto)
    db.session.commit()
    
    return jsonify({'success': True})

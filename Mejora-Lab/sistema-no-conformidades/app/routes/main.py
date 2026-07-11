from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import db, NoConformidad, Area
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Página principal - Dashboard"""
    # Estadísticas generales
    total_nc = NoConformidad.query.count()
    nc_abiertas = NoConformidad.query.filter_by(estado='Abierta').count()
    nc_en_proceso = NoConformidad.query.filter_by(estado='En proceso').count()
    nc_cerradas = NoConformidad.query.filter_by(estado='Cerrada').count()

    # Últimas NC registradas
    ultimas_nc = NoConformidad.query.order_by(NoConformidad.fecha_creacion.desc()).limit(5).all()

    return render_template('index.html',
                         total_nc=total_nc,
                         nc_abiertas=nc_abiertas,
                         nc_en_proceso=nc_en_proceso,
                         nc_cerradas=nc_cerradas,
                         ultimas_nc=ultimas_nc)


@main_bp.route('/no-conformidades')
def listar_nc():
    """Lista todas las no conformidades"""
    page = request.args.get('page', 1, type=int)
    estado = request.args.get('estado', '')
    area = request.args.get('area', '')

    query = NoConformidad.query

    # Filtros
    if estado:
        query = query.filter_by(estado=estado)
    if area:
        query = query.filter_by(area_afectada=area)

    # Paginación
    nc_pagination = query.order_by(NoConformidad.fecha_creacion.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    areas = db.session.query(NoConformidad.area_afectada).distinct().all()
    areas = [a[0] for a in areas]

    return render_template('no_conformidades/lista.html',
                         no_conformidades=nc_pagination.items,
                         pagination=nc_pagination,
                         areas=areas)


@main_bp.route('/no-conformidades/nueva', methods=['GET', 'POST'])
def nueva_nc():
    """Crear nueva no conformidad"""
    if request.method == 'POST':
        try:
            # Generar número automático
            numero_nc = NoConformidad.generar_numero_nc()

            nc = NoConformidad(
                numero_nc=numero_nc,
                descripcion=request.form.get('descripcion'),
                area_afectada=request.form.get('area_afectada'),
                tipo_nc=request.form.get('tipo_nc'),
                severidad=request.form.get('severidad'),
                estado='Abierta',
                creado_por=request.form.get('creado_por', 'Usuario'),
                responsable=request.form.get('responsable'),
                accion_inmediata=request.form.get('accion_inmediata'),
                observaciones=request.form.get('observaciones')
            )

            db.session.add(nc)
            db.session.commit()

            flash(f'No Conformidad {numero_nc} creada exitosamente', 'success')
            return redirect(url_for('main.ver_nc', id=nc.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la NC: {str(e)}', 'error')

    # GET - mostrar formulario
    areas = db.session.query(NoConformidad.area_afectada).distinct().all()
    areas = [a[0] for a in areas if a[0]]

    return render_template('no_conformidades/nueva.html', areas=areas)


@main_bp.route('/no-conformidades/<int:id>')
def ver_nc(id):
    """Ver detalle de una no conformidad"""
    nc = NoConformidad.query.get_or_404(id)
    return render_template('no_conformidades/detalle.html', nc=nc)


@main_bp.route('/no-conformidades/<int:id>/editar', methods=['GET', 'POST'])
def editar_nc(id):
    """Editar una no conformidad"""
    nc = NoConformidad.query.get_or_404(id)

    if request.method == 'POST':
        try:
            nc.descripcion = request.form.get('descripcion')
            nc.area_afectada = request.form.get('area_afectada')
            nc.tipo_nc = request.form.get('tipo_nc')
            nc.severidad = request.form.get('severidad')
            nc.estado = request.form.get('estado')
            nc.responsable = request.form.get('responsable')
            nc.causa_raiz = request.form.get('causa_raiz')
            nc.accion_inmediata = request.form.get('accion_inmediata')
            nc.accion_correctiva = request.form.get('accion_correctiva')
            nc.accion_preventiva = request.form.get('accion_preventiva')
            nc.observaciones = request.form.get('observaciones')
            nc.modificado_por = request.form.get('modificado_por', 'Usuario')
            nc.fecha_modificacion = datetime.utcnow()

            # Si se marca como cerrada, agregar fecha de cierre
            if nc.estado == 'Cerrada' and not nc.fecha_cierre:
                nc.fecha_cierre = datetime.utcnow()

            db.session.commit()
            flash('No Conformidad actualizada exitosamente', 'success')
            return redirect(url_for('main.ver_nc', id=nc.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la NC: {str(e)}', 'error')

    areas = db.session.query(NoConformidad.area_afectada).distinct().all()
    areas = [a[0] for a in areas if a[0]]

    return render_template('no_conformidades/editar.html', nc=nc, areas=areas)


@main_bp.route('/no-conformidades/<int:id>/eliminar', methods=['POST'])
def eliminar_nc(id):
    """Eliminar una no conformidad"""
    nc = NoConformidad.query.get_or_404(id)

    try:
        db.session.delete(nc)
        db.session.commit()
        flash('No Conformidad eliminada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la NC: {str(e)}', 'error')

    return redirect(url_for('main.listar_nc'))


@main_bp.route('/api/estadisticas')
def api_estadisticas():
    """API para obtener estadísticas"""
    total_nc = NoConformidad.query.count()
    nc_abiertas = NoConformidad.query.filter_by(estado='Abierta').count()
    nc_en_proceso = NoConformidad.query.filter_by(estado='En proceso').count()
    nc_cerradas = NoConformidad.query.filter_by(estado='Cerrada').count()

    return jsonify({
        'total': total_nc,
        'abiertas': nc_abiertas,
        'en_proceso': nc_en_proceso,
        'cerradas': nc_cerradas
    })

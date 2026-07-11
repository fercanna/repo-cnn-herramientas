import streamlit as st
import time
from datetime import datetime
from database import db_manager

def _add_time_entry_to_db(entry_data):
    """Función interna para añadir una sesión de trabajo a la DB."""
    try:
        db_manager.add_time_entry(
            task_id=entry_data['task_id'],
            start_time=entry_data['start_time'],
            end_time=entry_data['end_time']
        )
        duration = int((datetime.fromisoformat(entry_data['end_time']) - datetime.fromisoformat(entry_data['start_time'])).total_seconds() / 60)
        st.success(f"Sesión de {duration} minutos registrada para la tarea ID {entry_data['task_id']}.")
    except Exception as e:
        st.error(f"Error al registrar la sesión de trabajo: {e}")

def timer_widget():
    """
    Muestra un widget para cronometrar tareas existentes, guardando cada
    sesión en la base de datos y detectando superposiciones.
    """
    st.subheader("Cronometrar Tarea Existente")

    # --- Inicialización del Estado ---
    for key in ['timer_running', 'timing_task_id', 'start_time', 'confirming_overlap_timer', 'pending_time_entry', 'conflicting_entries']:
        if key not in st.session_state:
            st.session_state[key] = None

    # --- Lógica de la Interfaz de Usuario ---
    if st.session_state.get('confirming_overlap_timer'):
        st.warning("¡Atención! El tiempo registrado se superpone con las siguientes sesiones:")
        for entry in st.session_state.get('conflicting_entries', []):
            st.error(f"**Tarea '{entry['task_description']}'**: {entry['start_time']} - {entry['end_time']}")

        if st.button("Guardar de Todos Modos", type="primary", use_container_width=True):
            entry_data = st.session_state.get('pending_time_entry')
            if entry_data:
                _add_time_entry_to_db(entry_data)
            # Limpiar estado y refrescar
            st.session_state.clear()
            st.rerun()
        if st.button("Cancelar Registro", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    elif st.session_state.get('timer_running'):
        task = db_manager.get_task_by_id(st.session_state.timing_task_id)
        if not task:
            st.error("La tarea que se estaba cronometrando ya no existe."); st.session_state.clear(); st.rerun()
            return

        st.info(f"Temporizador activo para: **{task['task_description']}**")
        
        timer_placeholder = st.empty()
        
        if st.button("Detener Temporizador", type="primary", use_container_width=True):
            end_time = datetime.now()
            start_time = st.session_state.start_time

            pending_entry = {
                "task_id": task['id'],
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }
            
            conflicts = db_manager.check_for_overlapping_tasks(
                start_time=pending_entry['start_time'], end_time=pending_entry['end_time']
            )

            if conflicts:
                st.session_state.pending_time_entry = pending_entry
                st.session_state.conflicting_entries = [dict(row) for row in conflicts]
                st.session_state.confirming_overlap_timer = True
                st.rerun()
            else:
                _add_time_entry_to_db(pending_entry)
                st.session_state.timer_running = False
                st.session_state.timing_task_id = None
                st.rerun()

        while st.session_state.timer_running:
            current_duration = datetime.now() - st.session_state.start_time
            display_seconds = int(current_duration.total_seconds())
            h, rem = divmod(display_seconds, 3600); m, s = divmod(rem, 60)
            timer_placeholder.metric("Tiempo Transcurrido", f"{h:02}:{m:02}:{s:02}")
            time.sleep(1)
            st.rerun()

    else:
        tasks = db_manager.get_tasks()
        if not tasks:
            st.warning("No hay tareas creadas para cronometrar.")
            return

        task_options = {f"ID {task['id']} - {task['task_description']}": task['id'] for task in tasks if task['task_description']}
        if not task_options:
            st.warning("No hay tareas con descripción para seleccionar.")
            return
            
        selected_task_label = st.selectbox("Selecciona una tarea", options=list(task_options.keys()))

        if st.button("Iniciar Temporizador", use_container_width=True):
            if selected_task_label:
                st.session_state.timing_task_id = task_options[selected_task_label]
                st.session_state.start_time = datetime.now()
                st.session_state.timer_running = True
                st.rerun()

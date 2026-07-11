import streamlit as st
from database import db_manager
from components.task_entry import task_entry_form
from components.timer import timer_widget
from datetime import datetime

def _update_task_details(task_data):
    """Función interna para actualizar los detalles de una tarea en la DB."""
    try:
        db_manager.update_task(
            task_id=task_data['task_id'],
            client=task_data.get('client'),
            project=task_data.get('project'),
            task_description=task_data['task_description'],
            tags=task_data.get('tags'),
            billable=task_data.get('billable'),
            notes=task_data.get('notes')
        )
        st.success(f"Tarea {task_data['task_id']} actualizada con éxito!")
    except Exception as e:
        st.error(f"Error al actualizar la tarea: {e}")

def main():
    """Función principal de la aplicación Streamlit."""
    
    st.set_page_config(page_title="TimeTracker", page_icon="⏱️", layout="wide")
    db_manager.init_db()
    
    if 'editing_task_id' not in st.session_state:
        st.session_state.editing_task_id = None

    with st.sidebar:
        st.header("Control de Tiempo")
        if not st.session_state.editing_task_id:
            timer_widget()
        st.markdown("---")
        if st.button("Refrescar Tareas", help="Actualiza la lista de tareas mostradas."):
            st.rerun()

    st.title("TimeTracker - Gestión de Tiempo")

    if st.session_state.get('editing_task_id'):
        # --- VISTA DE EDICIÓN DE DETALLES DE TAREA ---
        task_id = st.session_state.editing_task_id
        task_to_edit = db_manager.get_task_by_id(task_id)

        if not task_to_edit:
            st.error("La tarea que intentas editar no existe."); st.session_state.editing_task_id = None; st.rerun()
            return

        st.subheader(f"Editando Detalles de Tarea ID: {task_id}")
        with st.form("edit_details_form"):
            client = st.text_input("Cliente", value=task_to_edit['client'])
            project = st.text_input("Proyecto", value=task_to_edit['project'])
            task_description = st.text_area("Descripción", value=task_to_edit['task_description'])
            tags = st.text_input("Etiquetas", value=task_to_edit['tags'])
            billable = st.checkbox("Facturable", value=bool(task_to_edit['billable']))
            notes = st.text_area("Notas", value=task_to_edit['notes'])

            submitted, cancelled = st.form_submit_button("Guardar Cambios"), st.form_submit_button("Cancelar")

            if submitted:
                task_data = {
                    "task_id": task_id, "client": client, "project": project, 
                    "task_description": task_description, "tags": tags, 
                    "billable": billable, "notes": notes
                }
                _update_task_details(task_data)
                st.session_state.editing_task_id = None
                st.rerun()
            if cancelled:
                st.session_state.editing_task_id = None
                st.rerun()
    else:
        # --- VISTA NORMAL ---
        task_entry_form()
        st.markdown("---")
        st.subheader("Tareas Registradas")
        
        tasks_data = db_manager.get_tasks()
        if not tasks_data:
            st.info("No hay tareas creadas para cronometrar. ¡Usa el formulario de arriba para empezar!")
        else:
            cols = st.columns((0.5, 1.5, 1.5, 2.5, 1, 1, 2))
            headers = ["ID", "Cliente", "Proyecto", "Descripción", "Tiempo Total", "Facturable", "Acciones"]
            for col, header in zip(cols, headers): col.write(f"**{header}**")
            
            for task in tasks_data:
                cols = st.columns((0.5, 1.5, 1.5, 2.5, 1, 1, 2))
                duration = task['total_duration_minutes'] or 0
                cols[0].write(task['id'])
                cols[1].write(task['client'])
                cols[2].write(task['project'])
                cols[3].write(task['task_description'])
                cols[4].write(f"{duration} min")
                cols[5].write("✔️" if task['billable'] else "❌")
                
                with cols[6]:
                    c1, c2 = st.columns(2)
                    if c1.button("✏️ Editar", key=f"edit_{task['id']}", use_container_width=True):
                        st.session_state.editing_task_id = task['id']; st.rerun()
                    if c2.button("🗑️ Borrar", key=f"delete_{task['id']}", use_container_width=True):
                        db_manager.delete_task(task['id']); st.success(f"Tarea {task['id']} eliminada."); st.rerun()

if __name__ == "__main__":
    main()

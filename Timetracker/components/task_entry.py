import streamlit as st
from database import db_manager

def _add_task_to_db(task_data):
    """Función interna para añadir los datos de una tarea en la DB."""
    try:
        db_manager.add_task(
            client=task_data.get('client'),
            project=task_data.get('project'),
            task_description=task_data['task_description'],
            tags=task_data.get('tags'),
            billable=task_data.get('billable'),
            notes=task_data.get('notes')
        )
        st.success(f"Tarea '{task_data['task_description']}' creada con éxito!")
    except Exception as e:
        st.error(f"Error al crear la tarea: {e}")

def task_entry_form():
    """
    Muestra un formulario para la creación de tareas de alto nivel (sin tiempos específicos).
    """
    st.subheader("Crear o Planificar Tarea")

    # --- Formulario Normal de Creación de Tarea ---
    with st.form("manual_task_form", clear_on_submit=True): # clear_on_submit=True to clear after successful save
        col1, col2 = st.columns(2)
        with col1:
            client = st.text_input("Cliente", help="Nombre del cliente asociado a la tarea.")
            project = st.text_input("Proyecto", help="Nombre del proyecto de la tarea.")
            task_description = st.text_area("Descripción de la Tarea", help="Una descripción detallada de la tarea a realizar.")
        with col2:
            st.markdown(" ") # Placeholder for alignment
            st.markdown(" ") # Placeholder for alignment
            st.markdown(" ") # Placeholder for alignment
            st.markdown(" ") # Placeholder for alignment
            tags = st.text_input("Etiquetas (separadas por comas)", help="Ej: desarrollo, reunión, urgente")
            billable = st.checkbox("Facturable", value=True)
            notes = st.text_area("Notas Adicionales", help="Cualquier información extra relevante.")

        submitted = st.form_submit_button("Crear Tarea")

        if submitted:
            if not task_description:
                st.error("La descripción de la tarea es obligatoria.")
            else:
                task_data = {
                    "client": client or None,
                    "project": project or None,
                    "task_description": task_description,
                    "tags": tags or None,
                    "billable": billable,
                    "notes": notes or None
                }
                _add_task_to_db(task_data)
                # clear_on_submit solo vacía el formulario; hace falta rerun() para que
                # la tarea nueva aparezca de inmediato en el widget de Cronometrar (sidebar).
                st.rerun()

# Para pruebas
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("Prueba de Formulario de Creación de Tarea")
    db_manager.init_db()
    task_entry_form()
    
    st.write("---")
    st.subheader("Tareas Existentes (solo para depuración)")
    tasks = db_manager.get_tasks()
    if tasks:
        # Note: get_tasks now returns total_duration_minutes, so adjust display
        for task in tasks:
            st.write(f"ID: {task['id']}, Desc: {task['task_description']}, Duración Total: {task['total_duration_minutes']} min")
    else:
        st.info("No hay tareas registradas aún.")

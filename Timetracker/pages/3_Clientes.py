import streamlit as st
from database import db_manager

st.set_page_config(page_title="Clientes - TimeTracker", page_icon="💼", layout="wide")
db_manager.init_db()

st.title("Clientes y Honorarios Mensuales")
st.caption(
    "Cargá acá el monto mensual que le facturás a cada cliente. "
    "Con eso, el Dashboard calcula tu costo/hora real por cliente "
    "(honorario mensual ÷ horas trabajadas ese mes)."
)

st.markdown("---")

existing_clients = db_manager.get_clients()
task_clients = db_manager.get_distinct_task_clients()
configured_names = {c['name'] for c in existing_clients}
missing = [c for c in task_clients if c not in configured_names]

if missing:
    st.info(
        "Estos clientes ya tienen tareas registradas pero todavía no tienen "
        f"honorario mensual configurado: **{', '.join(missing)}**"
    )

st.subheader("Agregar / Actualizar Cliente")
with st.form("client_form", clear_on_submit=True):
    name = st.text_input("Nombre del Cliente (debe coincidir con el usado en las tareas)")
    monthly_fee = st.number_input("Honorario Mensual", min_value=0.0, step=1000.0, format="%.2f")
    submitted = st.form_submit_button("Guardar")
    if submitted:
        if not name.strip():
            st.error("El nombre del cliente no puede estar vacío.")
        else:
            db_manager.upsert_client(name.strip(), monthly_fee)
            st.success(f"Honorario de '{name.strip()}' guardado: {monthly_fee:.2f}/mes")
            st.rerun()

st.markdown("---")
st.subheader("Clientes Configurados")

clients = db_manager.get_clients()
if not clients:
    st.info("Todavía no configuraste ningún honorario mensual.")
else:
    cols = st.columns((3, 2, 2))
    for col, header in zip(cols, ["Cliente", "Honorario Mensual", "Acciones"]):
        col.write(f"**{header}**")
    for client in clients:
        cols = st.columns((3, 2, 2))
        cols[0].write(client['name'])
        cols[1].write(f"{client['monthly_fee']:.2f}")
        if cols[2].button("🗑️ Borrar", key=f"del_client_{client['id']}"):
            db_manager.delete_client(client['id'])
            st.rerun()

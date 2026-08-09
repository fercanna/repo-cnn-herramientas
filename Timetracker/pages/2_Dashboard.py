import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import os
from datetime import datetime, timedelta
from database.config import get_db_folder

# Ruta de la base de datos
DB_FOLDER = get_db_folder()
DB_NAME = 'timetracker.db'
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

def get_data_as_dataframe():
    """
    Obtiene todos los datos de tasks y time_entries, los une y los devuelve como un DataFrame de pandas.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Obtener todas las tareas
        tasks_df = pd.read_sql_query("SELECT * FROM tasks", conn)
        
        # Obtener todas las entradas de tiempo
        time_entries_df = pd.read_sql_query("SELECT * FROM time_entries", conn)
        
        if tasks_df.empty or time_entries_df.empty:
            return pd.DataFrame() # Devolver DataFrame vacío si no hay datos
        
        # Unir los DataFrames
        df = pd.merge(time_entries_df, tasks_df, left_on='task_id', right_on='id', suffixes=('_entry', '_task'))
        
        # Convertir columnas de tiempo a datetime
        df['start_time'] = pd.to_datetime(df['start_time'])
        df['end_time'] = pd.to_datetime(df['end_time'])
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Calcular duración en horas
        df['duration_hours'] = df['duration_minutes'] / 60
        
        return df
    except sqlite3.Error as e:
        st.error(f"Error al conectar o leer de la base de datos: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def get_clients_as_dataframe():
    """Obtiene la configuración de honorarios mensuales por cliente."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        clients_df = pd.read_sql_query("SELECT name, monthly_fee FROM clients", conn)
        return clients_df
    except sqlite3.Error as e:
        st.error(f"Error al leer clientes: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def calculate_cost_per_hour(df, clients_df, month_period):
    """
    Calcula, para un mes dado, las horas trabajadas por cliente y el costo
    real por hora (honorario mensual / horas trabajadas ese mes).
    """
    if df.empty or clients_df.empty:
        return pd.DataFrame()

    df_month = df[df['start_time'].dt.to_period('M') == month_period]
    if df_month.empty:
        return pd.DataFrame()

    hours_by_client = df_month.groupby('client')['duration_hours'].sum().reset_index()
    merged = pd.merge(clients_df, hours_by_client, left_on='name', right_on='client', how='inner')
    merged = merged.drop(columns=['client'])
    merged['cost_per_hour'] = merged.apply(
        lambda r: (r['monthly_fee'] / r['duration_hours']) if r['duration_hours'] > 0 else None,
        axis=1
    )
    merged = merged.rename(columns={'name': 'client', 'duration_hours': 'hours_worked'})
    return merged.sort_values('cost_per_hour', ascending=False)

def calculate_daily_hours(df):
    """Calcula el total de horas trabajadas por día."""
    if df.empty:
        return pd.DataFrame()
    df['date'] = df['start_time'].dt.date
    daily_hours = df.groupby('date')['duration_hours'].sum().reset_index()
    daily_hours['date'] = pd.to_datetime(daily_hours['date']) # Para plotly
    return daily_hours

def calculate_weekly_hours(df):
    """Calcula el total de horas trabajadas por semana."""
    if df.empty:
        return pd.DataFrame()
    df['week'] = df['start_time'].dt.to_period('W').apply(lambda r: r.start_time) # Inicio de la semana
    weekly_hours = df.groupby('week')['duration_hours'].sum().reset_index()
    return weekly_hours

def calculate_hours_by_client(df):
    """Calcula el total de horas trabajadas por cliente."""
    if df.empty:
        return pd.DataFrame()
    client_hours = df.groupby('client')['duration_hours'].sum().reset_index()
    client_hours = client_hours.sort_values('duration_hours', ascending=False)
    return client_hours

def calculate_service_product_ratio(df):
    """
    Calcula el ratio de horas dedicadas a servicio vs. desarrollo de producto
    basado en las etiquetas de las tareas.
    Asume que las tags contienen 'servicio' para servicio y 'producto' para producto.
    """
    if df.empty:
        return None, None, None, None

    # Asegurarse de que 'tags' sea una cadena, manejar NaN
    df['tags'] = df['tags'].fillna('').astype(str)

    service_hours = df[df['tags'].str.contains('servicio', case=False, na=False)]['duration_hours'].sum()
    product_hours = df[df['tags'].str.contains('producto', case=False, na=False)]['duration_hours'].sum()
    
    total_tagged_hours = service_hours + product_hours
    
    if total_tagged_hours == 0:
        return 0, 0, 0, 0 # No hay horas etiquetadas para calcular un ratio
    
    ratio = product_hours / service_hours if service_hours > 0 else float('inf') # Evitar división por cero
    
    return service_hours, product_hours, total_tagged_hours, ratio

def display_dashboard():
    st.title("TimeTracker Dashboard")
    df = get_data_as_dataframe()

    if df.empty:
        st.warning("No hay datos para mostrar en el dashboard. Registre algunas tareas y entradas de tiempo.")
        return

    st.header("Horas Totales")

    # Horas por día
    daily_hours_df = calculate_daily_hours(df)
    if not daily_hours_df.empty:
        st.subheader("Horas por Día")
        fig_daily = px.bar(daily_hours_df, x='date', y='duration_hours', 
                           title='Total de Horas Trabajadas por Día',
                           labels={'date': 'Fecha', 'duration_hours': 'Horas'})
        st.plotly_chart(fig_daily)
    else:
        st.info("No hay datos de horas diarias para mostrar.")

    # Horas por semana
    weekly_hours_df = calculate_weekly_hours(df)
    if not weekly_hours_df.empty:
        st.subheader("Horas por Semana")
        fig_weekly = px.bar(weekly_hours_df, x='week', y='duration_hours', 
                            title='Total de Horas Trabajadas por Semana',
                            labels={'week': 'Semana', 'duration_hours': 'Horas'})
        st.plotly_chart(fig_weekly)
    else:
        st.info("No hay datos de horas semanales para mostrar.")

    st.header("Distribución por Cliente")
    client_hours_df = calculate_hours_by_client(df)
    if not client_hours_df.empty:
        st.subheader("Horas por Cliente")
        fig_client = px.pie(client_hours_df, values='duration_hours', names='client',
                            title='Distribución de Horas por Cliente')
        st.plotly_chart(fig_client)
    else:
        st.info("No hay datos de horas por cliente para mostrar.")

    st.header("Ratio Servicio vs. Desarrollo de Producto")
    service_h, product_h, total_tagged_h, ratio_val = calculate_service_product_ratio(df)

    if total_tagged_h > 0:
        st.subheader("Resumen de Horas por Categoría")
        st.write(f"Horas de Servicio: {service_h:.2f}")
        st.write(f"Horas de Desarrollo de Producto: {product_h:.2f}")

        if service_h > 0:
            st.write(f"Ratio Producto/Servicio: {ratio_val:.2f}")
        else:
            st.write("No hay horas de servicio para calcular un ratio significativo.")
        
        # Visualización opcional (ejemplo de gráfico de barras simple)
        ratio_data = pd.DataFrame({
            'Categoría': ['Servicio', 'Producto'],
            'Horas': [service_h, product_h]
        })
        fig_ratio = px.bar(ratio_data, x='Categoría', y='Horas', 
                           title='Horas por Categoría (Servicio vs. Producto)',
                           color='Categoría')
        st.plotly_chart(fig_ratio)

    else:
        st.info("No hay tareas etiquetadas como 'servicio' o 'producto' para calcular el ratio.")

    st.header("Costo Real por Hora por Cliente")
    st.caption(
        "Honorario mensual del cliente ÷ horas que le dedicaste ese mes. "
        "Configurá los honorarios en la página 'Clientes'."
    )
    clients_df = get_clients_as_dataframe()

    if clients_df.empty:
        st.info("Todavía no configuraste honorarios mensuales. Andá a la página 'Clientes' para cargarlos.")
    else:
        available_months = sorted(df['start_time'].dt.to_period('M').unique(), reverse=True)
        month_labels = [str(m) for m in available_months]
        selected_label = st.selectbox("Mes", month_labels, index=0)
        selected_period = pd.Period(selected_label, freq='M')

        cost_df = calculate_cost_per_hour(df, clients_df, selected_period)
        if cost_df.empty:
            st.info("No hay horas registradas ese mes para ningún cliente con honorario configurado.")
        else:
            display_df = cost_df.copy()
            display_df['hours_worked'] = display_df['hours_worked'].round(2)
            display_df['cost_per_hour'] = display_df['cost_per_hour'].round(2)
            display_df = display_df.rename(columns={
                'client': 'Cliente', 'monthly_fee': 'Honorario Mensual',
                'hours_worked': 'Horas Trabajadas', 'cost_per_hour': 'Costo Real por Hora'
            })
            st.dataframe(display_df, use_container_width=True)

            fig_cost = px.bar(
                cost_df, x='client', y='cost_per_hour',
                title=f'Costo Real por Hora ({selected_label})',
                labels={'client': 'Cliente', 'cost_per_hour': 'Costo por Hora'}
            )
            st.plotly_chart(fig_cost)


# Llamar a la función principal del dashboard si se ejecuta directamente
if __name__ == '__main__':
    display_dashboard()
import sqlite3
import os
from datetime import datetime
from database.config import get_db_folder

# --- DB Setup ---
DB_FOLDER = get_db_folder()
DB_NAME = 'timetracker.db'
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

def _get_connection():
    """Gets a DB connection and enables foreign keys."""
    os.makedirs(DB_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the DB with the new schema."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Simplified tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client TEXT,
        project TEXT,
        task_description TEXT NOT NULL,
        tags TEXT,
        billable BOOLEAN DEFAULT 1,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # New table for time entries
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS time_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        duration_minutes INTEGER NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
    )
    """)

    # Table for monthly fee per client (used to compute real cost/hour)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        monthly_fee REAL DEFAULT 0
    )
    """)

    # Tracks the currently running timer (if any) so it survives a dropped
    # connection, browser reload, or app restart. Single-user app, so at
    # most one row ever exists here.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_timer (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        task_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

def add_task(client, project, task_description, tags, billable, notes):
    """Adds a new high-level task."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tasks (client, project, task_description, tags, billable, notes)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (client, project, task_description, tags, billable, notes))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def add_time_entry(task_id, start_time, end_time):
    """Adds a work session (time entry) for a task."""
    conn = _get_connection()
    cursor = conn.cursor()
    duration_minutes = int((datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds() / 60)
    cursor.execute("""
    INSERT INTO time_entries (task_id, start_time, end_time, duration_minutes)
    VALUES (?, ?, ?, ?)
    """, (task_id, start_time, end_time, duration_minutes))
    conn.commit()
    conn.close()

def get_tasks():
    """
    Gets all tasks and calculates their total duration and last activity time
    from the time_entries table.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT
        t.*,
        SUM(te.duration_minutes) as total_duration_minutes,
        MAX(te.end_time) as last_activity
    FROM tasks t
    LEFT JOIN time_entries te ON t.id = te.task_id
    GROUP BY t.id
    ORDER BY t.created_at DESC
    """)
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_task_by_id(task_id):
    """Gets a single task by its ID, including total duration."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT
        t.*,
        SUM(te.duration_minutes) as total_duration_minutes
    FROM tasks t
    LEFT JOIN time_entries te ON t.id = te.task_id
    WHERE t.id = ?
    GROUP BY t.id
    """, (task_id,))
    task = cursor.fetchone()
    conn.close()
    return task

def check_for_overlapping_tasks(start_time, end_time):
    """Checks for overlapping time entries."""
    conn = _get_connection()
    cursor = conn.cursor()
    query = "SELECT te.*, t.task_description FROM time_entries te JOIN tasks t ON te.task_id = t.id WHERE te.start_time < ? AND te.end_time > ?"
    params = [end_time, start_time]
    cursor.execute(query, params)
    overlapping = cursor.fetchall()
    conn.close()
    return overlapping

def update_task(task_id, client, project, task_description, tags, billable, notes):
    """Updates the non-time-related fields of a task."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tasks
    SET client = ?, project = ?, task_description = ?, tags = ?, billable = ?, notes = ?
    WHERE id = ?
    """, (client, project, task_description, tags, billable, notes, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    """Deletes a task and all its time entries via CASCADE."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def upsert_client(name, monthly_fee):
    """Creates or updates the monthly fee for a client (matched by name)."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO clients (name, monthly_fee) VALUES (?, ?)
    ON CONFLICT(name) DO UPDATE SET monthly_fee = excluded.monthly_fee
    """, (name, monthly_fee))
    conn.commit()
    conn.close()

def get_clients():
    """Returns all clients with their configured monthly fee."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients ORDER BY name")
    clients = cursor.fetchall()
    conn.close()
    return clients

def delete_client(client_id):
    """Removes a client's monthly fee configuration (does not touch tasks)."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()

def start_active_timer(task_id, start_time):
    """Persists the running timer so it survives a dropped connection/reload."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO active_timer (id, task_id, start_time) VALUES (1, ?, ?)
    ON CONFLICT(id) DO UPDATE SET task_id = excluded.task_id, start_time = excluded.start_time
    """, (task_id, start_time))
    conn.commit()
    conn.close()

def get_active_timer():
    """Returns the currently running timer (task_id, start_time), if any."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT task_id, start_time FROM active_timer WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row

def clear_active_timer():
    """Clears the running timer once it's stopped and saved (or cancelled)."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_timer WHERE id = 1")
    conn.commit()
    conn.close()

def get_distinct_task_clients():
    """Returns the distinct client names that already appear in tasks."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DISTINCT client FROM tasks
    WHERE client IS NOT NULL AND TRIM(client) != ''
    ORDER BY client
    """)
    rows = cursor.fetchall()
    conn.close()
    return [row['client'] for row in rows]

if __name__ == '__main__':
    # Para pruebas y configuración inicial
    print("Inicializando la base de datos...")
    init_db()
    print("Base de datos inicializada en:", DB_PATH)

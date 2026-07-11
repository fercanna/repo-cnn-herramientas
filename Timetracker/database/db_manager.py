import sqlite3
import os
from datetime import datetime

# --- DB Setup ---
DB_FOLDER = 'data'
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

if __name__ == '__main__':
    # Para pruebas y configuración inicial
    print("Inicializando la base de datos...")
    init_db()
    print("Base de datos inicializada en:", DB_PATH)

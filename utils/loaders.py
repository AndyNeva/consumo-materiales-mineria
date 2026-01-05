from flask import current_app
import sqlite3
from pathlib import Path

def get_db_connection_flask():
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # permite dict(row)
    return conn
def get_db_connection_standalone():
    db_path = Path(__file__).parent.parent / "db" / "gestion_materiales.db"
    conn = sqlite3.connect(db_path)
    return conn
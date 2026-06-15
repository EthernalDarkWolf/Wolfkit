import sqlite3

from .db import get_connection, init_db


def get_user_info(username: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT u.nombre_usuario AS username, r.nombre_rol AS role "
            "FROM usuarios u "
            "JOIN roles r ON u.id_rol = r.id "
            "WHERE u.nombre_usuario = ? AND u.contrasena = ?",
            (username, password),
        )
    except sqlite3.OperationalError:
        conn.close()
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT u.nombre_usuario AS username, r.nombre_rol AS role "
            "FROM usuarios u "
            "JOIN roles r ON u.id_rol = r.id "
            "WHERE u.nombre_usuario = ? AND u.contrasena = ?",
            (username, password),
        )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def verify_user(username: str, password: str) -> bool:
    return bool(get_user_info(username, password))

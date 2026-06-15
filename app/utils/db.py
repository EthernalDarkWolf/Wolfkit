from pathlib import Path
import sqlite3

ROOT_DIR = Path(__file__).resolve().parents[2]
DATABASE_DIR = ROOT_DIR / "db"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "education.db"


def get_connection():
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS semestre_periodo (
            id_SemestrePeriodo INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_semestre TEXT NOT NULL,
            numero_periodo TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS estudiantes (
            id_estudiantes INTEGER PRIMARY KEY AUTOINCREMENT,
            nombres TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            ci TEXT NOT NULL UNIQUE,
            semestre_periodo INTEGER NOT NULL,
            FOREIGN KEY (semestre_periodo) REFERENCES semestre_periodo(id_SemestrePeriodo)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS asist (
            id_asist INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_asistencia TEXT NOT NULL UNIQUE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS asistencia_estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_estudiante INTEGER NOT NULL,
            asistio_a_clases INTEGER NOT NULL,
            fecha DATE NOT NULL,
            nombre_estudiante TEXT,
            FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id_estudiantes),
            FOREIGN KEY (asistio_a_clases) REFERENCES asist(id_asist)
        )
        """
    )

    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_estudiante_fecha ON asistencia_estudiantes(id_estudiante, fecha)"
    )

    # Asegurar columna nombre_estudiante en asistencia_estudiantes para mantener el nombre histórico
    try:
        cursor.execute("PRAGMA table_info(asistencia_estudiantes)")
        cols = [r[1] for r in cursor.fetchall()]
        if "nombre_estudiante" not in cols:
            try:
                cursor.execute("ALTER TABLE asistencia_estudiantes ADD COLUMN nombre_estudiante TEXT")
            except Exception:
                pass
    except Exception:
        pass

    # Nota: no insertar filas por defecto aquí — la tabla la maneja el usuario.

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_rol TEXT NOT NULL UNIQUE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            id_rol INTEGER NOT NULL,
            FOREIGN KEY (id_rol) REFERENCES roles(id)
        )
        """
    )

    # Asegurar columna foto_perfil en usuarios
    try:
        cursor.execute("PRAGMA table_info(usuarios)")
        cols = [r[1] for r in cursor.fetchall()]
        if "foto_perfil" not in cols:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN foto_perfil BLOB")
    except Exception:
        pass

    cursor.executemany(
        "INSERT OR IGNORE INTO asist (nombre_asistencia) VALUES (?)",
        [("Asistió",), ("No Asistió",)],
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO roles (nombre_rol) VALUES (?)",
        [("Creador",), ("Profesor",)],
    )

    cursor.execute(
        "INSERT OR IGNORE INTO usuarios (nombre_usuario, contrasena, id_rol) VALUES (?, ?, ?)",
        ("Anthony", "162618", 1),
    )

    # Asegurar que existan opciones de semestre/periodo por defecto para la UI
    try:
        cursor.execute("SELECT COUNT(*) FROM semestre_periodo")
        cnt = cursor.fetchone()[0]
        if cnt == 0:
            cursor.executemany(
                "INSERT INTO semestre_periodo (numero_semestre, numero_periodo) VALUES (?, ?)",
                [("1", "1"), ("1", "2"), ("1", "3"), ("2", "1"), ("2", "2"), ("2", "3")],
            )
    except Exception:
        # Si hay algún problema no bloquear la inicialización; la UI podrá crear semestres manualmente.
        pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS unidades (
            id_unidad INTEGER PRIMARY KEY AUTOINCREMENT,
            id_semestre_periodo INTEGER NOT NULL,
            nombre_unidad TEXT NOT NULL,
            contexto TEXT,
            completada INTEGER DEFAULT 0,
            FOREIGN KEY (id_semestre_periodo) REFERENCES semestre_periodo(id_SemestrePeriodo)
        )
        """
    )

    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_unidad_semestre_periodo ON unidades(id_semestre_periodo, nombre_unidad)"
    )

    # Migración ligera: si la tabla existe pero no tiene las columnas nuevas, añadirlas.
    cursor.execute("PRAGMA table_info(unidades)")
    cols = [r[1] for r in cursor.fetchall()]
    if "contexto" not in cols:
        try:
            cursor.execute("ALTER TABLE unidades ADD COLUMN contexto TEXT")
        except Exception:
            pass
    if "completada" not in cols:
        try:
            cursor.execute("ALTER TABLE unidades ADD COLUMN completada INTEGER DEFAULT 0")
        except Exception:
            pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notas (
            id_nota INTEGER PRIMARY KEY AUTOINCREMENT,
            id_estudiante INTEGER NOT NULL,
            id_semestre_periodo INTEGER NOT NULL,
            id_unidad INTEGER NOT NULL,
            nota TEXT NOT NULL,
            comentarios TEXT,
            FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id_estudiantes),
            FOREIGN KEY (id_semestre_periodo) REFERENCES semestre_periodo(id_SemestrePeriodo),
            FOREIGN KEY (id_unidad) REFERENCES unidades(id_unidad)
        )
        """
    )

    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_nota_estudiante_unidad ON notas(id_estudiante, id_semestre_periodo, id_unidad)"
    )
    # Después de crear tablas y valores por defecto, migrar datos de DBs legacy si existen
    def _migrate_legacy_db(legacy_path):
        try:
            legacy_path = Path(legacy_path)
            if not legacy_path.exists():
                return 0
            if legacy_path.resolve() == DATABASE_PATH.resolve():
                return 0

            migrated = 0
            legacy_conn = sqlite3.connect(str(legacy_path))
            legacy_conn.row_factory = sqlite3.Row
            lcur = legacy_conn.cursor()

            # Mapear semestres: (numero_semestre, numero_periodo) -> id en DB actual
            sem_map = {}
            lcur.execute("SELECT id_SemestrePeriodo, numero_semestre, numero_periodo FROM semestre_periodo")
            for row in lcur.fetchall():
                ns, np = row[1], row[2]
                # insertar si no existe
                cursor.execute(
                    "SELECT id_SemestrePeriodo FROM semestre_periodo WHERE numero_semestre = ? AND numero_periodo = ?",
                    (ns, np),
                )
                r = cursor.fetchone()
                if r:
                    sem_map[row[0]] = r[0]
                else:
                    cursor.execute(
                        "INSERT INTO semestre_periodo (numero_semestre, numero_periodo) VALUES (?, ?)",
                        (ns, np),
                    )
                    sem_map[row[0]] = cursor.lastrowid

            # Mapear unidades: legacy id_unidad -> new id_unidad
            unit_map = {}
            try:
                lcur.execute("SELECT id_unidad, id_semestre_periodo, nombre_unidad, contexto, completada FROM unidades")
                for row in lcur.fetchall():
                    old_uid, old_sem, name = row[0], row[1], row[2]
                    new_sem = sem_map.get(old_sem)
                    if new_sem is None:
                        continue
                    cursor.execute(
                        "SELECT id_unidad FROM unidades WHERE id_semestre_periodo = ? AND nombre_unidad = ?",
                        (new_sem, name),
                    )
                    r = cursor.fetchone()
                    if r:
                        unit_map[old_uid] = r[0]
                    else:
                        # intentar incluir contexto/completada si existen en esquema actual
                        try:
                            cursor.execute(
                                "INSERT INTO unidades (id_semestre_periodo, nombre_unidad, contexto, completada) VALUES (?, ?, ?, ?)",
                                (new_sem, name, row[3] if len(row) > 3 else None, int(bool(row[4])) if len(row) > 4 else 0),
                            )
                        except Exception:
                            cursor.execute(
                                "INSERT INTO unidades (id_semestre_periodo, nombre_unidad) VALUES (?, ?)",
                                (new_sem, name),
                            )
                        unit_map[old_uid] = cursor.lastrowid
            except Exception:
                # si no existe la tabla unidades en legacy, ignorar
                pass

            # Migrar estudiantes (usar ci como clave única)
            lcur.execute("SELECT id_estudiantes, nombres, apellidos, ci, semestre_periodo FROM estudiantes")
            for row in lcur.fetchall():
                old_id, nombres, apellidos, ci, old_sem = row[0], row[1], row[2], row[3], row[4]
                # comprobar existencia por CI
                cursor.execute("SELECT id_estudiantes FROM estudiantes WHERE ci = ?", (ci,))
                if cursor.fetchone():
                    # ya existe
                    continue
                new_sem = sem_map.get(old_sem)
                if new_sem is None:
                    # si no se mapeó, dejar como NULL no permitido -> saltar
                    continue
                cursor.execute(
                    "INSERT INTO estudiantes (nombres, apellidos, ci, semestre_periodo) VALUES (?, ?, ?, ?)",
                    (nombres, apellidos, ci, new_sem),
                )
                new_student_id = cursor.lastrowid
                migrated += 1

                # Migrar asistencia del estudiante
                try:
                    lcur.execute("SELECT asistio_a_clases, fecha FROM asistencia_estudiantes WHERE id_estudiante = ?", (old_id,))
                    for arow in lcur.fetchall():
                        asist_old, fecha = arow[0], arow[1]
                        # mapear asist (Asistió / No Asistió) por nombre
                        lcur.execute("SELECT nombre_asistencia FROM asist WHERE id_asist = ?", (asist_old,))
                        asist_name_row = lcur.fetchone()
                        asist_name = asist_name_row[0] if asist_name_row else None
                        if asist_name:
                            cursor.execute("SELECT id_asist FROM asist WHERE nombre_asistencia = ?", (asist_name,))
                            ar = cursor.fetchone()
                            if ar:
                                aid = ar[0]
                                try:
                                    cursor.execute(
                                        "INSERT OR IGNORE INTO asistencia_estudiantes (id_estudiante, asistio_a_clases, fecha) VALUES (?, ?, ?)",
                                        (new_student_id, aid, fecha),
                                    )
                                except Exception:
                                    pass
                except Exception:
                    pass

                # Migrar notas del estudiante
                try:
                    lcur.execute("SELECT id_semestre_periodo, id_unidad, nota, comentarios FROM notas WHERE id_estudiante = ?", (old_id,))
                    for nrow in lcur.fetchall():
                        old_sem_n, old_uid_n, nota_text, comentarios = nrow[0], nrow[1], nrow[2], nrow[3] if len(nrow) > 3 else None
                        new_sem_n = sem_map.get(old_sem_n)
                        new_uid_n = unit_map.get(old_uid_n)
                        if new_sem_n is None:
                            continue
                        try:
                            if new_uid_n:
                                cursor.execute(
                                    "INSERT OR IGNORE INTO notas (id_estudiante, id_semestre_periodo, id_unidad, nota, comentarios) VALUES (?, ?, ?, ?, ?)",
                                    (new_student_id, new_sem_n, new_uid_n, nota_text, comentarios),
                                )
                            else:
                                cursor.execute(
                                    "INSERT OR IGNORE INTO notas (id_estudiante, id_semestre_periodo, unidad, nota, comentarios) VALUES (?, ?, ?, ?, ?)",
                                    (new_student_id, new_sem_n, None, nota_text, comentarios),
                                )
                        except Exception:
                            pass
                except Exception:
                    pass

            legacy_conn.close()
            return migrated
        except Exception:
            return 0

    # buscar DBs legacy creadas en rutas alternativas y migrar datos si hay registros
    legacy_candidates = [ROOT_DIR / 'app' / 'education.db', ROOT_DIR / 'app' / 'db' / 'education.db', ROOT_DIR / 'app' / 'db' / 'education.db']
    total_migrated = 0
    for cand in legacy_candidates:
        try:
            migrated = _migrate_legacy_db(cand)
            if migrated:
                total_migrated += migrated
        except Exception:
            pass

    if total_migrated:
        print(f"Migrated {total_migrated} estudiantes from legacy DB(s)")

    conn.commit()
    conn.close()


def select_semesters():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id_SemestrePeriodo, numero_semestre, numero_periodo FROM semestre_periodo ORDER BY id_SemestrePeriodo"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def select_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.id_estudiantes, e.nombres, e.apellidos, e.ci,
               s.numero_semestre, s.numero_periodo
        FROM estudiantes e
        JOIN semestre_periodo s ON e.semestre_periodo = s.id_SemestrePeriodo
        ORDER BY e.apellidos, e.nombres
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def insert_student(nombres: str, apellidos: str, ci: str, semestre_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO estudiantes (nombres, apellidos, ci, semestre_periodo) VALUES (?, ?, ?, ?)",
        (nombres, apellidos, ci, semestre_id),
    )
    conn.commit()
    conn.close()


def update_student(student_id: int, nombres: str, apellidos: str, ci: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE estudiantes SET nombres = ?, apellidos = ?, ci = ? WHERE id_estudiantes = ?",
        (nombres, apellidos, ci, student_id),
    )
    conn.commit()
    conn.close()


def select_attendance_types():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_asist, nombre_asistencia FROM asist ORDER BY id_asist")
    rows = cursor.fetchall()
    conn.close()
    return {row["nombre_asistencia"]: row["id_asist"] for row in rows}


def insert_or_update_attendance(student_id: int, attendance_type_id: int, attendance_date: str):
    conn = get_connection()
    cursor = conn.cursor()
    # Obtener nombre completo del estudiante para registrarlo junto a la asistencia (snapshot)
    try:
        cursor.execute("SELECT nombres, apellidos FROM estudiantes WHERE id_estudiantes = ?", (student_id,))
        r = cursor.fetchone()
        nombre_completo = (r[0] + ' ' + r[1]) if r else None
    except Exception:
        nombre_completo = None

    cursor.execute(
        "INSERT INTO asistencia_estudiantes (id_estudiante, asistio_a_clases, fecha, nombre_estudiante) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(id_estudiante, fecha) DO UPDATE SET asistio_a_clases = excluded.asistio_a_clases, nombre_estudiante = excluded.nombre_estudiante",
        (student_id, attendance_type_id, attendance_date, nombre_completo),
    )
    conn.commit()
    conn.close()


def select_today_attendance(student_id: int, attendance_date: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT a.nombre_asistencia FROM asistencia_estudiantes ae "
        "JOIN asist a ON ae.asistio_a_clases = a.id_asist "
        "WHERE ae.id_estudiante = ? AND ae.fecha = ?",
        (student_id, attendance_date),
    )
    row = cursor.fetchone()
    conn.close()
    return row["nombre_asistencia"] if row else None


def select_history(student_id: int, limit: int = 15):
    conn = get_connection()
    cursor = conn.cursor()
    # Intentar usar nombre_estudiante almacenado; si no existe, obtener del registro actual en estudiantes
    cursor.execute(
        "SELECT ae.fecha, a.nombre_asistencia, COALESCE(ae.nombre_estudiante, (SELECT nombres || ' ' || apellidos FROM estudiantes e WHERE e.id_estudiantes = ae.id_estudiante)) AS nombre_estudiante "
        "FROM asistencia_estudiantes ae "
        "JOIN asist a ON ae.asistio_a_clases = a.id_asist "
        "WHERE ae.id_estudiante = ? ORDER BY ae.fecha DESC LIMIT ?",
        (student_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_student(student_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM asistencia_estudiantes WHERE id_estudiante = ?", (student_id,))
    cursor.execute("DELETE FROM notas WHERE id_estudiante = ?", (student_id,))
    cursor.execute("DELETE FROM estudiantes WHERE id_estudiantes = ?", (student_id,))
    conn.commit()
    conn.close()


def delete_all_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM asistencia_estudiantes")
    cursor.execute("DELETE FROM notas")
    cursor.execute("DELETE FROM estudiantes")
    conn.commit()
    conn.close()


def insert_or_update_note(student_id: int, semestre_id: int, unidad_id: int, nota_text: str, comentarios: str):
    conn = get_connection()
    cursor = conn.cursor()
    # Detect schema: notas puede tener id_unidad (FK) o unidad (TEXT)
    cursor.execute("PRAGMA table_info(notas)")
    cols = [r[1] for r in cursor.fetchall()]
    if "id_unidad" in cols:
        cursor.execute(
            "INSERT INTO notas (id_estudiante, id_semestre_periodo, id_unidad, nota, comentarios) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id_estudiante, id_semestre_periodo, id_unidad) DO UPDATE SET nota = excluded.nota, comentarios = excluded.comentarios",
            (student_id, semestre_id, unidad_id, nota_text, comentarios),
        )
    else:
        # obtener nombre de la unidad y usar la columna texto 'unidad'
        cursor.execute("SELECT nombre_unidad FROM unidades WHERE id_unidad = ?", (unidad_id,))
        row = cursor.fetchone()
        nombre = row["nombre_unidad"] if row else None
        if nombre is None:
            conn.close()
            raise ValueError("Unidad no encontrada para el id proporcionado")

        # Revisar si ya existe la nota para ese estudiante/semestre/unidad
        cursor.execute(
            "SELECT id_nota FROM notas WHERE id_estudiante = ? AND id_semestre_periodo = ? AND unidad = ?",
            (student_id, semestre_id, nombre),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE notas SET nota = ?, comentarios = ? WHERE id_nota = ?",
                (nota_text, comentarios, existing[0]),
            )
        else:
            cursor.execute(
                "INSERT INTO notas (id_estudiante, id_semestre_periodo, unidad, nota, comentarios) VALUES (?, ?, ?, ?, ?)",
                (student_id, semestre_id, nombre, nota_text, comentarios),
            )

    conn.commit()
    conn.close()


def select_notes(student_id: int, semestre_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    # Adaptar según esquema de 'notas'
    cursor.execute("PRAGMA table_info(notas)")
    cols = [r[1] for r in cursor.fetchall()]
    if "id_unidad" in cols:
        cursor.execute(
            "SELECT u.nombre_unidad AS unidad, n.nota, n.comentarios FROM notas n "
            "JOIN unidades u ON n.id_unidad = u.id_unidad "
            "WHERE n.id_estudiante = ? AND n.id_semestre_periodo = ? "
            "ORDER BY u.nombre_unidad",
            (student_id, semestre_id),
        )
    else:
        cursor.execute(
            "SELECT unidad AS unidad, nota, comentarios FROM notas "
            "WHERE id_estudiante = ? AND id_semestre_periodo = ? ORDER BY unidad",
            (student_id, semestre_id),
        )

    rows = cursor.fetchall()
    conn.close()
    return rows


def insert_or_update_unit(nombre_unidad: str, semestre_id: int, contexto: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    # Intentar insertar incluyendo contexto si la columna existe
    cursor.execute("PRAGMA table_info(unidades)")
    cols = [r[1] for r in cursor.fetchall()]
    if "contexto" in cols:
        cursor.execute(
            "INSERT OR IGNORE INTO unidades (id_semestre_periodo, nombre_unidad, contexto) VALUES (?, ?, ?)",
            (semestre_id, nombre_unidad, contexto),
        )
    else:
        cursor.execute(
            "INSERT OR IGNORE INTO unidades (id_semestre_periodo, nombre_unidad) VALUES (?, ?)",
            (semestre_id, nombre_unidad),
        )

    conn.commit()
    cursor.execute(
        "SELECT id_unidad FROM unidades WHERE id_semestre_periodo = ? AND nombre_unidad = ?",
        (semestre_id, nombre_unidad),
    )
    row = cursor.fetchone()
    conn.close()
    return row["id_unidad"] if row else None


def select_units(semestre_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    # Seleccionar también la columna 'contexto' y 'completada' si existen
    cursor.execute("PRAGMA table_info(unidades)")
    cols = [r[1] for r in cursor.fetchall()]
    fields = ["id_unidad", "nombre_unidad"]
    if "contexto" in cols:
        fields.append("contexto")
    if "completada" in cols:
        fields.append("completada")
    sql = f"SELECT {', '.join(fields)} FROM unidades WHERE id_semestre_periodo = ? ORDER BY nombre_unidad"
    cursor.execute(sql, (semestre_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_unit(unidad_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    # Eliminar notas asociadas primero para mantener integridad.
    # Si la tabla 'notas' usa columna id_unidad, eliminar por id; si usa 'unidad' (texto), eliminar por nombre.
    cursor.execute("PRAGMA table_info(notas)")
    cols = [r[1] for r in cursor.fetchall()]
    if "id_unidad" in cols:
        cursor.execute("DELETE FROM notas WHERE id_unidad = ?", (unidad_id,))
    else:
        cursor.execute("SELECT nombre_unidad FROM unidades WHERE id_unidad = ?", (unidad_id,))
        r = cursor.fetchone()
        if r:
            nombre = r["nombre_unidad"]
            cursor.execute("DELETE FROM notas WHERE unidad = ?", (nombre,))

    cursor.execute("DELETE FROM unidades WHERE id_unidad = ?", (unidad_id,))
    conn.commit()
    conn.close()


def update_unit(unidad_id: int, nombre_unidad: str = None, contexto: str = None, completada: int = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(unidades)")
    cols = [r[1] for r in cursor.fetchall()]
    updates = []
    params = []
    if nombre_unidad is not None:
        updates.append("nombre_unidad = ?")
        params.append(nombre_unidad)
    if "contexto" in cols and contexto is not None:
        updates.append("contexto = ?")
        params.append(contexto)
    if "completada" in cols and completada is not None:
        updates.append("completada = ?")
        params.append(completada)

    if not updates:
        conn.close()
        return

    params.append(unidad_id)
    sql = f"UPDATE unidades SET {', '.join(updates)} WHERE id_unidad = ?"
    try:
        cursor.execute(sql, tuple(params))
        conn.commit()
    finally:
        conn.close()


def update_user_profile_pic(username: str, image_bytes: bytes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE usuarios SET foto_perfil = ? WHERE nombre_usuario = ?",
        (image_bytes, username)
    )
    conn.commit()
    conn.close()


def get_user_profile_pic(username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT foto_perfil FROM usuarios WHERE nombre_usuario = ?",
        (username,)
    )
    row = cursor.fetchone()
    conn.close()
    return row["foto_perfil"] if row else None


def update_user_credentials(old_username: str, new_username: str, new_password: str):
    conn = get_connection()
    cursor = conn.cursor()
    if old_username != new_username:
        cursor.execute("SELECT id FROM usuarios WHERE nombre_usuario = ?", (new_username,))
        if cursor.fetchone():
            conn.close()
            raise ValueError("El nombre de usuario ya está registrado.")
            
    cursor.execute(
        "UPDATE usuarios SET nombre_usuario = ?, contrasena = ? WHERE nombre_usuario = ?",
        (new_username, new_password, old_username)
    )
    conn.commit()
    conn.close()


def get_user_credentials(username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT contrasena FROM usuarios WHERE nombre_usuario = ?",
        (username,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

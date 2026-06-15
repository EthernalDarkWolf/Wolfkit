import sqlite3
from pathlib import Path

candidates = [Path('db/education.db'), Path('app/db/education.db'), Path('app/education.db')]
for p in candidates:
    print('---')
    print('PATH:', p.resolve())
    if not p.exists():
        print('MISSING')
        continue
    conn = sqlite3.connect(str(p))
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print('tables:', tables)
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                print(t, 'count=', cur.fetchone()[0])
            except Exception as e:
                print('count error', t, e)
        try:
            cur.execute('SELECT id_estudiantes, nombres, apellidos, ci, semestre_periodo FROM estudiantes LIMIT 20')
            rows = cur.fetchall()
            print('estudiantes sample:')
            for r in rows:
                print(r)
        except Exception as e:
            print('no estudiantes or error', e)
    finally:
        conn.close()

"""Small migration helper to add new columns to the Posts table in SQLite if they are missing.

Run: python scripts/sqlite_migrate_posts.py

This will attempt to add columns: platform, external_id, url, status (all TEXT) if they don't exist.
"""
import sqlite3

DB_PATH = 'db.db'


def _get_columns(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    rows = cur.fetchall()
    return [r[1] for r in rows]


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cols = _get_columns(conn, 'Posts')
    to_add = []
    if 'platform' not in cols:
        to_add.append("ALTER TABLE Posts ADD COLUMN platform TEXT")
    if 'external_id' not in cols:
        to_add.append("ALTER TABLE Posts ADD COLUMN external_id TEXT")
    if 'url' not in cols:
        to_add.append("ALTER TABLE Posts ADD COLUMN url TEXT")
    if 'status' not in cols:
        to_add.append("ALTER TABLE Posts ADD COLUMN status TEXT")

    for sql in to_add:
        print('Executing:', sql)
        conn.execute(sql)
    conn.commit()
    conn.close()
    print('Migration complete.')


if __name__ == '__main__':
    migrate()

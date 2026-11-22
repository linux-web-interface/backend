
import os
import sqlite3
from contextlib import contextmanager

# Lokasi database permanen
DATA_DIR = "/var/lib/linux-web-interface"
DB_PATH = os.path.join(DATA_DIR, "search.db")


def ensure_database():
    """Memastikan direktori dan database tersedia."""
    os.makedirs(DATA_DIR, exist_ok=True)

    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS filesystem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                name_normalized TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('file', 'dir')),
                size_bytes INTEGER NOT NULL DEFAULT 0,
                modified_at REAL NOT NULL DEFAULT 0
            )
        """)

        # Menyimpan status proses indexing
        connection.execute("""
            CREATE TABLE IF NOT EXISTS index_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)


        # Full-text index untuk pencarian substring
        connection.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS filesystem_fts
            USING fts5(
                name_normalized,
                path UNINDEXED,
                content='filesystem',
                content_rowid='id',
                tokenize='trigram'
            )
        """)

        # Sinkronisasi otomatis saat data baru dimasukkan
        connection.execute("""
            CREATE TRIGGER IF NOT EXISTS filesystem_ai
            AFTER INSERT ON filesystem
            BEGIN
                INSERT INTO filesystem_fts(
                    rowid, name_normalized, path
                )
                VALUES (
                    new.id, new.name_normalized, new.path
                );
            END;
        """)

        # Sinkronisasi saat data diperbarui
        connection.execute("""
            CREATE TRIGGER IF NOT EXISTS filesystem_au
            AFTER UPDATE ON filesystem
            BEGIN
                INSERT INTO filesystem_fts(
                    filesystem_fts,
                    rowid,
                    name_normalized,
                    path
                )
                VALUES (
                    'delete',
                    old.id,
                    old.name_normalized,
                    old.path
                );

                INSERT INTO filesystem_fts(
                    rowid, name_normalized, path
                )
                VALUES (
                    new.id, new.name_normalized, new.path
                );
            END;
        """)

        # Sinkronisasi saat data dihapus
        connection.execute("""
            CREATE TRIGGER IF NOT EXISTS filesystem_ad
            AFTER DELETE ON filesystem
            BEGIN
                INSERT INTO filesystem_fts(
                    filesystem_fts,
                    rowid,
                    name_normalized,
                    path
                )
                VALUES (
                    'delete',
                    old.id,
                    old.name_normalized,
                    old.path
                );
            END;
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_filesystem_name
            ON filesystem(name_normalized)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_filesystem_type
            ON filesystem(type)
        """)

        connection.commit()


@contextmanager
def get_connection():
    """Membuat koneksi SQLite."""
    connection = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    try:
        yield connection
    finally:
        connection.close()

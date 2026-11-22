
import os
import sys
import fcntl
import traceback

from services.search_index import (
    ensure_database,
    get_connection
)

from services.filesystem_scanner import scan_filesystem


DATA_DIR = "/var/lib/linux-web-interface"
LOCK_FILE = os.path.join(DATA_DIR, "scanner.lock")


def acquire_lock():
    """
    Memastikan hanya satu scanner yang berjalan.
    Menggunakan Linux flock.
    """

    os.makedirs(DATA_DIR, exist_ok=True)

    lock = open(LOCK_FILE, "w")

    try:
        fcntl.flock(
            lock,
            fcntl.LOCK_EX | fcntl.LOCK_NB
        )

        return lock

    except BlockingIOError:
        lock.close()
        return None


def get_index_status():
    with get_connection() as connection:
        row = connection.execute("""
            SELECT value
            FROM index_state
            WHERE key = 'status'
        """).fetchone()

        return row["value"] if row else None


def set_index_status(status):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO index_state (key, value)
            VALUES ('status', ?)

            ON CONFLICT(key)
            DO UPDATE SET value = excluded.value
        """, (status,))

        connection.commit()


def main():

    print("[SCANNER] Initializing database...")

    ensure_database()

    lock = acquire_lock()

    if lock is None:
        print("[SCANNER] Another scanner is already running.")
        return 0

    try:
        status = get_index_status()

        if status == "completed":
            print("[SCANNER] Index already completed.")
            print("[SCANNER] Skipping initial scan.")
            return 0

        print("[SCANNER] Starting filesystem scan...")

        set_index_status("scanning")

        result = scan_filesystem()

        set_index_status("completed")

        print("[SCANNER] Initial scan completed.")
        print(f"[SCANNER] Scanned: {result['total_scanned']}")
        print(f"[SCANNER] Errors: {result['total_errors']}")

        return 0

    except Exception:
        set_index_status("failed")

        print("[SCANNER] Scan failed!")
        traceback.print_exc()

        return 1

    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    sys.exit(main())

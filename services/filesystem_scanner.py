
import os
import time

from services.search_index import get_connection


# Direktori yang tidak perlu dipindai
EXCLUDED_DIRS = {
    "proc",
    "sys",
    "dev",
    "run",
    "tmp",
    ".cache"
}

# Jumlah data yang disimpan dalam satu transaksi
BATCH_SIZE = 500


def scan_filesystem():
    """
    Memindai filesystem dan menyimpan metadata
    file serta direktori ke SQLite.
    """

    batch = []
    total_scanned = 0
    total_errors = 0

    def save_batch(connection):
        nonlocal batch

        if not batch:
            return

        connection.executemany("""
            INSERT INTO filesystem (
                path,
                name,
                name_normalized,
                type,
                size_bytes,
                modified_at
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(path) DO UPDATE SET
                name = excluded.name,
                name_normalized = excluded.name_normalized,
                type = excluded.type,
                size_bytes = excluded.size_bytes,
                modified_at = excluded.modified_at
        """, batch)

        connection.commit()
        batch.clear()

    def walk_error(error):
        nonlocal total_errors
        total_errors += 1

    with get_connection() as connection:

        for root, dirs, files in os.walk(
            "/",
            topdown=True,
            followlinks=False,
            onerror=walk_error
        ):

            # Filter direktori sebelum masuk lebih dalam
            filtered_dirs = []

            for directory in dirs:
                path = os.path.join(root, directory)

                if directory in EXCLUDED_DIRS:
                    continue

                if os.path.islink(path):
                    continue

                filtered_dirs.append(directory)

            dirs[:] = filtered_dirs

            # Proses direktori
            for directory in dirs:
                path = os.path.join(root, directory)

                try:
                    stat = os.stat(
                        path,
                        follow_symlinks=False
                    )

                    batch.append((
                        path,
                        directory,
                        directory.casefold(),
                        "dir",
                        0,
                        stat.st_mtime
                    ))

                    total_scanned += 1

                except OSError:
                    total_errors += 1
                    continue

                if len(batch) >= BATCH_SIZE:
                    save_batch(connection)

            # Proses file
            for filename in files:
                path = os.path.join(root, filename)

                try:
                    if os.path.islink(path):
                        continue

                    stat = os.stat(
                        path,
                        follow_symlinks=False
                    )

                    if not os.path.isfile(path):
                        continue

                    batch.append((
                        path,
                        filename,
                        filename.casefold(),
                        "file",
                        stat.st_size,
                        stat.st_mtime
                    ))

                    total_scanned += 1

                except OSError:
                    total_errors += 1
                    continue

                if len(batch) >= BATCH_SIZE:
                    save_batch(connection)

        # Simpan sisa data
        save_batch(connection)

    return {
        "total_scanned": total_scanned,
        "total_errors": total_errors,
        "completed_at": time.time()
    }

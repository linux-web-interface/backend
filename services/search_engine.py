
from services.search_index import get_connection


def search_files(query, limit=500, offset=0):
    """
    Mencari file dan direktori berdasarkan nama
    menggunakan SQLite FTS5.
    """

    query = query.strip().casefold()

    if not query:
        raise ValueError("Kata kunci pencarian tidak boleh kosong")

    if len(query) > 200:
        raise ValueError("Kata kunci maksimal 200 karakter")

    if not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("Limit harus antara 1 sampai 500")

    if not isinstance(offset, int) or offset < 0:
        raise ValueError("Offset tidak valid")

    with get_connection() as connection:

        if len(query) >= 3:
            # Escape tanda kutip untuk FTS5
            safe_query = '"' + query.replace('"', '""') + '"'

            rows = connection.execute("""
                SELECT
                    filesystem.name,
                    filesystem.type,
                    filesystem.path,
                    filesystem.size_bytes,
                    filesystem.modified_at
                FROM filesystem_fts
                JOIN filesystem
                    ON filesystem.id = filesystem_fts.rowid
                WHERE filesystem_fts MATCH ?
                ORDER BY filesystem.name_normalized ASC
                LIMIT ? OFFSET ?
            """, (safe_query, limit + 1, offset)).fetchall()

        else:
            # Trigram membutuhkan minimal 3 karakter.
            # Fallback ini hanya memindai tabel SQLite,
            # bukan filesystem.
            rows = connection.execute("""
                SELECT
                    name,
                    type,
                    path,
                    size_bytes,
                    modified_at
                FROM filesystem
                WHERE instr(name_normalized, ?) > 0
                ORDER BY name_normalized ASC
                LIMIT ? OFFSET ?
            """, (query, limit + 1, offset)).fetchall()

    limit_reached = len(rows) > limit
    rows = rows[:limit]

    items = []

    for row in rows:
        from datetime import datetime

        items.append({
            "name": row["name"],
            "type": row["type"],
            "path": row["path"],
            "size_bytes": row["size_bytes"],
            "modified_at": datetime.fromtimestamp(
                row["modified_at"]
            ).strftime("%d/%m/%Y")
        })

    return {
        "query": query,
        "total": len(items),
        "limit": limit,
        "limit_reached": limit_reached,
        "items": items
    }

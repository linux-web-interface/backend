
import os
import datetime

from flask import Blueprint, jsonify, send_from_directory, request

from services.search_engine import search_files


browseBp = Blueprint("browseBp", __name__)


# ==========================================
# DIRECTORY BROWSING
# ==========================================

@browseBp.route(
    "/browse/",
    defaults={"directory": ""},
    methods=["GET"]
)
@browseBp.route(
    "/browse/<path:directory>",
    methods=["GET"]
)
def api_browse(directory):

    target_path = os.path.realpath("/" + directory)

    if not os.path.exists(target_path):
        return jsonify({
            "error": "File atau direktori tidak ditemukan!"
        }), 404

    if os.path.isfile(target_path):
        return send_from_directory(
            os.path.dirname(target_path),
            os.path.basename(target_path),
            as_attachment=True
        )

    items = []

    try:
        with os.scandir(target_path) as entries:
            for entry in entries:

                is_dir = entry.is_dir(
                    follow_symlinks=False
                )

                stat = entry.stat(
                    follow_symlinks=False
                )

                item_time = datetime.datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%d/%m/%Y")

                items.append({
                    "name": entry.name,
                    "type": "dir" if is_dir else "file",
                    "path": entry.path,
                    "size_bytes": 0 if is_dir else stat.st_size,
                    "modified_at": item_time
                })

    except PermissionError:
        return jsonify({
            "error": "Akses ditolak (Permission Denied)"
        }), 403

    except OSError as e:
        return jsonify({
            "error": str(e)
        }), 500

    return jsonify({
        "current_dir": target_path,
        "total_items": len(items),
        "items": items
    })


# ==========================================
# GLOBAL SEARCH
# ==========================================

@browseBp.route("/search", methods=["GET"])
def api_search():

    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({
            "error": "Kata kunci pencarian tidak boleh kosong"
        }), 400

    if len(query) > 200:
        return jsonify({
            "error": "Kata kunci maksimal 200 karakter"
        }), 400

    try:
        limit = int(request.args.get("limit", 500))
        offset = int(request.args.get("offset", 0))

        if not 1 <= limit <= 500:
            raise ValueError("Limit harus antara 1 sampai 500")

        if offset < 0:
            raise ValueError("Offset tidak valid")

        result = search_files(
            query=query,
            limit=limit,
            offset=offset
        )

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:
        return jsonify({
            "error": f"Gagal melakukan pencarian: {str(e)}"
        }), 500

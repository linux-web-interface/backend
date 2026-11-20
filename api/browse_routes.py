import os
from flask import Blueprint, jsonify, send_from_directory, request
import datetime

browseBp = Blueprint('brwoseBp', __name__)

NEEDED_DIR = [
    '/',
]


@browseBp.route('/dir')
def dir():
    items = []

    try:
        for path in NEEDED_DIR:
            with os.scandir(path) as entries:
                for entry in entries:
                    is_dir = entry.is_dir(follow_symlinks=False)

                    stat = entry.stat(follow_symlinks=False)

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

    return jsonify({
        "total_items": len(items),
        "items": items
    })



@browseBp.route('/browse/', defaults={'directory': '/'}, methods=['GET'])
@browseBp.route('/browse/<path:directory>', methods=['GET'])
def api_browse(directory):
    target_path = os.path.realpath('/' + directory)

    # Normalisasi path
    target_path = os.path.realpath(target_path)

    # Pastikan path tersedia
    if not os.path.exists(target_path):
        return jsonify({
            "error": "File atau direktori tidak ditemukan!"
        }), 404

    # Jika target adalah file, kirim sebagai attachment
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
                is_dir = entry.is_dir(follow_symlinks=False)

                stat = entry.stat(follow_symlinks=False)

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

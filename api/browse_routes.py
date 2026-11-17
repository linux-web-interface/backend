import os
from flask import Blueprint, jsonify, send_from_directory
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


@browseBp.route('/browse/<dir_name>', defaults={'subpath': ''})
@browseBp.route('/browse/<dir_name>/<path:subpath>')
def api_browse(dir_name, subpath):
    target_path = os.path.join(dir_name, subpath)
    
    if not os.path.exists(target_path):
        return jsonify({"error": "File atau direktori tidak ditemukan!"}), 404

    if os.path.isfile(target_path):
        return send_from_directory(os.path.dirname(target_path), os.path.basename(target_path), as_attachment=True)

    items = []
    try:
        for item in os.listdir(target_path):
            item_full_path = os.path.join(target_path, item)
            
            is_dir = os.path.isdir(item_full_path)
            item_type = "direktori" if is_dir else "file"
            
            item_path = item if not subpath else f"{subpath}/{item}"
            
            items.append({
                "name": item,
                "type": item_type,       
                "path": item_path
            })
            
    except PermissionError:
        return jsonify({"error": "Akses ditolak (Permission Denied)"}), 403

    return jsonify({
        "current_dir": dir_name,
        "subpath": subpath,
        "total_items": len(items),
        "items": items
    })
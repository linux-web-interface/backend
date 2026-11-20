import os
from flask import Blueprint, jsonify, send_from_directory, request
import datetime

browseBp = Blueprint('brwoseBp', __name__)

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


@browseBp.route('/search', methods=['GET'])
def api_search():
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({
            "error": "Kata kunci pencarian tidak boleh kosong"
        }), 400

    if len(query) > 200:
        return jsonify({
            "error": "Kata kunci maksimal 200 karakter"
        }), 400

    query = query.casefold()
    max_results = 500
    items = []
    limit_reached = False

    # Direktori virtual dan sistem yang tidak perlu dicari
    excluded_dirs = {
        'proc',
        'sys',
        'dev',
        'run',
        'tmp',
        '.cache'
    }

    def add_result(path, item_type):
        nonlocal limit_reached

        try:
            if os.path.islink(path):
                return

            stat = os.stat(path, follow_symlinks=False)

            if item_type == "file" and not os.path.isfile(path):
                return

            if item_type == "dir" and not os.path.isdir(path):
                return

            name = os.path.basename(path)

            items.append({
                "name": name,
                "type": item_type,
                "path": path,
                "size_bytes": 0 if item_type == "dir" else stat.st_size,
                "modified_at": datetime.datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%d/%m/%Y")
            })

            if len(items) >= max_results:
                limit_reached = True

        except (PermissionError, OSError):
            pass

    def walk_error(error):
        # Abaikan direktori yang tidak bisa diakses
        pass

    try:
        for root, dirs, files in os.walk(
            '/',
            topdown=True,
            followlinks=False,
            onerror=walk_error
        ):
            # Jangan masuk ke direktori sistem tertentu
            dirs[:] = [
                directory
                for directory in dirs
                if directory not in excluded_dirs
                and not os.path.islink(
                    os.path.join(root, directory)
                )
            ]

            # Cari nama folder
            for directory in dirs:
                if query in directory.casefold():
                    add_result(
                        os.path.join(root, directory),
                        "dir"
                    )

                    if limit_reached:
                        break

            if limit_reached:
                break

            # Cari nama file
            for filename in files:
                if query in filename.casefold():
                    add_result(
                        os.path.join(root, filename),
                        "file"
                    )

                    if limit_reached:
                        break

            if limit_reached:
                break

    except OSError as e:
        return jsonify({
            "error": str(e)
        }), 500

    return jsonify({
        "query": request.args.get('q', '').strip(),
        "total": len(items),
        "limit": max_results,
        "limit_reached": limit_reached,
        "items": items
    }), 200

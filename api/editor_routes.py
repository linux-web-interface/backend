
import os
import stat
import tempfile

from flask import Blueprint, jsonify, request


editorBp = Blueprint("editorBp", __name__)

# Batas ukuran file: 2 MB
MAX_FILE_SIZE = 2 * 1024 * 1024

# Filesystem virtual yang tidak boleh diedit
BLOCKED_PATHS = (
    "/proc",
    "/sys",
    "/dev",
    "/run",
)


def validate_file_path(path):
    """
    Memvalidasi path dan memastikan seluruh komponennya
    bukan symbolic link.
    """

    if not path or not isinstance(path, str):
        raise ValueError("Path file tidak valid.")

    if not os.path.isabs(path):
        raise ValueError("Path harus berupa absolute path.")

    path = os.path.abspath(path)

    for blocked in BLOCKED_PATHS:
        if path == blocked or path.startswith(blocked + os.sep):
            raise PermissionError(
                "Akses ke filesystem virtual tidak diizinkan."
            )

    # Periksa setiap komponen path terhadap symbolic link
    current = os.path.sep

    for part in path.strip(os.path.sep).split(os.path.sep):
        if not part:
            continue

        current = os.path.join(current, part)

        try:
            info = os.lstat(current)
        except FileNotFoundError:
            raise FileNotFoundError("File tidak ditemukan.")

        if stat.S_ISLNK(info.st_mode):
            raise PermissionError(
                "Symbolic link tidak diizinkan."
            )

    try:
        info = os.lstat(path)
    except FileNotFoundError:
        raise FileNotFoundError("File tidak ditemukan.")

    if not stat.S_ISREG(info.st_mode):
        raise ValueError(
            "Hanya file biasa yang dapat dibuka di Code Editor."
        )

    return path, info


def read_text_file(path):
    """
    Membaca file sebagai teks UTF-8.
    """

    path, _ = validate_file_path(path)

    flags = os.O_RDONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)

    fd = os.open(path, flags)

    try:
        info = os.fstat(fd)

        if not stat.S_ISREG(info.st_mode):
            raise ValueError("File bukan file reguler.")

        if info.st_size > MAX_FILE_SIZE:
            raise ValueError(
                "Ukuran file melebihi batas 2 MB."
            )

        with os.fdopen(fd, "rb") as file:
            fd = None
            content = file.read(MAX_FILE_SIZE + 1)

        if len(content) > MAX_FILE_SIZE:
            raise ValueError(
                "Ukuran file melebihi batas 2 MB."
            )

        if b"\x00" in content:
            raise ValueError(
                "File binary tidak dapat dibuka di Code Editor."
            )

        try:
            return content.decode("utf-8")

        except UnicodeDecodeError:
            raise ValueError(
                "Format file bukan teks UTF-8 yang valid."
            )

    finally:
        if fd is not None:
            os.close(fd)


def save_text_file(path, content):
    """
    Menyimpan teks menggunakan temporary file
    dan atomic replace.
    """

    path, original_info = validate_file_path(path)

    if not isinstance(content, str):
        raise ValueError("Konten file harus berupa teks.")

    try:
        encoded = content.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("Konten tidak dapat dikonversi ke UTF-8.")

    if len(encoded) > MAX_FILE_SIZE:
        raise ValueError(
            "Ukuran konten melebihi batas 2 MB."
        )

    if b"\x00" in encoded:
        raise ValueError(
            "Konten mengandung karakter binary yang tidak diizinkan."
        )

    parent_dir = os.path.dirname(path)
    temp_path = None

    try:
        fd, temp_path = tempfile.mkstemp(
            prefix=".lwi-editor-",
            suffix=".tmp",
            dir=parent_dir,
        )

        with os.fdopen(fd, "wb") as temp_file:
            temp_file.write(encoded)
            temp_file.flush()
            os.fsync(temp_file.fileno())

            if os.geteuid() == 0:
                os.fchown(
                    temp_file.fileno(),
                    original_info.st_uid,
                    original_info.st_gid,
                )

            os.fchmod(
                temp_file.fileno(),
                stat.S_IMODE(original_info.st_mode),
            )

        # Pastikan file target masih bukan symbolic link
        _, current_info = validate_file_path(path)

        if (
            current_info.st_ino != original_info.st_ino
            or current_info.st_dev != original_info.st_dev
        ):
            raise PermissionError(
                "File berubah selama proses penyimpanan."
            )

        os.replace(temp_path, path)
        temp_path = None

        return True

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# =====================================
# READ FILE
# =====================================

@editorBp.route("/editor/read", methods=["GET"])
def api_editor_read():
    path = request.args.get("path", "").strip()

    if not path:
        return jsonify({
            "success": False,
            "error": "Path file wajib diisi.",
        }), 400

    try:
        content = read_text_file(path)

        return jsonify({
            "success": True,
            "path": path,
            "content": content,
        }), 200

    except FileNotFoundError as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 404

    except PermissionError as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 403

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 400

    except OSError as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# =====================================
# SAVE FILE
# =====================================

@editorBp.route("/editor/save", methods=["PUT"])
def api_editor_save():
    data = request.get_json(silent=True) or {}

    path = data.get("path")
    content = data.get("content")

    if not path:
        return jsonify({
            "success": False,
            "error": "Path file wajib diisi.",
        }), 400

    if content is None:
        return jsonify({
            "success": False,
            "error": "Konten file wajib diisi.",
        }), 400

    try:
        save_text_file(path, content)

        return jsonify({
            "success": True,
            "message": "File berhasil disimpan.",
            "path": path,
        }), 200

    except FileNotFoundError as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 404

    except PermissionError as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 403

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 400

    except OSError as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 500

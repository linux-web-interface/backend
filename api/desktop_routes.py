
import os
import json
import math
import tempfile

from flask import Blueprint, jsonify, request


desktopBp = Blueprint("desktopBp", __name__)


# Lokasi penyimpanan data aplikasi
DATA_DIR = "/var/lib/linux-web-interface"
DATA_FILE = os.path.join(DATA_DIR, "desktop.json")


# ==============================
# DATA HELPERS
# ==============================

def ensure_data_file():
    """Memastikan direktori dan file JSON tersedia."""

    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        save_desktop({"items": []})


def read_desktop():
    """Membaca data desktop dari JSON."""

    ensure_data_file()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ValueError("Format desktop.json tidak valid")

        return data

    except (json.JSONDecodeError, ValueError) as error:
        raise RuntimeError(f"Gagal membaca data desktop: {error}")


def save_desktop(data):
    """Menyimpan data secara atomik agar JSON tidak mudah rusak."""

    os.makedirs(DATA_DIR, exist_ok=True)

    temp_path = None

    try:
        fd, temp_path = tempfile.mkstemp(
            dir=DATA_DIR,
            suffix=".tmp"
        )

        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, DATA_FILE)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ==============================
# VALIDATION
# ==============================

def validate_item(payload, require_all=True):
    """Validasi data ikon desktop."""

    if not isinstance(payload, dict):
        return "Data harus berupa object"

    required = ["id", "name", "type", "path", "pos"]

    if require_all:
        missing = [key for key in required if key not in payload]

        if missing:
            return f"Field wajib belum diisi: {', '.join(missing)}"

    if "id" in payload:
        if not isinstance(payload["id"], str) or not payload["id"].strip():
            return "ID harus berupa string yang tidak kosong"

    if "name" in payload:
        if not isinstance(payload["name"], str) or not payload["name"].strip():
            return "Nama ikon tidak valid"

    if "type" in payload:
        if payload["type"] not in ("dir", "file"):
            return "Type harus berupa dir atau file"

    if "path" in payload:
        if (
            not isinstance(payload["path"], str)
            or not payload["path"].startswith("/")
        ):
            return "Path harus berupa absolute Linux path"

    if "pos" in payload:
        pos = payload["pos"]

        if not isinstance(pos, dict):
            return "Pos harus berupa object"

        if "x" not in pos or "y" not in pos:
            return "Pos harus memiliki properti x dan y"

        for key in ("x", "y"):
            value = pos[key]

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                return f"Pos.{key} harus berupa angka positif atau nol"

    return None


# ==============================
# GET DESKTOP ITEMS
# ==============================

@desktopBp.route("/desktop", methods=["GET"])
def get_desktop():

    try:
        data = read_desktop()

        return jsonify(data), 200

    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500


# ==============================
# ADD DESKTOP ITEM
# ==============================

@desktopBp.route("/desktop", methods=["POST"])
def add_desktop_item():

    payload = request.get_json(silent=True)

    error = validate_item(payload)

    if error:
        return jsonify({"error": error}), 400

    try:
        data = read_desktop()

        # Cegah ID duplikat
        if any(item["id"] == payload["id"] for item in data["items"]):
            return jsonify({
                "error": "ID ikon sudah digunakan"
            }), 409

        item = {
            "id": payload["id"],
            "name": payload["name"].strip(),
            "type": payload["type"],
            "path": payload["path"],
            "pos": {
                "x": payload["pos"]["x"],
                "y": payload["pos"]["y"]
            }
        }

        data["items"].append(item)

        save_desktop(data)

        return jsonify({
            "message": "Ikon berhasil ditambahkan",
            "item": item
        }), 201

    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500


# ==============================
# UPDATE DESKTOP ITEM
# ==============================

@desktopBp.route("/desktop/<item_id>", methods=["PUT"])
def update_desktop_item(item_id):

    payload = request.get_json(silent=True)

    error = validate_item(payload, require_all=False)

    if error:
        return jsonify({"error": error}), 400

    allowed_fields = ("name", "type", "path", "pos")

    if not any(key in payload for key in allowed_fields):
        return jsonify({
            "error": "Tidak ada data yang diperbarui"
        }), 400

    try:
        data = read_desktop()

        item = next(
            (item for item in data["items"] if item["id"] == item_id),
            None
        )

        if item is None:
            return jsonify({
                "error": "Ikon tidak ditemukan"
            }), 404

        for key in allowed_fields:
            if key in payload:
                value = payload[key]

                if key == "name":
                    value = value.strip()

                elif key == "pos":
                    value = {
                        "x": value["x"],
                        "y": value["y"]
                    }

                item[key] = value

        save_desktop(data)

        return jsonify({
            "message": "Ikon berhasil diperbarui",
            "item": item
        }), 200

    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500


# ==============================
# DELETE DESKTOP ITEM
# ==============================

@desktopBp.route("/desktop/<item_id>", methods=["DELETE"])
def delete_desktop_item(item_id):

    try:
        data = read_desktop()

        original_count = len(data["items"])

        data["items"] = [
            item for item in data["items"]
            if item["id"] != item_id
        ]

        if len(data["items"]) == original_count:
            return jsonify({
                "error": "Ikon tidak ditemukan"
            }), 404

        save_desktop(data)

        return jsonify({
            "message": "Ikon berhasil dihapus"
        }), 200

    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500

"""
Rastreador de teléfonos personales.

Recibe la ubicación de varios teléfonos Android (a través de la app
gratuita GPSLogger, configurada para enviar a /api/report) y muestra
todas las posiciones en un tablero web con mapa.

Ejecución local:
    SECRET_TOKEN=miclave python app.py

Despliegue: ver README.md y Dockerfile.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "positions.json")
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "")
HISTORY_PER_DEVICE = 50  # cuántos puntos se guardan por teléfono

os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
_store_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Almacén en JSON (simple, suficiente para unos pocos teléfonos)
# ---------------------------------------------------------------------------
def _load_store():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"devices": {}}


def _save_store(store):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_report_payload():
    """Acepta JSON, formulario o parámetros de consulta (GET de GPSLogger)."""
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    for key, value in request.values.items():
        if key not in data:
            data[key] = value
    return data


def _check_token(payload):
    if not SECRET_TOKEN:
        return True  # sin token configurado: acepta todo (solo para pruebas)
    supplied = (
        payload.get("token")
        or request.headers.get("X-Token")
        or request.args.get("token")
        or request.form.get("token")
    )
    return supplied == SECRET_TOKEN


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.route("/api/report", methods=["GET", "POST"])
def api_report():
    payload = _extract_report_payload()

    if not _check_token(payload):
        return jsonify({"ok": False, "error": "token inválido"}), 401

    device = str(payload.get("device") or payload.get("dev") or "sin-nombre").strip()
    lat = _to_float(payload.get("lat"))
    lon = _to_float(payload.get("lon") or payload.get("long"))

    if lat is None or lon is None:
        return jsonify({"ok": False, "error": "faltan lat/lon"}), 400
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({"ok": False, "error": "lat/lon fuera de rango"}), 400

    point = {
        "device": device,
        "lat": lat,
        "lon": lon,
        "time": str(payload.get("time") or payload.get("timestamp") or _now_iso()),
        "received_at": _now_iso(),
        "battery": payload.get("battery") or payload.get("batt"),
        "accuracy": _to_float(payload.get("accuracy") or payload.get("acc")),
        "speed": _to_float(payload.get("speed") or payload.get("spd")),
        "altitude": _to_float(payload.get("altitude") or payload.get("alt")),
    }

    with _store_lock:
        store = _load_store()
        entry = store["devices"].setdefault(device, {"latest": None, "history": []})
        entry["latest"] = point
        entry["history"].append(point)
        entry["history"] = entry["history"][-HISTORY_PER_DEVICE:]
        _save_store(store)

    return jsonify({"ok": True, "device": device})


@app.route("/api/positions", methods=["GET"])
def api_positions():
    with _store_lock:
        store = _load_store()
    latest = {
        name: entry["latest"]
        for name, entry in store["devices"].items()
        if entry.get("latest")
    }
    return jsonify({"ok": True, "devices": latest, "server_time": _now_iso()})


@app.route("/api/history/<device>", methods=["GET"])
def api_history(device):
    with _store_lock:
        store = _load_store()
    entry = store["devices"].get(device)
    if not entry:
        return jsonify({"ok": False, "error": "teléfono no encontrado"}), 404
    return jsonify({"ok": True, "device": device, "history": entry["history"]})


@app.route("/api/devices/<device>", methods=["DELETE"])
def api_delete_device(device):
    """Borra un teléfono del tablero (por si cambias de móvil)."""
    with _store_lock:
        store = _load_store()
        if device in store["devices"]:
            del store["devices"][device]
            _save_store(store)
            return jsonify({"ok": True, "deleted": device})
    return jsonify({"ok": False, "error": "teléfono no encontrado"}), 404


# ---------------------------------------------------------------------------
# Tablero web
# ---------------------------------------------------------------------------
@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if not SECRET_TOKEN:
        print("⚠️  SECRET_TOKEN no está configurado: /api/report acepta todo.")
        print("   En producción siempre configura un token, por ejemplo:")
        print("   SECRET_TOKEN=miclave python app.py")
    app.run(host="0.0.0.0", port=port)

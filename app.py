#!/usr/bin/env python3
"""
FullTrack Manager - Backend Flask
API REST + serve frontend estático
"""

import os
import threading
import queue
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory

from database import Database
from automation import FullTrackAutomation

# ─── Setup ──────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
db = Database()

# ─── Estado Global do Processamento ─────────────────────────────────────────────

processing_queue = queue.Queue()
processing_lock = threading.Lock()
processing_status = {
    "running": False,
    "current": None,
    "total": 0,
    "processed": 0,
    "errors": 0,
    "started_at": None,
}

LOG_BUFFER = []
MAX_LOG_BUFFER = 500


def add_log(level: str, message: str, serial_id: int = None):
    entry = {
        "id": len(LOG_BUFFER),
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "serial_id": serial_id,
    }
    LOG_BUFFER.append(entry)
    if len(LOG_BUFFER) > MAX_LOG_BUFFER:
        LOG_BUFFER.pop(0)
    db.add_log(level, message, serial_id)


# ─── Worker Thread ───────────────────────────────────────────────────────────────

def run_worker():
    """Thread de processamento em background"""
    while True:
        job = processing_queue.get()
        if job is None:
            break

        serial_ids = job
        with processing_lock:
            processing_status.update(
                running=True,
                total=len(serial_ids),
                processed=0,
                errors=0,
                current=None,
                started_at=datetime.now().isoformat(),
            )

        try:
            config = db.get_config()
            creds = db.get_credentials()

            if not creds.get("username") or not creds.get("password"):
                add_log("ERROR", "❌ Credenciais não configuradas! Acesse a aba Configurações e salve usuário/senha do FullTrack.")
                db.reset_serials_status("processando", "pendente")
                continue

            add_log("INFO", f"⚙️  Config: headless={config['headless']}, timeout={config['timeout']}s")
            automation = FullTrackAutomation(config, creds, add_log)

            if not automation.start():
                add_log("ERROR", "❌ Falha ao iniciar Chrome. Verifique se o chromium-driver está instalado.")
                db.reset_serials_status("processando", "pendente")
                continue

            try:
                if not automation.login():
                    add_log("ERROR", "❌ Falha no login. Verifique as credenciais em Configurações.")
                    db.reset_serials_status("processando", "pendente")
                    continue

                for i, sid in enumerate(serial_ids):
                    serial = db.get_serial_by_id(sid)
                    if not serial:
                        continue

                    with processing_lock:
                        processing_status["current"] = serial["numero"]

                    db.update_serial_status(sid, "processando")
                    result = automation.bloquear_serial(serial["numero"])

                    db.update_serial_status(
                        sid,
                        result["status"],
                        result.get("mensagem", ""),
                        result.get("resultado", ""),
                    )

                    with processing_lock:
                        processing_status["processed"] += 1
                        if result["status"] in ("erro", "nao_encontrado"):
                            processing_status["errors"] += 1

                    level = "INFO" if result["status"] == "bloqueado" else "WARNING"
                    add_log(
                        level,
                        f"[{i+1}/{len(serial_ids)}] {serial['numero']} → {result['status']}: {result.get('mensagem', '')}",
                        sid,
                    )

                add_log(
                    "INFO",
                    f"🏁 Concluído! {processing_status['processed']} processados | "
                    f"{processing_status['processed'] - processing_status['errors']} OK | "
                    f"{processing_status['errors']} erros",
                )

            finally:
                automation.stop()

        except Exception as e:
            add_log("ERROR", f"❌ Erro crítico no processamento: {e}")
            db.reset_serials_status("processando", "erro")

        finally:
            with processing_lock:
                processing_status.update(running=False, current=None)
            processing_queue.task_done()


_worker = threading.Thread(target=run_worker, daemon=True)
_worker.start()

# ─── Frontend ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


# ─── API: Seriais ────────────────────────────────────────────────────────────────

@app.route("/api/serials", methods=["GET"])
def list_serials():
    status = request.args.get("status")
    return jsonify(success=True, data=db.get_serials(status))


@app.route("/api/serials", methods=["POST"])
def create_serials():
    data = request.get_json(force=True) or {}
    raw = data.get("numeros", "")
    if isinstance(raw, list):
        numbers = [str(n).strip() for n in raw if str(n).strip()]
    else:
        numbers = [n.strip() for n in str(raw).split("\n") if n.strip()]

    added = sum(1 for n in numbers if db.add_serial(n))
    duplicates = len(numbers) - added
    return jsonify(success=True, added=added, duplicates=duplicates, total=len(numbers))


@app.route("/api/serials/upload", methods=["POST"])
def upload_serials():
    if "file" not in request.files:
        return jsonify(success=False, error="Nenhum arquivo enviado"), 400

    f = request.files["file"]
    fname = (f.filename or "").lower()
    records = []

    def is_header_row(row):
        header = " ".join(str(cell or "").strip().lower() for cell in row)
        return any(keyword in header for keyword in ["chave contrato", "numero de série", "número de série", "nome cliente", "observação", "observacao", "serial"])

    try:
        if fname.endswith((".xlsx", ".xls")):
            import openpyxl
            from io import BytesIO
            wb = openpyxl.load_workbook(BytesIO(f.read()), read_only=True, data_only=True)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                    continue
                if is_header_row(row):
                    continue

                contrato = str(row[0]).strip() if len(row) > 0 and row[0] is not None else ""
                numero = str(row[1]).strip() if len(row) > 1 and row[1] is not None and str(row[1]).strip() else contrato
                cliente = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
                observacao = str(row[3]).strip() if len(row) > 3 and row[3] is not None else ""
                if numero:
                    records.append((numero, contrato, cliente, observacao))

        elif fname.endswith(".csv"):
            import csv
            from io import StringIO
            for row in csv.reader(StringIO(f.read().decode("utf-8-sig"))):
                if not row or all(not cell.strip() for cell in row):
                    continue
                if is_header_row(row):
                    continue

                contrato = row[0].strip() if len(row) > 0 else ""
                numero = row[1].strip() if len(row) > 1 and row[1].strip() else contrato
                cliente = row[2].strip() if len(row) > 2 else ""
                observacao = row[3].strip() if len(row) > 3 else ""
                if numero:
                    records.append((numero, contrato, cliente, observacao))

        else:
            for line in f.read().decode("utf-8").splitlines():
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split("\t") if p.strip()]
                if len(parts) == 0:
                    continue
                if len(parts) == 1:
                    records.append((parts[0], "", "", ""))
                else:
                    contrato = parts[0]
                    numero = parts[1]
                    cliente = parts[2] if len(parts) > 2 else ""
                    observacao = parts[3] if len(parts) > 3 else ""
                    if numero:
                        records.append((numero, contrato, cliente, observacao))

        added = 0
        for numero, contrato, cliente, observacao in records:
            if db.add_serial(numero, contrato, cliente, observacao):
                added += 1

        return jsonify(success=True, added=added, duplicates=len(records) - added, total=len(records))

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/api/serials/<int:sid>", methods=["DELETE"])
def delete_serial(sid):
    db.delete_serial(sid)
    return jsonify(success=True)


@app.route("/api/serials/clear", methods=["DELETE"])
def clear_serials():
    status = request.args.get("status")
    db.clear_serials(status)
    return jsonify(success=True)


@app.route("/api/serials/<int:sid>/block", methods=["POST"])
def manual_block(sid):
    if processing_status["running"]:
        return jsonify(success=False, error="Já existe um processamento em andamento"), 409

    serial = db.get_serial_by_id(sid)
    if not serial:
        return jsonify(success=False, error="Serial não encontrado"), 404

    processing_queue.put([sid])
    add_log("INFO", f"🔒 Bloqueio manual iniciado: {serial['numero']}", sid)
    return jsonify(success=True, message="Bloqueio iniciado")


@app.route("/api/serials/<int:sid>/reset", methods=["POST"])
def reset_serial(sid):
    db.update_serial_status(sid, "pendente", "", "")
    return jsonify(success=True)


# ─── API: Processamento ──────────────────────────────────────────────────────────

@app.route("/api/process/start", methods=["POST"])
def start_processing():
    if processing_status["running"]:
        return jsonify(success=False, error="Já existe um processamento em andamento"), 409

    data = request.get_json(force=True) or {}
    status_filter = data.get("status", "pendente")

    serials = db.get_serials(status_filter)
    if not serials:
        return jsonify(success=False, error=f"Nenhum serial com status '{status_filter}'"), 400

    ids = [s["id"] for s in serials]
    processing_queue.put(ids)
    add_log("INFO", f"🚀 Lote iniciado: {len(ids)} serial(is) com status '{status_filter}'")
    return jsonify(success=True, queued=len(ids))


@app.route("/api/process/status", methods=["GET"])
def process_status():
    return jsonify(success=True, data=dict(processing_status))


# ─── API: Logs ───────────────────────────────────────────────────────────────────

@app.route("/api/logs", methods=["GET"])
def get_logs():
    limit = int(request.args.get("limit", 100))
    after_id = request.args.get("after_id")

    if after_id is not None:
        filtered = [l for l in LOG_BUFFER if l["id"] > int(after_id)]
    else:
        filtered = LOG_BUFFER[-limit:]

    return jsonify(success=True, data=list(reversed(filtered)))


@app.route("/api/logs/clear", methods=["DELETE"])
def clear_logs():
    LOG_BUFFER.clear()
    db.clear_logs()
    return jsonify(success=True)


# ─── API: Configurações ──────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def get_config():
    config = db.get_config()
    creds = db.get_credentials()
    return jsonify(success=True, data={
        **config,
        "username": creds.get("username", ""),
        "password_set": bool(creds.get("password")),
    })


@app.route("/api/config", methods=["POST"])
def save_config():
    data = request.get_json(force=True) or {}

    str_fields = ["username", "login_url", "fulltrack_url", "timeout", "delay_between", "search_selector"]
    for key in str_fields:
        if key in data:
            db.set_setting(key, str(data[key]))

    if "password" in data and data["password"]:
        db.set_setting("password", str(data["password"]))

    if "headless" in data:
        db.set_setting("headless", "true" if data["headless"] else "false")

    add_log("INFO", "⚙️  Configurações atualizadas")
    return jsonify(success=True, message="Configurações salvas com sucesso!")


# ─── API: Estatísticas ───────────────────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
def get_stats():
    return jsonify(success=True, data=db.get_stats())


# ─── Main ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init()
    db.reset_serials_status("processando", "pendente")
    add_log("INFO", "🎯 FullTrack Manager iniciado")
    print("=" * 60)
    print("  FullTrack Manager rodando em http://0.0.0.0:5000")
    print("  Acesse pelo navegador: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

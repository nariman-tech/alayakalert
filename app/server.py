"""Сервер дашборда (Flask). Даёт всё, что офлайн-сборка, плюс проверку своего текста.

    pip install flask scikit-learn networkx
    python -m evaluation.evaluate     # один раз: метрики и результаты
    python -m app.server              # открыть http://localhost:8000

API:
    GET  /api/data       — все данные дашборда
    POST /api/analyze    — {"text": "..."} -> риск, признаки, объяснение
    POST /api/feedback   — {"id": "...", "verdict": "ok" | "fp" | null} -> reports/feedback.jsonl
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from flask import Flask, Response, jsonify, request
except ImportError:  # pragma: no cover
    raise SystemExit("Нужен Flask: pip install flask\nБез сервера: python -m app.build и открыть dist/safenet_dashboard.html")

from app.payload import build_payload, render_page  # noqa: E402
from engine.ml import TextModel  # noqa: E402
from engine.pipeline import analyze_text  # noqa: E402

DATA = ROOT / "data" / "cases.jsonl"
FEEDBACK = ROOT / "reports" / "feedback.jsonl"

cases = [json.loads(line) for line in DATA.open(encoding="utf-8")]
MODEL = TextModel().fit([c for c in cases if c["split"] == "train"])
PAYLOAD = build_payload("server", model=MODEL)
PAGE = render_page(PAYLOAD, full_document=True)

app = Flask(__name__)


@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.get("/api/data")
def data():
    return jsonify(PAYLOAD)


@app.post("/api/analyze")
def analyze():
    body = request.get_json(silent=True) or {}
    text = str(body.get("text", ""))[:20000]
    if not text.strip():
        return jsonify({"error": "Пустой текст"}), 400
    return jsonify(analyze_text(text, model=MODEL))


@app.post("/api/feedback")
def feedback():
    body = request.get_json(silent=True) or {}
    FEEDBACK.parent.mkdir(exist_ok=True)
    with FEEDBACK.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"id": body.get("id"), "verdict": body.get("verdict"), "ts": int(time.time())},
                           ensure_ascii=False) + "\n")
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("SafeNet KZ: http://localhost:8000")
    app.run(host="0.0.0.0", port=8000, debug=False)

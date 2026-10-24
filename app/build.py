"""Офлайн-сборка дашборда в один HTML-файл (открывается двойным щелчком, без сервера и интернета*).

    python -m app.build   ->  dist/alayakalert.html

* Шрифты подгружаются из Google Fonts; без интернета браузер подставит системный шрифт.
Свой текст и выгрузки чатов проверяются в браузере (app/static/engine.js). Копия кладётся в index.html для GitHub Pages.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.payload import build_payload, render_page  # noqa: E402


def main():
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    payload = build_payload("static")
    out = dist / "alayakalert.html"
    out.write_text(render_page(payload, full_document=True), encoding="utf-8")
    (dist / "artifact.html").write_text(render_page(payload, full_document=False), encoding="utf-8")
    (ROOT / "index.html").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")  # для GitHub Pages
    print(f"Готово: {out} ({out.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    main()

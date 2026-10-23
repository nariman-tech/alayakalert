"""Разбор выгрузки чата из командной строки.

    python -m app.import_chat путь/к/result.json
    python -m app.import_chat "путь/к/Чат WhatsApp с Группа.txt"
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.importers import load_export  # noqa: E402
from engine.pipeline import analyze_chat  # noqa: E402


def main(path: str):
    p = Path(path)
    cases = load_export(p.name, p.read_bytes())
    if not cases:
        print("В файле не найдено сообщений.")
        return
    for c in cases:
        r = analyze_chat(c)
        ch = r["chat"]
        print(f"\n{c['title']} · {c['platform']} · {ch['messages']} сообщений")
        print(f"Риск {r['risk']} ({r['level_label']}), {r['track_name']}")
        print(r["summary"])
        if ch["messages"] > len(r["case"]["messages"]):
            print(f"Самое опасное окно: сообщения {ch['window'][0] + 1}–{ch['window'][1] + 1}")
        if ch["first_high"] is not None:
            print(f"Высокий риск впервые на сообщении {ch['first_high'] + 1}")
        print("Кто пишет подозрительное:")
        for a in ch["authors"][:5]:
            if a["points"]:
                print(f"  {a['author']}: {a['messages']} сообщ., {a['points']} баллов — {', '.join(a['signals'])}")
        for s in r["signals"]:
            if s["points"] > 0:
                ev = s["evidence"][0]["text"] if s["evidence"] else ""
                print(f"  +{s['points']} {s['title']}" + (f" — {s['note']}" if s["note"] else "") + (f"\n      «{ev}»" if ev else ""))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    else:
        main(sys.argv[1])

"""Собирает данные для дашборда: кейсы, результаты, граф, «живые» таймлайны, метрики, примеры."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.pipeline import analyze_text  # noqa: E402
from engine.signals import CATALOG  # noqa: E402

RESULTS = ROOT / "reports" / "results.json"
TEMPLATE = Path(__file__).with_name("static") / "dashboard.html"

SAMPLES = [
    ("Розыгрыш за покупку гайда", "Розыгрыш iPhone 17! Для участия купи мой гайд «Сторис, которые продают» за 19 990 тг, победителя выберем колесом в эфире."),
    ("Честный конкурс", "Подпишись и отметь 2 друзей — разыгрываем наушники. Участие бесплатное, итоги через рандомайзер в пятницу."),
    ("Пирамида транслитом", "vlozhi 5000 poluchi 10000 za 7 dnei, perevod na kaspi gold, uspei, ostalos 3 mesta"),
    ("Казино с маскировкой", "Поднял 480к на сл0тах 🎰 промокод GOLD2X, +200% к депозиту, ссылка в шапке"),
    ("Касса айналымы", "Касса айналымы: 5000 тг салсаңыз, 7 күннен кейін 10 000 тг аласыз. Каспиге аударыңыз, тек бүгін!"),
    ("Эфир-аукцион", "Кто последний скинет на каспи — забирает весь банк! Банк уже 250 000. Это благотворительность, от души."),
    ("Банковский депозит", "Депозит «Накопительный»: 14,5% годовых, вклады гарантируются КФГД. Откройте онлайн в приложении."),
    ("Новость АФМ", "АФМ предупреждает: мошенники обещают «вложи 5000 — получи 10 000» и просят переводить на личную карту. Не ведитесь."),
]

CASE_KEYS = ("id", "type", "platform", "account", "title", "split", "label", "scheme_name", "track", "messages", "images", "rules")


def build_payload(mode: str = "static", model=None) -> dict:
    if not RESULTS.exists():
        raise SystemExit("Нет reports/results.json. Сначала запустите: python -m evaluation.evaluate")
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    cases = [{k: c.get(k) for k in CASE_KEYS if k in c} for c in data["cases"]]
    for c in cases:
        c["messages"] = [{k: m[k] for k in ("t", "author", "text") if k in m} for m in c["messages"]]
    catalog = {k: {"title": v.title, "points": v.points, "weight": v.weight} for k, v in CATALOG.items()}
    samples = [{"label": label, "text": text, "result": analyze_text(text, model=model)} for label, text in SAMPLES]
    team_file = ROOT / "reports" / "team_history.json"
    team = json.loads(team_file.read_text(encoding="utf-8")) if team_file.exists() else {"rows": []}
    return {"mode": mode, "cases": cases, "results": data["results"], "graph": data["graph"],
            "timelines": data["timelines"], "metrics": data["metrics"], "catalog": catalog, "samples": samples,
            "team": team}


def render_page(payload: dict, full_document: bool = True) -> str:
    fragment = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    fragment = fragment.replace("/*__DATA__*/null", blob)
    if not full_document:
        return fragment
    return ("<!doctype html>\n<html lang=\"ru\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "<style>html,body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n"
            + fragment + "\n</body>\n</html>\n")

"""Собирает данные для дашборда: кейсы, результаты, граф, «живые» таймлайны, метрики, примеры."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.importers import load_export  # noqa: E402
from engine.pipeline import analyze_chat, analyze_input  # noqa: E402
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
    ("Расшифровка эфира-аукциона", """[0:00] @host: Салем бәріне! Бүгінгі банк — 150 000 тг 🔥
[0:15] @host: ставки кидаем на каспи +7 700 000 12 34, кто последний скинет — забирает весь банк
[0:30] @host: один победитель выигрывает только один раз, дальше смотрит. это благотворительность
[0:50] @aru25: +500
[1:05] @dias83: кинул 1000
[1:20] @host: ставка от @marat66 — 2 000 тг, банк растёт!
[1:41] @helper_77: +3000
[1:48] @host: Победитель раунда — @star_win! Забирает 150 000 тг
[2:10] @asel38: +1000
[2:25] @dana50: ставлю 2к
[2:43] @helper_77: +3000
[2:50] @host: Победитель — @star_win! Құттықтаймыз
[3:10] @kamila80: +500
[3:30] @helper_77: +2000
[3:37] @host: Победитель раунда — @star_win, забирает 150 000 тг
[4:00] @host: завтра снова в 20:00, банк будет больше!"""),
    ("Эфир-прогрев (по наблюдению команды)", open(ROOT / "data" / "team" / "observed_warmup_anonymized.txt", encoding="utf-8").read()),
    ("Благотворительный аукцион", """[0:00] @fund_shans: Благотворительный аукцион картин, все средства идут на счёт фонда «Шанс», реквизиты в описании
[0:30] @fund_shans: картина уходит тому, кто предложит больше, оплата фонду после эфира
[1:00] @aru25: предлагаю 25 000 за лот 1
[1:40] @dias83: 30 000
[2:20] @fund_shans: Лот 1 продан @dias83, спасибо за помощь фонду!
[3:00] @asel38: за лот 2 даю 20 000
[3:50] @fund_shans: Лот 2 продан @asel38. Рахмет!"""),
]

FILE_SAMPLES = [
    ("Выгрузка Telegram: клуб «Береке»", "telegram_export_sample.json"),
    ("Выгрузка WhatsApp: касса айналымы", "whatsapp_sample.txt"),
    ("Выгрузка WhatsApp: честный родительский чат", "whatsapp_honest_sample.txt"),
]

CASE_KEYS = ("id", "type", "platform", "account", "title", "split", "label", "scheme_name", "track", "messages", "images",
             "rules", "date")


def build_payload(mode: str = "static", model=None) -> dict:
    if not RESULTS.exists():
        raise SystemExit("Нет reports/results.json. Сначала запустите: python -m evaluation.evaluate")
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    cases = [{k: c.get(k) for k in CASE_KEYS if k in c} for c in data["cases"]]
    for c in cases:
        c["messages"] = [{k: m[k] for k in ("t", "author", "text") if k in m} for m in c["messages"]]
    catalog = {k: {"title": v.title, "points": v.points, "weight": v.weight} for k, v in CATALOG.items()}
    samples = [{"label": label, "text": text,
                "result": analyze_input(text, model=model, case_id=f"sample-{i}")} for i, (label, text) in enumerate(SAMPLES)]
    for label, fname in FILE_SAMPLES:
        path = ROOT / "data" / "samples" / fname
        if not path.exists():
            continue
        cases_f = load_export(fname, path.read_bytes())
        if cases_f:
            cases_f[0]["id"] = "file-" + fname.split(".")[0]
            res = analyze_chat(cases_f[0], model=model)
            samples.append({"label": label, "file": True,
                            "text": f"Файл выгрузки: {fname} — {res['chat']['messages']} сообщений. "
                                    "Свой файл можно загрузить при запуске сервера.", "result": res})
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

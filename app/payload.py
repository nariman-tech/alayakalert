"""Собирает данные для дашборда: кейсы, результаты, граф, «живые» таймлайны, метрики, примеры."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.importers import load_export  # noqa: E402
from engine.pipeline import analyze_chat, analyze_input, analyze_text  # noqa: E402
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
            chat_text = "\n".join(f"{j + 1}. {m.get('author', '')}: {m.get('text', '')}" for j, m in enumerate(cases_f[0]["messages"]))
            samples.append({"label": label, "file": True, "chat_text": chat_text,
                            "text": f"Файл выгрузки: {fname} — {res['chat']['messages']} сообщений. "
                                    "Свой файл можно загрузить при запуске сервера.", "result": res})
    team_file = ROOT / "reports" / "team_history.json"
    team = json.loads(team_file.read_text(encoding="utf-8")) if team_file.exists() else {"rows": []}
    return {"mode": mode, "ai_sets": ai_sets(), "cases": cases, "results": data["results"], "graph": data["graph"],
            "timelines": data["timelines"], "metrics": data["metrics"], "catalog": catalog, "samples": samples,
            "team": team}


AI_SETS = [
    ("set4", "Набор 4 (слепой, писала команда)", "team_test4.tsv"),
    ("probe", "Провокационные честные тексты", "probe_negatives.tsv"),
]


def ai_sets() -> list[dict]:
    """Наборы команды для проверки второго мнения ИИ: текст, разметка команды и оценка правил (замер на текущей версии)."""
    import csv
    out = []
    for key, name, fname in AI_SETS:
        path = ROOT / "data" / "team" / fname
        if not path.exists():
            continue
        rows = list(csv.reader(path.open(encoding="utf-8"), delimiter="\t"))[1:]
        items = []
        for r in rows:
            if not r or not r[0].strip():
                continue
            res = analyze_text(r[0])
            items.append({"text": r[0], "label": r[1].strip().lower().startswith("д"), "track": r[2] if len(r) > 2 else "",
                          "engine_level": res["level"], "engine_risk": res["risk"]})
        out.append({"key": key, "name": name, "rows": items})
    return out


def render_page(payload: dict, full_document: bool = True) -> str:
    fragment = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    fragment = fragment.replace("/*__DATA__*/null", blob)
    from app.export_engine import engine_script
    fragment = fragment.replace("<script>/*__ENGINE__*/</script>", "<script>\n" + engine_script() + "\n</script>")
    if not full_document:
        return fragment
    return ("<!doctype html>\n<html lang=\"ru\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "<style>html,body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n"
            + fragment + "\n</body>\n</html>\n")

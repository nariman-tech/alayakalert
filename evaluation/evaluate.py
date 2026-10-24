"""Оценка качества AlayakAlert.

Считает:
1. precision / recall / доля ложных срабатываний (FPR) по видам схем — на train и test;
   кейс считается помеченным при среднем или высоком риске (риск ≥ 40);
2. сравнение с базовой линией «поиск по ключевым словам» (≥ 2 разных слова из списка);
3. стресс-тест маскировки: тестовые тексты портятся (транслит, к@зин0, разрядка, эмодзи,
   латинские двойники) — и снова считаем recall;
4. скорость обнаружения: на каком сообщении чата/эфира риск впервые становится высоким
   и успевает ли система до первого «скриншота выплаты».

Запуск:  python -m evaluation.evaluate   ->  reports/metrics.json, reports/metrics.md, reports/results.json
"""
from __future__ import annotations

import copy
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.ml import HAVE_SKLEARN, TextModel  # noqa: E402
from engine.pipeline import analyze_case, analyze_corpus, first_high, timeline  # noqa: E402

DATA = ROOT / "data" / "cases.jsonl"
REPORTS = ROOT / "reports"
FLAG = ("medium", "high")

BASELINE_WORDS = ["казино", "слот", "промокод", "депозит", "розыгрыш", "выиграл", "вложи", "получи", "каспи", "kaspi",
                  "доход", "прибыль", "гарант", "пирамид", "ставк", "бонус", "приз", "инвест", "перевод", "x2"]


def load() -> list[dict]:
    return [json.loads(line) for line in DATA.open(encoding="utf-8")]


def case_raw(case: dict) -> str:
    parts = [m["text"] for m in case.get("messages", [])] + [i.get("ocr", "") for i in case.get("images", [])]
    return "\n".join(parts).lower()


def baseline_flag(case: dict) -> bool:
    t = case_raw(case)
    return sum(1 for w in BASELINE_WORDS if w in t) >= 2


def metrics(pairs: list[tuple[int, bool]]) -> dict:
    tp = sum(1 for y, p in pairs if y and p)
    fp = sum(1 for y, p in pairs if not y and p)
    fn = sum(1 for y, p in pairs if y and not p)
    tn = sum(1 for y, p in pairs if not y and not p)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"n": len(pairs), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(prec, 3), "recall": round(rec, 3), "fpr": round(fpr, 3), "f1": round(f1, 3)}


def table(cases, flags: dict[str, bool], split: str) -> dict:
    out = {}
    for track in (1, 2, 3, "all"):
        sel = [c for c in cases if c["split"] == split and (track == "all" or c["track"] == track)]
        out[str(track)] = metrics([(c["label"], flags[c["id"]]) for c in sel])
    return out


# ── Маскировка ───────────────────────────────────────────────────────────────
CYR2LAT = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
           "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
           "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
           "э": "e", "ю": "yu", "я": "ya", "ә": "a", "ғ": "g", "қ": "q", "ң": "n", "ө": "o", "ұ": "u", "ү": "u",
           "һ": "h", "і": "i"}
HOMO = {"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "к": "k"}
LEETM = {"о": "0", "а": "@", "з": "3", "и": "1"}
EMO = {"казино": "🎰", "деньги": "💰", "розыгрыш": "🎁"}
KEY_STEMS = ["казино", "слот", "промокод", "депозит", "розыгр", "выигр", "влож", "получ", "каспи", "доход", "гарант",
             "курс", "приз", "колес", "банк", "ставк", "бонус", "занос", "поднял", "зеркал", "перевод", "карт",
             "скин", "участ", "оплат", "реферал", "пригла", "вклад"]
WORD = re.compile(r"[а-яёәғқңөұүһі]+", re.I)


def translit(text: str) -> str:
    return "".join(CYR2LAT.get(ch, CYR2LAT.get(ch.lower(), ch).upper() if ch.isupper() else ch) for ch in text)


def obfuscate_word(w: str, how: str) -> str:
    lw = w.lower()
    if how == "homoglyph":
        return "".join(HOMO.get(ch, ch) for ch in lw)
    if how == "leet":
        return "".join(LEETM.get(ch, ch) if i > 0 else ch for i, ch in enumerate(lw))
    if how == "spaced":
        return " ".join(lw)
    if how == "stretch":
        return lw[:2] + lw[2] * 4 + lw[3:] if len(lw) > 3 else lw
    if how == "emoji":
        return EMO.get(lw, lw)
    return w


def mask_text(text: str, rng: random.Random) -> tuple[str, str]:
    how = rng.choice(["translit", "homoglyph", "leet", "spaced", "stretch", "emoji", "mixed"])
    if how == "translit":
        return translit(text), how

    def sub(m):
        w = m.group(0)
        if not any(s in w.lower() for s in KEY_STEMS):
            return w
        h = rng.choice(["homoglyph", "leet", "spaced", "stretch", "emoji"]) if how == "mixed" else how
        return obfuscate_word(w, h)

    return WORD.sub(sub, text), how


def mask_case(case: dict, rng: random.Random) -> tuple[dict, str]:
    c = copy.deepcopy(case)
    how = ""
    for m in c.get("messages", []):
        m["text"], how = mask_text(m["text"], rng)
    for i in c.get("images", []):
        i["ocr"], _ = mask_text(i.get("ocr", ""), rng)
    return c, how


# ── Главная функция ──────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    cases = load()
    train = [c for c in cases if c["split"] == "train"]
    model = TextModel().fit(train) if HAVE_SKLEARN else None

    results_rules, graph = analyze_corpus(cases, model=None, with_network=False)
    results_full, graph = analyze_corpus(cases, model=model, with_network=True)
    by = {c["id"]: c for c in cases}

    flags = {
        "baseline": {c["id"]: baseline_flag(c) for c in cases},
        "rules": {r["id"]: r["level"] in FLAG for r in results_rules},
        "full": {r["id"]: r["level"] in FLAG for r in results_full},
    }
    report = {"dataset": {"total": len(cases), "train": len(train), "test": len(cases) - len(train),
                          "positive": sum(c["label"] for c in cases), "negative": sum(1 - c["label"] for c in cases)},
              "ml_available": bool(model and model.ready)}
    for name, fl in flags.items():
        report[name] = {"train": table(cases, fl, "train"), "test": table(cases, fl, "test")}

    # ошибки на test (для разбора в README, не для подгонки)
    errors = []
    for r in results_full:
        c = by[r["id"]]
        if c["split"] == "test" and (r["level"] in FLAG) != bool(c["label"]):
            errors.append({"id": c["id"], "scheme": c["scheme_name"], "label": c["label"], "risk": r["risk"],
                           "text": case_raw(c)[:160]})
    report["test_errors"] = errors

    # маскировка (только тестовая часть, без сети и ML — чистая устойчивость правил)
    rng = random.Random(7)
    test = [c for c in cases if c["split"] == "test"]
    masked = []
    for c in test:
        mc, how = mask_case(c, rng)
        masked.append((c, mc, how))
    stress = {}
    for name, fn in (("baseline", baseline_flag), ("engine", lambda cc: analyze_case(cc)["level"] in FLAG)):
        clean_pairs = [(c["label"], fn(c)) for c, _, _ in masked]
        mask_pairs = [(c["label"], fn(mc)) for c, mc, _ in masked]
        stress[name] = {"clean": metrics(clean_pairs), "masked": metrics(mask_pairs)}
    by_how = {}
    for c, mc, how in masked:
        if c["label"]:
            d = by_how.setdefault(how, {"n": 0, "baseline": 0, "engine": 0})
            d["n"] += 1
            d["baseline"] += baseline_flag(mc)
            d["engine"] += analyze_case(mc)["level"] in FLAG
    stress["by_technique"] = by_how
    report["stress"] = stress
    report["stress_examples"] = [{"how": how, "masked": mc["messages"][0]["text"][:140]}
                                 for c, mc, how in masked[:40] if c["label"] and c["type"] == "post"][:6]

    # скорость обнаружения
    ttd, timelines = [], {}
    for c in cases:
        if c["type"] not in ("chat", "stream"):
            continue
        tl = timeline(c, model=model)
        timelines[c["id"]] = tl
        if not c["label"]:
            continue
        fh = first_high(tl)
        payout = next((i for i, m in enumerate(c["messages"]) if m.get("kind") == "payout"), None)
        ttd.append({"id": c["id"], "type": c["type"], "messages": len(c["messages"]), "first_high": fh,
                    "payout": payout, "before_payout": fh is not None and payout is not None and fh < payout})
    detected = [x for x in ttd if x["first_high"] is not None]
    chats = [x for x in ttd if x["type"] == "chat"]
    chats_det = [x for x in chats if x["first_high"] is not None]
    report["time_to_detection"] = {
        "cases": len(ttd), "detected_high": len(detected),
        "avg_first_high_msg": round(sum(x["first_high"] + 1 for x in detected) / max(1, len(detected)), 1),
        "avg_share_of_conversation": round(sum((x["first_high"] + 1) / x["messages"] for x in detected) / max(1, len(detected)), 2),
        "chats": len(chats),
        "chats_before_first_payout": sum(x["before_payout"] for x in chats_det),
        "chats_with_payout": sum(1 for x in chats if x["payout"] is not None),
        "items": ttd,
    }
    report["graph"] = {"clusters": graph["clusters"][:10], "nodes": len(graph["nodes"]), "links": len(graph["links"])}
    report["runtime_sec"] = round(time.time() - t0, 1)

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS / "metrics.md").write_text(render_md(report), encoding="utf-8")
    results_payload = {"cases": cases, "results": results_full, "graph": graph, "timelines": timelines,
                       "metrics": {k: v for k, v in report.items() if k not in ("time_to_detection",)} |
                       {"time_to_detection": {k: v for k, v in report["time_to_detection"].items() if k != "items"}}}
    (REPORTS / "results.json").write_text(json.dumps(results_payload, ensure_ascii=False), encoding="utf-8")
    print(render_md(report))


def pct(x: float) -> str:
    return f"{int(x * 100 + 0.5)}%"


def render_md(r: dict) -> str:
    L = ["# Метрики AlayakAlert", "",
         f"Датасет: {r['dataset']['total']} кейсов (train {r['dataset']['train']}, test {r['dataset']['test']}; "
         f"подозрительных {r['dataset']['positive']}, честных {r['dataset']['negative']}). "
         "Кейс помечен, если риск средний или высокий.", "",
         "## Тестовая выборка (другая манера письма: сленг, казахский, транслит)", "",
         "| Метод | Вид схемы | Precision | Recall | Ложные срабатывания |", "| --- | --- | --- | --- | --- |"]
    names = {"baseline": "Словарь (≥ 2 ключевых слова)", "rules": "Признаки (без сети и ML)", "full": "AlayakAlert (признаки + сеть + ML)"}
    for m in ("baseline", "rules", "full"):
        for t in ("1", "2", "3", "all"):
            x = r[m]["test"][t]
            L.append(f"| {names[m]} | {'все' if t == 'all' else t} | {pct(x['precision'])} | {pct(x['recall'])} | {pct(x['fpr'])} |")
    s = r["stress"]
    L += ["", "## Стресс-тест маскировки (тестовая выборка)", "",
          "| Метод | Recall без маскировки | Recall с маскировкой | Ложные срабатывания с маскировкой |", "| --- | --- | --- | --- |"]
    for m, label in (("baseline", "Словарь"), ("engine", "AlayakAlert")):
        L.append(f"| {label} | {pct(s[m]['clean']['recall'])} | {pct(s[m]['masked']['recall'])} | {pct(s[m]['masked']['fpr'])} |")
    L += ["", "По техникам (только подозрительные кейсы): " + "; ".join(
        f"{k}: словарь {v['baseline']}/{v['n']}, AlayakAlert {v['engine']}/{v['n']}" for k, v in sorted(s["by_technique"].items()))]
    t = r["time_to_detection"]
    L += ["", "## Скорость обнаружения (чаты и эфиры)", "",
          f"- Высокий риск достигнут в {t['detected_high']} из {t['cases']} подозрительных чатов и эфиров.",
          f"- В среднем на {t['avg_first_high_msg']}-м сообщении, это {pct(t['avg_share_of_conversation'])} разговора.",
          f"- В {t['chats_before_first_payout']} из {t['chats_with_payout']} чатов пирамид — раньше первого «скриншота выплаты»."]
    if r.get("test_errors"):
        L += ["", "## Ошибки на тесте (для разбора)", ""]
        for e in r["test_errors"]:
            kind = "пропуск" if e["label"] else "ложное срабатывание"
            L.append(f"- {e['id']} · {e['scheme']} · {kind} (риск {e['risk']}): {e['text'][:110]}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()

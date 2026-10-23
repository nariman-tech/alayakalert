"""Проверка разбора сырой расшифровки эфира.

Каждый синтетический эфир превращается в сырой текст (строки «[м:сс] @ник: текст»,
ставки зрителей в разных стилях: «+500», «кинул 1000», «ставлю 2к», «ставка от @ник — 1000 тг»).
Готовые таблицы ставок и победителей удаляются. Затем текст разбирается заново,
и результат сравнивается с анализом по исходным таблицам.

    python -m evaluation.transcript_check
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.pipeline import analyze_case  # noqa: E402
from engine.transcript import parse_transcript  # noqa: E402

KEY = ("T1_SHILL", "T1_REPEAT_WINNER", "T1_POT_RATIO", "T1_POT")


def fmt(t: int) -> str:
    return f"[{t // 60}:{t % 60:02d}]"


def render(case: dict, rng: random.Random) -> str:
    bid_keys = {(b["t"], b["user"]) for b in case.get("bids", [])}
    lines = []
    for m in case["messages"]:
        # ведущий иногда дублирует ставку — такие строки заменяем репликой зрителя
        if any(t == m["t"] and u in m["text"] for t, u in bid_keys):
            continue
        lines.append((m["t"], f"{fmt(m['t'])} {m['author'] or '@host'}: {m['text']}"))
    for b in case.get("bids", []):
        amt = b["amount"]
        style = rng.choice(["plus", "kinul", "k", "host"])
        if style == "plus":
            txt = f"{b['user']}: +{amt}"
        elif style == "kinul":
            txt = f"{b['user']}: кинул {amt}"
        elif style == "k" and amt % 1000 == 0:
            txt = f"{b['user']}: ставлю {amt // 1000}к"
        else:
            txt = f"@host: ставка от {b['user']} — {amt:,} тг".replace(",", " ")
        lines.append((b["t"], f"{fmt(b['t'])} {txt}"))
    lines.sort(key=lambda x: x[0])
    return "\n".join(l for _, l in lines)


def main():
    cases = [json.loads(l) for l in (ROOT / "data" / "cases.jsonl").open(encoding="utf-8")]
    streams = [c for c in cases if c["type"] == "stream"]
    rng = random.Random(11)
    same_level = same_flag = 0
    key_match = key_total = 0
    rows = []
    for c in streams:
        ref = analyze_case(c)
        raw = render(c, rng)
        parsed = parse_transcript(raw, case_id=c["id"])
        got = analyze_case(parsed)
        ref_ids = {s["id"] for s in ref["signals"]} & set(KEY)
        got_ids = {s["id"] for s in got["signals"]} & set(KEY)
        key_total += len(ref_ids)
        key_match += len(ref_ids & got_ids)
        same_level += ref["level"] == got["level"]
        same_flag += (ref["level"] != "low") == (got["level"] != "low")
        rows.append((c["id"], c["label"], len(c.get("bids", [])), parsed["parsed"]["bids"], len(c.get("winners", [])),
                     parsed["parsed"]["winners"], ref["risk"], got["risk"], sorted(ref_ids - got_ids)))
    for r in rows:
        print(f"{r[0]} метка {r[1]} · ставок {r[2]}→{r[3]} · победителей {r[4]}→{r[5]} · риск {r[6]}→{r[7]}"
              + (f" · потеряно {r[8]}" if r[8] else ""))
    n = len(streams)
    print(f"\nЭфиров: {n}. Тот же уровень риска: {same_level}/{n}. То же решение «помечать / нет»: {same_flag}/{n}. "
          f"Ключевые признаки эфира найдены по тексту: {key_match}/{key_total}.")
    out = {"streams": n, "same_level": same_level, "same_flag": same_flag, "key_match": key_match, "key_total": key_total}
    (ROOT / "reports" / "transcript_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

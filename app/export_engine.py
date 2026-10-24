"""Данные движка для браузерной версии (app/static/engine.js).

Регулярные выражения не переписываются вручную: их исходный текст берётся прямо из модулей Python,
поэтому правила в браузере и на сервере одни и те же. Проверка совпадения результатов:
    python -m evaluation.js_parity
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engine.concepts as C  # noqa: E402
import engine.importers as I  # noqa: E402
import engine.normalize as N  # noqa: E402
import engine.returns as R  # noqa: E402
import engine.scoring as SC  # noqa: E402
import engine.signals as S  # noqa: E402
import engine.streams as ST  # noqa: E402
import engine.transcript as T  # noqa: E402


def _pat(p: re.Pattern) -> list:
    return [p.pattern, "i" if p.flags & re.I else ""]


def _mod(mod) -> dict:
    return {k: _pat(v) for k, v in vars(mod).items() if isinstance(v, re.Pattern)}


def engine_data() -> dict:
    return {
        "rx": {"N": _mod(N), "R": _mod(R), "C": _mod(C), "S": _mod(S), "T": _mod(T), "I": _mod(I)},
        "periods": [[p.pattern, d] for p, d in R.PERIODS],
        "bid_patterns": [p.pattern for p in T.BID_PATTERNS],
        "winner_patterns": [p.pattern for p in T.WINNER],
        "amount": T.AMOUNT,
        "lookalike": N.LOOKALIKE, "leet": N.LEET, "lat_leet": N.LAT_LEET, "emoji": list(N.EMOJI.items()),
        "translit_digraphs": N.TRANSLIT_DIGRAPHS, "translit": N.TRANSLIT,
        "catalog": [{"id": d.id, "track": d.track, "weight": d.weight, "title": d.title, "hint": d.hint, "points": d.points}
                    for d in S.CATALOG.values()],
        "track_names": SC.TRACK_NAMES, "legal_hint": SC.LEGAL_HINT,
        "floor": SC.FLOOR, "floor_med": SC.FLOOR_MED,
        "combo_labels": [[t, label] for t, label, _ in SC.COMBOS],
        "combo_med_labels": [[t, label] for t, label, _ in SC.COMBOS_MED],
        "snipe_window": ST.SNIPE_WINDOW, "max_messages": I.MAX_MESSAGES,
    }


def engine_script() -> str:
    data = json.dumps(engine_data(), ensure_ascii=False).replace("</", "<\\/")
    code = (ROOT / "app" / "static" / "engine.js").read_text(encoding="utf-8")
    return "var ENGINE_DATA = " + data + ";\n" + code


if __name__ == "__main__":
    out = ROOT / "dist" / "engine_bundle.js"
    out.parent.mkdir(exist_ok=True)
    out.write_text(engine_script(), encoding="utf-8")
    print("Готово:", out)

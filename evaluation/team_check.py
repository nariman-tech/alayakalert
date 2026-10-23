"""Проверка движка на таблице команды (TSV: Текст, Подозрительный?, Трек, Где такое пишут).

    python -m evaluation.team_check data/team/team_test2.tsv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.pipeline import analyze_case  # noqa: E402


def load(path: str) -> list[dict]:
    cases = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.reader(f, delimiter="\t"):
            if not r or not r[0].strip() or r[0].startswith("Текст") or len(r) < 2:
                continue
            text, lab, tr, plat = (r + ["", "", "", ""])[:4]
            if not lab.strip():
                continue
            cases.append({"id": f"{Path(path).stem}-{len(cases) + 1:03d}", "type": "post", "platform": plat.strip(),
                          "account": "@team", "label": 1 if lab.strip().lower().startswith("д") else 0,
                          "track": int(tr) if tr.strip().isdigit() else 0,
                          "messages": [{"t": 0, "author": "", "text": text.strip()}], "images": []})
    return cases


def run(path: str, verbose: bool = True) -> dict:
    cases = load(path)
    tp = fp = fn = tn = 0
    per_track: dict[int, list] = {}
    for c in cases:
        r = analyze_case(c)
        flag = r["level"] != "low"
        y = c["label"]
        tp += y and flag
        fp += (not y) and flag
        fn += y and not flag
        tn += (not y) and not flag
        per_track.setdefault(c["track"], []).append((y, flag))
        if verbose:
            mark = "ок " if flag == bool(y) else ("ПРОПУСК" if y else "ЛОЖНОЕ ")
            print(f"{mark:8} {'да ' if y else 'нет'} риск {r['risk']:3d}  {c['messages'][0]['text'][:80]}")
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    fpr = fp / (fp + tn) if fp + tn else 0
    print(f"\n{len(cases)} текстов · TP {tp} · FP {fp} · FN {fn} · TN {tn}")
    print(f"Precision {prec:.0%} · Recall {rec:.0%} · F1 {f1:.0%} · Ложные срабатывания {fpr:.0%}")
    for t, pairs in sorted(per_track.items()):
        pos = [p for y, p in pairs if y]
        print(f"  трек {t}: найдено {sum(pos)} из {len(pos)} подозрительных, ложных {sum(p for y, p in pairs if not y)} из {sum(1 for y, _ in pairs if not y)}")
    return {"n": len(cases), "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": prec, "recall": rec, "f1": f1, "fpr": fpr}


def predict(texts_path: str, out_path: str) -> None:
    """Слепой режим: оценки по текстам без ответов. Ответы команды присылаются только после."""
    rows = []
    with open(texts_path, encoding="utf-8-sig") as f:
        for r in csv.reader(f, delimiter="\t"):
            if not r or not r[0].strip() or r[0].startswith("Текст"):
                continue
            rows.append(r[0].strip())
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("№\tТекст\tРиск\tУровень\tПомечен системой\tПризнаки\n")
        for i, text in enumerate(rows, 1):
            res = analyze_case({"id": f"blind-{i}", "type": "post", "messages": [{"t": 0, "text": text}], "images": []})
            sig = ", ".join(s["title"] for s in res["signals"] if s["points"] > 0)
            f.write(f"{i}\t{text}\t{res['risk']}\t{res['level_label']}\t{'да' if res['level'] != 'low' else 'нет'}\t{sig}\n")
    print(f"Оценки {len(rows)} текстов записаны в {out_path}")


def score(pred_path: str, labels_path: str) -> dict:
    """Сверка заранее записанных оценок с ответами команды (по номеру строки)."""
    preds = list(csv.reader(open(pred_path, encoding="utf-8-sig"), delimiter="\t"))[1:]
    labels = [r for r in csv.reader(open(labels_path, encoding="utf-8-sig"), delimiter="\t")
              if r and r[0].strip() and not r[0].startswith("Текст") and not r[0].startswith("№")]
    tp = fp = fn = tn = 0
    for p, l in zip(preds, labels):
        flag = p[4] == "да"
        y = l[-1].strip().lower().startswith("д") if len(l) <= 2 else l[1].strip().lower().startswith("д")
        tp += y and flag
        fp += (not y) and flag
        fn += y and not flag
        tn += (not y) and not flag
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    print(f"TP {tp} · FP {fp} · FN {fn} · TN {tn} · Precision {prec:.0%} · Recall {rec:.0%} · F1 {f1:.0%}")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


if __name__ == "__main__":
    if sys.argv[1:2] == ["--predict"]:
        predict(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ["--score"]:
        score(sys.argv[2], sys.argv[3])
    else:
        for p in sys.argv[1:]:
            print(f"== {p}")
            run(p)

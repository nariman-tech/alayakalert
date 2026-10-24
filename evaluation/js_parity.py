"""Совпадает ли браузерный движок (app/static/engine.js) с Python.

    python -m evaluation.js_parity

Прогоняет одни и те же входы через Python и через Node.js (тот же файл engine.js, что в дашборде):
нормализацию, все кейсы датасета, тексты команды, примеры, сырые расшифровки эфиров, выгрузки чатов.
Сравниваются риск, уровень, вид схемы, набор признаков, комбинации, окно чата и сообщение первого высокого риска.
"""
from __future__ import annotations

import csv
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.export_engine import engine_script  # noqa: E402
from app.payload import SAMPLES  # noqa: E402
from engine.importers import load_export  # noqa: E402
from engine.normalize import normalize  # noqa: E402
from engine.pipeline import analyze_case, analyze_chat, analyze_input, analyze_text, timeline  # noqa: E402
from evaluation.transcript_check import render  # noqa: E402

NODE = r"""
const fs = require("fs"), vm = require("vm");
const ctx = { console }; ctx.globalThis = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), ctx);
const A = ctx.AlayakEngine, jobs = JSON.parse(fs.readFileSync(process.argv[3], "utf8")), out = [];
function brief(r) { return { risk: r.risk, level: r.level, track: r.track, ids: r.signals.map(s => s.id).sort(), combos: r.combos, combos_med: r.combos_med }; }
for (const j of jobs) {
  try {
    if (j.kind === "norm") out.push(A.normalize(j.text));
    else if (j.kind === "case") { const r = A.analyzeCase(j.case); const b = brief(r); if (j.tl) b.tl = A.timeline(j.case).map(p => p.level); out.push(b); }
    else if (j.kind === "text") out.push(brief(A.analyzeText(j.text)));
    else if (j.kind === "input") { const r = A.analyzeInput(j.text, "x"); const b = brief(r); if (r.case) b.parsed = r.case.parsed; out.push(b); }
    else if (j.kind === "chat") {
      const cs = A.loadExport(j.name, j.raw); const r = A.analyzeChat(cs[0]); const b = brief(r);
      b.window = r.chat.window; b.first_high = r.chat.first_high; b.n = r.chat.messages;
      b.authors = r.chat.authors.map(a => [a.author, a.points]); out.push(b);
    }
  } catch (e) { out.push({ error: String(e && e.stack || e) }); }
}
fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""


def brief(r: dict) -> dict:
    return {"risk": r["risk"], "level": r["level"], "track": r["track"], "ids": sorted(s["id"] for s in r["signals"]),
            "combos": r["combos"], "combos_med": r["combos_med"]}


def main() -> int:
    cases = [json.loads(line) for line in (ROOT / "data" / "cases.jsonl").open(encoding="utf-8")]
    jobs, ref, labels = [], [], []

    def job(label, j, expected):
        labels.append(label); jobs.append(j); ref.append(expected)

    texts = []
    for c in cases:
        texts += [m["text"] for m in c["messages"]] + [i.get("ocr", "") for i in c.get("images", [])]
    team = []
    for f in sorted((ROOT / "data" / "team").glob("*.tsv")):
        rows = list(csv.reader(f.open(encoding="utf-8"), delimiter="\t"))[1:]
        team += [(f.name, r[0]) for r in rows if r and r[0].strip()]
    texts += [t for _, t in team] + [t for _, t in SAMPLES]
    for t in texts:
        job("нормализация: " + t[:60], {"kind": "norm", "text": t}, list(normalize(t)))
    for c in cases:
        c2 = {k: v for k, v in c.items()}
        b = brief(analyze_case(c2))
        tl = c["type"] != "post"
        if tl:
            b["tl"] = [p["level"] for p in timeline(c2)]
        job("кейс " + c["id"], {"kind": "case", "case": c2, "tl": tl}, b)
    for name, t in team:
        job(f"{name}: {t[:60]}", {"kind": "text", "text": t}, brief(analyze_text(t)))
    for label, t in SAMPLES:
        r = analyze_input(t, case_id="x")
        b = brief(r)
        if r.get("case"):
            b["parsed"] = r["case"]["parsed"]
        job("пример: " + label, {"kind": "input", "text": t}, b)
    rng = random.Random(11)
    for c in [c for c in cases if c["type"] == "stream"]:
        raw = render(c, rng)
        r = analyze_input(raw, case_id="x")
        b = brief(r)
        if r.get("case"):
            b["parsed"] = r["case"]["parsed"]
        job("расшифровка " + c["id"], {"kind": "input", "text": raw}, b)
    for f in sorted((ROOT / "data" / "samples").iterdir()):
        raw = f.read_bytes()
        r = analyze_chat(load_export(f.name, raw)[0])
        b = brief(r)
        b.update({"window": r["chat"]["window"], "first_high": r["chat"]["first_high"], "n": r["chat"]["messages"],
                  "authors": [[a["author"], a["points"]] for a in r["chat"]["authors"]]})
        job("выгрузка " + f.name, {"kind": "chat", "name": f.name, "raw": raw.decode("utf-8-sig")}, b)

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "engine.js").write_text(engine_script(), encoding="utf-8")
        (d / "run.js").write_text(NODE, encoding="utf-8")
        (d / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
        subprocess.run(["node", str(d / "run.js"), str(d / "engine.js"), str(d / "jobs.json"), str(d / "out.json")], check=True)
        got = json.loads((d / "out.json").read_text(encoding="utf-8"))

    bad = [(l, e, g) for l, e, g in zip(labels, ref, got) if json.loads(json.dumps(e, ensure_ascii=False)) != g]
    kinds = {}
    for l in labels:
        k = l.split(":")[0].split(" ")[0]
        kinds[k] = kinds.get(k, 0) + 1
    print(f"Проверено входов: {len(jobs)} ({', '.join(f'{k} {v}' for k, v in kinds.items())})")
    print(f"Расхождений: {len(bad)}")
    for l, e, g in bad[:25]:
        print("—", l)
        print("   Python:", json.dumps(e, ensure_ascii=False)[:400])
        print("   JS:    ", json.dumps(g, ensure_ascii=False)[:400])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

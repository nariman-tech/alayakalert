"""Конвейер: кейс -> предложения -> признаки -> риск -> объяснение.

Кейс (общий формат для постов, чатов и эфиров):
    {"id", "type": post|chat|stream, "platform", "account", "title",
     "messages": [{"t": сек, "author": "...", "text": "..."}],
     "images": [{"msg": i, "hash": "...", "ocr": "текст со скриншота"}],
     "bids": [...], "winners": [...], "rules": {...}}

Главные функции:
    analyze_case(case)       — один кейс;
    analyze_text(text)       — произвольный текст (для формы «проверить текст»);
    analyze_corpus(cases)    — все кейсы + граф связей + сетевые признаки;
    timeline(case)           — риск после каждого сообщения («живой эфир»).
"""
from __future__ import annotations

from collections import defaultdict

from .entities import ENTITY_LABELS, extract
from .ml import THRESHOLD, TextModel, case_text
from .normalize import match_text, sentences
from .scoring import LEGAL_HINT, TRACK_NAMES, score, summary
from .signals import CATALOG, Hit, Unit, detect_text
from .streams import analyze_bids


def build_units(case: dict, upto: int | None = None) -> list[Unit]:
    units = []
    msgs = case.get("messages", [])
    for i, m in enumerate(msgs):
        if upto is not None and i > upto:
            break
        for s in sentences(m.get("text", "")):
            units.append(Unit(i, s, match_text(s)))
    for img in case.get("images", []):
        i = img.get("msg", 0)
        if upto is not None and i > upto:
            continue
        for s in sentences(img.get("ocr", "")):
            units.append(Unit(i, "[скриншот] " + s, match_text(s)))
    return units


def _collect(case: dict, upto: int | None, extra: dict[str, Hit] | None, model: TextModel | None) -> dict[str, Hit]:
    units = build_units(case, upto)
    hits = detect_text(units)
    if case.get("bids") or case.get("winners"):
        until_t = None
        if upto is not None and case.get("messages"):
            until_t = case["messages"][min(upto, len(case["messages"]) - 1)].get("t")
        b_hits, _ = analyze_bids(case, until_t)
        for sid, h in b_hits.items():
            hits[sid] = Hit(sid, h["evidence"], h.get("note", ""))
    if model is not None and model.ready:
        p = model.prob(case_text(case, upto))
        if p >= THRESHOLD:
            hits["ML_SIMILAR"] = Hit("ML_SIMILAR", [], f"вероятность {p:.2f}")
    for sid, h in (extra or {}).items():
        hits[sid] = h
    return hits


def _result(case: dict, hits: dict[str, Hit]) -> dict:
    sc = score(set(hits))
    signals = []
    for sid, h in hits.items():
        d = CATALOG[sid]
        signals.append({"id": sid, "title": d.title, "hint": d.hint, "track": d.track, "weight": d.weight,
                        "points": d.points, "evidence": h.evidence, "note": h.note})
    signals.sort(key=lambda s: (-s["points"] if s["points"] > 0 else 1000 - s["points"]))
    res = {"id": case.get("id"), **sc, "track_name": TRACK_NAMES[sc["track"]], "signals": signals}
    res["summary"] = summary(res)
    res["legal_hint"] = LEGAL_HINT.get(sc["track"], "") if sc["level"] != "low" else ""
    return res


def analyze_case(case: dict, upto: int | None = None, extra: dict[str, Hit] | None = None,
                 model: TextModel | None = None) -> dict:
    hits = _collect(case, upto, extra, model)
    res = _result(case, hits)
    if case.get("bids") or case.get("winners"):
        _, stats = analyze_bids(case)
        res["stream"] = stats
    return res


def analyze_text(text: str, model: TextModel | None = None) -> dict:
    case = {"id": "manual", "type": "post", "messages": [{"t": 0, "author": "", "text": text}]}
    return analyze_case(case, model=model)


def timeline(case: dict, model: TextModel | None = None) -> list[dict]:
    """Риск после каждого сообщения. Сетевые признаки не используются — только то, что видно в эфире."""
    out, prev = [], set()
    for i, m in enumerate(case.get("messages", [])):
        hits = _collect(case, i, None, model)
        res = _result(case, hits)
        ids = {s["id"] for s in res["signals"]}
        out.append({"msg": i, "t": m.get("t", i), "risk": res["risk"], "level": res["level"],
                    "new": sorted(ids - prev)})
        prev = ids
    return out


def first_high(tl: list[dict]) -> int | None:
    for p in tl:
        if p["level"] == "high":
            return p["msg"]
    return None


# ── Граф связей ───────────────────────────────────────────────────────────────
NET_TYPES = {"phone", "card", "promo", "domain", "tg", "image", "winner"}


def analyze_corpus(cases: list[dict], model: TextModel | None = None, with_network: bool = True) -> tuple[list[dict], dict]:
    first = {c["id"]: analyze_case(c, model=model) for c in cases}
    by_id = {c["id"]: c for c in cases}
    ents = {c["id"]: [e for e in extract(c) if e[0] in NET_TYPES] for c in cases}

    owners: dict[tuple, set] = defaultdict(set)      # сущность -> {id кейсов}
    for cid, es in ents.items():
        for e in es:
            owners[e].add(cid)

    extra: dict[str, dict[str, Hit]] = defaultdict(dict)
    if with_network:
        for e, cids in owners.items():
            if len(cids) < 2:
                continue
            accounts = {by_id[c].get("account") for c in cids}
            label = f"{ENTITY_LABELS[e[0]]} {e[1]}"
            for cid in cids:
                others = [o for o in cids if o != cid]
                risky_others = [o for o in others if first[o]["level"] != "low"]
                gambling_ctx = any(s["track"] == 2 and s["points"] > 0 for s in first[cid]["signals"])
                if e[0] == "promo" and len(accounts) >= 3 and gambling_ctx:
                    _add(extra[cid], "NET_PROMO", f"{label} встречается у {len(accounts)} аккаунтов")
                if e[0] == "image":
                    _add(extra[cid], "NET_SCREENSHOT", f"{label} найден ещё в {len(others)} чатах")
                if risky_others and e[0] in {"phone", "card", "tg", "domain", "winner", "promo"}:
                    names = sorted({by_id[o].get("account", o) for o in risky_others})[:3]
                    _add(extra[cid], "NET_SHARED", f"{label} — также у " + ", ".join(names))

    results = [analyze_case(c, extra=extra.get(c["id"]), model=model) for c in cases]
    graph = build_graph(cases, results, ents, owners)
    return results, graph


def _add(hits: dict[str, Hit], sid: str, text: str):
    h = hits.setdefault(sid, Hit(sid))
    if len(h.evidence) < 3:
        h.evidence.append({"msg": -1, "text": text})


def build_graph(cases, results, ents, owners) -> dict:
    res = {r["id"]: r for r in results}
    acc_cases: dict[str, list] = defaultdict(list)
    for c in cases:
        acc_cases[c.get("account", c["id"])].append(c["id"])
    acc_of = {c["id"]: c.get("account", c["id"]) for c in cases}
    # в граф — только общие сущности, где хотя бы один связанный кейс помечен
    shared = {e: cids for e, cids in owners.items()
              if len({acc_of[x] for x in cids}) >= 2 and any(res[x]["level"] != "low" for x in cids)}
    nodes, links, seen = [], [], set()
    for e, cids in shared.items():
        eid = f"{e[0]}:{e[1]}"
        nodes.append({"id": eid, "label": e[1], "type": e[0], "kind": "entity", "cases": sorted(cids)})
        for cid in cids:
            acc = next(c for c in cases if c["id"] == cid).get("account", cid)
            aid = "acc:" + acc
            if aid not in seen:
                seen.add(aid)
                rs = [res[x] for x in acc_cases[acc]]
                nodes.append({"id": aid, "label": acc, "type": "account", "kind": "account",
                              "cases": acc_cases[acc], "risk": max(r["risk"] for r in rs),
                              "tracks": sorted({r["track"] for r in rs if r["track"]})})
            link = (aid, eid)
            if link not in links:
                links.append(link)
    # компоненты связности
    parent = {n["id"]: n["id"] for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        parent[find(a)] = find(b)
    comps: dict[str, list] = defaultdict(list)
    for n in nodes:
        comps[find(n["id"])].append(n)
    clusters = []
    for i, (root, ns) in enumerate(sorted(comps.items(), key=lambda kv: -len(kv[1]))):
        accs = [n for n in ns if n["kind"] == "account"]
        tracks = sorted({t for n in accs for t in n.get("tracks", [])})
        max_risk = max((n.get("risk", 0) for n in accs), default=0)
        for n in ns:
            n["cluster"] = i
        clusters.append({"id": i, "accounts": len(accs), "entities": len(ns) - len(accs), "tracks": tracks,
                         "max_risk": max_risk, "cross_track": len(tracks) >= 2,
                         "cases": sorted({c for n in accs for c in n["cases"]})})
    _layout(nodes, links)
    return {"nodes": nodes, "links": [{"source": a, "target": b} for a, b in links], "clusters": clusters}


def _layout(nodes, links):
    try:
        import networkx as nx
        g = nx.Graph()
        g.add_nodes_from(n["id"] for n in nodes)
        g.add_edges_from(links)
        pos = nx.spring_layout(g, seed=7, k=0.35, iterations=200)
        for n in nodes:
            n["x"], n["y"] = float(pos[n["id"]][0]), float(pos[n["id"]][1])
    except Exception:
        import math
        for i, n in enumerate(nodes):
            a = 2 * math.pi * i / max(1, len(nodes))
            n["x"], n["y"] = math.cos(a), math.sin(a)

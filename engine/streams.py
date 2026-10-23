"""Анализ поведения в эфирах-аукционах: ставки, победители, рост «банка».

Вход (поля кейса):
    bids:    [{"t": сек, "round": n, "user": "ник", "amount": тг}]
    winners: [{"t": сек, "round": n, "user": "ник", "prize": тг}]
    rules:   {"one_win_per_user": true, "start_prize": тг}

Признаки:
    T1_REPEAT_WINNER — один ник выиграл ≥ 2 раундов при правиле «один раз»
                       (или ≥ 3 раундов без такого правила);
    T1_SHILL         — один ник делает последнюю ставку в последние 15 сек.
                       в ≥ 50% раундов (минимум 3 раунда);
    T1_POT_RATIO     — собрано с участников в 1.5+ раза больше объявленного приза.
"""
from __future__ import annotations

from collections import Counter, defaultdict

SNIPE_WINDOW = 15  # секунд до конца раунда


def analyze_bids(case: dict, until_t: float | None = None) -> tuple[dict, dict]:
    """Возвращает (hits, stats). hits: {signal_id: {"evidence": [...], "note": str}}."""
    bids = [b for b in case.get("bids", []) if until_t is None or b["t"] <= until_t]
    winners = [w for w in case.get("winners", []) if until_t is None or w["t"] <= until_t]
    rules = case.get("rules", {})
    hits: dict[str, dict] = {}
    stats = {"total_collected": 0, "rounds": 0, "pot_series": [], "last_bidders": {}, "win_counts": {}}
    if not bids and not winners:
        return hits, stats

    total = 0
    for b in sorted(bids, key=lambda x: x["t"]):
        total += b["amount"]
        stats["pot_series"].append({"t": b["t"], "total": total})
    stats["total_collected"] = total

    by_round: dict[int, list] = defaultdict(list)
    for b in bids:
        by_round[b["round"]].append(b)
    round_end = {w["round"]: w["t"] for w in winners}
    stats["rounds"] = len(set(by_round) | set(round_end))

    # подставные ставки: кто делает последнюю ставку перед закрытием раунда
    last = Counter()
    closed_rounds = 0
    for r, bs in by_round.items():
        if r not in round_end:
            continue
        closed_rounds += 1
        lb = max(bs, key=lambda x: x["t"])
        if round_end[r] - lb["t"] <= SNIPE_WINDOW:
            last[lb["user"]] += 1
    stats["last_bidders"] = dict(last)
    if closed_rounds >= 3 and last:
        user, n = last.most_common(1)[0]
        if n / closed_rounds >= 0.5 and n >= 3:
            hits["T1_SHILL"] = {
                "evidence": [{"msg": -1, "text": f"{user}: последняя ставка за ≤{SNIPE_WINDOW} сек. до конца в {n} из {closed_rounds} раундов"}],
                "note": f"{n}/{closed_rounds} раундов",
            }

    # повторный победитель
    wins = Counter(w["user"] for w in winners)
    stats["win_counts"] = dict(wins)
    if wins:
        user, n = wins.most_common(1)[0]
        limit = 2 if rules.get("one_win_per_user") else 3
        if n >= limit:
            rule_txt = " — правила разрешают побеждать один раз" if rules.get("one_win_per_user") else ""
            hits["T1_REPEAT_WINNER"] = {
                "evidence": [{"msg": -1, "text": f"{user} выиграл {n} из {len(winners)} раундов{rule_txt}"}],
                "note": f"{n} побед из {len(winners)}",
            }

    # сборы против приза
    prize = sum(w.get("prize", 0) for w in winners) or rules.get("start_prize", 0) * max(1, len(winners))
    if prize and total / prize >= 1.5:
        hits["T1_POT_RATIO"] = {
            "evidence": [{"msg": -1, "text": f"Собрано {total:,} тг при призах {prize:,} тг".replace(",", " ")}],
            "note": f"в {total / prize:.1f} раза больше",
        }
    return hits, stats

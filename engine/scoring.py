"""Прозрачная формула риска.

1. Сумма весов сработавших признаков: высокий = 30, средний = 15, низкий = 5.
2. Ключевая комбинация признаков (см. COMBOS) поднимает риск минимум до 70.
3. Снижающие факторы (предупреждение, официальный оператор, лицензированный
   финпродукт, явно бесплатное участие) вычитаются.
4. Итог обрезается до 0–100. Уровни: 0–39 низкий, 40–69 средний, 70–100 высокий.

Система не выносит вердикт: она показывает признаки и уровень риска для ручной проверки.
"""
from __future__ import annotations

from .signals import CATALOG

FLOOR = 70
LEVELS = [(70, "high", "Высокий"), (40, "medium", "Средний"), (0, "low", "Низкий")]
TRACK_NAMES = {0: "Не определён", 1: "Трек 1 · Розыгрыши", 2: "Трек 2 · Казино", 3: "Трек 3 · Пирамиды"}

COMBOS = [
    (1, "Платное участие + случайный выбор или доход организатора",
     lambda h: "T1_PAID" in h and bool({"T1_RANDOM", "T1_ORG_INCOME"} & h)),
    (1, "Приз — это деньги других участников", lambda h: "T1_POT" in h),
    (1, "Повторный победитель + подставные ставки", lambda h: {"T1_REPEAT_WINNER", "T1_SHILL"} <= h),
    (1, "Прогрев + платное участие или «кто последний скинет»",
     lambda h: "T1_WARMUP" in h and bool({"T1_PAID", "T1_POT", "X_PAY_TO_GET"} & h)),
    (1, "«Выигрыш», за который надо заплатить",
     lambda h: "T1_PRIZE_FEE" in h and bool({"X_CARD", "T2_LINK", "T3_URGENCY", "T1_RANDOM"} & h)),
    (2, "Промокод/бонус + игровой контекст",
     lambda h: "T2_PROMO" in h and bool({"T2_NATIVE_WIN", "T2_GAMBLING", "T2_LINK", "T2_CHANNEL"} & h)),
    (2, "Легальный бренд + ссылка, промокод или «выигрыш»",
     lambda h: "T2_BRAND_COVER" in h and bool({"T2_LINK", "T2_PROMO", "T2_CHANNEL", "T2_NATIVE_WIN"} & h)),
    (2, "Зеркала + казино", lambda h: {"T2_MIRROR", "T2_GAMBLING"} <= h),
    (2, "«Выигрыш» + казино + ссылка или канал",
     lambda h: {"T2_NATIVE_WIN", "T2_GAMBLING"} <= h and bool({"T2_LINK", "T2_CHANNEL"} & h)),
    (2, "Сеть одного промокода + казино", lambda h: "NET_PROMO" in h and bool({"T2_GAMBLING", "T2_NATIVE_WIN", "T2_PROMO"} & h)),
    (3, "Нереалистичная доходность + рефералка, личная карта, гарантия или срочность",
     lambda h: "T3_RETURN" in h and bool({"T3_REFERRAL", "X_CARD", "T3_GUARANTEE", "T3_URGENCY"} & h)),
    (3, "Повтор скриншота «выплаты» + обещание дохода",
     lambda h: "NET_SCREENSHOT" in h and bool({"T3_RETURN", "T3_RETURN_MED", "T3_GUARANTEE"} & h)),
    (3, "Рефералка + личная карта + легенда, гарантия или реинвест",
     lambda h: {"T3_REFERRAL", "X_CARD"} <= h and bool({"T3_GUARANTEE", "T3_LEGEND", "T3_REINVEST"} & h)),
    (1, "Платное участие + гарантия или денежная приманка",
     lambda h: "T1_PAID" in h and bool({"T3_GUARANTEE", "T1_BAIT"} & h)),
    (1, "За «выигрыш» требуют заплатить", lambda h: "T1_PRIZE_FEE" in h),
    (2, "Гарантия выигрыша в азартной игре", lambda h: "T3_GUARANTEE" in h and "T2_GAMBLING" in h),
    (0, "Плата за вывод денег", lambda h: "X_WITHDRAW_FEE" in h),
    (0, "«Заплати — получишь больше» + нереалистичная сумма",
     lambda h: "X_PAY_TO_GET" in h and bool({"T3_RETURN", "T3_RETURN_MED", "X_CARD", "T1_BAIT"} & h)),
    (3, "Доход из денег новых участников", lambda h: "T3_NEW_MONEY" in h and bool({"T3_REFERRAL", "T3_INVEST_CALL", "T3_GUARANTEE", "T3_EASY_INCOME"} & h)),
    (3, "Обещание удвоения или высокой доходности без риска",
     lambda h: "T3_RETURN" in h and "T3_GUARANTEE" in h),
]

# Комбинации, при которых кейс стоит хотя бы проверить: риск не ниже 45 (средний).
FLOOR_MED = 45
COMBOS_MED = [
    (0, "Схема «заплати — получишь больше»", lambda h: "X_PAY_TO_GET" in h),
    (3, "Нереалистичная доходность", lambda h: "T3_RETURN" in h),
    (1, "Платное участие в розыгрыше", lambda h: "T1_PAID" in h),
    (1, "Условия розыгрыша только в личке", lambda h: "T1_HIDDEN_TERMS" in h),
    (1, "Прогрев: раздача денег зрителям и переход в канал", lambda h: "T1_WARMUP" in h),
    (3, "Обещание дохода + давление или срочность", lambda h: "T3_EASY_INCOME" in h and "T3_URGENCY" in h),
    (0, "Перевод на личную карту + гарантия или обещание дохода",
     lambda h: "X_CARD" in h and bool({"T3_GUARANTEE", "T3_EASY_INCOME", "X_PAY_TO_GET"} & h)),
    (1, "Денежная приманка + давление, личка или оплата",
     lambda h: "T1_BAIT" in h and bool({"T3_URGENCY", "T2_CHANNEL", "X_CARD", "T1_PAID", "T1_WIN_DM", "T2_LINK"} & h)),
    (1, "Личное сообщение о «выигрыше»", lambda h: "T1_WIN_DM" in h),
    (1, "Крупная денежная приманка", lambda h: {"T1_BAIT", "T1_BIG_SUM"} <= h),
    (3, "Обещание лёгкого дохода + призыв вложить, карта, рефералка или гарантия",
     lambda h: "T3_EASY_INCOME" in h and bool({"T3_INVEST_CALL", "X_CARD", "T3_REFERRAL", "T3_GUARANTEE", "T3_URGENCY"} & h)),
    (3, "Рефералка + обещание дохода",
     lambda h: "T3_REFERRAL" in h and bool({"T3_EASY_INCOME", "T3_GUARANTEE", "T3_NEW_MONEY", "T3_RETURN", "T3_RETURN_MED"} & h)),
    (3, "Доход из денег новых участников", lambda h: "T3_NEW_MONEY" in h),
    (2, "Депозит казино + обещание бонуса или выигрыша",
     lambda h: "T2_GAMBLING" in h and bool({"T2_PROMO", "T3_RETURN_MED", "T1_BAIT"} & h)),
]

LEGAL_HINT = {
    1: "Подсказка для юриста: признаки лотереи без оператора (ч. 6 ст. 445-1 КоАП РК). Требуется проверка.",
    2: "Подсказка для юриста: признаки рекламы азартных игр в интернете. Требуется проверка.",
    3: "Подсказка для юриста: признаки финансовой пирамиды. Требуется проверка АФМ.",
}


def level_of(risk: int) -> tuple[str, str]:
    for threshold, code, label in LEVELS:
        if risk >= threshold:
            return code, label
    return "low", "Низкий"


def score(hit_ids: set[str]) -> dict:
    pos = sum(CATALOG[s].points for s in hit_ids if CATALOG[s].points > 0)
    neg = sum(CATALOG[s].points for s in hit_ids if CATALOG[s].points < 0)
    combos = [(t, label) for t, label, fn in COMBOS if fn(hit_ids)]
    labels70 = {c[1] for c in combos}
    combos_med = [(t, label) for t, label, fn in COMBOS_MED if fn(hit_ids) and label not in labels70]
    base = min(100, pos)
    if combos:
        base = max(base, FLOOR)
    elif combos_med:
        base = max(base, FLOOR_MED)
    risk = max(0, min(100, base + neg))

    track_scores = {1: 0, 2: 0, 3: 0}
    for s in hit_ids:
        d = CATALOG[s]
        if d.track in track_scores and d.points > 0:
            track_scores[d.track] += d.points
    for t, _ in combos:
        if t:
            track_scores[t] += 40
    for t, _ in combos_med:
        if t:
            track_scores[t] += 20
    best = max(track_scores, key=lambda k: track_scores[k])
    track = best if track_scores[best] > 0 else 0

    code, label = level_of(risk)
    return {"risk": risk, "level": code, "level_label": label, "track": track,
            "track_scores": track_scores, "combos": [c[1] for c in combos],
            "combos_med": [c[1] for c in combos_med] if not combos else [],
            "points_positive": pos, "points_negative": neg}


def summary(result: dict) -> str:
    names = [s["title"] for s in result["signals"] if s["points"] > 0][:4]
    lvl = result["level_label"]
    if not names:
        return f"{lvl} риск ({result['risk']}). Признаков схемы не найдено."
    tail = "Требуется ручная проверка." if result["level"] != "low" else "Достаточно выборочной проверки."
    return f"{lvl} риск ({result['risk']}): " + ", ".join(n[0].lower() + n[1:] for n in names) + f". {tail}"

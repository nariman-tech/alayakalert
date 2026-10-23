"""Разбор сырой расшифровки эфира или переписки чата.

В реальности у аналитика нет таблицы ставок — есть только текст: расшифровка голоса ведущего
и сообщения из чата эфира. Этот модуль сам вытаскивает из текста:

    сообщения   время, автор, текст (поддерживаются «[12:30] @ник: текст», «@ник: текст», «12:30 текст»);
    ставки      «@aru25 +2000», «ставка от @ник — 1000 тг», «@ник закинул 2к», «@ник 500 салды»;
    победители  «победитель — @ник», «@ник забирает банк», «жеңімпаз — @ник»;
    правила     «один победитель выигрывает только один раз», «бір адам бір рет қана ұтады»;
    приз        «разыгрываем банк 180 000 тг», «бүгінгі банк — 100 000 тг».

Раунд заканчивается объявлением победителя. Если в тексте нет времени, каждой строке
даётся шаг 5 секунд — тогда «последняя ставка в последние 15 секунд» означает
«за 3 строки до объявления победителя».

Результат — обычный кейс для конвейера (pipeline.analyze_case, timeline).
"""
from __future__ import annotations

import re

from .normalize import clean

TIME = re.compile(r"^\s*\[?(\d{1,2}):(\d{2})(?::(\d{2}))?\]?\s*[-–—·|]?\s*")
AUTHOR = re.compile(r"^\s*(@?[A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі0-9_.]{2,32})\s*[:：]\s+")
HANDLE = r"@[a-z0-9_.]{2,32}"
AMOUNT = r"(\d{1,3}(?:[  ]\d{3})+|\d+(?:[.,]\d+)?)\s*(к|k|тыс\w*|тис\w*|мың|т|тг|тенге|₸)?"
AMT = r"(?P<num>\d{1,3}(?:[  ]\d{3})+|\d+(?:[.,]\d+)?)\s*(?P<unit>к|k|тыс\w*|тис\w*|мың|т|тг|тенге|₸)?"

BID_PATTERNS = [
    # «@aru25 +2000», «@aru25 +2к 🔥»
    re.compile(r"(?P<user>" + HANDLE + r")\s*[:,—–-]?\s*\+\s*" + AMT),
    # «ставка от @ник — 1000 тг», «ставка @ник 500»
    re.compile(r"ставк\w*\s+(от\s+)?(?P<user>" + HANDLE + r")\s*[—–:-]?\s*" + AMT),
    # «@ник закинул 2к», «@ник скинул 500», «@ник поставил 1000»
    re.compile(r"(?P<user>" + HANDLE + r")\s+(закинул\w*|скинул\w*|кинул\w*|поставил\w*|перевел\w*|перевёл\w*|ставит)\s+" + AMT),
    # «@ник 500 салды»
    re.compile(r"(?P<user>" + HANDLE + r")\s+" + AMT + r"\s*(салды|аударды|тастады|кинул\w*|скинул\w*)"),
    # «от @ник 1000 принято», «принято от @ник 500»
    re.compile(r"(принят\w*\s+)?от\s+(?P<user>" + HANDLE + r")\s*[—–:-]?\s*" + AMT),
]
# сообщение зрителя «+500», «кинул 1000», «ставлю 2к» — ставка от автора строки
SELF_BID = re.compile(r"^\s*(\+\s*|кинул\w*\s+|скинул\w*\s+|закинул\w*\s+|ставлю\s+|ставка\s+)" + AMOUNT + r"(\s|$|!|🔥|💸)")

WINNER = [
    re.compile(r"(победител\w*|жеңімпаз\w*|выиграл\w*|выигрывает)\s*(раунда\s*)?(\d+\s*)?[—–:-]?\s*(?P<user>" + HANDLE + r")"),
    re.compile(r"(?P<user>" + HANDLE + r")\s*[!,]?\s*(забирает|забрал\w*|выиграл\w*|победил\w*|ұтты|алды)"),
    re.compile(r"(банк|приз)\s+(забирает|уходит|достается|достаётся)\s+(?P<user>" + HANDLE + r")"),
]
ONE_WIN = re.compile(r"(только один раз|один раз и (дальше|больше) не|повторно не участв|бір рет қана|больше не участвует|дальше смотрит)")
PRIZE = re.compile(r"(банк|приз|разыгрываем|разыгрываю|бүгінгі банк|розыгрыш)\w*\s*(—|-|–|:)?\s*(банк\s*)?" + AMOUNT)
POT_MENTION = re.compile(r"(банк|касса)\s*(уже|теперь|сейчас|—|:)\s*" + AMOUNT)


def _amount(num: str, unit: str | None) -> int:
    v = float(num.replace(" ", "").replace(" ", "").replace(",", "."))
    u = (unit or "").lower()
    if u.startswith(("к", "k", "тыс", "тис", "мың")):
        v *= 1000
    return int(round(v))


def parse_transcript(raw: str, case_id: str = "uploaded", title: str = "Загруженный эфир") -> dict:
    lines = [l for l in (raw or "").splitlines() if l.strip()]
    has_time = sum(1 for l in lines if TIME.match(l)) >= max(1, len(lines) // 2)
    messages, bids, winners = [], [], []
    rules: dict = {}
    rnd, last_t = 1, 0
    pot_points = []
    for i, line in enumerate(lines):
        t = last_t + 5
        m = TIME.match(line)
        if m:
            h_or_m, mm, ss = int(m.group(1)), int(m.group(2)), m.group(3)
            t = h_or_m * 3600 + mm * 60 + int(ss) if ss else h_or_m * 60 + mm
            line = line[m.end():]
        elif has_time:
            t = last_t
        t = max(t, last_t)
        last_t = t
        author = ""
        a = AUTHOR.match(line)
        if a:
            author, line = a.group(1), line[a.end():]
        text = line.strip()
        messages.append({"t": t, "author": author, "text": text})
        low = clean(text)

        found_bid = False
        for rx in BID_PATTERNS:
            for bm in rx.finditer(low):
                amt = _amount(bm.group("num"), bm.group("unit"))
                if 50 <= amt <= 5_000_000:
                    bids.append({"t": t, "round": rnd, "user": bm.group("user"), "amount": amt})
                    found_bid = True
            if found_bid:
                break
        if not found_bid and author:
            sb = SELF_BID.match(low)
            if sb:
                amt = _amount(sb.group(2), sb.group(3))
                if 50 <= amt <= 5_000_000:
                    user = author if author.startswith("@") else "@" + author
                    bids.append({"t": t, "round": rnd, "user": user.lower(), "amount": amt})

        if ONE_WIN.search(low):
            rules["one_win_per_user"] = True
        if "start_prize" not in rules:
            pm = PRIZE.search(low)
            if pm:
                rules["start_prize"] = _amount(pm.group(4), pm.group(5))
        pmm = POT_MENTION.search(low)
        if pmm:
            pot_points.append({"t": t, "total": _amount(pmm.group(3), pmm.group(4))})

        for rx in WINNER:
            wm = rx.search(low)
            if wm:
                prize = rules.get("start_prize", 0)
                pz = re.search(r"(забирает|получает|алады)\s+" + AMOUNT, low)
                if pz:
                    prize = _amount(pz.group(2), pz.group(3))
                winners.append({"t": t, "round": rnd, "user": wm.group("user"), "prize": prize})
                rnd += 1
                break

    case = {"id": case_id, "type": "stream" if (len(bids) >= 3 or len(winners) >= 2) else ("chat" if len(messages) > 1 else "post"),
            "platform": "Эфир" if bids or winners else "Чат", "account": "@uploaded", "title": title,
            "messages": messages, "bids": bids, "winners": winners, "rules": rules, "images": [],
            "parsed": {"bids": len(bids), "winners": len(winners), "rounds": len({w["round"] for w in winners}),
                       "pot_mentions": pot_points[-5:], "has_time": has_time}}
    return case

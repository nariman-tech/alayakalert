"""Извлечение реквизитов и идентификаторов для графа связей.

Телефоны, карты (маскированные), промокоды, домены, Telegram-ники, хэши изображений.
В реальной системе хэш скриншота считается перцептивным хэшем (imagehash.phash);
в синтетике он задан в поле images[].hash.
"""
from __future__ import annotations

import re

from .normalize import clean

PHONE = re.compile(r"(?:\+?7|8)[\s\-()]*7\d{2}[\s\-()]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}")
CARD = re.compile(r"\b(4400|5169|4405|5522)[\s\-]?(\d{2})[\d*]{2}[\s\-]?[\d*]{4}[\s\-]?(\d{4})\b")
PROMO = re.compile(r"(?:промокод\w*|промо-код\w*|промик\w*|promo ?code|promocode|promokod|по коду|код)\s*[:\-–—]?\s*[«\"']?([a-z0-9_]{4,20})\b", re.I)
DOMAIN = re.compile(r"\b((?:[a-z0-9\-]+\.)+(?:com|net|org|io|kz|ru|xyz|top|bet|vip|club|site|online|win|cc|me|link|app|pro|fun|live|game|casino))\b")
HANDLE = re.compile(r"(?<![\w.])@([a-z][a-z0-9_]{4,31})", re.I)

STOP_PROMO = {"доставк", "скидк", "акци", "товар", "заказ", "подтвержден", "смс", "sms", "из", "для"}
SHORTENERS = {"bit.ly", "clck.ru", "t.ly", "tinyurl.com", "cutt.ly", "goo.su", "is.gd", "rb.gy"}
# общие сервисы, которые не связывают аккаунты между собой
BENIGN_DOMAINS = {"random.org", "instagram.com", "t.me", "youtube.com", "tiktok.com", "wa.me", "kaspi.kz",
                  "google.com", "egov.kz", "gov.kz"}


def extract(case: dict) -> list[tuple[str, str]]:
    """Список (тип, значение) уникальных сущностей кейса.

    Ники зрителей в эфирах и участников чатов не берём: один человек может смотреть
    много эфиров, это не связь организаторов. Победителей берём только из платных эфиров.
    """
    out: set[tuple[str, str]] = set()
    is_post = case.get("type", "post") == "post"
    for m in case.get("messages", []):
        raw = m.get("text", "")
        t = clean(raw)
        for p in PHONE.findall(raw):
            digits = re.sub(r"\D", "", p)
            out.add(("phone", "+7" + digits[-10:]))
        for c in CARD.finditer(raw):
            out.add(("card", f"{c.group(1)} {c.group(2)}** **** {c.group(3)}"))
        for pm in PROMO.finditer(t):
            code = pm.group(1).upper()
            if not any(s in code.lower() for s in STOP_PROMO) and re.search(r"[A-Z0-9]", code):
                out.add(("promo", code))
        for d in DOMAIN.findall(t):
            if d not in SHORTENERS and d not in BENIGN_DOMAINS:
                out.add(("domain", d))
        if is_post:
            for h in HANDLE.findall(raw):
                out.add(("tg", "@" + h.lower()))
    for img in case.get("images", []):
        if img.get("hash"):
            out.add(("image", img["hash"]))
    if case.get("bids"):
        for w in case.get("winners", []):
            out.add(("winner", w["user"]))
    return sorted(out)


ENTITY_LABELS = {"phone": "Телефон", "card": "Карта", "promo": "Промокод", "domain": "Домен",
                 "tg": "Telegram", "image": "Скриншот", "winner": "Победитель", "account": "Аккаунт"}

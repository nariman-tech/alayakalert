"""Импорт выгрузок чатов: Telegram Desktop (result.json) и WhatsApp (.txt).

Как получить выгрузку законно: участник или модератор группы делает встроенный экспорт
(Telegram Desktop → «Экспорт истории чата» → формат JSON; WhatsApp → «Экспорт чата» → «Без медиафайлов»),
например по жалобе гражданина, и передаёт файл аналитику. Система не подключается к мессенджерам сама.

Функции:
    load_export(filename, data_bytes) -> list[dict]   — кейсы формата конвейера (type = "chat")
"""
from __future__ import annotations

import json
import re
from datetime import datetime

MAX_MESSAGES = 5000

# ── Telegram ─────────────────────────────────────────────────────────────────


def _tg_text(t) -> str:
    if isinstance(t, str):
        return t
    if isinstance(t, list):
        return "".join(x if isinstance(x, str) else str(x.get("text", "")) for x in t)
    return ""


def _tg_chat(chat: dict, idx: int) -> dict | None:
    msgs, t0 = [], None
    for m in chat.get("messages", []):
        if m.get("type") != "message":
            continue
        text = _tg_text(m.get("text", "")).strip()
        if m.get("photo") or m.get("media_type") in ("photo", "video_file", "animation"):
            text = (text + " [фото]").strip() if m.get("photo") else (text + " [медиафайл]").strip()
        if not text:
            continue
        try:
            dt = datetime.fromisoformat(m["date"])
        except Exception:
            dt = None
        if dt and t0 is None:
            t0 = dt
        t = int((dt - t0).total_seconds()) if dt and t0 else len(msgs) * 60
        msgs.append({"t": t, "author": str(m.get("from") or m.get("actor") or "канал"), "text": text,
                     "date": dt.strftime("%Y-%m-%d %H:%M") if dt else ""})
        if len(msgs) >= MAX_MESSAGES:
            break
    if not msgs:
        return None
    name = chat.get("name") or f"Чат {idx + 1}"
    return {"id": f"tg-{idx + 1}", "type": "chat", "platform": "Telegram", "title": name,
            "account": _top_author(msgs), "messages": msgs, "images": [],
            "date": msgs[0]["date"][:10] if msgs[0]["date"] else "", "source": "Экспорт Telegram"}


def parse_telegram(raw: bytes) -> list[dict]:
    data = json.loads(raw.decode("utf-8-sig"))
    chats = data.get("chats", {}).get("list") if isinstance(data.get("chats"), dict) else None
    chats = chats or [data]
    out = [c for c in (_tg_chat(ch, i) for i, ch in enumerate(chats)) if c]
    return out


# ── WhatsApp ─────────────────────────────────────────────────────────────────
WA_LINE = re.compile(
    r"^‎?\[?(?P<d>\d{1,2})[./](?P<mo>\d{1,2})[./](?P<y>\d{2,4}),?\s+(?P<h>\d{1,2}):(?P<mi>\d{2})(?::(?P<s>\d{2}))?\s*(?P<ampm>[AaPp][Mm])?\]?"
    r"\s*(?:[-–—]\s*)?(?P<rest>.*)$")
WA_AUTHOR = re.compile(r"^(?P<a>[^:]{1,60}?):\s(?P<text>.*)$")
WA_MEDIA = re.compile(r"(<Без медиафайлов>|<Media omitted>|изображение отсутствует|image omitted|video omitted|<Медиа пропущено>)", re.I)


def parse_whatsapp(raw: bytes, name: str = "Чат WhatsApp") -> list[dict]:
    text = raw.decode("utf-8-sig", errors="replace")
    msgs, t0, cur = [], None, None
    for line in text.splitlines():
        m = WA_LINE.match(line)
        if m:
            rest = m.group("rest")
            a = WA_AUTHOR.match(rest)
            if not a:          # системное сообщение: «Сообщения защищены сквозным шифрованием» и т. п.
                cur = None
                continue
            y = int(m.group("y"))
            y = y + 2000 if y < 100 else y
            h = int(m.group("h")) % 12 + (12 if (m.group("ampm") or "").lower() == "pm" else 0) if m.group("ampm") else int(m.group("h"))
            try:
                dt = datetime(y, int(m.group("mo")), int(m.group("d")), h, int(m.group("mi")), int(m.group("s") or 0))
            except ValueError:
                dt = None
            if dt and t0 is None:
                t0 = dt
            body = WA_MEDIA.sub("[медиафайл]", a.group("text")).strip()
            cur = {"t": int((dt - t0).total_seconds()) if dt and t0 else len(msgs) * 60,
                   "author": a.group("a").strip().lstrip("‎"), "text": body,
                   "date": dt.strftime("%Y-%m-%d %H:%M") if dt else ""}
            msgs.append(cur)
            if len(msgs) >= MAX_MESSAGES:
                break
        elif cur is not None and line.strip():
            cur["text"] += "\n" + line.strip()
    msgs = [m for m in msgs if m["text"]]
    if not msgs:
        return []
    return [{"id": "wa-1", "type": "chat", "platform": "WhatsApp", "title": name, "account": _top_author(msgs),
             "messages": msgs, "images": [], "date": msgs[0]["date"][:10] if msgs[0]["date"] else "",
             "source": "Экспорт WhatsApp"}]


def _top_author(msgs: list[dict]) -> str:
    counts: dict[str, int] = {}
    for m in msgs:
        counts[m["author"]] = counts.get(m["author"], 0) + 1
    return max(counts, key=counts.get) if counts else ""


def load_export(filename: str, data: bytes) -> list[dict]:
    """Определяет формат по имени и содержимому."""
    head = data[:2000].decode("utf-8-sig", errors="ignore").lstrip()
    if filename.lower().endswith(".json") or head.startswith("{"):
        return parse_telegram(data)
    title = re.sub(r"\.(txt|zip)$", "", filename.split("/")[-1], flags=re.I)
    title = re.sub(r"^(WhatsApp Chat with|Чат WhatsApp с|Чат WhatsApp с )\s*", "", title).strip() or "Чат WhatsApp"
    return parse_whatsapp(data, name=title)

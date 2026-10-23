"""Нормализация текста: снимаем маскировку, которую используют мошенники.

Что умеет:
- NFKC: «красивые» шрифты (𝓴𝓪𝔃𝓲𝓷𝓸), полноширинные символы -> обычные буквы;
- удаляет невидимые символы (zero-width);
- латинские двойники в кириллических словах (кaзинo -> казино);
- цифры и символы внутри слов (к@зин0, каз1но -> казино);
- разрядку (к а з и н о, к.а.з.и.н.о -> казино);
- растянутые буквы (казиииино -> казино);
- эмодзи-заменители (🎰 -> казино);
- транслит (kazino, vlozhi, poluchi -> казино, вложи, получи).

Результат — две строки: кириллическая нормализация и «латинская» (как было, но
очищенная). Признаки ищутся в обеих.
"""
from __future__ import annotations

import re
import unicodedata

ZERO_WIDTH = re.compile("[​-‏⁠﻿­]")

CYR_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяәғқңөұүһі"
CYR_RE = re.compile(f"[{CYR_LETTERS}]")
LAT_RE = re.compile("[a-z]")

# латинские буквы, похожие на кириллические (после lower())
LOOKALIKE = {
    "a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "y": "у",
    "k": "к", "m": "м", "t": "т", "h": "н", "b": "в", "i": "и", "u": "и",
    "n": "п", "r": "г",
}
# цифры и символы внутри слов
LEET = {"0": "о", "1": "и", "3": "з", "4": "ч", "6": "б", "@": "а", "$": "с", "€": "е", "!": "и"}

EMOJI = {
    "🎰": " казино слоты ", "🎲": " казино ", "🃏": " казино ", "♠️": " казино ",
    "💰": " деньги ", "💸": " деньги ", "💵": " деньги ", "🤑": " деньги ",
    "🎁": " розыгрыш приз ", "🏆": " победитель ", "🍀": " удача ",
    "📈": " доход ", "🚀": " рост ", "💎": " ", "🔥": " ", "✅": " ", "❗": " ", "‼️": " ",
}

TRANSLIT_DIGRAPHS = [
    ("shch", "щ"), ("sch", "щ"), ("zh", "ж"), ("ch", "ч"), ("sh", "ш"), ("ya", "я"),
    ("yu", "ю"), ("yo", "ё"), ("ts", "ц"), ("kh", "х"), ("iy", "ий"), ("yy", "ый"),
]
TRANSLIT = {
    "a": "а", "b": "б", "v": "в", "g": "г", "d": "д", "e": "е", "z": "з", "i": "и",
    "y": "ы", "j": "й", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п",
    "r": "р", "s": "с", "t": "т", "u": "у", "f": "ф", "h": "х", "c": "к", "w": "в",
    "q": "к", "x": "кс",
}

SPACED_RE = re.compile(r"(?<![^\W\d_])((?:[^\W\d_][\s.\-*_·]{1,2}){3,}[^\W\d_])(?![^\W\d_])")
REPEAT_RE = re.compile(r"([^\W\d_])\1{2,}")
URLISH_RE = re.compile(r"(https?://|www\.|\.[a-z]{2,6}(/|$)|^@)", re.I)
LAT_LEET = {"0": "o", "1": "i", "3": "z", "@": "a", "$": "s", "€": "e", "!": "i"}


def _translit_word(word: str) -> str:
    out = word
    for src, dst in TRANSLIT_DIGRAPHS:
        out = out.replace(src, dst)
    return "".join(TRANSLIT.get(ch, ch) for ch in out)


def _leet_ok(tok: str, i: int) -> bool:
    """Заменять ли символ tok[i] как leet.

    Цифра — только если перед ней буква (к@зин0, каз1но), чтобы не ломать суммы
    вроде 500к или 3к. Символ (@ $ €) — если рядом есть буква. «!» — только внутри слова.
    """
    ch = tok[i]
    left = tok[i - 1] if i > 0 else ""
    right = tok[i + 1] if i + 1 < len(tok) else ""
    if ch == "!":
        return left.isalpha() and right.isalpha()
    if ch.isdigit():
        return left.isalpha()
    return left.isalpha() or right.isalpha()


def _fix_token(tok: str) -> tuple[str, str]:
    """Возвращает (кириллическая_версия, латинская_версия) токена."""
    if URLISH_RE.search(tok):
        return tok, tok  # ссылки, домены и ники не трогаем
    has_cyr = bool(CYR_RE.search(tok))
    has_lat = bool(LAT_RE.search(tok))
    if has_cyr:
        out = []
        for i, ch in enumerate(tok):
            if ch in LOOKALIKE:
                out.append(LOOKALIKE[ch])
            elif ch in LEET and _leet_ok(tok, i):
                out.append(LEET[ch])
            else:
                out.append(ch)
        return "".join(out), tok
    if has_lat:
        lat = "".join(LAT_LEET[ch] if ch in LAT_LEET and _leet_ok(tok, i) else ch
                      for i, ch in enumerate(tok))
        if len(re.sub(r"[^a-z]", "", lat)) >= 3:
            return _translit_word(lat), lat
        return tok, tok
    return tok, tok


def clean(text: str) -> str:
    """Общая очистка: NFKC, невидимые символы, эмодзи, разрядка, повторы, регистр."""
    t = unicodedata.normalize("NFKC", text or "")
    t = ZERO_WIDTH.sub("", t)
    for emo, word in EMOJI.items():
        t = t.replace(emo, word)
    t = t.lower().replace("ё", "е")
    t = SPACED_RE.sub(lambda m: re.sub(r"[\s.\-*_·]", "", m.group(1)), t)
    t = REPEAT_RE.sub(r"\1", t)
    return t


def normalize(text: str) -> tuple[str, str]:
    """Возвращает (кириллическая нормализация, латинская очищенная версия)."""
    t = clean(text)
    cyr_parts, lat_parts = [], []
    for tok in t.split():
        c, l = _fix_token(tok)
        cyr_parts.append(c)
        lat_parts.append(l)
    cyr = " ".join(cyr_parts).replace("ё", "е")
    lat = " ".join(lat_parts)
    return cyr, lat


def match_text(text: str) -> str:
    """Строка для поиска признаков: обе версии через перевод строки."""
    cyr, lat = normalize(text)
    return cyr if cyr == lat else cyr + "\n" + lat


SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


def sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENT_SPLIT.split(text or "")]
    return [p for p in parts if p]


if __name__ == "__main__":
    for s in ["к@зин0 и каз1но", "к а з и н о", "Кaзинo 🎰", "vlozhi 5000 poluchi 10000",
              "𝓴𝓪𝔃𝓲𝓷𝓸", "казииииино", "переводи на kaspi gold", "500к за 7 дней", "luckystep7.top"]:
        print(s, "->", normalize(s))

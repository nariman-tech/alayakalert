"""Калькулятор обещанной доходности: находит обещание и пересчитывает в годовые.

Примеры:
    «Вложи 5000 — через 7 дней получишь 10 000»  -> +100% за 7 дней -> > 1 000 000% годовых
    «30% в месяц»                                 -> ≈ 2 300% годовых
    «Депозит 14% годовых»                         -> 14% годовых (не подозрительно)

Порог системы: свыше 50% годовых — нереалистично (высокий вес), 25–50% — средний.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

NUM = r"(\d{1,3}(?:[  ]\d{3})+|\d+(?:[.,]\d+)?)\s*(к\b|k\b|тыс\w*|тис\w*|мың|млн|миллион\w*)?"
CUR = r"\s*(?:тг|тенге|₸|т\b)?"

PERIODS = [
    (re.compile(r"^(час|сағат)"), 1 / 24),
    (re.compile(r"^(дн|день|дня|дней|сут|күн)"), 1.0),
    (re.compile(r"^(недел|апта)"), 7.0),
    (re.compile(r"^(месяц|мес|ай)"), 30.0),
    (re.compile(r"^(год|жыл|лет)"), 365.0),
]
PERIOD_WORD = r"(час\w*|сағат\w*|день|дня|дней|дн\w*|сутки|суток|күн\w*|недел\w*|апта\w*|месяц\w*|мес\b|ай\w*|год\w*|жыл\w*)"

# «30% в месяц», «3% ежедневно», «10% за 5 дней»
PCT_PERIOD = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*%\s*(?:в|за|каждый|каждую|каждые|/|per|в течение)?\s*(\d+)?\s*" + PERIOD_WORD)
# «ежедневно 3%», «в месяц 30%», «айына 30%»
PERIOD_PCT = re.compile(
    r"(ежедневно|каждый день|в день|в сутки|күн сайын|күніне|еженедельно|в неделю|аптасына|"
    r"ежемесячно|в месяц|каждый месяц|ай сайын|айына|в год|жылына)\D{0,15}?(\d+(?:[.,]\d+)?)\s*%")
# «вложи 5000 ... получи 10000»
INVEST_GET = re.compile(
    r"(влож\w*|инвестир\w*|вкладыва\w*|внес\w*|салсаң\w*|салыңыз|салып|отправ\w*|скин\w*|переведи\w*|переводи\w*|заплат\w*|оплат\w*|переводт\w*)"
    r"\D{0,25}?" + NUM + CUR + r"[^\n]{0,40}?"
    r"(получ\w*|забер\w*|забира\w*|вывед\w*|вывод\w*|верн\w*|аласыз|аласың|аласыңыз|алып|қайтар\w*)\D{0,15}?" + NUM)
# «5000 тг салсаңыз, 10 000 тг аласыз» (казахский порядок слов)
INVEST_GET_KZ = re.compile(
    NUM + CUR + r"\D{0,10}(салсаң\w*|салыңыз|салып|салады|салу|влож\w*)[^\n]{0,40}?" + NUM + CUR + r"\D{0,10}(аласыз|аласың\w*|алыңыз|получ\w*|қайтар\w*)")
# «x2 за неделю», «удвоим», «екі есе»
MULT = re.compile(r"(?<![\w.])(?:x|х|×)\s?(\d+(?:[.,]\d+)?)(?![\w.])|(удво\w*|в два раза|екі есе)|(утро(?:ит|им|ят|ени|енн|ишь|ю)\w*|в три раза|үш есе)")
PERIOD_NEAR = re.compile(r"(?:через|за|в течение|спустя|кейін|ішінде)?\s*(\d+)?\s*" + PERIOD_WORD)

EXCLUDE_CTX = re.compile(r"(скидк|кэшб|кешб|cashback|налог|инфляц|кредит|комисси|рассрочк|уценк|процент\w* по займ"
                         r"|вырос|выросл|упал|подорож|подешев|снизил|курс\w*|индекс|рост цен|подешевел)")


@dataclass
class ReturnFinding:
    snippet: str
    ratio: float            # прибыль за период, 1.0 = +100%
    period_days: float | None
    annual_pct: float | None  # годовые, % (может быть inf)

    @property
    def level(self) -> str:
        if self.annual_pct is None:
            return "high" if self.ratio >= 1.0 else ("medium" if self.ratio >= 0.3 else "none")
        if self.annual_pct > 50:
            return "high"
        if self.annual_pct > 25:
            return "medium"
        return "none"

    def describe(self) -> str:
        gain = f"+{self.ratio * 100:.0f}%"
        if self.period_days is None:
            return f"обещано {gain} без указания срока"
        per = _period_label(self.period_days)
        if self.annual_pct is None or math.isinf(self.annual_pct) or self.annual_pct > 1e6:
            ann = "более 1 000 000% годовых"
        else:
            ann = f"≈ {self.annual_pct:,.0f}% годовых".replace(",", " ")
        return f"обещано {gain} {per} → {ann}"


def _period_label(days: float) -> str:
    if days < 1:
        return f"за {days * 24:.0f} ч"
    if days == 1:
        return "в день"
    if days == 7:
        return "в неделю"
    if days == 30:
        return "в месяц"
    if days == 365:
        return "в год"
    return f"за {days:.0f} дн."


def _amount(num: str, mult: str | None) -> float:
    v = float(num.replace(" ", "").replace(" ", "").replace(",", "."))
    if mult:
        m = mult.lower()
        if m.startswith(("к", "k", "тыс", "тис", "мың")):
            v *= 1_000
        elif m.startswith(("млн", "миллион")):
            v *= 1_000_000
    return v


def _period_days(word: str | None, count: str | None) -> float | None:
    if not word:
        return None
    for rx, days in PERIODS:
        if rx.match(word):
            n = float(count) if count else 1.0
            return days * n
    return None


def annualize(ratio: float, days: float | None) -> float | None:
    if days is None or days <= 0:
        return None
    exp = (365.0 / days) * math.log1p(ratio)
    if exp > math.log(1e7):
        return math.inf
    return (math.exp(exp) - 1) * 100


def find_returns(text: str) -> list[ReturnFinding]:
    """text — уже нормализованная строка (lower, кириллица)."""
    out: list[ReturnFinding] = []
    for m in PCT_PERIOD.finditer(text):
        ctx = text[max(0, m.start() - 40): m.start()]
        if EXCLUDE_CTX.search(ctx) or re.search(r"годов", text[m.end(): m.end() + 10]):
            continue
        pct = float(m.group(1).replace(",", "."))
        days = _period_days(m.group(3), m.group(2))
        if days is None or days >= 365 and pct < 100:
            if days == 365:
                out.append(ReturnFinding(m.group(0), pct / 100, 365, pct))
            continue
        out.append(ReturnFinding(m.group(0), pct / 100, days, annualize(pct / 100, days)))
    for m in PERIOD_PCT.finditer(text):
        ctx = text[max(0, m.start() - 40): m.start()]
        if EXCLUDE_CTX.search(ctx) or re.search(r"годов", text[m.end(): m.end() + 10]):
            continue
        word = m.group(1)
        days = 1.0 if re.search(r"(дн|ден|сут|күн)", word) else 7.0 if re.search(r"(недел|апта)", word) \
            else 365.0 if re.search(r"(год|жыл)", word) else 30.0
        pct = float(m.group(2).replace(",", "."))
        out.append(ReturnFinding(m.group(0), pct / 100, days, annualize(pct / 100, days)))
    for rx, a_in, a_out in ((INVEST_GET, (2, 3), (5, 6)), (INVEST_GET_KZ, (1, 2), (4, 5))):
        for m in rx.finditer(text):
            v_in = _amount(m.group(a_in[0]), m.group(a_in[1]))
            v_out = _amount(m.group(a_out[0]), m.group(a_out[1]))
            if v_in <= 0 or v_out <= v_in:
                continue
            tail = text[m.end(): m.end() + 40]
            head = text[max(0, m.start() - 10): m.start()]
            pm = PERIOD_NEAR.search(m.group(0) + " " + tail)
            days = _period_days(pm.group(2), pm.group(1)) if pm else None
            ratio = v_out / v_in - 1
            out.append(ReturnFinding((head + m.group(0) + tail).strip()[:120], ratio, days, annualize(ratio, days)))
    for m in MULT.finditer(text):
        if m.group(1):
            k = float(m.group(1).replace(",", "."))
            if k <= 1 or k > 1000:
                continue
        else:
            k = 2.0 if m.group(2) else 3.0
        ctx = text[max(0, m.start() - 50): m.end() + 50]
        if not re.search(r"(влож|вклад|инвест|депозит|сумм|деньг|ақша|салым|доход|прибыл|табыс|пайда|вывод|выплат|сал)", ctx):
            continue
        pm = PERIOD_NEAR.search(text[m.end(): m.end() + 40])
        days = _period_days(pm.group(2), pm.group(1)) if pm else None
        out.append(ReturnFinding(ctx.strip()[:120], k - 1, days, annualize(k - 1, days)))
    # убираем дубли по одному и тому же обещанию
    uniq, seen = [], set()
    for f in out:
        key = (round(f.ratio, 3), f.period_days)
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return uniq


if __name__ == "__main__":
    from engine.normalize import normalize
    tests = [
        "Вложи 5000 тг — через 7 дней получишь 10 000 тг!",
        "Доход 30% в месяц, выплаты каждую неделю",
        "Депозит «Накопительный» — 14% годовых, гарантия КФГД",
        "Ежедневно 3% от суммы вклада",
        "5 000 тг салсаңыз, 10 000 тг аласыз",
        "x2 к вложению за 10 дней",
        "Скидка 30% в месяц на всё",
        "vlozhi 5k poluchi 15k za nedelyu",
        "айына 25% пайда",
    ]
    for t in tests:
        found = find_returns(normalize(t)[0])
        print(t, "->", [f.describe() + f" [{f.level}]" for f in found])

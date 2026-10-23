"""Разбор сырой расшифровки эфира и история аккаунта. Запуск: python -m unittest discover tests"""
import unittest

from engine.pipeline import analyze_case, analyze_corpus, analyze_input
from engine.transcript import parse_transcript

RAW = """[0:00] @host: разыгрываем банк 50 000 тг, кто последний закинет — тот забирает весь банк
[0:10] @host: один победитель выигрывает только один раз
[0:20] @a1: +500
[0:30] @shill: +2000
[0:36] @host: Победитель — @boss!
[0:50] @a2: кинул 1000
[1:00] @shill: ставлю 3к
[1:06] @host: Победитель — @boss!
[1:20] @host: ставка от @a3 — 1 000 тг
[1:30] @shill: +2000
[1:36] @host: Победитель раунда — @boss, забирает 50 000 тг"""


class Transcript(unittest.TestCase):
    def test_parse(self):
        c = parse_transcript(RAW)
        self.assertEqual(c["type"], "stream")
        self.assertEqual(c["parsed"]["bids"], 6)
        self.assertEqual(c["parsed"]["winners"], 3)
        self.assertTrue(c["rules"].get("one_win_per_user"))
        self.assertEqual(c["rules"].get("start_prize"), 50000)
        self.assertIn({"t": 60, "round": 2, "user": "@shill", "amount": 3000}, c["bids"])

    def test_signals(self):
        r = analyze_case(parse_transcript(RAW))
        ids = {s["id"] for s in r["signals"]}
        self.assertTrue({"T1_SHILL", "T1_REPEAT_WINNER", "T1_POT"} <= ids)
        self.assertEqual(r["level"], "high")

    def test_input_routing(self):
        self.assertIn("case", analyze_input(RAW))
        self.assertNotIn("case", analyze_input("Подпишись и отметь друга, участие бесплатное"))

    def test_charity_auction_low(self):
        raw = """[0:00] @fund: Благотворительный аукцион картин, средства идут на счёт фонда
[1:00] @a: предлагаю 25 000 за лот 1
[2:00] @fund: Лот 1 продан @a, спасибо за помощь фонду"""
        self.assertEqual(analyze_input(raw)["level"], "low")


class AccountHistory(unittest.TestCase):
    def test_funnel(self):
        acc = "@test_acc"
        cases = [
            {"id": "f1", "type": "post", "account": acc, "date": "2026-09-01",
             "messages": [{"t": 0, "text": "Бесплатный розыгрыш наушников, участие бесплатное, рандомайзер"}]},
            {"id": "p1", "type": "post", "account": acc, "date": "2026-10-01",
             "messages": [{"t": 0, "text": "Розыгрыш iPhone, участие 2 000 тг на каспи, крутим колесо"}]},
        ]
        res, _ = analyze_corpus(cases)
        by = {r["id"]: r for r in res}
        self.assertIn("T1_FUNNEL", {s["id"] for s in by["p1"]["signals"]})
        self.assertEqual(by["f1"]["level"], "low")



class Warmup(unittest.TestCase):
    def test_observed_warmup(self):
        from pathlib import Path
        raw = (Path(__file__).resolve().parents[1] / "data" / "team" / "observed_warmup_anonymized.txt").read_text(encoding="utf-8")
        r = analyze_input(raw)
        ids = {s["id"] for s in r["signals"]}
        self.assertIn("T1_WARMUP", ids)
        self.assertNotIn("X_CARD", ids)  # автор переводит сам — это не просьба о деньгах
        self.assertEqual(r["level"], "medium")

    def test_outgoing_is_not_request(self):
        from engine.pipeline import analyze_text
        self.assertNotIn("X_CARD", {s["id"] for s in analyze_text("Перевожу на номер +7 700 000 11 04, держи на учёбу")["signals"]})
        self.assertIn("X_CARD", {s["id"] for s in analyze_text("Переводите на номер +7 700 000 11 04 за участие")["signals"]})


if __name__ == "__main__":
    unittest.main()

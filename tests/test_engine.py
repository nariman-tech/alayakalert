"""Базовые тесты движка. Запуск: python -m unittest discover tests"""
import unittest

from engine.normalize import normalize
from engine.pipeline import analyze_case, analyze_text
from engine.returns import find_returns


def ids(r):
    return {s["id"] for s in r["signals"]}


class Normalize(unittest.TestCase):
    def test_masking(self):
        for s in ["к@зин0", "к а з и н о", "kazino", "казииино", "кaзинo"]:
            self.assertIn("казино", normalize(s)[0], s)

    def test_amounts_not_broken(self):
        self.assertIn("500к", normalize("500к за 7 дней")[0])
        self.assertIn("3к", normalize("3к за участие")[0])


class Returns(unittest.TestCase):
    def annual(self, text):
        f = find_returns(normalize(text)[0])
        return f[0] if f else None

    def test_month(self):
        f = self.annual("доход 30% в месяц")
        self.assertEqual(f.level, "high")
        self.assertGreater(f.annual_pct, 2000)

    def test_invest_get(self):
        self.assertEqual(self.annual("Вложи 5000 тг — через 7 дней получишь 10 000").level, "high")

    def test_kazakh_order(self):
        self.assertEqual(self.annual("5000 тг салсаңыз, 7 күннен кейін 10 000 тг аласыз").level, "high")

    def test_deposit_ok(self):
        self.assertEqual(self.annual("депозит 14% годовых").level, "none")

    def test_discount_ignored(self):
        self.assertIsNone(self.annual("скидка 30% в месяц"))


class Signals(unittest.TestCase):
    def test_course_giveaway(self):
        r = analyze_text("Розыгрыш iPhone! Условие участия: купи мой курс за 29 990 тг. Победителя выберем колесом фортуны.")
        self.assertEqual(r["level"], "high")
        self.assertIn("T1_PAID", ids(r))

    def test_free_giveaway(self):
        r = analyze_text("Розыгрыш наушников! Подпишись и отметь 2 друзей, участие бесплатное, итоги рандомайзером.")
        self.assertEqual(r["level"], "low")

    def test_casino_masked(self):
        r = analyze_text("Поднял 480к на сл0тах 🎰 промокод GOLD2X, +200% к депозиту")
        self.assertEqual(r["level"], "high")
        self.assertEqual(r["track"], 2)

    def test_warning_news(self):
        r = analyze_text("АФМ предупреждает: мошенники обещают вложи 5000 получи 10000. Не переводите деньги!")
        self.assertEqual(r["level"], "low")

    def test_pyramid(self):
        r = analyze_text("Вложи 10к — через 5 дней заберёшь 25к, переводи на каспи голд, пригласи друга +10%")
        self.assertEqual(r["level"], "high")
        self.assertEqual(r["track"], 3)


class ShortMessages(unittest.TestCase):
    """Короткие сообщения из учебного набора команды (набор 1)."""

    def test_flagged(self):
        for t in ["zaplaty 17 tis tg 💰 i poluchi 200 tys 🎁", "Бонус 🎁 уже ждёт тебя, подробности в личке 👀",
                  "Переводты жаса 💸 сосын 200к аласың 🎁", "Вам начислен приз, но сначала нужно оплатить его оформление",
                  "Құттықтаймыз 🎉 сізге сыйлық бұйырды 🎁", "Инвестиция 📈 сал да, күн сайын пайда ал 💰"]:
            self.assertNotEqual(analyze_text(t)["level"], "low", t)

    def test_honest(self):
        for t in ["💸 На экскурсию собираем по 1500 тг, чек отправьте в группу",
                  "Ребят, на выпускной собираем по 2000 тг, список расходов закрепила",
                  "Предупреждение о проекте, который обещает доход только за привлечение людей"]:
            self.assertEqual(analyze_text(t)["level"], "low", t)


class Streams(unittest.TestCase):
    def test_shill_and_repeat_winner(self):
        bids, winners = [], []
        for r in range(1, 5):
            base = r * 1000
            bids += [{"t": base + 10, "round": r, "user": "@a", "amount": 500},
                     {"t": base + 50, "round": r, "user": "@shill", "amount": 2000}]
            winners.append({"t": base + 58, "round": r, "user": "@star" if r > 1 else "@x", "prize": 1000})
        case = {"id": "s", "type": "stream", "messages": [{"t": 0, "text": "Кто последний скинет — забирает весь банк!"}],
                "bids": bids, "winners": winners, "rules": {"one_win_per_user": True, "start_prize": 1000}}
        r = analyze_case(case)
        self.assertTrue({"T1_SHILL", "T1_REPEAT_WINNER", "T1_POT"} <= ids(r))
        self.assertEqual(r["level"], "high")


if __name__ == "__main__":
    unittest.main()

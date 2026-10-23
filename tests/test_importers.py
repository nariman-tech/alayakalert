"""Проверки импорта выгрузок Telegram/WhatsApp и разбора длинных чатов."""
import json
import unittest
from pathlib import Path

from engine.importers import load_export, parse_telegram, parse_whatsapp
from engine.pipeline import analyze_chat, build_units
from engine.signals import detect_text

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


class TelegramImport(unittest.TestCase):
    def test_single_chat_and_rich_text(self):
        raw = json.dumps({"name": "Тест", "type": "private_group", "messages": [
            {"id": 1, "type": "message", "date": "2026-10-01T10:00:00", "from": "А", "text": "привет"},
            {"id": 2, "type": "service", "date": "2026-10-01T10:01:00", "actor": "А", "action": "invite_members"},
            {"id": 3, "type": "message", "date": "2026-10-01T10:02:00", "from": "Б",
             "text": [{"type": "plain", "text": "переводи на "}, {"type": "bold", "text": "каспи"}]},
            {"id": 4, "type": "message", "date": "2026-10-01T10:03:00", "from": "Б", "text": "", "photo": "p.jpg"},
        ]}, ensure_ascii=False).encode()
        cases = parse_telegram(raw)
        self.assertEqual(len(cases), 1)
        texts = [m["text"] for m in cases[0]["messages"]]
        self.assertEqual(len(texts), 3)              # служебное сообщение пропущено
        self.assertIn("переводи на каспи", texts[1])  # куски форматированного текста склеены
        self.assertIn("[фото]", texts[2])

    def test_full_export_with_many_chats(self):
        chat = {"name": "X", "type": "private_group",
                "messages": [{"id": 1, "type": "message", "date": "2026-10-01T10:00:00", "from": "А", "text": "ок"}]}
        raw = json.dumps({"chats": {"list": [chat, dict(chat, name="Y")]}}).encode()
        self.assertEqual(len(parse_telegram(raw)), 2)


class WhatsAppImport(unittest.TestCase):
    def test_android_ios_and_continuations(self):
        raw = ("10.10.2026, 19:00 - Сообщения и звонки защищены сквозным шифрованием.\n"
               "10.10.2026, 19:02 - Асель: Ережелер:\n"
               "1) әр адам 10 000 тг салады\n"
               "[11.10.26, 9:15:03] Жанар: доброе утро\n"
               "10/12/26, 9:05 PM - Марат: <Без медиафайлов>\n").encode()
        msgs = parse_whatsapp(raw)[0]["messages"]
        self.assertEqual([m["author"] for m in msgs], ["Асель", "Жанар", "Марат"])
        self.assertIn("10 000 тг салады", msgs[0]["text"])   # строка-продолжение приклеена
        self.assertEqual(msgs[2]["text"], "[медиафайл]")

    def test_unknown_file(self):
        self.assertEqual(load_export("x.txt", "просто текст без дат".encode()), [])


class ChatAnalysis(unittest.TestCase):
    def _load(self, name):
        p = SAMPLES / name
        return load_export(p.name, p.read_bytes())[0]

    def test_scheme_found_after_chit_chat(self):
        r = analyze_chat(self._load("telegram_export_sample.json"))
        self.assertEqual(r["level"], "high")
        self.assertGreater(r["chat"]["first_high"], 39)        # не раньше начала схемы
        self.assertEqual(r["chat"]["authors"][0]["author"], "Айгуль Береке")

    def test_whatsapp_kassa(self):
        self.assertEqual(analyze_chat(self._load("whatsapp_sample.txt"))["level"], "high")

    def test_honest_long_chat_stays_low(self):
        r = analyze_chat(self._load("whatsapp_honest_sample.txt"))
        self.assertEqual(r["level"], "low")
        self.assertIsNone(r["chat"]["first_high"])

    def test_local_context(self):
        # слово «розыгрыш» в одном сообщении не превращает чужой сбор денег в лотерею
        case = {"messages": [{"text": "в магазине бесплатный розыгрыш рюкзака"},
                             {"text": "скиньте по 2000 на подарок учительнице"}]}
        ids = set(detect_text(build_units(case), local=True))
        self.assertNotIn("T1_PAID", ids)
        self.assertNotIn("T1_ORG_INCOME", ids)

    def test_question_is_not_denial(self):
        ids = set(detect_text(build_units({"messages": [{"text": "А это не пирамида?"}]}), local=True))
        self.assertNotIn("T3_DENIAL", ids)


if __name__ == "__main__":
    unittest.main()

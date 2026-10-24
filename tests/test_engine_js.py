"""Браузерный движок даёт те же результаты, что Python (нужен Node.js, иначе проверка пропускается)."""
import shutil
import unittest

from evaluation import js_parity


@unittest.skipUnless(shutil.which("node"), "нет Node.js")
class JsParity(unittest.TestCase):
    def test_same_results(self):
        self.assertEqual(js_parity.main(), 0)


if __name__ == "__main__":
    unittest.main()

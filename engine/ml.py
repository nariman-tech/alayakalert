"""Необязательная ML-модель: TF-IDF по символьным n-граммам + логистическая регрессия.

Даёт один признак средней силы ML_SIMILAR («похоже на известные схемы»), но не решает
сама: решение остаётся за прозрачной формулой. Если scikit-learn не установлен,
движок работает без неё.
"""
from __future__ import annotations

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    HAVE_SKLEARN = True
except Exception:  # pragma: no cover
    HAVE_SKLEARN = False

from .normalize import normalize

THRESHOLD = 0.8


def case_text(case: dict, upto: int | None = None) -> str:
    msgs = case.get("messages", [])
    if upto is not None:
        msgs = msgs[: upto + 1]
    parts = [normalize(m.get("text", ""))[0] for m in msgs]
    parts += [normalize(i.get("ocr", ""))[0] for i in case.get("images", [])
              if upto is None or i.get("msg", 0) <= upto]
    return "\n".join(parts)


class TextModel:
    def __init__(self):
        self.model = None

    @property
    def ready(self) -> bool:
        return self.model is not None

    def fit(self, cases: list[dict]) -> "TextModel":
        if not HAVE_SKLEARN:
            return self
        texts = [case_text(c) for c in cases]
        labels = [int(c["label"]) for c in cases]
        if len(set(labels)) < 2:
            return self
        self.model = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True),
            LogisticRegression(C=2.0, max_iter=3000, class_weight="balanced"),
        )
        self.model.fit(texts, labels)
        return self

    def prob(self, text: str) -> float:
        if not self.ready:
            return 0.0
        return float(self.model.predict_proba([text])[0][1])

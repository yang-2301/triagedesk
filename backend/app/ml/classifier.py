"""Multinomial Naive Bayes classifier — pure Python, no sklearn.

Deliberately dependency-free so the repo runs anywhere. On this task
(5-class ticket triage over short texts) a bigram-augmented NB is a
honest, explainable baseline; an LLM triager can be plugged in behind
the same interface (see services/triage.py).
"""
import math
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Set, Tuple

TOKEN_RE = re.compile(r"[a-z0-9']+")
STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "it", "this", "that", "i",
    "my", "we", "our", "you", "your", "at", "as", "by", "from", "but",
    "not", "can", "will", "would", "should", "have", "has", "had", "do",
    "does", "did", "so", "if", "when", "then", "there", "please",
}


def tokenize(text: str) -> List[str]:
    words = [w for w in TOKEN_RE.findall(text.lower()) if w not in STOPWORDS]
    bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:])]
    return words + bigrams


class NaiveBayesClassifier:
    """Multinomial NB with Laplace smoothing and prior weighting."""

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.classes: List[str] = []
        self.class_doc_counts: Counter = Counter()
        self.word_counts: Dict[str, Counter] = defaultdict(Counter)
        self.class_token_totals: Counter = Counter()
        self.vocab: Set[str] = set()

    def fit(self, samples: Iterable[Tuple[str, str]]) -> "NaiveBayesClassifier":
        for label, text in samples:
            self.classes.append(label) if label not in self.classes else None
            self.class_doc_counts[label] += 1
            for tok in tokenize(text):
                self.word_counts[label][tok] += 1
                self.class_token_totals[label] += 1
                self.vocab.add(tok)
        return self

    def predict(self, text: str) -> Tuple[str, float]:
        scores: Dict[str, float] = {}
        vocab_size = len(self.vocab)
        total_docs = sum(self.class_doc_counts.values())
        tokens = tokenize(text)

        for cls in self.classes:
            log_p = math.log(self.class_doc_counts[cls] / total_docs)
            denom = self.class_token_totals[cls] + self.alpha * vocab_size
            for tok in tokens:
                count = self.word_counts[cls].get(tok, 0)
                log_p += math.log((count + self.alpha) / denom)
            scores[cls] = log_p

        # Softmax over per-token-normalised log-probs. Dividing by token
        # count keeps confidence from saturating at 1.00 on long inputs —
        # it stays sensitive to how *distinctive* the evidence is.
        n = max(len(tokens), 1)
        best = max(scores.values())
        exps = {c: math.exp((v - best) / n) for c, v in scores.items()}
        total = sum(exps.values())
        probs = {c: e / total for c, e in exps.items()}
        label = max(probs, key=probs.get)
        return label, probs[label]

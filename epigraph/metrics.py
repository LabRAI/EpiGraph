import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Sequence


def accuracy(pred: Sequence[str], gold: Sequence[str]) -> float:
    n = max(len(gold), 1)
    return sum(str(p).strip() == str(g).strip() for p, g in zip(pred, gold)) / n


def top_k_accuracy(pred_ranked: Sequence[Sequence[str]], gold: Sequence[str], k: int = 1) -> float:
    n = max(len(gold), 1)
    hits = 0
    for ranked, label in zip(pred_ranked, gold):
        hits += str(label).strip() in [str(x).strip() for x in ranked[:k]]
    return hits / n


def token_f1(prediction: str, reference: str) -> float:
    p = _tokens(prediction)
    r = _tokens(reference)
    if not p or not r:
        return 0.0
    overlap = Counter(p) & Counter(r)
    common = sum(overlap.values())
    if common == 0:
        return 0.0
    precision = common / len(p)
    recall = common / len(r)
    return 2 * precision * recall / (precision + recall)


def bleu1(prediction: str, reference: str) -> float:
    p = _tokens(prediction)
    r = Counter(_tokens(reference))
    if not p or not r:
        return 0.0
    return sum(min(Counter(p)[tok], r[tok]) for tok in set(p)) / len(p)


def rouge_l(prediction: str, reference: str) -> float:
    p = _tokens(prediction)
    r = _tokens(reference)
    if not p or not r:
        return 0.0
    lcs = _lcs_len(p, r)
    prec = lcs / len(p)
    rec = lcs / len(r)
    return 0.0 if prec + rec == 0 else (2 * prec * rec) / (prec + rec)


def recall_at_k(pred: List[str], gold: List[str], k: int) -> float:
    return len(set(pred[:k]) & set(gold)) / max(len(set(gold)), 1)


def mrr_at_k(pred: List[str], gold: List[str], k: int) -> float:
    gold_set = set(gold)
    for idx, item in enumerate(pred[:k], 1):
        if item in gold_set:
            return 1.0 / idx
    return 0.0


def ndcg_at_k(pred: List[str], gold: List[str], k: int) -> float:
    gold_set = set(gold)
    dcg = 0.0
    for idx, item in enumerate(pred[:k], 1):
        dcg += (1.0 if item in gold_set else 0.0) / math.log2(idx + 1)
    ideal = min(len(gold_set), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal + 1))
    return dcg / idcg if idcg else 0.0


def drug_safety_score(selected: str, contraindicated: Iterable[str]) -> float:
    selected_norm = selected.lower()
    bad = [x.lower() for x in contraindicated]
    return 0.0 if any(x and x in selected_norm for x in bad) else 1.0


def kg_evidence_coverage(answer: str, retrieved_paths: Iterable[str]) -> float:
    answer_tokens = set(_tokens(answer))
    if not answer_tokens:
        return 0.0
    evidence_tokens = set(_tokens(" ".join(retrieved_paths)))
    return len(answer_tokens & evidence_tokens) / len(answer_tokens)


def summarize_scores(rows: List[Dict[str, float]], fields: List[str]) -> Dict[str, float]:
    return {field: sum(float(r.get(field, 0.0)) for r in rows) / max(len(rows), 1) for field in fields}


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _lcs_len(a: List[str], b: List[str]) -> int:
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[-1]))
        prev = cur
    return prev[-1]


"""Evaluation describes the labeled sample, not population-wide recall."""
from review_analyzer.validation.batches import RELEVANT


def evaluate(batch, judgments, threshold, split="evaluation"):
    """Keep threshold selection separate from held-out evaluation reviews."""
    if not 0 < threshold <= 1 or split not in ("calibration", "evaluation"):
        raise ValueError("Invalid evaluation threshold or split")
    counts = dict(tp=0, fp=0, fn=0, tn=0)
    eligible = labeled = 0
    for item in batch["items"]:
        if item["split"] != split:
            continue
        eligible += 1
        judgment = judgments.get((item["snapshot_id"], item["change_id"]), {})
        label = judgment.get("validation")
        if label not in RELEVANT | {"unrelated"}:
            continue
        labeled += 1
        predicted, actual = item["similarity"] >= threshold, label in RELEVANT
        counts[("tp" if actual else "fp") if predicted else ("fn" if actual else "tn")] += 1
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {"split": split, "threshold": threshold, "eligible": eligible, "labeled": labeled,
            "excluded_unlabeled_uncertain_or_disputed": eligible - labeled,
            **counts, "precision": precision, "recall": recall, "f1": f1,
            "scope": "Stratified labeled sample only; not an estimate of population recall."}

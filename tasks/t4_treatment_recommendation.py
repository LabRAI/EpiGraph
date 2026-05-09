import argparse

from datasets import load_dataset
from tqdm import tqdm

from epigraph.common import ChatClient, option_letter, read_json, stable_id, write_json
from epigraph.metrics import accuracy, drug_safety_score, kg_evidence_coverage
from epigraph.retrieval import EpiGraphRetriever


SYSTEM = """You are a clinical epilepsy specialist.
Select the safest guideline-consistent treatment option from A-D. Consider contraindications, patient context,
and epilepsy-specific evidence. Return only the option letter."""

EPILEPSY_TERMS = [
    "epilepsy",
    "seizure",
    "status epilepticus",
    "antiseizure",
    "antiepileptic",
    "dravet",
    "lennox",
    "eeg",
    "valproate",
    "carbamazepine",
    "lamotrigine",
]


def build_medqa_subset(out: str, max_items: int = 200) -> None:
    ds = load_dataset("GBaker/MedQA-USMLE-4-options", split="test")
    rows = []
    for item in ds:
        text = f"{item.get('question', '')} {' '.join(item.get('options', []))}".lower()
        if not any(term in text for term in EPILEPSY_TERMS):
            continue
        rows.append(
            {
                "id": stable_id(item["question"], prefix="t4"),
                "source": "MedQA-USMLE",
                "question": item["question"],
                "options": item["options"],
                "correct_answer": item["answer_idx"],
                "answer": item.get("answer", ""),
                "contraindicated": [],
            }
        )
        if len(rows) >= max_items:
            break
    write_json(rows, out)


def evaluate(args: argparse.Namespace) -> None:
    data = read_json(args.dataset)
    retriever = EpiGraphRetriever(args.triplets) if args.mode == "graph_rag" else None
    client = ChatClient(args.model, temperature=0.0)
    rows = []
    for item in tqdm(data[: args.sample or None]):
        body = item["question"] + "\n" + "\n".join(item["options"])
        paths = []
        if retriever:
            ret = retriever.retrieve(body)
            paths = ret["paths"]
            body = "Knowledge graph reasoning paths:\n" + "\n".join(paths) + "\n\n" + body
        pred = client.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": body}], max_tokens=50)
        letter = option_letter(pred)
        selected = ""
        for opt in item["options"]:
            if opt.startswith(f"{letter}") or opt.startswith(f"{letter})"):
                selected = opt
        rows.append(
            {
                "id": item["id"],
                "pred_option": letter,
                "gold_option": item["correct_answer"],
                "drug_safety": drug_safety_score(selected, item.get("contraindicated", [])),
                "kg_evidence_coverage": kg_evidence_coverage(selected, paths),
            }
        )
    write_json(rows, args.out)
    print({"top1_accuracy": accuracy([r["pred_option"] for r in rows], [r["gold_option"] for r in rows]), "drug_safety": sum(r["drug_safety"] for r in rows) / max(len(rows), 1), "kg_evidence_coverage": sum(r["kg_evidence_coverage"] for r in rows) / max(len(rows), 1)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 4: Treatment Recommendation.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--out", default="data/epibench/t4/medqa_epilepsy.json")
    build.add_argument("--max_items", type=int, default=200)
    ev = sub.add_parser("eval")
    ev.add_argument("--dataset", required=True)
    ev.add_argument("--triplets", default="data/epikg/triplets.json")
    ev.add_argument("--model", default="openai/gpt-4o")
    ev.add_argument("--mode", choices=["no_rag", "graph_rag"], default="graph_rag")
    ev.add_argument("--sample", type=int, default=0)
    ev.add_argument("--out", default="runs/t4_predictions.json")
    args = parser.parse_args()
    build_medqa_subset(args.out, args.max_items) if args.command == "build" else evaluate(args)


if __name__ == "__main__":
    main()


import argparse
from pathlib import Path

from tqdm import tqdm

from epigraph.common import ChatClient, option_letter, read_json, write_json
from epigraph.metrics import accuracy, bleu1, rouge_l, summarize_scores, token_f1
from epigraph.retrieval import EpiGraphRetriever


MCQ_SYSTEM = """You are an epilepsy specialist taking a clinical decision exam.
Select exactly one option letter (A, B, C, or D). Use guideline-consistent reasoning.
Return only the option letter."""

QA_SYSTEM = """You are an epilepsy specialist. Answer the clinical question in 2-4 concise sentences.
Name relevant syndromes, EEG/MRI findings, genes, treatments, contraindications, or outcomes when applicable."""


def build_messages(item: dict, retriever: EpiGraphRetriever | None, mode: str) -> list[dict]:
    question = item["question"]
    evidence = ""
    if mode == "graph_rag" and retriever:
        ret = retriever.retrieve(question)
        evidence = "\n".join(ret["paths"])
    if item.get("options"):
        body = question + "\n" + "\n".join(item["options"])
        system = MCQ_SYSTEM
    else:
        body = question
        system = QA_SYSTEM
    if evidence:
        body = f"Knowledge graph reasoning paths:\n{evidence}\n\nQuestion:\n{body}"
    return [{"role": "system", "content": system}, {"role": "user", "content": body}]


def evaluate(args: argparse.Namespace) -> None:
    data = read_json(args.dataset)
    retriever = EpiGraphRetriever(args.triplets) if args.mode == "graph_rag" else None
    client = ChatClient(args.model, temperature=0.0)
    rows = []
    for item in tqdm(data[: args.sample or None]):
        answer = client.complete(build_messages(item, retriever, args.mode), max_tokens=400)
        row = {"id": item.get("id"), "prediction": answer, "gold": item.get("answer"), "mode": args.mode}
        if item.get("options"):
            row["pred_option"] = option_letter(answer)
            row["gold_option"] = item.get("correct_answer")
            row["correct"] = float(row["pred_option"] == row["gold_option"])
        else:
            row.update(
                {
                    "bleu1": bleu1(answer, item.get("answer", "")),
                    "rouge_l": rouge_l(answer, item.get("answer", "")),
                    "token_f1": token_f1(answer, item.get("answer", "")),
                }
            )
        rows.append(row)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_json(rows, args.out)
    if rows and "correct" in rows[0]:
        print({"accuracy": accuracy([r["pred_option"] for r in rows], [r["gold_option"] for r in rows])})
    else:
        print(summarize_scores(rows, ["bleu1", "rouge_l", "token_f1"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 1: Clinical Decision Accuracy.")
    parser.add_argument("--dataset", required=True, help="EpiBench-MCQ or EpiBench-QA JSON.")
    parser.add_argument("--triplets", default="data/epikg/triplets.json")
    parser.add_argument("--model", default="openai/gpt-4o")
    parser.add_argument("--mode", choices=["no_rag", "graph_rag"], default="graph_rag")
    parser.add_argument("--sample", type=int, default=0)
    parser.add_argument("--out", default="runs/t1_predictions.json")
    evaluate(parser.parse_args())


if __name__ == "__main__":
    main()


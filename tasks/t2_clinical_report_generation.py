import argparse
from pathlib import Path

from tqdm import tqdm

from epigraph.common import ChatClient, normalize_text, read_json, stable_id, write_json
from epigraph.metrics import rouge_l, summarize_scores, token_f1
from epigraph.retrieval import EpiGraphRetriever


SYSTEM = """You are a clinical neurophysiologist.
Generate a neurologist-style EEG clinical impression from the patient history and EEG description.
The impression must summarize: (1) abnormal EEG findings, (2) likely clinical interpretation,
and (3) relevant recommendations or correlation with seizure history. Be concise and clinically safe."""


def build_harvard_preview(raw_jsonl: str, out_json: str) -> None:
    """Convert a local Harvard EEG export to the schema used by the evaluator.

    The Harvard EEG database cannot be redistributed. Prepare a local JSONL with:
    patient_history, eeg_description, bandpower, spike_rate, impression.
    """
    rows = []
    for line in Path(raw_jsonl).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        src = read_json_from_line(line)
        text = " ".join(
            [
                src.get("patient_history", ""),
                src.get("eeg_description", ""),
                f"Bandpower: {src.get('bandpower', '')}",
                f"Spike rate: {src.get('spike_rate', '')}",
            ]
        )
        rows.append(
            {
                "id": stable_id(text, prefix="t2"),
                "patient_history": normalize_text(src.get("patient_history", "")),
                "eeg_description": normalize_text(src.get("eeg_description", "")),
                "bandpower": src.get("bandpower", {}),
                "spike_rate": src.get("spike_rate", None),
                "gold_impression": normalize_text(src.get("impression", "")),
            }
        )
    write_json(rows, out_json)


def read_json_from_line(line: str) -> dict:
    import json

    return json.loads(line)


def make_prompt(item: dict, retriever: EpiGraphRetriever | None, mode: str) -> list[dict]:
    body = f"""Patient history:
{item.get('patient_history', '')}

EEG description:
{item.get('eeg_description', '')}

Computed EEG statistics:
bandpower={item.get('bandpower', {})}
spike_rate={item.get('spike_rate', '')}
"""
    if mode == "graph_rag" and retriever:
        query = f"{item.get('patient_history', '')} {item.get('eeg_description', '')}"
        paths = retriever.retrieve(query)["paths"]
        body = "Knowledge graph context:\n" + "\n".join(paths) + "\n\n" + body
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": body}]


def evaluate(args: argparse.Namespace) -> None:
    data = read_json(args.dataset)
    retriever = EpiGraphRetriever(args.triplets) if args.mode == "graph_rag" else None
    client = ChatClient(args.model, temperature=0.3)
    rows = []
    for item in tqdm(data[: args.sample or None]):
        pred = client.complete(make_prompt(item, retriever, args.mode), max_tokens=300)
        gold = item.get("gold_impression", "")
        rows.append(
            {
                "id": item.get("id"),
                "prediction": pred,
                "gold_impression": gold,
                "rouge_l": rouge_l(pred, gold),
                "token_f1": token_f1(pred, gold),
                "mode": args.mode,
            }
        )
    write_json(rows, args.out)
    print(summarize_scores(rows, ["rouge_l", "token_f1"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 2: Clinical Report Generation.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--raw_jsonl", required=True)
    build.add_argument("--out", default="data/epibench/t2/harvard_preview.json")
    ev = sub.add_parser("eval")
    ev.add_argument("--dataset", required=True)
    ev.add_argument("--triplets", default="data/epikg/triplets.json")
    ev.add_argument("--model", default="medgemma-4b-it")
    ev.add_argument("--mode", choices=["no_rag", "graph_rag"], default="graph_rag")
    ev.add_argument("--sample", type=int, default=0)
    ev.add_argument("--out", default="runs/t2_predictions.json")
    args = parser.parse_args()
    if args.command == "build":
        build_harvard_preview(args.raw_jsonl, args.out)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()


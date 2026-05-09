import argparse
import random
from pathlib import Path

from tqdm import tqdm

from epigraph.common import ChatClient, option_letter, stable_id, write_json, read_json
from epigraph.metrics import accuracy, drug_safety_score
from epigraph.retrieval import EpiGraphRetriever


RULES = [
    {
        "gene": "SCN1A",
        "variant": "loss-of-function",
        "phenotype": "Dravet syndrome with recurrent febrile and myoclonic seizures",
        "recommended": "Valproate",
        "avoid": ["Carbamazepine", "Lamotrigine", "Phenytoin", "Oxcarbazepine"],
        "rationale": "Sodium-channel blockers may worsen seizures in SCN1A loss-of-function Dravet syndrome.",
    },
    {
        "gene": "TSC2",
        "variant": "pathogenic variant",
        "phenotype": "refractory focal seizures in tuberous sclerosis complex",
        "recommended": "Everolimus",
        "avoid": [],
        "rationale": "mTOR inhibition targets the TSC pathway and is guideline-consistent for refractory TSC seizures.",
    },
    {
        "gene": "POLG",
        "variant": "pathogenic variant",
        "phenotype": "Alpers-Huttenlocher syndrome with seizures",
        "recommended": "Levetiracetam",
        "avoid": ["Valproate"],
        "rationale": "Valproate is contraindicated because of liver failure risk in POLG-related disease.",
    },
    {
        "gene": "HLA-B*15:02",
        "variant": "positive allele",
        "phenotype": "epilepsy patient of Asian ancestry requiring ASM initiation",
        "recommended": "Levetiracetam",
        "avoid": ["Carbamazepine", "Oxcarbazepine", "Phenytoin"],
        "rationale": "HLA-B*15:02 increases severe cutaneous adverse reaction risk with aromatic ASMs.",
    },
]


SYSTEM = """You are a clinical epilepsy geneticist.
Select the most appropriate antiseizure medication from A-D using CPIC/ILAE-style pharmacogenomic reasoning.
Return only the option letter."""


def build_dataset(out: str, seed: int = 13) -> None:
    random.seed(seed)
    distractor_pool = sorted({d for r in RULES for d in r["avoid"]} | {r["recommended"] for r in RULES} | {"Clobazam", "Topiramate"})
    rows = []
    for idx, rule in enumerate(RULES, 1):
        distractors = [x for x in distractor_pool if x != rule["recommended"]]
        options = [rule["recommended"]] + random.sample(distractors, 3)
        random.shuffle(options)
        labels = ["A", "B", "C", "D"]
        rows.append(
            {
                "id": stable_id(rule["gene"], rule["variant"], prefix="t3"),
                "gene": rule["gene"],
                "variant": rule["variant"],
                "clinical_scenario": f"A patient with {rule['phenotype']} has a {rule['gene']} {rule['variant']}. Which ASM is most appropriate?",
                "options": [f"{label}) {option}" for label, option in zip(labels, options)],
                "correct_answer": labels[options.index(rule["recommended"])],
                "recommended": rule["recommended"],
                "avoid": rule["avoid"],
                "rationale": rule["rationale"],
            }
        )
    write_json(rows, out)


def evaluate(args: argparse.Namespace) -> None:
    data = read_json(args.dataset)
    retriever = EpiGraphRetriever(args.triplets) if args.mode == "graph_rag" else None
    client = ChatClient(args.model, temperature=0.0)
    rows = []
    for item in tqdm(data[: args.sample or None]):
        body = item["clinical_scenario"] + "\n" + "\n".join(item["options"])
        if retriever:
            paths = retriever.retrieve(body)["paths"]
            body = "Knowledge graph reasoning paths:\n" + "\n".join(paths) + "\n\n" + body
        pred = client.complete([{"role": "system", "content": SYSTEM}, {"role": "user", "content": body}], max_tokens=50)
        letter = option_letter(pred)
        selected = ""
        for option in item["options"]:
            if option.startswith(f"{letter})"):
                selected = option.split(")", 1)[1].strip()
        rows.append(
            {
                "id": item["id"],
                "prediction": pred,
                "pred_option": letter,
                "gold_option": item["correct_answer"],
                "drug_safety": drug_safety_score(selected, item.get("avoid", [])),
            }
        )
    write_json(rows, args.out)
    print({"top1_accuracy": accuracy([r["pred_option"] for r in rows], [r["gold_option"] for r in rows]), "drug_safety": sum(r["drug_safety"] for r in rows) / max(len(rows), 1)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 3: Biomarker-Driven Precision Medicine.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--out", default="data/epibench/t3/bpm_mcq.json")
    ev = sub.add_parser("eval")
    ev.add_argument("--dataset", required=True)
    ev.add_argument("--triplets", default="data/epikg/triplets.json")
    ev.add_argument("--model", default="openai/gpt-4o")
    ev.add_argument("--mode", choices=["no_rag", "graph_rag"], default="graph_rag")
    ev.add_argument("--sample", type=int, default=0)
    ev.add_argument("--out", default="runs/t3_predictions.json")
    args = parser.parse_args()
    build_dataset(args.out) if args.command == "build" else evaluate(args)


if __name__ == "__main__":
    main()


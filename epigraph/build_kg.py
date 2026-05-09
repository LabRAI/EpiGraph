import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from .common import stable_id, write_json


LAYERS = {
    "gene": ["SCN1A", "SCN2A", "SCN8A", "KCNQ2", "TSC1", "TSC2", "POLG", "HLA-B", "CYP2C9"],
    "phenotype": ["febrile seizures", "myoclonic seizures", "tonic seizures", "spasms", "status epilepticus"],
    "syndrome": ["Dravet syndrome", "Lennox-Gastaut syndrome", "temporal lobe epilepsy", "tuberous sclerosis"],
    "treatment": ["valproate", "clobazam", "stiripentol", "carbamazepine", "lamotrigine", "everolimus"],
    "outcome": ["seizure freedom", "adverse effects", "drug resistance", "seizure reduction"],
}


RELATION_HINTS = {
    ("gene", "syndrome"): "caused_by_gene",
    ("syndrome", "phenotype"): "has_phenotype",
    ("syndrome", "treatment"): "treated_with",
    ("gene", "treatment"): "pharmacogenomic_recommendation",
    ("treatment", "outcome"): "has_outcome",
}


def parse_pmc_xml(path: Path) -> dict:
    root = ET.parse(path).getroot()
    text = " ".join(root.itertext())
    title = " ".join(root.findall(".//article-title")[0].itertext()) if root.findall(".//article-title") else path.stem
    return {"paper_id": path.stem, "title": re.sub(r"\s+", " ", title), "text": re.sub(r"\s+", " ", text)}


def detect_entities(text: str) -> dict:
    lower = text.lower()
    out = {}
    for layer, terms in LAYERS.items():
        hits = []
        for term in terms:
            if term.lower() in lower:
                hits.append(term)
        out[layer] = sorted(set(hits))
    return out


def build_triplets(papers: list[dict]) -> list[dict]:
    evidence = {}
    for paper in papers:
        entities = detect_entities(paper["text"])
        for (src_layer, dst_layer), relation in RELATION_HINTS.items():
            for head in entities[src_layer]:
                for tail in entities[dst_layer]:
                    if head.lower() == tail.lower():
                        continue
                    key = (head, relation, tail, src_layer, dst_layer)
                    evidence.setdefault(key, set()).add(paper["paper_id"])
    rows = []
    for (head, relation, tail, head_layer, tail_layer), paper_ids in evidence.items():
        rows.append(
            {
                "id": stable_id(head, relation, tail, prefix="kg"),
                "head": head,
                "relation": relation,
                "tail": tail,
                "head_layer": head_layer,
                "tail_layer": tail_layer,
                "paper_count": len(paper_ids),
                "paper_ids": sorted(paper_ids),
            }
        )
    return sorted(rows, key=lambda x: (-x["paper_count"], x["head"], x["tail"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a lightweight EPIKG preview from PMC XML files.")
    parser.add_argument("--pmc_dir", required=True, help="Directory containing PMC XML files.")
    parser.add_argument("--out_dir", default="data/epikg", help="Output directory.")
    args = parser.parse_args()

    pmc_dir = Path(args.pmc_dir)
    papers = [parse_pmc_xml(path) for path in sorted(pmc_dir.glob("*.xml"))]
    triplets = build_triplets(papers)
    metadata = [
        {
            "paper_id": paper["paper_id"],
            "title": paper["title"],
            "entity_counts": Counter({k: len(v) for k, v in detect_entities(paper["text"]).items()}),
        }
        for paper in papers
    ]
    out_dir = Path(args.out_dir)
    write_json(triplets, out_dir / "triplets.json")
    write_json(metadata, out_dir / "paper_metadata.json")
    print(json.dumps({"papers": len(papers), "triplets": len(triplets)}, indent=2))


if __name__ == "__main__":
    main()


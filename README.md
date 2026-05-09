<div align="center">

# <span style="color:#4F46E5">EpiGraph</span> Code Release

**A knowledge graph and benchmark toolkit for evidence-intensive reasoning in epilepsy**

<img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
<img alt="Graph RAG" src="https://img.shields.io/badge/Graph--RAG-PPR%20%2B%20Paths-7C3AED?style=for-the-badge">
<img alt="Tasks" src="https://img.shields.io/badge/EpiBench-5%20Tasks-14B8A6?style=for-the-badge">

</div>

---

## What This Folder Contains

This is a clean, paper-aligned code bundle for **EpiGraph: A Knowledge Graph and Benchmark for Evidence-Intensive Reasoning in Epilepsy**.

It includes:

| Area | File | Purpose |
|---|---|---|
| Knowledge graph | `epigraph/build_kg.py` | Build a lightweight EPIKG-style graph preview from PMC XML files |
| Graph retrieval | `epigraph/retrieval.py` | PPR-based graph retrieval and reasoning-path serialization |
| Metrics | `epigraph/metrics.py` | Accuracy, Top-k, ROUGE-L, Token-F1, BLEU-1, MRR/NDCG, safety and KG coverage |
| Common utilities | `epigraph/common.py` | JSON IO, OpenRouter-compatible client, normalization helpers |
| Task 1 | `tasks/t1_clinical_decision_accuracy.py` | Clinical Decision Accuracy: MCQ and open-ended clinical QA |
| Task 2 | `tasks/t2_clinical_report_generation.py` | Clinical Report Generation from EEG descriptions and patient context |
| Task 3 | `tasks/t3_biomarker_precision_medicine.py` | Biomarker-driven precision medicine from gene variants to ASMs |
| Task 4 | `tasks/t4_treatment_recommendation.py` | Treatment recommendation on epilepsy-relevant MedQA/MMLU-style questions |
| Task 5 | `tasks/t5_deep_research_planning.py` | Deep epilepsy research question and study-plan generation |

---

## EpiBench Tasks

<div style="border-left:6px solid #4F46E5;padding:10px 14px;background:#F5F3FF">

**T1 Clinical Decision Accuracy (CDA)**  
Epilepsy-specific MCQ and open-ended QA covering diagnosis, treatment, outcome, factual recall, and clinical reasoning.

</div>

<div style="border-left:6px solid #0EA5E9;padding:10px 14px;background:#EFF6FF">

**T2 Clinical Report Generation (CRG)**  
Generate neurologist-style EEG impressions from patient history, EEG text, and computed EEG statistics.  
The Harvard EEG data cannot be redistributed, so this release provides a local-schema builder and evaluator.

</div>

<div style="border-left:6px solid #10B981;padding:10px 14px;background:#ECFDF5">

**T3 Biomarker-Driven Precision Medicine (BPM)**  
Select antiseizure medications from genetic variants and phenotypes using CPIC/ILAE-style pharmacogenomic evidence.

</div>

<div style="border-left:6px solid #F97316;padding:10px 14px;background:#FFF7ED">

**T4 Treatment Recommendation (TR)**  
Recommend guideline-consistent therapies under patient-specific constraints, with drug safety and KG evidence coverage.

</div>

<div style="border-left:6px solid #DB2777;padding:10px 14px;background:#FDF2F8">

**T5 Deep Research Planning (DRP)**  
Generate clinically meaningful research questions and feasible study plans from epilepsy literature.

</div>

---

## Setup

```bash
cd EpiGraph_code_release
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENROUTER_API_KEY="your_key_here"
```

For local models, replace `ChatClient` calls with your local inference wrapper or run an OpenAI-compatible local endpoint.

---

## Build A Lightweight EPIKG Preview

The full paper graph is built from 48,166 papers plus clinical resources. This script provides a reproducible preview builder for local PMC XML files:

```bash
python -m epigraph.build_kg \
  --pmc_dir /path/to/pmc_xml \
  --out_dir data/epikg
```

Expected outputs:

```text
data/epikg/triplets.json
data/epikg/paper_metadata.json
```

The triplet schema follows the paper:

```json
{
  "head": "SCN1A",
  "relation": "caused_by_gene",
  "tail": "Dravet syndrome",
  "head_layer": "gene",
  "tail_layer": "syndrome",
  "paper_count": 12,
  "paper_ids": ["pmc_..."]
}
```

---

## Run The Five Tasks

### T1 Clinical Decision Accuracy

```bash
python tasks/t1_clinical_decision_accuracy.py \
  --dataset data/epibench/t1/mcq.json \
  --triplets data/epikg/triplets.json \
  --model openai/gpt-4o \
  --mode graph_rag \
  --out runs/t1_mcq_graph_rag.json
```

### T2 Clinical Report Generation

Prepare a private local JSONL from Harvard EEG-derived data:

```json
{"patient_history":"...","eeg_description":"...","bandpower":{"delta":0.31},"spike_rate":2.4,"impression":"..."}
```

Then build and evaluate:

```bash
python tasks/t2_clinical_report_generation.py build \
  --raw_jsonl data/private/harvard_eeg/local_export.jsonl \
  --out data/epibench/t2/harvard_preview.json

python tasks/t2_clinical_report_generation.py eval \
  --dataset data/epibench/t2/harvard_preview.json \
  --triplets data/epikg/triplets.json \
  --model medgemma-4b-it \
  --mode graph_rag
```

### T3 Biomarker-Driven Precision Medicine

```bash
python tasks/t3_biomarker_precision_medicine.py build \
  --out data/epibench/t3/bpm_mcq.json

python tasks/t3_biomarker_precision_medicine.py eval \
  --dataset data/epibench/t3/bpm_mcq.json \
  --triplets data/epikg/triplets.json \
  --model openai/gpt-4o \
  --mode graph_rag
```

### T4 Treatment Recommendation

```bash
python tasks/t4_treatment_recommendation.py build \
  --out data/epibench/t4/medqa_epilepsy.json \
  --max_items 200

python tasks/t4_treatment_recommendation.py eval \
  --dataset data/epibench/t4/medqa_epilepsy.json \
  --triplets data/epikg/triplets.json \
  --model openai/gpt-4o \
  --mode graph_rag
```

### T5 Deep Research Planning

```bash
python tasks/t5_deep_research_planning.py build \
  --lay_summaries data/epibench/t5/lay_summaries.json \
  --out data/epibench/t5/research_planning.json

python tasks/t5_deep_research_planning.py eval \
  --dataset data/epibench/t5/research_planning.json \
  --triplets data/epikg/triplets.json \
  --model openai/gpt-4o \
  --mode graph_rag
```

---

## Metrics Matched To The Paper

| Task | Main metrics |
|---|---|
| T1 CDA | MCQ Top-1 Accuracy; open-ended BLEU-1, ROUGE-L, Token-F1, LLM-as-Judge-ready outputs |
| T2 CRG | ROUGE-L, Token-F1, report alignment / clinical relevance via human or LLM judge |
| T3 BPM | Top-1 Accuracy, Drug Safety Score |
| T4 TR | Top-1 Accuracy, Drug Safety Score, KG Evidence Coverage |
| T5 DRP | ROUGE-L / Token-F1 when expert annotations exist; LLM-as-Judge dimensions for validity, clinical relevance, feasibility, novelty, literature alignment |

---

## Notes On Private Or Restricted Data

The paper uses the Harvard EEG database for T2. This dataset is not redistributed here. The provided T2 code intentionally expects a **local JSONL export** and keeps only a small, replaceable schema:

```text
patient_history
eeg_description
bandpower
spike_rate
impression
```

This preserves the evaluation logic while respecting dataset restrictions.

---

## Repository Layout

```text
EpiGraph_code_release/
  configs/default.json
  epigraph/
    build_kg.py
    common.py
    metrics.py
    retrieval.py
  tasks/
    t1_clinical_decision_accuracy.py
    t2_clinical_report_generation.py
    t3_biomarker_precision_medicine.py
    t4_treatment_recommendation.py
    t5_deep_research_planning.py
  requirements.txt
  README.md
```

---

<div align="center">

<b style="color:#4F46E5">EpiGraph</b> turns epilepsy literature into structured evidence, then tests whether LLMs can reason with it.

</div>


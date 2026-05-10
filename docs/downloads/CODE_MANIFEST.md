# Code Manifest

This folder centralizes the paper-aligned code for the EpiGraph / EpiBench submission.

## Paper-To-Code Mapping

| Paper component | Release code | Notes |
|---|---|---|
| EPIKG construction from literature and clinical layers | `epigraph/build_kg.py` | Lightweight reproducible builder for PMC XML; follows five-layer schema: gene, phenotype, syndrome, treatment, outcome |
| Graph-RAG retrieval with graph structure | `epigraph/retrieval.py` | PPR-style retrieval and reasoning-path serialization |
| Evaluation metrics | `epigraph/metrics.py` | Includes task accuracy, ROUGE-L, Token-F1, BLEU-1, ranking metrics, drug safety, KG evidence coverage |
| T1 Clinical Decision Accuracy | `tasks/t1_clinical_decision_accuracy.py` | Supports MCQ and open-ended QA |
| T2 Clinical Report Generation | `tasks/t2_clinical_report_generation.py` | Harvard EEG data is private; code expects a local JSONL export and preserves the paper's evaluation logic |
| T3 Biomarker-Driven Precision Medicine | `tasks/t3_biomarker_precision_medicine.py` | CPIC/ILAE-style rule builder and Graph-RAG evaluator |
| T4 Treatment Recommendation | `tasks/t4_treatment_recommendation.py` | Epilepsy-filtered MedQA-USMLE builder plus treatment safety metrics |
| T5 Deep Research Planning | `tasks/t5_deep_research_planning.py` | Builds literature-planning instances and evaluates generated research plans |

## Differences From Earlier Working Scripts

The original workspace contains exploratory scripts with hardcoded absolute paths and API keys. This release version:

- uses relative paths and command-line arguments;
- removes embedded private keys;
- keeps Harvard EEG handling as a private local-data adapter;
- aligns the five task names, task inputs, and metrics with the paper text;
- keeps each task runnable independently.


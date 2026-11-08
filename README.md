# Data and scripts for "Efficient Tool Use for Agentic AI" (survey)

Supporting data for the survey *Efficient Tool Use for Agentic AI: A Survey and an Analytical Cost
Model for Tool-Using LLM Agents* (H. Mohasel Arjomandi and A. GhaffarTehrani, preprint, November 2026).
Survey cutoff: October 31, 2026. Archived on Zenodo: [10.5281/zenodo.23938630](https://doi.org/10.5281/zenodo.23938630)
(all versions; resolves to the latest). Version 1.0: [10.5281/zenodo.23938631](https://doi.org/10.5281/zenodo.23938631).

**Version 1.1** (November 2026) adds `data/second_coder/` (two-coder screening and benchmark-audit agreement),
`data/rescreen/` (re-screen of the uncited tool-titled records), the adjudicated `data/audit/benchmark_audit.tsv`,
and an updated `data/checks/verify_bib_report.tsv`.

This repository contains the literature harvest and screening sheet, the coverage-check decisions,
the full-text benchmark audit, the outputs of the trace consistency check and catalog sweep, and the
scripts that recompute every number in Section IV (cost model), Section II (bibliometrics), and
Section X (benchmark audit).

## Contents

| Path | What it is | Used in the paper |
|---|---|---|
| `data/harvest/harvest_config.json` | arXiv queries, date window, title rule | §II-A |
| `data/harvest/harvest.json`, `screening.csv` | All 2,493 unique harvested records (title, date, abstract, matched queries, tool-title flag) | §II, Figs. 1–2 |
| `data/harvest/harvest_summary.json` | Per-query and screening counts | Fig. 1 |
| `data/coverage/gaps.tsv` | Works cited by the 11 competing surveys and not by us | §II-D |
| `data/coverage/gaps_decisions.tsv` | Decision (added / excluded) and category for the 120 works cited by ≥2 of them | §II-D |
| `data/audit/benchmark_audit.tsv` | Abstract and full-text efficiency codes for 43 benchmarks, with the supporting passage | Table IV, §X |
| `data/second_coder/screening_second_coder.csv`, `screening_first_author_rescreen.csv` | Both authors' screening decisions on the 100-record sample under the same written criteria (`criteria_and_instructions.md`) | §II-A |
| `data/second_coder/screening_pair_adjudication.csv`, `screening_pair_score.txt` | Agreement (κ = 0.88) and the adjudication of the 5 disagreements | §II-A |
| `data/second_coder/screening_first_author.csv`, `screening_adjudication.csv` | Earlier comparison against the first author's citation decisions (κ = 0.17) and its adjudication | §II-A |
| `data/second_coder/audit_*.csv`, `score.py` | Benchmark-audit codes of both coders, adjudication, and the κ script | §X, Table IV |
| `data/rescreen/` | Codes and rules of the re-screen of all 648 uncited tool-titled records | §II-C |
| `data/traces/traces_summary.tsv`, `traces_episodes.tsv` | Per-group and per-episode results of the trace consistency check | Table III, §IV-F |
| `data/traces/sweep_grid.tsv`, `sweep_fine.tsv`, `sweep_output.txt` | Catalog-padding sweep (k = 1, 3, 5; fine grid near the crossing) | Fig. 4, §IV-F |
| `data/checks/cost_model_output.txt` | Output of `cost_model.py` (scenario numbers, caching, Monte Carlo) | §IV, Table II, Fig. 3 |
| `data/checks/bibliometrics_output.txt` | Output of `bibliometrics.py` | §II-B, Fig. 2 |
| `data/checks/verify_bib_report.tsv` | Identifier, title, and first-author check of every arXiv-backed reference | §II-C |
| `scripts/harvest.py` | Reproducible arXiv harvest | §II-A |
| `scripts/bibliometrics.py` | Title and abstract statistics, yearly shares, quarterly counts | §II-B |
| `scripts/cost_model.py` | All analytic numbers of the cost model | §IV |
| `scripts/trace_analysis.py` | Consistency check on τ-bench and SWE-agent traces | §IV-F |
| `scripts/catalog_sweep.py` | Catalog padding with BFCL schemas; flip points | §IV-F |
| `scripts/benchmark_audit_scan.py` | Keyword scan of benchmark full texts used for the audit | §X |
| `scripts/verify_bib.py` | Checks arXiv-backed BibTeX entries (arXiv API or Semantic Scholar) | §II-C |

## Third-party data (not redistributed)

The trace check and sweep read public data that you download yourself:

- τ-bench historical trajectories (MIT License):
  `https://github.com/sierra-research/tau-bench/tree/main/historical_trajectories`
  (`gpt-4o-{retail,airline}.json`, `sonnet-35-new-{retail,airline}.json`). Put them in one directory
  together with the tool sources of `tau_bench/envs/{retail,airline}/tools/*.py` in subfolders
  `tools_retail/` and `tools_airline/`. The tool schemas are parsed with `ast` and not executed.
- SWE-agent trajectories (Nebius, CC BY 4.0):
  `https://huggingface.co/datasets/nebius/SWE-agent-trajectories`, file
  `data/train-00000-of-00012.parquet` (the first 2,000 rows are used).
- BFCL v4 evaluation data (Apache-2.0):
  `https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard/bfcl_eval/data`
  (`BFCL_v4_multiple.json`, `BFCL_v4_live_multiple.json`, `BFCL_v4_simple_python.json`,
  `BFCL_v4_parallel_multiple.json`).

## Reproduce the numbers

```bash
pip install tiktoken pyarrow
python3 scripts/cost_model.py                       # Section IV, Table II, Fig. 3
python3 scripts/bibliometrics.py data/harvest/screening.csv
python3 -I scripts/trace_analysis.py <tau_dir> <swe_shard.parquet> traces
python3 -I scripts/catalog_sweep.py  <tau_dir> <swe_shard.parquet> <bfcl_dir> sweep
python3 scripts/verify_bib.py references.bib s2     # or 'arxiv'
```

Tokens are counted with tiktoken `o200k_base` for all sources.

## License

Scripts: MIT. Data in `data/`: CC BY 4.0. See `LICENSE`. Third-party datasets keep their own licenses.

## Citation

Please cite the survey (arXiv identifier to be added) and this repository:

H. Mohasel Arjomandi, *Data and Scripts for "Efficient Tool Use for Agentic AI"*, version 1.1, Zenodo, 2026.
DOI: [10.5281/zenodo.23938630](https://doi.org/10.5281/zenodo.23938630) (all versions)

# Re-screen of uncited tool-titled records (Paper 3), 2026-11-08

Why: the second-coder sample (`../second_screening/`) found 15 of 50 uncited tool-titled records relevant and
missed. This pass codes the whole stratum.

Population: the 648 harvest records (`../screening.csv`) with `topic_centric == True` whose arXiv id is not cited
in `paper/references.bib` (stratum B of `make_sample.py`).

Coder: Claude (LLM), from title + abstract (the first 650 characters; full abstract read for uncertain records).
**Not a human screening decision. The first author must check at least the E codes and the borderline T codes
before any of this is reported as screening in the paper.**

Codes (`B_codes.csv`: id, code, lever, note):
- `E` bears on a term of the cost model or on the evaluation of tool-use efficiency: tool retrieval/selection that
  limits what enters the prompt; fewer calls/turns or call-necessity decisions; parallel/async/speculative/serving
  execution; tool-output and context management; smaller, quantized, distilled, or on-device tool-calling models,
  or training that reduces calls; benchmarks or measurements that report or target efficiency; audits of tool-use
  benchmarks; surveys of tool use. Candidates to cite.
- `T` LLM tool-use work without a cost bearing (capability benchmarks, training for accuracy, safety/security,
  applications). `lever = robust` marks attacks/defenses on tool selection or execution.
- `X` not LLM tool use.

Rules applied for consistency: tool-retrieval methods are E (they shrink the static term); selection work judged
only on accuracy is T; small-model work is E only when the small or on-device model is the contribution; data
generation whose only cost claim is the cost of making data is T; safety work is T even when it reports latency.

Result: 127 E, 491 T, 30 X (E by lever: selection 32, models 26, planning 22, invocation 18, benchmark 13,
context 7, other 7, survey 2). On the 50 sampled records the codes match the adjudication in
`../second_screening/screening_adjudication.csv` exactly (15 E).
Note: 127/648 = 19.6%, below the sample's 15/50 = 30% (within its 95% interval).

Not covered: the 1,646 uncited records whose titles do not name tools (stratum C; the sample found 1 of 20 relevant).

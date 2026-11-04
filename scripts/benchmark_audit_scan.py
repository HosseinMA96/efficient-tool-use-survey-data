#!/usr/bin/env python3
"""Keyword scan of benchmark full texts (pdftotext output) for efficiency metrics.

Usage: python3 benchmark_audit_scan.py <dir with <bibkey>.txt files> <ids.txt>
Prints, for each benchmark, matches for monetary, time, token and call/turn
metrics with context.  Every match was then read by the coder, and the final
codes are recorded in literature/benchmark_audit.tsv (matches in dataset
statistics, dataset-construction costs, task text and references are not
counted)."""
import re
import sys
PATS = {
    "MONEY": r"(\$\s?\d[\d.,]*|\bUSD\b|dollars?\b|API cost|monetary|inference cost|cost per task|total cost|average cost)",
    "TIME": r"(latency|wall[- ]clock|execution time|running time|time cost|seconds per|average time|duration \(s\))",
    "TOK": r"(token (?:usage|consumption|cost|count)s?|(?:input|output|prompt|completion|total) tokens|tokens per (?:task|query|turn|episode))",
    "CALLS": r"(average (?:number of )?(?:tool |API )?(?:calls|turns|steps|rounds)|avg\.? (?:calls|turns|steps)|# ?turns|tool calls per task)",
}
d, ids = sys.argv[1], sys.argv[2]
for line in open(ids):
    key = line.split()[0]
    t = re.sub(r"\s+", " ", open(f"{d}/{key}.txt", errors="ignore").read())
    cut = [m.start() for m in re.finditer(r"\bReferences\b|\bREFERENCES\b", t)]
    body = t[:cut[-1]] if cut and cut[-1] > 0.4 * len(t) else t
    print("=====", key)
    for name, p in PATS.items():
        hits = list(re.finditer(p, body, re.I))
        print(f"  {name}: {len(hits)}")
        for m in hits[:6]:
            s = max(0, m.start() - 120)
            print("     ..." + body[s:m.end() + 80] + "...")

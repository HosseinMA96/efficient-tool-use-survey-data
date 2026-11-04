#!/usr/bin/env python3
"""Reproducible bibliometrics for Paper 3 (Section II, Fig. 1).

Reads literature/screening.csv (output of shared/tools/harvest.py) and
classifies the 838 tool-titled records as efficiency-titled with an explicit,
word-bounded rule.  It also applies the same rule to abstracts, so that the
title statistic can be compared with an abstract statistic, and reports the
agreement (Cohen's kappa) between the two.

Usage: python3 bibliometrics.py ../literature/screening.csv
"""
import csv
import re
import sys
from collections import Counter

EFF = re.compile(
    r"\b(efficien\w*|cost\w*|cheap\w*|frugal|budget\w*|latency|tokens?|speed\w*|"
    r"fast(?:er)?|accelerat\w*|throughput|compress\w*|parallel\w*|asynchron\w*|"
    r"cach\w*|overhead|lightweight|small|on-device|edge)\b",
    re.I,
)

rows = [r for r in csv.DictReader(open(sys.argv[1])) if r["topic_centric"] == "True"]
n = len(rows)
title = [bool(EFF.search(r["title"])) for r in rows]
abst = [bool(EFF.search(r["abstract"])) for r in rows]

print(f"tool-titled records: {n}")
print(f"efficiency-titled:   {sum(title)} ({sum(title)/n:.1%})")
print(f"efficiency term in abstract: {sum(abst)} ({sum(abst)/n:.1%})")

by_year, by_year_t, by_year_a = Counter(), Counter(), Counter()
by_q, by_q_t = Counter(), Counter()
for r, t, a in zip(rows, title, abst):
    y = r["published"][:4]
    q = f"{y[2:]}Q{(int(r['published'][5:7]) - 1) // 3 + 1}"
    by_year[y] += 1
    by_year_t[y] += t
    by_year_a[y] += a
    by_q[q] += 1
    by_q_t[q] += t
print("\nyear  all  eff-title  share   eff-abstract share")
for y in sorted(by_year):
    print(f"{y}  {by_year[y]:4d}  {by_year_t[y]:5d}  {by_year_t[y]/by_year[y]:6.1%}"
          f"   {by_year_a[y]:5d}  {by_year_a[y]/by_year[y]:6.1%}")
print("\nquarterly (all, eff-title):")
print(" ".join(f"({q},{by_q[q]},{by_q_t[q]})" for q in sorted(by_q)))

# agreement between title rule and abstract rule
both = sum(t and a for t, a in zip(title, abst))
neither = sum((not t) and (not a) for t, a in zip(title, abst))
po = (both + neither) / n
pt, pa = sum(title) / n, sum(abst) / n
pe = pt * pa + (1 - pt) * (1 - pa)
print(f"\ntitle-positive also abstract-positive: {both}/{sum(title)}")
print(f"observed agreement {po:.3f}, Cohen's kappa {(po - pe) / (1 - pe):.3f}")

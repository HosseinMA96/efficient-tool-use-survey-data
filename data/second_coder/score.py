"""Cohen's kappa between the first author and the second coder (Paper 3).

Usage:
  python3 score.py screening       screening_second_coder.csv   (vs. the first author's citation decisions)
  python3 score.py audit           audit_second_coder.csv
  python3 score.py screening-pair  screening_first_author_rescreen.csv screening_second_coder.csv

The answer files use the formats in criteria_and_instructions.md (the web sheet's "Copy all answers" output is
the same format). Keys: screening_first_author.csv (cited or not), audit_first_coder.csv (pre-adjudication codes).
"""
import csv, sys, pathlib
from collections import Counter
H = pathlib.Path(__file__).resolve().parent


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")


def table(a, b, labels):
    print("        coder2: " + "  ".join(f"{l:>8}" for l in labels))
    for x in labels:
        print(f"  first {x:>8}" + "".join(f"{sum(1 for p, q in zip(a, b) if p == x and q == y):>10}" for y in labels))


def load(path, key):
    rows = {r[key].strip(): r for r in csv.DictReader(open(path, encoding="utf-8-sig"))}
    return rows


def screening(path):
    keyrows = list(csv.DictReader(open(H / "screening_first_author.csv")))
    ans = load(path, "arxiv_id")
    missing = [k["id"] for k in keyrows if ans.get(k["id"], {}).get("decision", "").strip() not in ("include", "exclude")]
    if missing:
        sys.exit(f"{len(missing)} records without a decision, e.g. {missing[:5]}")
    a = [k["first_author"] for k in keyrows]
    b = [ans[k["id"]]["decision"].strip() for k in keyrows]
    po, k = kappa(a, b)
    print(f"Abstract screening, n = {len(a)} (stratified: 30 cited / 50 tool-titled uncited / 20 other uncited)")
    print(f"  agreement {po:.1%}, Cohen's kappa {k:.3f}")
    table(a, b, ["include", "exclude"])
    for s in "ABC":
        idx = [i for i, r in enumerate(keyrows) if r["stratum"] == s]
        agree = sum(a[i] == b[i] for i in idx)
        print(f"  stratum {s}: {agree}/{len(idx)} agree")
    uns = [k["id"] for k in keyrows if ans[k["id"]].get("unsure", "").strip() in ("1", "true", "True")]
    print(f"  marked unsure: {len(uns)}; disagreements among them: {sum(1 for i, r in enumerate(keyrows) if r['id'] in uns and a[i] != b[i])}")
    print("  disagreements:")
    for i, r in enumerate(keyrows):
        if a[i] != b[i]:
            print(f"    #{r['n']:>3} {r['id']}  first={a[i]}  coder2={b[i]} ({ans[r['id']].get('reason', '')})  {r['bibkey']}")


def audit(path):
    keyrows = list(csv.DictReader(open(H / "audit_first_coder.csv")))
    ans = load(path, "bibkey")
    metrics = ["money", "latency", "tokens", "calls"]
    bad = [k["bibkey"] for k in keyrows for m in metrics if ans.get(k["bibkey"], {}).get(m, "").strip() not in ("yes", "no")]
    if bad:
        sys.exit(f"{len(bad)} missing yes/no codes, e.g. {sorted(set(bad))[:5]}")
    allA, allB = [], []
    print(f"Benchmark audit, n = {len(keyrows)} papers x 4 metrics")
    for m in metrics:
        a = [k[m] for k in keyrows]; b = [ans[k["bibkey"]][m].strip() for k in keyrows]
        allA += a; allB += b
        po, k = kappa(a, b)
        print(f"  {m:<8} agreement {po:.1%}  kappa {k:.3f}  (first yes={a.count('yes')}, coder2 yes={b.count('yes')})")
    po, k = kappa(allA, allB)
    print(f"  pooled   agreement {po:.1%}  kappa {k:.3f}  ({len(allA)} judgments)")
    a = ["yes" if any(k[m] == "yes" for m in metrics) else "no" for k in keyrows]
    b = ["yes" if any(ans[k["bibkey"]][m].strip() == "yes" for m in metrics) else "no" for k in keyrows]
    po, kk = kappa(a, b)
    print(f"  any metric reported: agreement {po:.1%}  kappa {kk:.3f}  (first {a.count('yes')}, coder2 {b.count('yes')})")
    print("  disagreements:")
    for k in keyrows:
        d = [m for m in metrics if k[m] != ans[k["bibkey"]][m].strip()]
        if d:
            got = ans[k["bibkey"]]
            diffs = ", ".join(m + ": first=" + k[m] + " coder2=" + got[m].strip() for m in d)
            print(f"    #{k['n']:>2} {k['benchmark']:<20} {diffs}")


def screening_pair(path1, path2):
    """Both coders screened against the same written criteria (first author blind re-screen)."""
    keyrows = list(csv.DictReader(open(H / "screening_first_author.csv")))
    A, B = load(path1, "arxiv_id"), load(path2, "arxiv_id")
    for name, d in (("coder1", A), ("coder2", B)):
        miss = [k["id"] for k in keyrows if d.get(k["id"], {}).get("decision", "").strip() not in ("include", "exclude")]
        if miss:
            sys.exit(f"{name}: {len(miss)} records without a decision, e.g. {miss[:5]}")
    a = [A[k["id"]]["decision"].strip() for k in keyrows]
    b = [B[k["id"]]["decision"].strip() for k in keyrows]
    po, k = kappa(a, b)
    print(f"Abstract screening, same criteria, n = {len(a)} (stratified: 30 cited / 50 tool-titled uncited / 20 other)")
    print(f"  agreement {po:.1%}, Cohen's kappa {k:.3f}")
    table(a, b, ["include", "exclude"])
    for s in "ABC":
        idx = [i for i, r in enumerate(keyrows) if r["stratum"] == s]
        print(f"  stratum {s}: {sum(a[i] == b[i] for i in idx)}/{len(idx)} agree")
    print("  disagreements:")
    for i, r in enumerate(keyrows):
        if a[i] != b[i]:
            print(f"    #{r['n']:>3} {r['id']} [{r['stratum']}] coder1={a[i]} ({A[r['id']].get('reason', '')})"
                  f"  coder2={b[i]} ({B[r['id']].get('reason', '')})")


if __name__ == "__main__":
    if sys.argv[1] == "screening-pair":
        screening_pair(sys.argv[2], sys.argv[3])
    else:
        {"screening": screening, "audit": audit}[sys.argv[1]](sys.argv[2])

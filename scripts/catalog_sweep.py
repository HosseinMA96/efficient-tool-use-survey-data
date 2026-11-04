#!/usr/bin/env python3
"""Catalog sweep: does the better lever flip where the crossover T* says?

Each recorded trace keeps its actions and observations; only the tool catalog
is enlarged by appending m real function schemas from the Berkeley Function
Calling Leaderboard (BFCL v4 data, Apache-2.0,
github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard/bfcl_eval/data,
files *_multiple, *_live_multiple, *_simple_python, *_parallel_multiple).
For each catalog size we compare, on the exact trace (Eq. 2),
  retrieval: load the top-k tools (k * mean schema size) + 300 tokens/turn,
  filtering: pass 2% of tool-result tokens to the model,
and record which saves more.  Two predictions are scored against that winner:
  (a) the regime rule: retrieval wins iff T < T*(Ns)          (Eq. 5)
  (b) the mean-based model: rank the two levers with Eq. 3 using episode means.
Only cases where both levers apply are scored.

Usage: python3 -I catalog_sweep.py <taubench_dir> <swe_parquet> <bfcl_dir> <out_prefix>
"""
import glob
import json
import random
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trace_analysis import ntok, tool_schemas  # noqa: E402

RET_OVH, FILT = 300, 0.02
KS = (1, 3, 5)
PAD = [0, 25, 50, 100, 200, 300, 400, 600, 800, 1000, 1165]


def load_tau(tau_dir):
    eps = []
    for f in sorted(Path(tau_dir).glob("*.json")):
        model, dom = f.stem.rsplit("-", 1)
        tools = tool_schemas(Path(tau_dir) / f"tools_{dom}")
        Ns, n = ntok(json.dumps(tools)), len(tools)
        for ep in json.load(open(f)):
            traj = ep["traj"]
            P = ntok(traj[0]["content"])
            i, task = 1, 0
            while i < len(traj) and traj[i]["role"] != "assistant":
                task += ntok(str(traj[i].get("content", "")))
                i += 1
            acts, obs, fobs = [], [], []
            for m in traj[i:]:
                tok = ntok(str(m.get("content") or "")) + ntok(str(m.get("tool_calls") or ""))
                if m["role"] == "assistant":
                    acts.append(tok); obs.append(0); fobs.append(0)
                elif acts:
                    obs[-1] += tok
                    if m["role"] == "tool":
                        fobs[-1] += tok
            if len(acts) >= 2:
                eps.append(dict(src="tau-bench", P=P + task, Ns=Ns, n=n, acts=acts, obs=obs, fobs=fobs))
    return eps


def load_swe(parquet, limit=2000):
    import pyarrow.parquet as pq
    t = pq.read_table(parquet, columns=["trajectory"])
    eps = []
    for rec in t.slice(0, limit).to_pylist():
        traj = rec["trajectory"]
        P = ntok(traj[0].get("system_prompt") or traj[0].get("text") or "")
        i = 1
        while i < len(traj) and traj[i]["role"] != "ai":
            P += ntok(traj[i]["text"]); i += 1
        acts, obs = [], []
        for m in traj[i:]:
            tok = ntok(m["text"])
            if m["role"] == "ai":
                acts.append(tok); obs.append(0)
            elif acts:
                obs[-1] += tok
        if len(acts) >= 2:
            # command docs stay in P; padded tools form the retrievable catalog
            eps.append(dict(src="SWE-agent", P=P, Ns=0, n=0, acts=acts, obs=obs, fobs=list(obs)))
    return eps


def bfcl_pool(bfcl_dir, seed=0):
    names = {}
    for f in sorted(glob.glob(f"{bfcl_dir}/*.json")):
        for line in open(f):
            for fn in json.loads(line)["function"]:
                names.setdefault(fn["name"], fn)
    pool = [ntok(json.dumps({"type": "function", "function": fn})) for _, fn in sorted(names.items())]
    random.Random(seed).shuffle(pool)
    return pool


def evaluate(ep, add_tok, add_n, k):
    acts, obs, fobs = ep["acts"], ep["obs"], ep["fobs"]
    T = len(acts)
    Ns, n = ep["Ns"] + add_tok, ep["n"] + add_n
    S = ep["P"] + Ns
    w = [T - 1 - j for j in range(T)]                     # re-reads of turn-j tokens
    dyn = sum(wj * (a + r) for wj, a, r in zip(w, acts, obs))
    I = T * S + dyn
    s_bar = Ns / n
    ret_save = T * max(0.0, Ns - k * s_bar) - T * RET_OVH  # can be negative
    fil_save = (1 - FILT) * sum(wj * f for wj, f in zip(w, fobs))
    # mean-based (Eq. 3) predictions
    a_m = sum(acts[:-1]) / (T - 1)
    r_m = sum(obs[:-1]) / (T - 1)
    f_m = sum(fobs[:-1]) / (T - 1)
    ret_pred = T * max(0.0, Ns - k * s_bar) - T * RET_OVH
    fil_pred = (1 - FILT) * f_m * T * (T - 1) / 2
    tstar = 2 * S / (a_m + r_m) + 1
    return dict(T=T, S=S, Ns=Ns, tstar=tstar, I=I, ret=ret_save / I, fil=fil_save / I,
                ret_wins=ret_save > fil_save, rule=T < tstar, mean=ret_pred > fil_pred)


def main():
    tau_dir, swe_pq, bfcl_dir, out = sys.argv[1:5]
    pool = bfcl_pool(bfcl_dir)
    cum = [0]
    for x in pool:
        cum.append(cum[-1] + x)
    corpora = {"tau-bench": load_tau(tau_dir), "SWE-agent": load_swe(swe_pq)}
    rows = []
    for name, eps in corpora.items():
        for k in KS:
            for m in PAD:
                if name == "SWE-agent" and m == 0:
                    continue  # no catalog: retrieval does not apply
                res = [evaluate(e, cum[m], m, k) for e in eps]
                rows.append(dict(
                    corpus=name, k=k, pad=m, Ns_med=st.median(r["Ns"] for r in res),
                    tstar_med=st.median(r["tstar"] for r in res),
                    past_tstar=sum(not r["rule"] for r in res) / len(res),
                    ret_med=st.median(r["ret"] for r in res), fil_med=st.median(r["fil"] for r in res),
                    ret_wins=sum(r["ret_wins"] for r in res) / len(res),
                    rule_acc=sum(r["rule"] == r["ret_wins"] for r in res) / len(res),
                    mean_acc=sum(r["mean"] == r["ret_wins"] for r in res) / len(res)))
    # fine grid near the crossing, for the figure (k=3)
    fine = []
    for name, eps in corpora.items():
        for m in list(range(0, 101, 5)) + [125, 150, 200]:
            if name == "SWE-agent" and m == 0:
                continue
            res = [evaluate(e, cum[m], m, 3) for e in eps]
            fine.append(dict(corpus=name, pad=m, Ns_med=st.median(r["Ns"] for r in res),
                             ret_wins=sum(r["ret_wins"] for r in res) / len(res),
                             rule=sum(r["rule"] for r in res) / len(res),
                             mean=sum(r["mean"] for r in res) / len(res),
                             rule_acc=sum(r["rule"] == r["ret_wins"] for r in res) / len(res),
                             mean_acc=sum(r["mean"] == r["ret_wins"] for r in res) / len(res)))
    with open(out + "_fine.tsv", "w") as fh:
        cols = list(fine[0])
        fh.write("\t".join(cols) + "\n")
        for r in fine:
            fh.write("\t".join(f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c]) for c in cols) + "\n")
    # per-episode flip points (k=3): first catalog size at which the winner changes,
    # on the exact trace and in the mean-based prediction
    flips = []
    grid = [m for m in range(0, len(pool) + 1, 5)]
    for name, eps in corpora.items():
        for e in eps:
            prev, exact_flip, mean_flip, ratio = None, None, None, None
            for m in grid:
                if name == "SWE-agent" and m == 0:
                    continue
                r = evaluate(e, cum[m], m, 3)
                if prev is not None:
                    if exact_flip is None and r["ret_wins"] != prev["ret_wins"]:
                        exact_flip, ratio = r["Ns"], r["T"] / r["tstar"]
                    if mean_flip is None and r["mean"] != prev["mean"]:
                        mean_flip = r["Ns"]
                if exact_flip is not None and mean_flip is not None:
                    break
                prev = r
            if exact_flip is not None:
                flips.append(dict(corpus=name, Ns_flip=exact_flip, ratio_T_tstar=ratio,
                                  mean_flip=mean_flip))
    with open(out + "_grid.tsv", "w") as fh:
        cols = list(rows[0])
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c]) for c in cols) + "\n")
    print(f"BFCL pool: {len(pool)} schemas, {cum[-1]} tokens, mean {cum[-1]/len(pool):.0f}")
    for r in rows:
        if r["k"] == 3:
            print(json.dumps({c: (round(v, 3) if isinstance(v, float) else v) for c, v in r.items()}))
    for name in corpora:
        f = [x for x in flips if x["corpus"] == name]
        n_eps = len(corpora[name])
        if f:
            ratios = sorted(x["ratio_T_tstar"] for x in f)
            q = lambda p: ratios[int(p * (len(ratios) - 1))]
            print(f"{name}: flip found in {len(f)}/{n_eps} episodes; T/T* at flip "
                  f"p10={q(.1):.2f} p50={q(.5):.2f} p90={q(.9):.2f}; "
                  f"within 0.67-1.5: {sum(0.67 <= x <= 1.5 for x in ratios)/len(ratios):.1%}")
            mr = sorted(x["Ns_flip"] / x["mean_flip"] for x in f if x["mean_flip"])
            if mr:
                qm = lambda p: mr[int(p * (len(mr) - 1))]
                print(f"   exact flip Ns / mean-model flip Ns: p10={qm(.1):.2f} p50={qm(.5):.2f} "
                      f"p90={qm(.9):.2f}; within +-10%: {sum(0.9 <= x <= 1.1 for x in mr)/len(mr):.1%}")
    by_k = {}
    for r in rows:
        by_k.setdefault((r["corpus"], r["k"]), []).append(r)
    for (c, k), rs in by_k.items():
        print(f"{c} k={k}: rule acc (pooled over catalog sizes) {st.mean(x['rule_acc'] for x in rs):.3f}, "
              f"mean-model acc {st.mean(x['mean_acc'] for x in rs):.3f}")


if __name__ == "__main__":
    main()

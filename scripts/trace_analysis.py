#!/usr/bin/env python3
"""Test the cost model of Paper 3 against public agent traces.

Sources (downloaded separately; paths passed as arguments):
  * tau-bench historical trajectories (Sierra, MIT licence):
      github.com/sierra-research/tau-bench/tree/main/historical_trajectories
      {gpt-4o,sonnet-35-new}-{retail,airline}.json, plus the tool sources in
      tau_bench/envs/{retail,airline}/tools/*.py (parsed with ast, not executed)
  * SWE-agent trajectories (Nebius, CC-BY-4.0):
      huggingface.co/datasets/nebius/SWE-agent-trajectories, shard 00000

For every episode we measure the static prefix S = P + Ns (system prompt,
tool schemas, first user message), the number of model calls T, and the
per-turn action a_j and observation r_j (tool results and, in tau-bench,
simulated-user messages). We then compare
  * exact full-history input tokens  sum_t I_t  with the constant-mean
    prediction of Eq. (2);
  * the observed T with the crossover T* of Eq. (3) (regime classification);
  * counterfactual levers applied to the real trace (retrieval, filtering,
    turn merging with the same work), uncached and with prefix caching.
Tokens are counted with tiktoken o200k_base for all sources (an approximation
for non-OpenAI models).

Usage: python3 -I trace_analysis.py <taubench_dir> <swe_parquet> <out_prefix>
"""
import ast
import json
import math
import statistics as st
import sys
from pathlib import Path

import tiktoken

ENC = tiktoken.get_encoding("o200k_base")
KAPPA, OMEGA = 0.1, 0.25
K_TOP, RET_OVH, FILT = 3, 300, 0.02   # retrieval keeps the top-3 tools


def ntok(s):
    return len(ENC.encode(s, disallowed_special=())) if s else 0


# --------------------------------------------------------------- tau-bench tools
def tool_schemas(tool_dir):
    """Extract the dict returned by get_info() from each tool file via ast."""
    out = []
    for f in sorted(Path(tool_dir).glob("*.py")):
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_info":
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Return):
                        out.append(ast.literal_eval(sub.value))
    return out


# --------------------------------------------------------------- episode model
def episode(static, acts, obs, observ_filterable=None):
    """static: tokens; acts[j], obs[j]: tokens appended after model call j."""
    T = len(acts)
    exact = sum(static + sum(acts[:t]) + sum(obs[:t]) for t in range(T))
    a_bar = st.mean(acts[:-1]) if T > 1 else 0
    r_bar = st.mean(obs[:-1]) if T > 1 else 0
    pred = T * static + (a_bar + r_bar) * T * (T - 1) / 2
    tstar = 2 * static / (a_bar + r_bar) + 1 if a_bar + r_bar > 0 else math.inf
    hist = [a + r for a, r in zip(acts[:-1], obs[:-1])]
    dyn = sum(h * (T - 1 - j) for j, h in enumerate(hist))
    big = max(range(len(hist)), key=lambda j: obs[j]) if hist else None
    big_share = obs[big] * (T - 1 - big) / dyn if dyn else 0
    return dict(T=T, S=static, a=a_bar, r=r_bar, exact=exact, pred=pred,
                tstar=tstar, static_share=T * static / exact if exact else 0,
                big_share=big_share)


def cost(static, acts, obs, cached=False, fixed=None):
    """Input cost of a trace, in base-price token equivalents."""
    T = len(acts)
    if not cached:
        return sum(static + sum(acts[:t]) + sum(obs[:t]) for t in range(T))
    total = 0.0
    for t in range(T):
        prefix = static + sum(acts[:t]) + sum(obs[:t])
        if t == 0:
            total += (1 + OMEGA) * prefix
        elif fixed is None:
            prev = static + sum(acts[:t - 1]) + sum(obs[:t - 1])
            total += KAPPA * prev + (1 + OMEGA) * (prefix - prev)
        else:  # only `fixed` tokens survive in cache (tool list changes each turn)
            total += KAPPA * fixed + (1 + OMEGA) * (prefix - fixed)
    return total


def levers(P, Ns, task, acts, obs, filterable, n_tools=0):
    """Relative change of each counterfactual lever, uncached and cached."""
    static = P + Ns + task
    res = {}
    # mean-based predictions from Eq. (2) using episode means only
    T = len(acts)
    a_m = sum(acts[:-1]) / (T - 1)
    r_m = sum(obs[:-1]) / (T - 1)
    rf_m = sum(o for o, f in zip(obs[:-1], filterable[:-1]) if f) / (T - 1)
    eq2 = lambda S_, a_, r_, T_: T_ * S_ + (a_ + r_) * T_ * (T_ - 1) / 2
    b = eq2(static, a_m, r_m, T)
    res["ret_pred"] = eq2(P + (K_TOP * Ns / n_tools if n_tools else 0) + RET_OVH + task, a_m, r_m, T) / b - 1
    res["fil_pred"] = eq2(static, a_m, r_m - (1 - FILT) * rf_m, T) / b - 1
    for cached in (False, True):
        base = cost(static, acts, obs, cached)
        st_ret = P + (K_TOP * Ns / n_tools if n_tools else 0) + RET_OVH + task
        ret = cost(st_ret, acts, obs, cached)
        obs_f = [o * FILT if f else o for o, f in zip(obs, filterable)]
        fil = cost(static, acts, obs_f, cached)
        # halving with fixed work: merge consecutive turns pairwise (1+2, 3+4, ...),
        # summing their actions and observations; the same tokens enter the
        # history, but in half as many model calls
        ma = [sum(acts[i:i + 2]) for i in range(0, len(acts), 2)]
        mo = [sum(obs[i:i + 2]) for i in range(0, len(obs), 2)]
        hal = cost(static, ma, mo, cached)
        tag = "c" if cached else "u"
        res[f"ret_{tag}"] = ret / base - 1
        res[f"fil_{tag}"] = fil / base - 1
        res[f"hal_{tag}"] = hal / base - 1
        if cached:
            inv = cost(st_ret, acts, obs, True, fixed=P)
            res["ret_inv"] = inv / base - 1
            res["cache_saving"] = base / cost(static, acts, obs, False) - 1
    return res


# --------------------------------------------------------------- tau-bench
def tau(tau_dir):
    rows = []
    for f in sorted(Path(tau_dir).glob("*.json")):
        model, dom = f.stem.rsplit("-", 1)
        Ns = ntok(json.dumps(tool_schemas(Path(tau_dir) / f"tools_{dom}")))
        n_tools = len(tool_schemas(Path(tau_dir) / f"tools_{dom}"))
        for ep in json.load(open(f)):
            traj = ep["traj"]
            P = ntok(traj[0]["content"])
            i = 1
            task = 0
            while i < len(traj) and traj[i]["role"] != "assistant":
                task += ntok(str(traj[i].get("content", "")))
                i += 1
            acts, obs, filt = [], [], []
            for m in traj[i:]:
                tok = ntok(str(m.get("content") or "")) + ntok(str(m.get("tool_calls") or ""))
                if m["role"] == "assistant":
                    acts.append(tok)
                    obs.append(0)
                    filt.append(False)
                elif acts:
                    obs[-1] += tok
                    if m["role"] == "tool":
                        filt[-1] = True
            if len(acts) < 2:
                continue
            e = episode(P + Ns + task, acts, obs)
            e.update(levers(P, Ns, task, acts, obs, filt, n_tools))
            e.update(src="tau-bench", model=model, domain=dom, n_tools=n_tools,
                     Ns=Ns, P=P, success=ep["reward"] >= 1.0, out=sum(acts),
                     obs_all=obs[:-1])
            rows.append(e)
    return rows


# --------------------------------------------------------------- SWE-agent
def swe(parquet, limit=2000):
    import pyarrow.parquet as pq
    t = pq.read_table(parquet, columns=["model_name", "target", "trajectory"])
    rows = []
    for rec in t.slice(0, limit).to_pylist():
        traj = rec["trajectory"]
        sys_txt = traj[0].get("system_prompt") or traj[0].get("text") or ""
        P = ntok(sys_txt)  # command docs live in the system prompt (P + Ns)
        i, task = 1, 0
        while i < len(traj) and traj[i]["role"] != "ai":
            task += ntok(traj[i]["text"])
            i += 1
        acts, obs = [], []
        for m in traj[i:]:
            tok = ntok(m["text"])
            if m["role"] == "ai":
                acts.append(tok)
                obs.append(0)
            elif acts:
                obs[-1] += tok
        if len(acts) < 2:
            continue
        e = episode(P + task, acts, obs)
        e.update(levers(P, 0, task, acts, obs, [True] * len(obs)))
        e.update(src="SWE-agent", model=rec["model_name"], domain="swe",
                 n_tools=None, Ns=0, P=P, success=bool(rec["target"]),
                 out=sum(acts), obs_all=obs[:-1])
        rows.append(e)
    return rows


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * (len(xs) - 1)))]


def summarize(rows, key):
    groups = {}
    for r in rows:
        groups.setdefault(key(r), []).append(r)
    lines = []
    for g, rs in sorted(groups.items()):
        obs = [o for r in rs for o in r["obs_all"]]
        err = [r["pred"] / r["exact"] - 1 for r in rs]
        d = dict(
            group=g, n=len(rs), success=sum(r["success"] for r in rs) / len(rs),
            S_med=st.median(r["S"] for r in rs), T_med=st.median(r["T"] for r in rs),
            T_p90=q([r["T"] for r in rs], .9), a_med=st.median(r["a"] for r in rs),
            r_mean=st.mean(obs), r_med=st.median(obs), r_p99=q(obs, .99), r_max=max(obs),
            tstar_med=st.median(r["tstar"] for r in rs),
            frac_dynamic=sum(r["T"] > r["tstar"] for r in rs) / len(rs),
            static_share=st.median(r["static_share"] for r in rs),
            pred_err_med=st.median(err), pred_err_absp90=q([abs(x) for x in err], .9),
            big_share_med=st.median(r["big_share"] for r in rs),
            exact_mean=st.mean(r["exact"] for r in rs),
            cost_per_success=(st.mean(r["exact"] for r in rs) /
                              max(1e-9, sum(r["success"] for r in rs) / len(rs))),
        )
        for k in ("ret_u", "fil_u", "hal_u", "ret_c", "fil_c", "hal_c", "ret_inv",
                  "cache_saving"):
            # aggregate as ratio of totals is not available; use median relative change
            d[k] = st.median(r[k] for r in rs)
        d["rank_agree"] = sum((r["ret_pred"] < r["fil_pred"]) == (r["ret_u"] < r["fil_u"])
                              for r in rs) / len(rs)
        d["ret_pred_err"] = st.median(abs(r["ret_pred"] - r["ret_u"]) for r in rs)
        d["fil_pred_err"] = st.median(abs(r["fil_pred"] - r["fil_u"]) for r in rs)
        d["regime_agree"] = sum((r["T"] < r["tstar"]) == (r["ret_u"] < r["fil_u"])
                                for r in rs) / len(rs)
        d["Ns"] = st.median(r["Ns"] for r in rs)
        d["P_med"] = st.median(r["P"] for r in rs)
        lines.append(d)
    return lines


def main():
    tau_dir, swe_pq, out = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = tau(tau_dir) + swe(swe_pq)
    summ = summarize(rows, lambda r: f"{r['src']}|{r['domain']}|{r['model']}")
    summ += summarize(rows, lambda r: f"{r['src']}|ALL")
    cols = list(summ[0].keys())
    with open(out + "_summary.tsv", "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for d in summ:
            fh.write("\t".join(f"{d[c]:.4g}" if isinstance(d[c], float) else str(d[c])
                               for c in cols) + "\n")
    with open(out + "_episodes.tsv", "w") as fh:
        ec = ["src", "domain", "model", "success", "T", "S", "a", "r", "tstar", "exact",
              "pred", "static_share", "big_share", "ret_u", "fil_u", "hal_u", "ret_c",
              "fil_c", "hal_c", "ret_inv", "cache_saving", "ret_pred", "fil_pred"]
        fh.write("\t".join(ec) + "\n")
        for r in rows:
            fh.write("\t".join(f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c])
                               for c in ec) + "\n")
    for d in summ:
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v)
                          for k, v in d.items()}))


if __name__ == "__main__":
    main()

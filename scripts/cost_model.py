#!/usr/bin/env python3
"""Analytic computations for the cost model of Paper 3 (Section IV).

Reproduces every number in Section IV, Table II and Fig. 2, under the
"same work" convention: halving the number of turns T keeps the total
action and result tokens fixed, so per-turn a and r double.

Usage: python3 cost_model.py > cost_model_output.txt
"""
import math
import random

P, A_TOK = 2_000, 200
SCEN = {
    "A": dict(Ns=134_000, r=1_000),   # large catalog, small results
    "B": dict(Ns=5_000, r=10_000),    # small catalog, large results
}
T0 = 20
KAPPA, OMEGA = 0.1, 0.25   # cached-read multiplier, cache-write premium (illustrative)
RET_FRAC, RET_OVH = 0.05, 300   # retrieval loads 5% of schemas, 300-token overhead/turn
FILT = 0.02                      # filtering passes 2% of result tokens


def uncached(S, a, r, T):
    """Total input tokens, Eq. (2)."""
    return T * S + (a + r) * T * (T - 1) / 2


def cached(S, a, r, T, kappa=KAPPA, omega=OMEGA, S_fixed=None):
    """Input cost in base-price token equivalents with prefix caching.

    New tokens (first appearance) are written at (1+omega); every later re-read
    of the append-only prefix is read at kappa.  If S_fixed is given, only that
    part of the static prefix survives between turns (the rest, and therefore
    the whole history behind it, is invalidated every turn).
    """
    if S_fixed is None:
        new = S + (T - 1) * (a + r)
        reread = (T - 1) * S + (a + r) * (T - 1) * (T - 2) / 2
        return (1 + omega) * new + kappa * reread
    # invalidated every turn: only S_fixed is re-read from cache
    new = T * (S - S_fixed) + S_fixed + (a + r) * T * (T - 1) / 2
    reread = (T - 1) * S_fixed
    return (1 + omega) * new + kappa * reread


def tstar(S, a, r):
    return 2 * S / (a + r) + 1


def levers(name, Ns, r, T=T0, cost=uncached, **kw):
    S = P + Ns
    base = cost(S, A_TOK, r, T, **kw)
    out = {"base": base}
    S_ret = P + RET_FRAC * Ns + RET_OVH
    out["retrieval"] = cost(S_ret, A_TOK, r, T, **kw)
    out["filtering"] = cost(S, A_TOK, FILT * r, T, **kw)
    out["halve_same_work"] = cost(S, 2 * A_TOK, 2 * r, T // 2, **kw)
    out["halve_half_work"] = cost(S, A_TOK, r, T // 2, **kw)
    return out


def pct(x, b):
    return f"{100 * (x - b) / b:+.1f}%"


print("== Uncached, T=20 (Table II) ==")
for k, v in SCEN.items():
    o = levers(k, **v)
    S = P + v["Ns"]
    print(f"Scenario {k}: base {o['base']/1e6:.3f}M  T*={tstar(S, A_TOK, v['r']):.1f}")
    for lv in ("retrieval", "filtering", "halve_same_work", "halve_half_work"):
        print(f"   {lv:16s} {o[lv]/1e6:.3f}M  {pct(o[lv], o['base'])}")

print("\n== Prefix caching (kappa=%.2f, omega=%.2f), T=20 ==" % (KAPPA, OMEGA))
for k, v in SCEN.items():
    S = P + v["Ns"]
    unc = uncached(S, A_TOK, v["r"], T0)
    o = levers(k, cost=cached, **v)
    print(f"Scenario {k}: base {o['base']/1e6:.3f}M equiv ({pct(o['base'], unc)} vs uncached)")
    for lv in ("retrieval", "filtering", "halve_same_work"):
        print(f"   {lv:16s} {o[lv]/1e6:.3f}M  {pct(o[lv], o['base'])}")
    # retrieval whose tool set changes every turn: only P survives in the cache
    S_ret = P + RET_FRAC * v["Ns"] + RET_OVH
    inv = cached(S_ret, A_TOK, v["r"], T0, S_fixed=P)
    print(f"   retrieval, cache invalidated each turn {inv/1e6:.3f}M  {pct(inv, o['base'])}")
    # new-token floor
    floor = (1 + OMEGA) * (S + (T0 - 1) * (A_TOK + v["r"]))
    print(f"   new-token (write) share of cached cost: {floor/o['base']:.0%}")
Tk = 2 * (1 + OMEGA) / KAPPA + 2
print(f"Cache horizon T_kappa = 2(1+omega)/kappa + 2 = {Tk:.0f}")
for kap, om in ((0.1, 0.25), (0.1, 0.0), (0.25, 0.0), (0.5, 0.0)):
    print(f"   kappa={kap}, omega={om}: T_kappa={2*(1+om)/kap+2:.0f}")

print("\n== Output and reasoning tokens (gamma = c_out/c_in) ==")
for gamma in (4, 5):
    for b in (0, 1_000, 3_000):
        for k, v in SCEN.items():
            S = P + v["Ns"]
            out = gamma * T0 * (A_TOK + b)
            for lab, inp in (("uncached", uncached(S, A_TOK, v["r"], T0)),
                             ("cached", cached(S, A_TOK, v["r"], T0))):
                print(f"   gamma={gamma} b={b:5d} {k} {lab:8s}: output share {out/(out+inp):.0%}")

print("\n== Cost per success: break-even success ratio p'/p = 1 - f ==")
for f in (0.86, 0.5, 0.3, 0.06):
    print(f"   saving {f:.0%}: pays off iff p'/p > {1-f:.2f}")

print("\n== Heavy-tailed results: Monte Carlo, T=20, mean r=1000 (100k episodes) ==")
random.seed(0)
for sigma in (0.0, 1.0, 1.5, 2.0):
    mu = math.log(1000) - sigma ** 2 / 2
    with_a, r_only = [], []
    for _ in range(100000):
        rs = [math.exp(random.gauss(mu, sigma)) if sigma else 1000.0 for _ in range(T0)]
        dyn_r = sum(rs[j] * (T0 - 1 - j) for j in range(T0 - 1))
        r_only.append(dyn_r)
        with_a.append(dyn_r + A_TOK * T0 * (T0 - 1) / 2)
    for lab, vals, pred in (("results only", r_only, 1000 * T0 * (T0 - 1) / 2),
                            ("incl. a=200", with_a, (A_TOK + 1000) * T0 * (T0 - 1) / 2)):
        vals.sort()
        q = lambda p: vals[int(p * (len(vals) - 1))] / pred
        print(f"   sigma={sigma} {lab:13s}: p10={q(.1):.2f} p50={q(.5):.2f} p90={q(.9):.2f} p99={q(.99):.2f}")
print("   one 50k-token result at turn 2 of 20 adds", 50_000 * (T0 - 2), "tokens")

print("\n== Fig. 2 series (uncached), T*: A=%.1f B=%.1f ==" % (
    tstar(P + 134_000, A_TOK, 1_000), tstar(P + 5_000, A_TOK, 10_000)))
for T in range(5, 61, 5):
    a = uncached(P + 134_000, A_TOK, 1_000, T)
    b = uncached(P + 5_000, A_TOK, 10_000, T)
    print(f"   T={T:2d} A={a/1e6:.3f} Astat={T*(P+134_000)/1e6:.3f} B={b/1e6:.3f} Bstat={T*(P+5_000)/1e6:.3f}")

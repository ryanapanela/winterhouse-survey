"""Winterhouse multilayer network analysis.

Usage:  python3 tools/analyze.py TIDY_DIR [OUT_DIR]
TIDY_DIR is the folder flatten.py writes (winterhouse-data/tidy). Writes OUT_DIR/results.json
(everything the reveal needs) and OUT_DIR/pairs.csv, OUT_DIR/people.csv for your own digging.

Layers (same 16 people, one map each):
  connection  what the two of you report: closeness 40% + shared time 35% + support 25%
  alignment   how alike two people answered the 50 Part 1 items
  knowing     prediction-game accuracy + how well each guessed the other's words
  trust       Traitors ally trust (A5), both directions
  perception  pairs the group named: closest, unexpected, most alike, confessional duo
  suspicion   D10 picks (directed, kept apart: it is a negative tie)
Every layer is expressed as a percentile across pairs, so layers can be compared and combined.
THE NETWORK combines them: each pair's tie = mean of the switched-on layer percentiles (all five
positive layers by default; suspicion optional, as a penalty). Hubs, circles and roles come from it,
and results.json holds every on/off combination so the reveal can toggle layers live.
"""
import itertools, json, os, sys
from collections import Counter, defaultdict
import numpy as np, pandas as pd, networkx as nx
from networkx.algorithms.community import louvain_communities
from scipy.stats import spearmanr, rankdata
from sklearn.metrics import adjusted_rand_score

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from survey_items import LIKERT_IDS, TOT_IDS, ITEM_TEXT, WORDS, WORD_CODE, SUPPORT_QS, HOST, G_QS  # noqa: E402
from prediction_design import NAMES  # noqa: E402

TIDY = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(TIDY)), "analysis")
os.makedirs(OUT, exist_ok=True)
rd = lambda f: pd.read_csv(os.path.join(TIDY, f"{f}.csv"))
AL, DY, WD, PR, NOM, PRS = rd("alignment"), rd("dyads"), rd("words"), rd("predictions"), rd("nominations"), rd("pairs")
PLAYERS = [n for n in NAMES if n != HOST]
PAIRS = [tuple(sorted(p)) for p in itertools.combinations(NAMES, 2)]
key = lambda a, b: tuple(sorted((a, b)))
W_MAIN = {"closeness": .40, "time": .35, "support": .25}   # E1 lives in the perception layer, not here
LAYERS = ["connection", "alignment", "knowing", "trust", "perception"]
# How much each layer counts in the combined network (relative). Equal by default: every layer is
# already a percentile, and connection, knowing and trust overlap, so closeness is not under-counted.
LAYER_WEIGHTS = {"connection": 1, "alignment": 1, "knowing": 1, "trust": 1, "perception": 1, "no_suspicion": 1}

def pct(series):
    """Percentile rank (0–1) of each non-missing value; missing stays missing."""
    s = pd.Series(series, dtype=float); m = s.notna(); out = pd.Series(np.nan, index=s.index)
    if m.sum() > 1: out[m] = (rankdata(s[m]) - 1) / (m.sum() - 1)
    return out

P = pd.DataFrame(PAIRS, columns=["a", "b"]).set_index(["a", "b"])

# ---------------- connection facets ----------------
dy = DY.pivot_table(index=["rater", "target"], columns="measure", values="value", aggfunc="first")
ios = dy["ios"].dropna().reset_index()
ios["z"] = ios.groupby("rater")["ios"].transform(lambda x: (x - x.mean()) / (x.std() or 1))
zmap = {(r.rater, r.target): r.z for r in ios.itertuples()}
def both(m, a, b):
    v = [m[k] for k in [(a, b), (b, a)] if k in m and pd.notna(m[k])]
    return np.mean(v) if v else np.nan
P["closeness"] = [both(zmap, a, b) for a, b in P.index]
tmap = {k: v for k, v in dy["time"].dropna().items()}
hmap = {k: v for k, v in dy["history"].dropna().items()} if "history" in dy else {}
P["time"] = [.75 * (both(tmap, a, b) - 1) / 4 + .25 * ((both(hmap, a, b) if hmap else 1) - 1) / 4 for a, b in P.index]
sup = NOM[NOM.question.isin(SUPPORT_QS)]
sc = Counter(key(r.rater, r.target) for r in sup.itertuples())
P["support"] = [sc.get(k, 0) for k in P.index]
e1 = Counter(key(r.a, r.b) for r in PRS[PRS.question == "E01"].itertuples())
P["view"] = [e1.get(k, 0) for k in P.index]
for f in W_MAIN: P[f + "_p"] = pct(P[f].values).values
def composite(w): return sum(w[f] * P[f + "_p"] for f in w) / sum(w.values())
P["connection"] = composite(W_MAIN)

# ---------------- alignment ----------------
A = AL.pivot_table(index="person", columns="item", values="value", aggfunc="first")
def align(a, b):
    num = den = 0.0
    for it in LIKERT_IDS:
        if it in A and pd.notna(A.at[a, it]) and pd.notna(A.at[b, it]):
            num += 1 - abs(float(A.at[a, it]) - float(A.at[b, it])) / 4; den += 1
    for it in TOT_IDS:
        if it in A and pd.notna(A.at[a, it]) and pd.notna(A.at[b, it]):
            num += .5 * (A.at[a, it] == A.at[b, it]); den += .5
    return num / den if den else np.nan
P["alignment_raw"] = [align(a, b) if a in A.index and b in A.index else np.nan for a, b in P.index]
P["alignment"] = pct(P["alignment_raw"].values).values

# ---------------- knowing ----------------
def item_score(item, guess, actual):
    if item in LIKERT_IDS: return 1 - abs(float(guess) - float(actual)) / 4
    return float(str(guess) == str(actual))
PR["actual"] = [A.at[t, it] if t in A.index and it in A else np.nan for t, it in zip(PR.target, PR.item)]
PR = PR.dropna(subset=["actual"]).copy()
PR["score"] = [item_score(i, g, a) for i, g, a in zip(PR.item, PR.guess, PR.actual)]
PR["own"] = [A.at[p, it] if p in A.index else np.nan for p, it in zip(PR.predictor, PR.item)]
PR["own_score"] = [item_score(i, g, o) if pd.notna(o) else np.nan for i, g, o in zip(PR.item, PR.guess, PR.own)]
dacc = PR.groupby(["predictor", "target"]).score.mean()
P["pred_acc"] = [both(dacc.to_dict(), a, b) for a, b in P.index]
w_words = WD[WD.kind == "words"].groupby(["rater", "target"]).word.apply(set).to_dict()
w_meta = WD[WD.kind == "meta"].groupby(["rater", "target"]).word.apply(set).to_dict()
meta_acc = {}  # (A, B): how well A guessed B's words for A
for (r, t), guess in w_meta.items():
    actual = w_words.get((t, r))
    if actual: meta_acc[(r, t)] = len(guess & actual) / 3
P["word_acc"] = [both(meta_acc, a, b) for a, b in P.index]
P["knowing"] = pd.concat([pct(P["pred_acc"].values), pct(P["word_acc"].values)], axis=1).mean(axis=1, skipna=True).values

# ---------------- trust, perception, suspicion ----------------
trust = {k: v for k, v in dy["trust"].dropna().items()} if "trust" in dy else {}
P["trust_raw"] = [both(trust, a, b) if HOST not in (a, b) else np.nan for a, b in P.index]
P["trust"] = pct(P["trust_raw"].values).values
perc = Counter(key(r.a, r.b) for r in PRS[PRS.question.isin(["E01", "E02", "E04", "E07"])].itertuples())
P["perception_raw"] = [perc.get(k, 0) for k in P.index]
P["perception"] = pct(P["perception_raw"].values).values
susp = NOM[NOM.question == "D10"]
suspicion_edges = [(r.rater, r.target) for r in susp.itertuples()]

# ---------------- the combined network ----------------
# The network every map, hub, circle and role comes from: each pair's tie is the mean of the
# layer percentiles that are switched on. Suspicion enters as "no suspicion" (1 − its percentile),
# so pairs who suspect each other get weaker ties. It is off by default.
sus_pair = Counter(key(a, b) for a, b in suspicion_edges)
P["suspicion_raw"] = [sus_pair.get(k, 0) for k in P.index]
P["no_suspicion"] = 1 - pct(P["suspicion_raw"].values).values
TOGGLES = LAYERS + ["no_suspicion"]
DEFAULT_ON = list(LAYERS)
def combo_key(on): return "".join("1" if t in on else "0" for t in TOGGLES)
def network_col(on, src=None):
    """Add the combined score for the layers in `on` as a column; return its name."""
    name = "net_" + combo_key(on)
    X = (src if src is not None else P)[list(on)]
    w = pd.Series({t: LAYER_WEIGHTS[t] for t in on})
    num = X.mul(w, axis=1).sum(axis=1, skipna=True); den = X.notna().mul(w, axis=1).sum(axis=1)
    P[name] = num / den.replace(0, np.nan)          # weighted mean over the layers this pair has
    return name

def backbone(col, top_share=.38, per_person=2):
    s = P[col].dropna(); thr = s.quantile(1 - top_share); keep = set(s[s >= thr].index)
    for n in NAMES:
        mine = s[[k for k in s.index if n in k]]
        keep |= set(mine.nlargest(per_person).index)
    G = nx.Graph(); G.add_nodes_from(NAMES)
    for a, b in keep:
        w = float(P.at[(a, b), col]); G.add_edge(a, b, weight=w, dist=1 / max(w, .05))
    return G
def strength(col): return {n: float(P[col][[k for k in P.index if n in k]].sum(skipna=True)) for n in NAMES}
def communities(G, seeds=50):
    runs = [louvain_communities(G, weight="weight", seed=s) for s in range(seeds)]
    lab = lambda run: {n: i for i, c in enumerate(sorted(run, key=len, reverse=True)) for n in c}
    labs = [lab(r) for r in runs]
    co = {k: np.mean([l[k[0]] == l[k[1]] for l in labs]) for k in PAIRS}
    best = max(runs, key=lambda r: nx.algorithms.community.modularity(G, r, weight="weight"))
    return lab(best), co, nx.algorithms.community.modularity(G, best, weight="weight")

def analyse(col, seeds=50):
    """Backbone, centrality, circles and roles for one network column."""
    G = backbone(col); comm, co, Q = communities(G, seeds)
    st = strength(col); btw = nx.betweenness_centrality(G, weight="dist")
    try: eig = nx.eigenvector_centrality_numpy(G, weight="weight")
    except Exception: eig = dict.fromkeys(NAMES, 0.0)
    part = {}
    for n in NAMES:
        tot = sum(d["weight"] for *_, d in G.edges(n, data=True)) or 1
        byc = defaultdict(float)
        for _, m, d in G.edges(n, data=True): byc[comm[m]] += d["weight"]
        part[n] = 1 - sum((v / tot) ** 2 for v in byc.values())
    srank = pd.Series(st).rank(ascending=False); brank = pd.Series(btw).rank(ascending=False)
    q25 = np.percentile(list(st.values()), 25)
    def role(n):
        if srank[n] <= 2: return "Hub"
        if brank[n] <= 3 and part[n] >= .35: return "Bridge"
        if st[n] < q25: return "Floater"
        if part[n] >= .5: return "Free agent"
        return "Core"
    stab = {n: float(np.mean([co[key(n, m)] for m in NAMES if m != n and comm[m] == comm[n]] or [1])) for n in NAMES}
    return dict(G=G, comm=comm, Q=Q, st=st, btw=btw, eig=eig, part=part, roles={n: role(n) for n in NAMES}, stab=stab)

NET = network_col(DEFAULT_ON)
M = analyse(NET)
Gc, comm, Q, st, btw, eig, part, roles, stability = (M[k] for k in ["G", "comm", "Q", "st", "btw", "eig", "part", "roles", "stab"])

# every on/off combination of the six toggles, so the reveal page can switch layers live
combos = {}
for r in range(1, len(TOGGLES) + 1):
    for on in itertools.combinations(TOGGLES, r):
        if on == ("no_suspicion",): continue
        col = network_col(on); m = analyse(col, seeds=10)
        combos[combo_key(on)] = dict(
            edges=[[u, v, round(d["weight"], 3)] for u, v, d in m["G"].edges(data=True)],
            people={n: [m["comm"][n], m["roles"][n], round(m["st"][n], 2), round(m["btw"][n], 3)] for n in NAMES},
            modularity=round(m["Q"], 3),
            rank_rho_vs_default=round(float(spearmanr([st[n] for n in NAMES], [m["st"][n] for n in NAMES])[0]), 3),
            circles_ari_vs_default=round(adjusted_rand_score([comm[n] for n in NAMES], [m["comm"][n] for n in NAMES]), 3))
        P.drop(columns=col, inplace=True, errors="ignore") if col != NET else None
leave_one_out = [dict(dropped=t, rank_rho=combos[combo_key([x for x in DEFAULT_ON if x != t])]["rank_rho_vs_default"],
                      circles_ari=combos[combo_key([x for x in DEFAULT_ON if x != t])]["circles_ari_vs_default"]) for t in DEFAULT_ON]

# robustness of the connection layer's own weights (effect on the combined network)
schemes = {"Main": W_MAIN, "Equal": dict.fromkeys(W_MAIN, 1 / 3),
           "Feelings-heavy": {"closeness": .6, "time": .2, "support": .2},
           "Behaviour-heavy": {"closeness": .2, "time": .6, "support": .2}}
X = P[[f + "_p" for f in W_MAIN]].values; Xc = (X - X.mean(0)) / X.std(0)
ev, evec = np.linalg.eigh(np.cov(Xc.T)); pc = np.abs(evec[:, -1]) / np.abs(evec[:, -1]).sum()
schemes["PCA-derived"] = dict(zip(W_MAIN, pc.round(3)))
robust = []
for name, w in schemes.items():
    keep = P["connection"].copy(); P["connection"] = composite(w)
    network_col(DEFAULT_ON); P["_tmp"] = P[NET]; P["connection"] = keep; network_col(DEFAULT_ON)
    m = analyse("_tmp", seeds=10)
    robust.append(dict(scheme=name, weights={k: float(v) for k, v in w.items()},
                       rank_rho=round(spearmanr([st[n] for n in NAMES], [m["st"][n] for n in NAMES])[0], 3),
                       circles_ari=round(adjusted_rand_score([comm[n] for n in NAMES], [m["comm"][n] for n in NAMES]), 3)))
P.drop(columns="_tmp", inplace=True)

# ---------------- multilayer ----------------
layer_graphs = {l: backbone(l) for l in LAYERS}
layer_strength = {l: strength(l) for l in LAYERS}
def _layer_rank(l):
    names = PLAYERS if l == "trust" else NAMES          # the host has no trust ratings
    r = pd.Series({n: layer_strength[l][n] for n in names}).rank(ascending=False).astype(int).to_dict()
    return {n: r.get(n) for n in NAMES}
layer_rank = {l: _layer_rank(l) for l in LAYERS}
def _rho(l1, l2):
    if l1 == l2: return 1.0
    d = P[[l1, l2]].dropna(); return round(float(spearmanr(d[l1], d[l2])[0]), 2)
agree = {l1: {l2: _rho(l1, l2) for l2 in LAYERS} for l1 in LAYERS}
P["overall"] = P[LAYERS].mean(axis=1, skipna=True)
P["n_strong"] = (P[LAYERS] >= .75).sum(axis=1)
people_layers = {n: {l: layer_rank[l][n] for l in LAYERS} for n in NAMES}
everywhere = [n for n in NAMES if sum(r is not None and r <= 5 for r in people_layers[n].values()) >= 4]
specialists = [dict(person=n, layer=l) for n in NAMES for l in LAYERS[1:]
               if layer_rank[l][n] is not None and layer_rank[l][n] <= 2 and layer_rank["connection"][n] > 8]
C = dict(zip(P.index, P["connection"]))
def broker(a, b):
    best = max((min(C[key(a, k)], C[key(b, k)]), k) for k in NAMES if k not in (a, b)); return best[1]
d5 = Counter((r.rater, r.target) for r in NOM[NOM.question == "D05"].itertuples())
e3 = Counter(key(r.a, r.b) for r in PRS[PRS.question == "E03"].itertuples())
def pairs_where(cond, n=6, sort="overall"):
    sub = P[cond].sort_values(sort, ascending=False).head(n)
    return [dict(a=a, b=b, **{l: (None if pd.isna(r[l]) else round(float(r[l]) * 100)) for l in LAYERS}) for (a, b), r in sub.iterrows()]
P["unexpected_score"] = P["alignment"] - P["connection"] + .15 * pd.Series(
    [(d5.get((a, b), 0) > 0) + (d5.get((b, a), 0) > 0) for a, b in P.index], index=P.index) + .1 * pd.Series([e3.get(k, 0) for k in P.index], index=P.index)
unexpected = pairs_where((P.alignment >= .7) & (P.connection <= .4), 8, "unexpected_score")
for u in unexpected:
    u["introducer"] = broker(u["a"], u["b"]); u["mutual_interest"] = int(d5.get((u["a"], u["b"]), 0) > 0) + int(d5.get((u["b"], u["a"]), 0) > 0)
    u["group_flagged"] = e3.get(key(u["a"], u["b"]), 0)
mismatches = {
    "close_but_unread": pairs_where((P.connection >= .75) & (P.knowing <= .35), 5, "connection"),
    "trust_without_closeness": pairs_where((P.trust >= .75) & (P.connection <= .35), 5, "trust"),
    "close_but_wary": pairs_where((P.connection >= .75) & (P.trust <= .3), 5, "connection"),
}
power_duos = pairs_where(P.n_strong >= 3, 6, "overall")

# ---------------- other reveals ----------------
acc = (PR.groupby("predictor").score.mean() * 100).round(1)
read = (PR.groupby("target").score.mean() * 100).round(1)
proj = (PR.own_score - PR.score).groupby(PR.predictor).mean().round(3)  # > 0: guesses look more like your own answers
duels = []
for a, b in PAIRS:
    if (a, b) in dacc and (b, a) in dacc:
        duels.append(dict(a=a, b=b, a_acc=round(dacc[(a, b)] * 100), b_acc=round(dacc[(b, a)] * 100)))
received = WD[WD.kind == "words"].groupby("target").word.apply(list)
traitor_vibe = {n: round(100 * np.mean([WORD_CODE[w] == "traitor" for w in received.get(n, [])]), 1) for n in NAMES if n in received}
top_words = {n: [w for w, _ in Counter(received.get(n, [])).most_common(3)] for n in NAMES}
selfw = WD[WD.kind == "self"].groupby("rater").word.apply(set).to_dict()
self_other = {n: len(selfw.get(n, set()) & set(top_words[n])) for n in NAMES}
meta_person = pd.Series(meta_acc).groupby(level=0).mean().mul(100).round(1).to_dict()
trust_in = DY[DY.measure == "trust"].groupby("target").value.mean().round(2).to_dict()
susp_in = Counter(t for _, t in suspicion_edges)
gaps = {}
for (r, t), mt in (dy["metaTrust"].dropna().items() if "metaTrust" in dy else []):
    if (t, r) in trust: gaps.setdefault(r, []).append(mt - trust[(t, r)])
trust_gap = {n: round(float(np.mean(v)), 2) for n, v in gaps.items()}
one_sided = [dict(truster=a, suspects_back=b) for (a, b), v in trust.items() if v >= 4 and (b, a) in set(suspicion_edges)]
pct_series = lambda d: pct(pd.Series(d)).to_dict()
s_pct, b_pct = pct_series(st), pct_series(btw)
def guess_scores(qid, truth):
    out = {}
    for r in NOM[NOM.question == qid].itertuples(): out[r.rater] = round(truth.get(r.target, 0) * 100)
    for r in PRS[PRS.question == qid].itertuples(): out[r.rater] = round(float(P.at[key(r.a, r.b), "alignment"]) * 100)
    return out
guessing = {"E04_most_alike": guess_scores("E04", None)}
grown_most = [dict(name=n, votes=v) for n, v in Counter(NOM[NOM.question == "E10"].target).most_common(3)]
AWARD_TITLE = {g[0]: g[1] for g in G_QS}
awards = {q: dict(title=AWARD_TITLE.get(q, q), finalists=[dict(name=n, votes=v) for n, v in Counter(NOM[NOM.question == q].target).most_common(3)])
          for q in sorted(NOM.question.unique()) if q.startswith("G")}
fun = {q: [dict(name=n, votes=v) for n, v in Counter(NOM[NOM.question == q].target).most_common(3)] for q in ["D06", "D07", "D08", "D09", "D11", "D13"]}
splits = []
for it in LIKERT_IDS + TOT_IDS:
    if it not in A: continue
    col = A[it].dropna()
    if it in LIKERT_IDS:
        yes, no = list(col[col.astype(float) >= 4].index), list(col[col.astype(float) <= 2].index)
    else:
        yes, no = list(col[col == "a"].index), list(col[col == "b"].index)
    splits.append(dict(item=it, text=ITEM_TEXT[it], side_a=yes, side_b=no, balance=min(len(yes), len(no))))
splits = sorted(splits, key=lambda s: -s["balance"])[:6]

# ---------------- layout + output ----------------
pos3 = nx.spring_layout(Gc, dim=3, weight="weight", seed=11, k=.55, iterations=300)
c3 = np.array(list(pos3.values())); c3 = (c3 - c3.mean(0)) / (np.abs(c3 - c3.mean(0)).max() or 1)
pos3 = {n: [round(float(v), 4) for v in c3[i]] for i, n in enumerate(pos3)}
pos = nx.spring_layout(Gc, weight="weight", seed=11, k=.55, iterations=300)
xs, ys = np.array([p[0] for p in pos.values()]), np.array([p[1] for p in pos.values()])
pos = {n: ((p[0] - xs.min()) / (np.ptp(xs) or 1), (p[1] - ys.min()) / (np.ptp(ys) or 1)) for n, p in pos.items()}
r2 = lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 3)
res = dict(
    names=NAMES, host=HOST, modularity=round(Q, 3), pc1_share=round(float(ev[-1] / ev.sum()), 3),
    toggles=TOGGLES, default_on=DEFAULT_ON, layer_weights=LAYER_WEIGHTS, connection_weights=W_MAIN, combos=combos, leave_one_out=leave_one_out,
    people=[dict(id=n, x=round(pos[n][0], 4), y=round(pos[n][1], 4), xyz=pos3[n], circle=comm[n], role=roles[n],
                 strength=round(st[n], 2), betweenness=round(btw[n], 3), eigenvector=round(float(eig[n]), 3),
                 participation=round(part[n], 3), circle_stability=round(stability[n], 2),
                 layer_rank=people_layers[n], layer_strength={l: round(layer_strength[l][n], 2) for l in LAYERS},
                 accuracy=acc.get(n), readability=read.get(n), projection=r2(proj.get(n)),
                 top_words=top_words[n], traitor_vibe=traitor_vibe.get(n), self_other_match=self_other[n],
                 word_meta_accuracy=meta_person.get(n), trust_received=trust_in.get(n), suspicion_received=susp_in.get(n, 0),
                 trust_gap=trust_gap.get(n)) for n in NAMES],
    pairs=[dict(a=a, b=b, **{l: r2(r[l]) for l in LAYERS}, no_suspicion=r2(r["no_suspicion"]), network=r2(r[NET]), n_strong=int(r["n_strong"])) for (a, b), r in P.iterrows()],
    layer_edges={l: [dict(a=u, b=v, w=round(d["weight"], 3)) for u, v, d in g.edges(data=True)] for l, g in layer_graphs.items()},
    suspicion=[dict(a=a, b=b) for a, b in suspicion_edges],
    layer_agreement=agree, everywhere=everywhere, specialists=specialists, power_duos=power_duos,
    unexpected_pairings=unexpected, mismatches=mismatches, robustness=robust,
    duels=sorted(duels, key=lambda d: -abs(d["a_acc"] - d["b_acc"])), guessing=guessing, grown_most=grown_most,
    one_sided_alliances=one_sided, awards=awards, fun_picks=fun, splits=splits,
)
truth_path = os.path.join(os.path.dirname(os.path.abspath(TIDY)), "hidden_truth.json")
if os.path.exists(truth_path):  # simulation only: did the pipeline recover the planted structure?
    T = json.load(open(truth_path)); ix = {n: i for i, n in enumerate(T["names"])}
    truth = [T["latent_closeness"][ix[a]][ix[b]] for a, b in P.index]
    res["simulation_check"] = dict(connection_vs_truth_rho=round(float(spearmanr(P["connection"], truth)[0]), 3),
                                   network_vs_truth_rho=round(float(spearmanr(P[NET], truth)[0]), 3))
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
P.reset_index().round(4).to_csv(os.path.join(OUT, "pairs.csv"), index=False)
pd.DataFrame(res["people"]).drop(columns=["layer_rank", "layer_strength", "top_words"]).to_csv(os.path.join(OUT, "people.csv"), index=False)

print(f"Wrote {OUT}/results.json, pairs.csv, people.csv")
print("Hubs:", [n for n in NAMES if roles[n] == "Hub"], "| Bridges:", [n for n in NAMES if roles[n] == "Bridge"],
      "| Floaters:", [n for n in NAMES if roles[n] == "Floater"], f"| modularity {Q:.2f}")
print("Layer agreement (Spearman over pairs):")
print(pd.DataFrame(agree).to_string())
print("Connection-weight robustness:", [(r["scheme"], r["rank_rho"], r["circles_ari"]) for r in robust])
print("Leave one layer out:", [(r["dropped"], r["rank_rho"], r["circles_ari"]) for r in leave_one_out])
if "simulation_check" in res: print("Simulation check:", res["simulation_check"])

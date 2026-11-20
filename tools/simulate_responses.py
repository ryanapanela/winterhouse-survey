"""Write fake survey submissions in exactly the format the live site saves.

Usage:  python3 tools/simulate_responses.py OUT_DIR [--seed 2026]
Creates OUT_DIR/responses/part1/<Name>.json and part2/<Name>.json, so the real pipeline
(flatten.py -> analyze.py) can be tested end to end. Friend groups are random:
the output says nothing about the real people.
"""
import argparse, itertools, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prediction_design as pdz  # noqa: E402
from survey_items import LIKERT_IDS, TOT_IDS, WORDS, WORD_CODE, BLOCKS, D_QS, E_QS, G_QS, HOST, NON_PLAYERS, AWAY, WEEKEND_ONLY  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--seed", type=int, default=2026)
a = ap.parse_args()
R = np.random.default_rng(a.seed)
NAMES = pdz.NAMES
N = len(NAMES)
ix = {n: i for i, n in enumerate(NAMES)}
PLAYERS = [n for n in NAMES if n not in NON_PLAYERS]
ATCOTTAGE = [n for n in NAMES if n not in AWAY]

# ---- hidden truth: 3 circles, 2 bridges, 1 newcomer ----
perm = R.permutation(N)
circ = np.zeros((N, 3))
for i in perm[:5]: circ[i, 0] = 1
for i in perm[5:9]: circ[i, 1] = 1
for i in perm[9:13]: circ[i, 2] = 1
circ[perm[13], [0, 1]] = .7
circ[perm[14], [1, 2]] = .7
circ[perm[15]] = .15
soc = R.normal(0, .45, N)
gen = R.normal(0, .6, N)                      # rating generosity
L = np.zeros((N, N))
for i, j in itertools.combinations(range(N), 2):
    L[i, j] = L[j, i] = -1 + 2.4 * circ[i] @ circ[j] + soc[i] + soc[j] + R.normal(0, .55)
sig = lambda x: 1 / (1 + np.exp(-x))

# answers to the 50 items: traits shared within circles
traits = R.normal(0, 1, (N, 5)) + .5 * (circ @ R.normal(0, 1, (3, 5)))
load = R.normal(0, .8, (5, len(LIKERT_IDS + TOT_IDS)))
raw = traits @ load / 2.2 + R.normal(0, .7, (N, len(LIKERT_IDS + TOT_IDS)))
B = []
for i in range(N):
    ans = {}
    for k, item in enumerate(LIKERT_IDS + TOT_IDS):
        if item in LIKERT_IDS: ans[item] = int(np.clip(np.rint(3 + raw[i, k]), 1, 5))
        else: ans[item] = "a" if raw[i, k] > 0 else "b"
    B.append(ans)

# word "true profile": each person leans toward some categories
cats = list(WORDS)
lean = R.dirichlet(np.ones(4) * .8, N)
WORD_LIST = [w for c in cats for w in WORDS[c]]
def true_words(i):
    p = np.array([lean[i, cats.index(WORD_CODE[w])] for w in WORD_LIST]) + .02
    p /= p.sum()
    return list(R.choice(WORD_LIST, 3, replace=False, p=p))
def noisy_words(i, accuracy):
    """Words someone else picks for i: accurate observers track i's lean."""
    base = np.array([lean[i, cats.index(WORD_CODE[w])] for w in WORD_LIST])
    p = accuracy * base + (1 - accuracy) / len(WORD_LIST) + .01
    p /= p.sum()
    return list(R.choice(WORD_LIST, 3, replace=False, p=p))

# ---- Part 2: per-person ratings ----
picks = {}                                    # A3 words chosen by rater for target (needed for A4 guesses)
for i in range(N):
    for j in range(N):
        if i != j: picks[(i, j)] = noisy_words(j, sig(1.2 * L[i, j] + .4))
trust_true = R.normal(0, .5, N)               # how trustworthy people seem in-game

def clip(x, lo, hi): return int(np.clip(np.rint(x), lo, hi))

def pick_people(i, score, k, pool):
    cand = [ix[n] for n in pool if n != NAMES[i]]
    s = np.array([score[c] for c in cand]); p = np.exp(s - s.max()); p /= p.sum()
    return [NAMES[c] for c in R.choice(cand, min(k, len(cand)), replace=False, p=p)]

ALIGN = np.corrcoef(raw)
pred = pdz.by_predictor(pdz.build())

os.makedirs(os.path.join(a.out, "responses", "part1"), exist_ok=True)
os.makedirs(os.path.join(a.out, "responses", "part2"), exist_ok=True)
QUOTES = ["Reviewer 2 is just Reviewer 1 with a grudge", "I'll start writing after one more analysis",
          "That's not a bug, it's an effect", "Who scheduled lab meeting at 9am", "Coffee is a methods section"]
for i, me in enumerate(NAMES):
    # Part 1
    p1 = {"B": B[i],
          "H": {"quotes": [{"text": R.choice(QUOTES), "who": str(R.choice([n for n in NAMES if n != me]))}],
                "fav": "Be so good they can't ignore you", "photos": [], "videos": ""},
          "F": {"F1": "", "F2": ""}}
    json.dump({"me": me, "part": 1, "pilot": False, "answers": p1, "meta": {"submittedAt": "2026-11-18T20:00:00Z"}},
              open(os.path.join(a.out, "responses", "part1", f"{me}.json"), "w"), indent=1)
    # Part 2
    people, hist = {}, {}
    for j, other in enumerate(NAMES):
        if j == i: continue
        felt = L[i, j] + R.normal(0, .45)
        unknown = L[i, j] < -1.6 and R.random() < .6
        P = {"ios": clip(3.6 + 1.2 * felt + gen[i], 1, 7), "time": clip(2.6 + L[i, j] + R.normal(0, .4), 1, 5)}
        hist[other] = clip(2.5 + 1.2 * max(L[i, j], 0) + R.normal(0, .8), 1, 5)
        if unknown: P["unknown"] = True
        else:
            P["words"] = picks[(i, j)]
            acc = sig(1.3 * L[i, j])            # how well i guesses j's words for i
            P["meta"] = list(picks[(j, i)][:int(R.binomial(3, acc))])
            P["meta"] += [w for w in noisy_words(i, .3) if w not in P["meta"]][:3 - len(P["meta"])]
        if me not in NON_PLAYERS and other not in NON_PLAYERS:
            P["trust"] = clip(3 + .8 * L[i, j] + trust_true[j] + R.normal(0, .6), 1, 5)
            if not unknown:
                actual = 3 + .8 * L[j, i] + trust_true[i]
                P["metaTrust"] = clip(actual + .3 + R.normal(0, .7), 1, 5)
        people[other] = P
    # Prediction game
    C = {}
    for t, blk in pred[me]:
        j = ix[t]; know = sig(L[i, j] + .2)
        C[t] = {}
        for item in BLOCKS[blk]:
            truth, own = B[j][item], B[i][item]
            if item in LIKERT_IDS:
                g = know * truth + (1 - know) * own + R.normal(0, .6)
                C[t][item] = clip(g, 1, 5)
            else:
                C[t][item] = truth if R.random() < .5 + .4 * know else ("a" if truth == "b" else "b")
    # Nominations
    D = {}
    for qid, _, k, ex in D_QS:
        pool = PLAYERS if ex else ATCOTTAGE if qid in WEEKEND_ONLY else NAMES
        if qid in ("D01", "D02", "D03", "D04"): score = 2.0 * L[i]
        elif qid == "D05": score = 2.5 * ALIGN[i] - 1.2 * L[i]
        elif qid == "D10": score = 1.5 * soc - .5 * L[i] - trust_true + R.normal(0, .6, N)
        elif qid == "D11": score = 1.6 * L[i] + trust_true
        else: score = 1.0 * L[i] + R.normal(0, .8, N)
        D[qid] = pick_people(i, score, k, pool)
    E = {}
    others = [n for n in NAMES if n != me]
    for qid, _, kind, k, ex in E_QS:
        pool = [n for n in (PLAYERS if ex else [o for o in others if o not in AWAY] if qid in WEEKEND_ONLY else others) if n != me]
        if kind == "person":
            score = (soc * 2 if qid == "E09" else soc + R.normal(0, .5, N))
            E[qid] = pick_people(i, score, k, pool)
            continue
        cand = [(x, y) for x, y in itertools.combinations(pool, 2)]
        if qid in ("E01", "E07"): v = np.array([L[ix[x], ix[y]] + .3 * (L[i, ix[x]] + L[i, ix[y]]) for x, y in cand])
        elif qid == "E03": v = np.array([ALIGN[ix[x], ix[y]] * 2 - L[ix[x], ix[y]] for x, y in cand])
        elif qid == "E04": v = np.array([ALIGN[ix[x], ix[y]] * 3 for x, y in cand])
        else: v = np.array([R.normal() + .5 * L[ix[x], ix[y]] for x, y in cand])
        v = v + R.normal(0, .5, len(v)); p = np.exp(2 * v - (2 * v).max()); p /= p.sum()
        E[qid] = [list(cand[c]) for c in R.choice(len(cand), k, replace=False, p=p)]
    G = {gid: pick_people(i, (L[i] * .5 + R.normal(0, 1, N)), 1, PLAYERS if ex else NAMES) for gid, _, ex in G_QS}
    p2 = {"A": {"self": true_words(i), "history": hist, "people": people}, "C": C, "D": D, "E": E, "G": G}
    json.dump({"me": me, "part": 2, "pilot": False, "answers": p2, "meta": {"submittedAt": "2026-11-21T20:00:00Z"}},
              open(os.path.join(a.out, "responses", "part2", f"{me}.json"), "w"), indent=1)

json.dump({"names": NAMES, "latent_closeness": L.round(3).tolist(), "circle_weights": circ.tolist()},
          open(os.path.join(a.out, "hidden_truth.json"), "w"))
print(f"Wrote {N} Part 1 and {N} Part 2 files to {a.out}/responses (seed {a.seed}).")

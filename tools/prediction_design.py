"""Prediction-game assignment: 17 people, 8 targets each, 6 items per target.

Cyclic design on a shuffled ring. Each person predicts the people 1, 2, 4 and 8 places
ahead of them and 1, 2, 4 and 8 places behind (offsets 1, 2, 4, 8, 9, 13, 15, 16).
Offsets d and 17-d share an item block, so every prediction is mutual and both people
guess the same 6 items. Balance: everyone predicts 8 and is predicted by 8; each block
appears twice per predictor and twice per target; 68 of the 136 pairs are covered.
"""
import collections
import random

NAMES = ["Ryan", "Lola", "Sarra", "Eloise", "Mikayla", "Elaine", "Hanieh", "Ruth",
         "Sarah", "Zachary", "Leif", "Norman", "Mac", "Elizabeth", "Princeton", "Colin", "Jesse"]
BLOCK = {1: "A", 16: "A", 2: "B", 15: "B", 4: "C", 13: "C", 8: "D", 9: "D"}

# Fixed ring (seed 1127) so the assignments match the survey doc.
RING = ["Lola", "Princeton", "Sarah", "Eloise", "Colin", "Ryan", "Jesse", "Ruth", "Norman",
        "Mac", "Mikayla", "Leif", "Elizabeth", "Elaine", "Zachary", "Hanieh", "Sarra"]


def build(ring=RING):
    n = len(ring)
    rows = [(p, ring[(i + d) % n], BLOCK[d]) for i, p in enumerate(ring) for d in BLOCK]
    check(rows, n)
    return rows


def check(rows, n):
    c = collections.Counter
    assert set(c(r[0] for r in rows).values()) == {8}
    assert set(c(r[1] for r in rows).values()) == {8}
    assert set(c((r[0], r[2]) for r in rows).values()) == {2}
    assert set(c((r[1], r[2]) for r in rows).values()) == {2}
    s = set(rows)
    assert all((b, a, k) in s for a, b, k in rows), "every prediction should be mutual"
    assert all(a != b for a, b, _ in rows)
    assert len(rows) == len(set((a, b) for a, b, _ in rows)), "nobody predicts the same person twice"


def by_predictor(rows):
    out = {p: [] for p in NAMES}
    for a, t, b in rows:
        out[a].append([t, b])
    return out


if __name__ == "__main__":
    rows = build()
    pairs = {frozenset((a, b)) for a, b, _ in rows}
    n = len(NAMES)
    print(f"balanced design OK; pairs covered {len(pairs)}/{n * (n - 1) // 2}")
    for p, ts in by_predictor(rows).items():
        print(p, "->", ", ".join(f"{t} ({b})" for t, b in sorted(ts, key=lambda x: x[1])))

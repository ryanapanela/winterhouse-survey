"""Prediction-game assignment: 16 people, 8 targets each, 6 items per target.

Cyclic design on a shuffled ring using all 8 odd offsets. Offsets d and 16-d share an
item block, so every prediction is mutual and both people guess the same 6 items.
Balance: everyone predicts 8 and is predicted by 8; each block appears twice per
predictor and twice per target; 64 of the 120 pairs are covered.
"""
import collections
import random

NAMES = ["Ryan", "Lola", "Sarra", "Eloise", "Mikayla", "Elaine", "Hanieh", "Ruth",
         "Sarah", "Zachary", "Leif", "Norman", "Mac", "Elizabeth", "Princeton", "Colin"]
BLOCK = {1: "A", 15: "A", 3: "B", 13: "B", 5: "C", 11: "C", 7: "D", 9: "D"}

# Fixed ring (seed 1127) so the assignments match the survey doc.
RING = ["Lola", "Norman", "Eloise", "Princeton", "Colin", "Elizabeth", "Mac", "Zachary",
        "Ruth", "Sarah", "Hanieh", "Elaine", "Ryan", "Leif", "Mikayla", "Sarra"]


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


def by_predictor(rows):
    out = {p: [] for p in NAMES}
    for a, t, b in rows:
        out[a].append([t, b])
    return out


if __name__ == "__main__":
    rows = build()
    pairs = {frozenset((a, b)) for a, b, _ in rows}
    print(f"balanced design OK; pairs covered {len(pairs)}/120")
    for p, ts in by_predictor(rows).items():
        print(p, "->", ", ".join(f"{t} ({b})" for t, b in sorted(ts, key=lambda x: x[1])))

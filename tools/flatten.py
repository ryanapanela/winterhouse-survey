"""Turn the JSON responses in the data repo into tidy CSVs for analysis.

Usage:  python3 tools/flatten.py path/to/winterhouse-data  [out_dir]

Writes (long format, one row per answer):
  alignment.csv     person, item, value            (B01–B30 and B52 as 1–5, B31–B51 and B53 as a/b)
  dyads.csv         rater, target, measure, value  (ios, time, trust, metaTrust, unknown, history)
  words.csv         rater, target, kind, word      (kind = words | meta | self)
  predictions.csv   predictor, target, item, guess
  nominations.csv   rater, question, target        (D and G, plus E person questions)
  pairs.csv         rater, question, a, b          (E pair questions)
  submissions.csv   person, part, submitted_at, opt_in
Text answers (quotes, P1–P5 "All about you", F1, F2, F4 (hot take), photo captions, award stories in G_text) are left in the JSON on purpose:
read them by hand only where you planned to.
"""
import csv, glob, json, os, sys

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(src, "tidy")
os.makedirs(out, exist_ok=True)
T = {k: [] for k in ["alignment", "dyads", "words", "predictions", "nominations", "pairs", "submissions"]}
HIST = ["<6 mo", "6–12 mo", "1–2 yr", "2–5 yr", "5+ yr"]

for part in (1, 2):
    for path in sorted(glob.glob(os.path.join(src, "responses", f"part{part}", "*.json"))):
        d = json.load(open(path))
        me, a, meta = d["me"], d.get("answers", {}), d.get("meta", {})
        T["submissions"].append([me, part, meta.get("submittedAt", ""), a.get("optIn", "")])
        if part == 1:
            for item, v in (a.get("B") or {}).items():
                if v is not None:
                    T["alignment"].append([me, item, v])
            continue
        AA = a.get("A") or {}
        for w in AA.get("self") or []:
            T["words"].append([me, me, "self", w])
        for t, v in (AA.get("history") or {}).items():
            if v is not None:
                T["dyads"].append([me, t, "history", v])  # 1..5 = <6 mo .. 5+ yr
        for t, P in (AA.get("people") or {}).items():
            for m in ["ios", "time", "trust", "metaTrust"]:
                if P.get(m) is not None:
                    T["dyads"].append([me, t, m, P[m]])
            if P.get("unknown"):
                T["dyads"].append([me, t, "unknown", 1])
            for kind in ["words", "meta"]:
                for w in P.get(kind) or []:
                    T["words"].append([me, t, kind, w])
        for t, items in (a.get("C") or {}).items():
            for item, v in items.items():
                if v is not None:
                    T["predictions"].append([me, t, item, v])
        for sec in ["D", "G"]:
            for qid, picks in (a.get(sec) or {}).items():
                if not isinstance(picks, list): continue
                for t in picks:
                    if t: T["nominations"].append([me, qid, t])
        for qid, v in (a.get("E") or {}).items():
            for x in v or []:
                if isinstance(x, list):
                    if len(x) == 2 and x[0] and x[1]:
                        T["pairs"].append([me, qid, *sorted(x)])
                elif x:
                    T["nominations"].append([me, qid, x])

HEAD = {
    "alignment": ["person", "item", "value"], "dyads": ["rater", "target", "measure", "value"],
    "words": ["rater", "target", "kind", "word"], "predictions": ["predictor", "target", "item", "guess"],
    "nominations": ["rater", "question", "target"], "pairs": ["rater", "question", "a", "b"],
    "submissions": ["person", "part", "submitted_at", "opt_in"],
}
for name, rows in T.items():
    with open(os.path.join(out, f"{name}.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(HEAD[name]); w.writerows(rows)
    print(f"{name}.csv: {len(rows)} rows")

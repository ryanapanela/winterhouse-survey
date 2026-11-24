# Winterhouse Survey

The pre-trip survey for Winterhouse (Nov 27–30). It's a static site on GitHub Pages, and every submission is saved as a file in a **private** GitHub repo.

```
people's phones ──► GitHub Pages site (public, this repo /docs)
                        │  answers + photos
                        ▼
                Cloudflare Worker relay (holds the GitHub token, checks each person's code)
                        │  commits
                        ▼
                winterhouse-data (PRIVATE repo)
                  responses/part1/<Name>.json
                  responses/part2/<Name>.json
                  media/<Name>/<photo-id>.jpg …
```

The site can't write to GitHub directly. That would put a write token in public JavaScript, and anyone could take it and read every answer. The Worker keeps the token secret and is free.

## Set up (about 30 minutes, once)

1. **Make two repos.**
   - `winterhouse-survey`, public: push this folder. Do **not** push `private/` (it's in `.gitignore`).
   - `winterhouse-data`, **private**: create it with a README, so it has a `main` branch.
2. **Make a GitHub token.** Settings → Developer settings → Fine-grained tokens → Generate. Under Repository access, choose *Only select repositories* → `winterhouse-data`. Under Permissions → Contents, choose **Read and write**. Set the expiry to Dec 31, then copy the token.
3. **Deploy the relay.** Make a free Cloudflare account, then:
   ```
   cd worker
   # edit wrangler.toml: REPO and ALLOWED_ORIGIN with your GitHub username
   npx wrangler login
   npx wrangler deploy                      # prints https://winterhouse-survey.<you>.workers.dev
   npx wrangler secret put GITHUB_TOKEN     # paste the token
   ```
4. **Generate links and config.**
   ```
   python3 tools/make_links.py \
     --site https://<you>.github.io/winterhouse-survey/ \
     --endpoint https://winterhouse-survey.<you>.workers.dev \
     --album "https://link-to-a-shared-video-folder"   # optional
   cd worker && npx wrangler secret put TOKENS < ../private/worker_TOKENS.json
   ```
   This writes `docs/config.js` (public, contains no codes) and `private/links.csv` (everyone's two personal links).
5. **Turn on Pages.** In `winterhouse-survey`, go to Settings → Pages → Deploy from branch → `main` / `/docs`. Commit `docs/config.js` and push.
6. **Test with your own links** from `private/links.csv`. A file should appear in `winterhouse-data/responses/` within a few seconds.
7. **Send links by DM:** Part 1 on Mon Nov 16, Part 2 on Thu Nov 19. The relay refuses submissions after `CLOSES_AT` (end of Wed Nov 25, midnight Toronto; people are told end of Tue Nov 24, so there is a day of buffer).

## Piloting

`private/links.csv` also has `pilot_part1_link` and `pilot_part2_link` columns: the same links with `&pilot=1`. They show a "Pilot run" band, and save to `pilot/responses/…` and `pilot/media/…` in the data repo, never mixed with real answers. To analyse pilot data: `python3 tools/flatten.py winterhouse-data/pilot`.

## Day to day

- People can reopen their link and resubmit. The newest version replaces the old one, and git history keeps the old ones.
- Progress saves on each person's device as they go. If they open their link on a different device, the site reloads whatever they last submitted, so nothing gets wiped.
- Photos upload the moment they're picked (people can select many at once), resized to 1800 px. Each gets a unique name, so nothing is ever overwritten: everything in `media/<Name>/` is theirs, even if they later removed it from their list. Videos go to the shared folder link.
- Autosave: while someone is filling it in, unsent changes are backed up every minute (and when they change screens or leave the tab) to `drafts/part1|2/<Name>.json` in the data repo. The header shows "Saved 9:03 AM". Submit still writes `responses/`. `flatten.py` uses whichever of a person's submission and autosave is newer (so it covers people who never submitted and people who edited afterwards), and prints whose autosave it used.
- If someone's link leaks, rerun `make_links.py --new-codes`, update the `TOKENS` secret, and resend links.

## Analysis

```
git clone https://github.com/ryanapanela/winterhouse-data.git      # first time; later: git pull
python3 tools/flatten.py winterhouse-data                          # → winterhouse-data/tidy/*.csv
python3 tools/analyze.py winterhouse-data/tidy                     # → winterhouse-data/analysis/
```
`flatten.py` writes tidy long-format CSVs: `alignment`, `dyads` (ios, time, trust, metaTrust, history), `words`, `predictions`, `nominations`, `pairs` and `submissions`. Text answers (quotes, F1–F3, captions) stay in the JSON.

`analyze.py` builds the multilayer network and writes:
- `results.json`: everything the reveal needs. That covers the layer maps; roles, circles and centrality; layer agreement; power duos; Unexpected Pairings with introducers; mismatches; prediction scores, readability and duels; words and Traitor vibe; trust gaps and one-sided alliances; group-view guessing; Prom Award finalists; and hot-take splits.
- `pairs.csv`: all 120 pairs with every facet and layer percentile.
- `people.csv`: one row per person.

The network combines six layers: connection, alignment, knowing, trust, perception and suspicion. Each pair's tie is the weighted mean of the layer percentiles that are switched on (equal weights by default, set in `LAYER_WEIGHTS`). Connection uses only what the two people report (closeness 40%, time 35%, support 25%); E1 lives in the perception layer, so nothing is counted twice. Suspicion is an optional penalty. Hubs, circles and roles come from that combined network, and `results.json` includes all 62 on/off combinations so the reveal can toggle layers live. To change the default, edit `DEFAULT_ON` in `analyze.py`. The field guide (`analysis-field-guide.html`, one folder up) explains each step.

To test the whole chain without real data:
```
python3 tools/simulate_responses.py sim-data
python3 tools/flatten.py sim-data && python3 tools/analyze.py sim-data/tidy
```
The simulation's friend groups are random, and `analyze.py` reports how well it recovered them.

Needs Python with pandas, numpy, scipy, networkx and scikit-learn (all included in Anaconda).

## Editing questions

All wording is in `docs/questions.js`. Ids (B01, D05 …) are what land in the data, so don't reuse an id for a different question once responses start. The prediction-game assignments come from `tools/prediction_design.py` and match the survey doc.

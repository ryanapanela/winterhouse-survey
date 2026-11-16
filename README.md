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
7. **Send links by DM:** Part 1 on Mon Nov 16, Part 2 on Thu Nov 19. The relay refuses submissions after `CLOSES_AT` (Sun Nov 22, midnight Toronto).

## Day to day

- People can reopen their link and resubmit. The newest version replaces the old one, and git history keeps the old ones.
- Progress saves on each person's device as they go. If they open their link on a different device, the site reloads whatever they last submitted, so nothing gets wiped.
- Photos upload the moment they're picked (people can select many at once), resized to 1800 px. Each gets a unique name, so nothing is ever overwritten: everything in `media/<Name>/` is theirs, even if they later removed it from their list. Videos go to the shared folder link.
- If someone's link leaks, rerun `make_links.py --new-codes`, update the `TOKENS` secret, and resend links.

## Analysis

```
git clone git@github.com:<you>/winterhouse-data.git
python3 tools/flatten.py winterhouse-data          # writes winterhouse-data/tidy/*.csv
```
This produces tidy long-format CSVs: `alignment`, `dyads` (ios, time, trust, metaTrust, history), `words`, `predictions`, `nominations`, `pairs` and `submissions`. Text answers (quotes, F1–F3, captions) stay in the JSON.

## Editing questions

All wording is in `docs/questions.js`. Ids (B01, D05 …) are what land in the data, so don't reuse an id for a different question once responses start. The prediction-game assignments come from `tools/prediction_design.py` and match the survey doc.

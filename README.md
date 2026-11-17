# DRI Tracker

The Dissident Resonance Index (DRI) is a 0–100 index of how large the US far-right extremist media ecosystem is beside mainstream media, which way it is moving, and where its audience lives.

It is deterministic: every figure in the index is a recorded public observation or computed from one. Nothing in it is simulated, interpolated or estimated, and rebuilding from the same commit produces the same bytes. Beside the index the dashboard shows two things that are not part of it: Rumble weekly views scaled for the views young uploads have yet to collect (a labelled estimate, shown with the recorded count), and counts of incidents the ADL recorded offline.

## How it works

```
backend/dri/collectors   one module per public source; each returns observations and a list of what it could not read
data/observations        append-only JSON-lines store, one file per source and month, committed to git
backend/dri/model.py     seven pillars and their weighted composite, pure functions of the store
frontend                 static Next.js dashboard built from frontend/public/data/index.json
```

A daily GitHub Action runs the collectors, commits the new observations, rebuilds the dataset and publishes the site.

## The index

| Group | Pillar | What it measures | Weight |
|---|---|---|---|
| Scale | Reach | Share of the combined audience held by the extremism basket | 20% |
| Scale | Engagement | Share of combined weekly views | 20% |
| Scale | Mainstreaming | Share of Apple podcast-chart points | 10% |
| Dynamics | Momentum | Annualised audience growth | 15% |
| Dynamics | Breadth | Share of accounts that are growing | 8% |
| Dynamics | Heat | Wikipedia and news attention against its trailing-year median | 12% |
| Structure | Depth | How far the audience sits on low-moderation platforms | 15% |

"Share" always means the extremism basket against itself plus a reference basket of twelve mainstream US news and commentary outlets. A pillar whose inputs were not recorded is withheld and the remaining weights are rescaled; if less than half the weight is available, no reading is published. Formulas and parameters are in [METHODOLOGY.md](METHODOLOGY.md).

## Who is tracked

`backend/dri/registry/constituents.json` lists every constituent. An entry is accepted into the extremism basket only with a link to a profile published by a monitoring organisation (SPLC or ADL); the loader rejects entries without one. Those characterisations are the organisations' own. YouTube channels are pinned by channel ID and every collector checks identity, so a renamed or squatted handle cannot substitute another account.

## Sources

| Source | What is read | Access |
|---|---|---|
| YouTube | Subscribers, views on recent uploads, lifetime views | Public pages and feeds; free `YOUTUBE_API_KEY` recommended |
| Telegram | Subscribers, views on the last week of posts | Public `t.me` pages |
| BitChute | Subscribers, lifetime views | Public channel API |
| Apple Podcasts | US chart positions, overall and News | Public Apple feeds |
| Wikipedia | Daily page views per article | Wikimedia REST API |
| GDELT | Daily count of US news articles per constituent | GDELT DOC 2.0 API |
| X | Followers | Free: FxTwitter's public profile API, a third-party mirror. Official API used instead when `X_BEARER_TOKEN` is set |
| Rumble | Followers, weekly views, views per upload week | Browser capture; Rumble refuses automated clients |
| ADL H.E.A.T. Map | Incidents recorded offline, by month and type (not in the index) | Public JSON behind the ADL's map; read monthly |

**Rumble.** The collector was refused (HTTP 403) from a cloud workspace and from GitHub Actions, so Rumble is read with a browser capture instead: open any rumble.com page, paste `backend/dri/tools/rumble_capture.js` into the DevTools console, save the JSON it prints under `data/captures/rumble/<date>.json`, and run `python -m dri import-capture <file>`. It records exact follower counts, the channel ID, views on the last week of uploads, and total views per upload week for up to a year. A follower reading counts for 10 days, so repeat the capture weekly. One capture shows views to date, which keep accumulating; from the second capture on, the build reports the views each channel actually gained in between.

**X.** X sells API access and has no free tier for reading. Without a token the collector asks FxTwitter's public profile API (`api.fxtwitter.com`), an open-source mirror, which returns the numeric user ID, display name and follower count X shows. It is a third party: it can lag, vanish, or answer "not found" for an account that exists, so each handle gets four tries and an unread account is reported, not guessed. Mirror readings are tagged `origin: fxtwitter mirror`, every account is pinned by numeric ID, and `DRI_X_MIRROR=off` disables the route. Spot-check a few counts against the profile pages now and then; if the mirror goes away, the choices are the paid API or hand readings with `dri record`.

**Take Rumble captures a week apart, on the same weekday.** The build compares the two to measure how fast young uploads are still gaining views, and uses that to judge each new week against the channel's own average.

X's public embed endpoint, Gab and Truth Social were also tested and refuse automated readers, and Odysee's follower count needs a login, so they have no collector. For any registered account on a platform that cannot be read automatically, a figure read by hand can be stored with `python -m dri record x:tucker_carlson=17300000 --note "profile page"`; it is saved with `origin: manual` so it stays distinguishable from collected data.

The collectors identify themselves with an honest User-Agent, pace their requests, and treat a refusal as final. A source that refuses is reported as blocked on the dashboard's data-quality page. Wikipedia and GDELT are asked for 400 days on every run, so a gap left by a rate-limited run refills on the next one.

## Running it

Requires Python 3.11+ and Node 20+. The backend has no runtime dependencies.

```bash
cd backend
python -m dri registry                 # validate and list the registry
python -m dri collect                  # read every source, record observations
python -m dri collect --sources gdelt --entities nick_fuentes   # retry part of a source
python -m dri record x:tucker_carlson=17300000   # store a follower count read by hand
python -m dri import-capture ../data/captures/rumble/2026-11-17.json   # import a Rumble browser capture
python -m dri collect --sources adl_heat   # monthly: re-read the ADL incident records (about 140 slow pages)
python -m dri build                    # compute the index, write frontend/public/data/index.json

pip install pytest && python -m pytest # tests

cd ../frontend
npm install
npm run dev                            # http://localhost:3000
npm run build                          # static site in frontend/out
```

Environment variables, all optional:

| Variable | Effect |
|---|---|
| `YOUTUBE_API_KEY` | Records each channel's lifetime view counter, which is what makes the Engagement pillar publishable |
| `X_BEARER_TOKEN` | Reads X through the official paid API instead of the free mirror |
| `DRI_X_MIRROR` | Set to `off` to stop using the free X mirror |
| `DRI_USER_AGENT` | Overrides the User-Agent; include a contact address |
| `DRI_DATA` | Overrides the data directory |

## How it runs

`.github/workflows/daily.yml` runs at 06:17 UTC on `main`: it tests, collects, rebuilds the dataset and commits the new observations. The site is hosted on Vercel (https://dri-tracker.vercel.app), which redeploys on every push to `main`, so each day's commit publishes itself. Add `YOUTUBE_API_KEY` as a repository secret under Settings → Secrets and variables → Actions.

## Limits

Audience is not agreement, and followers are neither all in the US nor all human. The index does not read content. Offline incidents are shown beside it, not inside it. The depth and view-equivalence coefficients are stated judgements; the dashboard shows how far the reading moves when they change.

## Licence

MIT. For research and analysis.

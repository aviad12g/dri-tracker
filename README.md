# DRI Tracker

The Dissident Resonance Index (DRI) is a 0–100 index of how large the US far-right extremist media ecosystem is beside mainstream media, which way it is moving, and where its audience lives.

It is deterministic: every figure is a recorded public observation or computed from one. Nothing is simulated, interpolated or estimated, and rebuilding from the same commit produces the same bytes.

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
| X | Followers | Official API only; needs paid `X_BEARER_TOKEN` (about $8 a month) |
| Rumble | Followers | Public pages; Rumble refuses many automated clients |

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
| `X_BEARER_TOKEN` | Enables the X collector |
| `DRI_USER_AGENT` | Overrides the User-Agent; include a contact address |
| `DRI_DATA` | Overrides the data directory |

## Limits

Audience is not agreement, and followers are neither all in the US nor all human. The index does not read content and says nothing about offline activity. The depth and view-equivalence coefficients are stated judgements; the dashboard shows how far the reading moves when they change.

## Licence

MIT. For research and analysis.

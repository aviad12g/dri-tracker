# Methodology (model 2.1.0)

All parameters live in `backend/dri/params.py`. Changing one changes the model version.

## Baskets

- **Extremism basket** X: constituents profiled by a monitoring organisation. Tier weight `w` is 1.0 for core and 0.5 for adjacent.
- **Reference basket** M: twelve large US news and commentary outlets across the spectrum, weight 1.0.

## Observations and staleness

An observation is `(date, source, entity, account, metric, value)`. A follower reading counts for 7 days, a weekly-views or chart reading for 3, a daily series for 6. After that the input is missing, not carried forward.

## Pillars

Let `F` be followers of one account, `σ(x) = 1 / (1 + e^-x)`.

**Reach.** Effective audience of a constituent `E = (Σ_platforms F^q)^(1/q)` with `q = 2` (q = 1 means audiences never overlap, q = ∞ means they fully overlap).
`Reach = 100 · Σ_X w·E / (Σ_X w·E + Σ_M E)`.

**Engagement.** Weekly views per account `V`, converted with view-equivalence `λ` (YouTube 1, Rumble 0.6, BitChute 0.6, Telegram 0.25, X 0.05).
`Engagement = 100 · Σ_X w·λ·V / (Σ_X w·λ·V + Σ_M λ·V)`.
`V` is either the change in a channel's lifetime view counter scaled to seven days, or a sum over posts that provably covers seven days. Incomplete windows are stored as `views_7d_partial` and ignored. The pillar is withheld unless at least half of each basket's view-capable accounts have a complete figure.

**Mainstreaming.** On a chart of size `N`, a show at rank `r` earns `1 − ln r / ln(N + 1)` points. Per chart, share = X points (tier-weighted) over X plus M points. The pillar is 100 times the mean share over the charts read (Apple US top 100, Apple US News top 200).

**Momentum.** Per account, `g = ln(F_now / F_then) · 365 / days`, where `F_then` is the reading nearest 28 days back within 7–400 days, clipped to ±ln 8. Basket growth `G` is the mean of `g` weighted by `w · F_then`. `Momentum = 100 · σ(G / ln 2)`.

**Breadth.** With `n ≥ 5` accounts having a growth reading and `k` of them growing, `Breadth = 100 · (k + 1) / (n + 2)`.

**Heat.** Two daily series for X: tier-weighted Wikipedia page views, and tier-weighted news articles divided by all articles GDELT monitored. Only series with at least 60 days of history enter. For each, `ratio = mean(last 7 days) / median(previous 365 days)` and `score = 100 · σ(ln ratio / ln 2)`. Heat is the mean of the available scores.

**Depth.** Depth coefficient `κ`: YouTube 0.15, X 0.50, Rumble 0.80, BitChute 0.90, Telegram 1.00.
`Depth = 100 · Σ_X w·κ·F / Σ_X w·F`, requiring at least two platforms.

## Composite

`DRI = Σ_k weight_k · pillar_k / Σ_k weight_k` over available pillars. Not published if the available weight is below 0.5.

Confidence is `Σ_k weight_k · coverage_k`, where coverage is the share of a pillar's registered inputs that were observed. Grades: A ≥ 0.80, B ≥ 0.60, C ≥ 0.40, D below.

## Robustness band

Each build recomputes the latest reading under alternative assumptions: equal pillar weights; each pillar removed in turn; adjacent tier at 0.25, 0.75 and 1.0; `q` at 1 and ∞; a Telegram view worth 0.1 and 0.5. The band is the minimum and maximum. This follows the uncertainty and sensitivity step of the OECD/JRC *Handbook on Constructing Composite Indicators* (2008), done exhaustively over named scenarios instead of by random sampling so that it stays deterministic.

## Design choices

- **Shares against a reference, not z-scores against own history.** A share is meaningful on day one and comparable over time. Version 1 normalised against its own first days and saturated.
- **Matched panels for change.** Momentum and Breadth compare each account with its own earlier reading, so adding a constituent cannot move them. In version 1 the index rose whenever a profile was added.
- **Withhold, never impute.** Missing inputs lower coverage and the confidence grade; they are not filled.
- **No clock in the output.** The dataset carries a SHA-256 of its inputs instead of a build time.

## Changes

- **2.1.0** Added BitChute as a platform (depth 0.90, view equivalence 0.6).
- **2.0.0** Rebuilt model.

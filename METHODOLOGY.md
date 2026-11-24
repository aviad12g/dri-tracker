# Methodology (model 2.3.1)

All parameters live in `backend/dri/params.py`. Changing one changes the model version.

## Baskets

- **Extremism basket** X: constituents profiled by a monitoring organisation. Tier weight `w` is 1.0 for core and 0.5 for adjacent.
- **Reference basket** M: twelve large US news and commentary outlets across the spectrum, weight 1.0.

## Observations and staleness

An observation is `(date, source, entity, account, metric, value)`. A follower reading counts for 10 days (long enough for a weekly browser capture), a weekly-views or chart reading for 3, a daily series for 6. After that the input is missing, not carried forward.

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

Confidence is `Σ_k weight_k · coverage_k` over available pillars divided by the total weight of all pillars, where coverage is the share of a pillar's registered inputs that were observed. Grades: A ≥ 0.80, B ≥ 0.60, C ≥ 0.40, D below.

## Robustness band

Each build recomputes the latest reading under alternative assumptions: equal pillar weights; each pillar removed in turn; adjacent tier at 0.25, 0.75 and 1.0; `q` at 1 and ∞; a Telegram view worth 0.1 and 0.5. The band is the minimum and maximum. This follows the uncertainty and sensitivity step of the OECD/JRC *Handbook on Constructing Composite Indicators* (2008), done exhaustively over named scenarios instead of by random sampling so that it stays deterministic.

## Outside the index

Three things are computed and shown beside the index. None of them enters it.

### View accumulation (Rumble)

A capture shows each upload's views to date, and a video keeps collecting views after it is published, so the newest weeks always look smaller than older ones. To compare a new week with a channel's average, young weeks are scaled to maturity with the constant-scaling model of Szabo & Huberman, "Predicting the popularity of online content" (CACM 2010, arXiv:0811.0405): views at a later age equal views at an earlier age times a factor that depends only on the two ages.

`A = V(a) / m(a)`, with `0 < m(a) ≤ 1`.

`V(a)` is the recorded views on one upload week at age `a` (whole weeks since the upload week ended; age 0 is the newest completed week). `m(a)` is the share of its settled views a week has typically reached at that age. The factors are estimated from this project's own Rumble readings, never taken from another platform or paper:

- **Longitudinal (measured).** Used when captures 6–8 days apart exist. Every upload week present in both, with the same number of uploads, gives `V_later / V_earlier`. `g(a)` is the median of those ratios at age `a` (ages 0, 1, 2 separately; ages 3–11 pooled), needing at least 3 ratios per age. `m(a) = 1 / Π_{k=a..11} g(k)`; a week 12 weeks old counts as settled. The band uses the 25th and 75th percentile of the ratios.
- **Cross-section (provisional).** Used while there is one capture. For each channel, `r(a) = (views per video at age a) / (views per video over ages 3–8)`, for ages 0–2, requiring at least 2 uploads in the young week and 8 in the reference weeks. `m(a) = min(1, median over channels of r(a))`, needing at least 3 channels; the band is the minimum and maximum across channels. Factors are capped so a younger week is never more complete than an older one. This assumes each channel's typical video drew a steady audience over the last two months; where that is false the factor absorbs part of a real rise or fall. It is replaced automatically by the longitudinal estimate.

Where an age has no factor, weeks of that age are left as recorded and are not judged. The published model estimates its factor by relative least squares over thousands of videos; with five or six channels a median is used instead, because a mean would be set by one outlier.

### A channel's average week

`B_w = mean(A over the 12 weeks before w)` (at least 4; weeks without uploads count as zero) and `change = A_w / B_w − 1`. The week is called **above** only if the low end of its adjusted band exceeds the 90th percentile of those earlier weeks, **below** only if its high end is under the 10th percentile, and otherwise **inside its usual range**. With a stationary channel roughly one week in five falls outside that range by chance, so a single call is weak evidence; a run of them is not.

### Views gained between captures

`gained = Σ_{upload weeks in both captures} (V_later − V_earlier) + views on weeks uploaded since the earlier capture`. This is a count, not an estimate, and needs two captures. A week that had already ended at the earlier capture counts only if it holds the same number of uploads in both; otherwise one capture missed or lost uploads, the difference would include their lifetime views, and the week is left out. The earlier capture's own week was still open, so it may gain uploads.

### Recorded incidents offline

Monthly tallies of the ADL's H.E.A.T. Map records by type: antisemitic incidents (any of assault, harassment, vandalism, whoever committed them), white-supremacist propaganda, white-supremacist events, and extremist violence (murders, terrorist plots and attacks, shootouts with police), in total and for perpetrators the ADL classed as right-wing. A record with several types counts once in each, so the series are not additive. Only counts are stored.

They are kept out of the index for three reasons. They lag by months and the latest year is incomplete until published, which would make a daily index move on publication dates. They measure reporting and the ADL's definitions as well as events. And the main use of offline counts is to test whether the online reading leads them; an index that already contained them could not be tested that way.

## Design choices

- **Shares against a reference, not z-scores against own history.** A share is meaningful on day one and comparable over time. Version 1 normalised against its own first days and saturated.
- **Matched panels for change.** Momentum and Breadth compare each account with its own earlier reading, so adding a constituent cannot move them. In version 1 the index rose whenever a profile was added.
- **Withhold, never impute.** Missing inputs lower coverage and the confidence grade; they are not filled. The one modelled quantity, maturity-adjusted Rumble views, is display-only, labelled, and shown with the recorded count.
- **No clock in the output.** The dataset carries a SHA-256 of its inputs instead of a build time.

## Changes

- **2.3.1** The Rumble capture script reads every video list on a channel page and drops the week where reading stopped. The 2026-11-17 capture read only the first list on page 1 and missed about 20 recent videos per channel, so its newest weeks were too low. Views gained between captures now skip ended weeks whose upload counts differ. No index formula changed.
- **2.3.0** X is read through a free public mirror when no API token is set, pinned by numeric user ID. Added the view-accumulation model, per-channel weekly baselines and the offline incident tallies, all outside the index. No pillar formula changed; the reading moved because X audiences are now counted.

- **2.2.0** Rumble enters through browser captures and counts towards Engagement; follower readings stay valid for 10 days instead of 7.
- **2.1.0** Added BitChute as a platform (depth 0.90, view equivalence 0.6).
- **2.0.0** Rebuilt model.

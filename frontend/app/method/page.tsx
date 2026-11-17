import type { Metadata } from 'next'
import { loadData } from '@/lib/data'
import { PLATFORM_NAME, pct } from '@/lib/format'

export const metadata: Metadata = { title: 'Method | Dissident Resonance Index' }

export default function Page() {
  const data = loadData()
  const p = data?.params
  return (
    <>
      <div className="page-head">
        <h1>How the index is computed</h1>
        <p>
          Seven pillars, each a number from 0 to 100 with a plain statistic behind it, combined as a weighted mean. Every input is a recorded
          public observation. The same observations always give the same reading.
        </p>
      </div>

      <div className="cols section">
        <div className="prose">
          <h3 style={{ marginTop: 0 }}>Two baskets</h3>
          <p>
            The extremism basket holds people and movements profiled by monitoring organisations. Core constituents count in full; adjacent
            ones, such as large commentators documented as platforming core figures, count at half. The reference basket holds twelve large US
            news and commentary outlets from across the spectrum. Scale is always measured as a share of the two baskets together, so the index
            asks how large this ecosystem is beside mainstream media, not how large it is in the abstract.
          </p>

          <h3>Reach</h3>
          <p>
            One person’s followers on different platforms overlap. A constituent’s effective audience combines its platforms with an exponent
            between adding them and taking the largest:
          </p>
          <div className="formula"><var>E</var> = ( Σ<sub>platforms</sub> <var>F</var><sup> q</sup> )<sup>1/q</sup>, with <var>q</var> = 2</div>
          <div className="formula">Reach = 100 × Σ <var>w</var>·<var>E</var> (extremism) ÷ [ Σ <var>w</var>·<var>E</var> (extremism) + Σ <var>E</var> (reference) ]</div>

          <h3>Engagement</h3>
          <p>
            Views in the last seven days, converted to YouTube-view equivalents, as a share of both baskets. A weekly figure counts only when
            it is complete: either the difference between two readings of a channel’s lifetime view counter, or a sum over a post list that
            reaches back the full seven days. If fewer than half of either basket’s accounts have a complete figure, the pillar is withheld.
          </p>

          <h3>Mainstreaming</h3>
          <p>
            Each show on Apple’s US podcast charts earns chart points by height, and the pillar is the basket’s share of points against
            reference shows, averaged over the overall top 100 and the News top 200:
          </p>
          <div className="formula">points = 1 − ln(rank) ÷ ln(chart size + 1)</div>

          <h3>Momentum</h3>
          <p>
            For each account, growth is measured against the reading closest to 28 days earlier (anything from 7 to 400 days back), annualised,
            and clipped so one account cannot dominate. The basket figure is the mean weighted by starting audience, passed through the logistic curve σ so that no change
            scores 50 and doubling in a year scores 73:
          </p>
          <div className="formula"><var>g</var> = ln(<var>F</var><sub>now</sub> ÷ <var>F</var><sub>then</sub>) × 365 ÷ days, &nbsp; Momentum = 100 × σ( <var>g</var> ÷ ln 2 )</div>

          <h3>Breadth</h3>
          <p>
            The share of accounts whose audience grew, with one success and one failure added so a handful of accounts cannot produce 0 or 100.
            It needs growth readings for at least five accounts.
          </p>
          <div className="formula">Breadth = 100 × (growing + 1) ÷ (accounts + 2)</div>

          <h3>Heat</h3>
          <p>
            Two attention series: weighted Wikipedia page views of the basket’s articles, and its share of US news articles in GDELT. Each
            compares the mean of the latest seven days with the median of the year before. Heat is the mean of the two scores; attention at its
            usual level scores 50 and double the usual scores 73.
          </p>
          <div className="formula">score = 100 × σ( ln(last week ÷ yearly median) ÷ ln 2 )</div>

          <h3>Depth</h3>
          <p>
            Each platform has a depth coefficient from 0 (heavily moderated) to 1 (unmoderated). Depth is the audience-weighted mean
            coefficient of the extremism basket, and needs follower counts on at least two platforms.
          </p>

          <h3>The composite</h3>
          <div className="formula">DRI = Σ <var>weight</var> × <var>pillar</var> ÷ Σ <var>weight</var>, over the pillars available that day</div>
          <p>
            A pillar whose inputs were not recorded is left out and the remaining weights are rescaled. If the available pillars carry less than
            half the total weight, no reading is published. The confidence grade is the weight-averaged share of inputs observed: A from 80%, B
            from 60%, C from 40%, D below.
          </p>

          <h3>What this does not measure</h3>
          <p>
            Audience is not agreement, and followers are not all in the United States or all human. The index does not read content, so it cannot
            tell a critic’s audience from a supporter’s. It says nothing about offline organising or violence. The coefficients for moderation
            depth and view equivalence are judgements, stated here so they can be challenged; the robustness band on the front page shows how
            far the reading moves when they change.
          </p>
        </div>

        {p && (
          <aside className="aside">
            <div className="panel">
              <h3>Pillar weights</h3>
              <div className="tablewrap">
                <table>
                  <tbody>
                    {data!.pillars.map((pl) => (
                      <tr key={pl.id}><td>{pl.label}</td><td className="num">{pct(pl.weight)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="panel" style={{ marginTop: '1.2rem' }}>
              <h3>Platform coefficients</h3>
              <div className="tablewrap">
                <table>
                  <thead><tr><th>Platform</th><th className="num">Depth</th><th className="num">View worth</th></tr></thead>
                  <tbody>
                    {data!.platforms.map((pl) => (
                      <tr key={pl.platform}><td>{PLATFORM_NAME[pl.platform]}</td><td className="num">{pl.depth.toFixed(2)}</td><td className="num">{pl.view_equiv.toFixed(2)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="foot">View worth is one view in YouTube-view equivalents.</p>
            </div>
            <div className="panel" style={{ marginTop: '1.2rem' }}>
              <h3>Other settings</h3>
              <dl className="kv">
                <dt>Adjacent tier weight</dt><dd>{p.tier_weight.adjacent}</dd>
                <dt>Overlap exponent</dt><dd>{p.overlap_q}</dd>
                <dt>Follower reading expires</dt><dd>{p.stale.followers} days</dd>
                <dt>View reading expires</dt><dd>{p.stale.views_7d} days</dd>
                <dt>Heat baseline</dt><dd>{p.baseline_days} days</dd>
                <dt>Minimum weight to publish</dt><dd>{pct(p.min_weight_coverage)}</dd>
              </dl>
            </div>
          </aside>
        )}
      </div>
    </>
  )
}

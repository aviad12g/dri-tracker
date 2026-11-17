import type { Metadata } from 'next'
import { loadData } from '@/lib/data'
import { PLATFORM_NAME, pct } from '@/lib/format'

export const metadata: Metadata = { title: 'Method | Dissident Resonance Index' }

export default function Page() {
  const data = loadData()
  const p = data?.params
  const mat = data?.rumble_maturity
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
          <p>
            Here <var>F</var> is a follower count on one platform and <var>w</var> is the tier weight: 1 for core constituents,{' '}
            {p ? p.tier_weight.adjacent : 0.5} for adjacent ones. A follower count is used for {p ? p.stale.followers : 10} days after it was
            read, then dropped.
          </p>

          <h3>Engagement</h3>
          <p>
            Views in the last seven days, converted to YouTube-view equivalents, as a share of both baskets. A weekly figure counts only when
            it is complete: either the difference between two readings of a channel’s lifetime view counter, or a sum over a post list that
            reaches back the full seven days. If fewer than half of either basket’s accounts have a complete figure, the pillar is withheld.
          </p>
          <div className="formula"><var>V</var> = Σ<sub>platforms</sub> <var>e</var> × views in 7 days</div>
          <div className="formula">Engagement = 100 × Σ <var>w</var>·<var>V</var> (extremism) ÷ [ Σ <var>w</var>·<var>V</var> (extremism) + Σ <var>V</var> (reference) ]</div>
          <p>The view worth <var>e</var> of each platform is in the table beside this text.</p>

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
          <div className="formula"><var>g</var> = ln(<var>F</var><sub>now</sub> ÷ <var>F</var><sub>then</sub>) × 365 ÷ days, clipped to ± ln 8</div>
          <div className="formula"><var>G</var> = Σ <var>w</var>·<var>F</var><sub>then</sub>·<var>g</var> ÷ Σ <var>w</var>·<var>F</var><sub>then</sub>, &nbsp; Momentum = 100 × σ( <var>G</var> ÷ ln 2 ), &nbsp; σ(<var>x</var>) = 1 ÷ (1 + e<sup>−<var>x</var></sup>)</div>

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
          <div className="formula">Wikipedia<sub>day</sub> = Σ <var>w</var> × page views</div>
          <div className="formula">News<sub>day</sub> = Σ <var>w</var> × articles naming the constituent ÷ all US articles that day</div>
          <div className="formula">score = 100 × σ( ln(mean of last 7 days ÷ median of the 365 days before) ÷ ln 2 )</div>
          <div className="formula">Heat = mean of the two scores</div>
          <p>
            Only series present in both the latest week and the baseline year enter, so a series that stopped updating cannot pull the
            latest week down.
          </p>

          <h3>Depth</h3>
          <p>
            Each platform has a depth coefficient from 0 (heavily moderated) to 1 (unmoderated). Depth is the audience-weighted mean
            coefficient of the extremism basket, and needs follower counts on at least two platforms.
          </p>
          <div className="formula">Depth = 100 × Σ <var>w</var>·<var>F</var>·<var>d</var><sub>platform</sub> ÷ Σ <var>w</var>·<var>F</var></div>

          <h3>The composite</h3>
          <div className="formula">DRI = Σ <var>weight</var> × <var>pillar</var> ÷ Σ <var>weight</var>, over the pillars available that day</div>
          <p>
            A pillar whose inputs were not recorded is left out and the remaining weights are rescaled. If the available pillars carry less than
            half the total weight, no reading is published. The confidence grade is the weight-averaged share of inputs observed: A from 80%, B
            from 60%, C from 40%, D below.
          </p>
          <div className="formula">Confidence = Σ <var>weight</var> × <var>coverage</var> (available pillars) ÷ Σ <var>weight</var> (all pillars)</div>
          <p>
            Coverage is the share of a pillar’s inputs that were actually read. The robustness band on the front page is the lowest and
            highest composite across a fixed list of alternative assumptions: equal weights, each pillar removed in turn, other tier weights,
            other overlap exponents and other view worths. Every scenario is listed there with its result.
          </p>

          <h3 id="accumulation">Views that are still accumulating</h3>
          <p>
            A capture of a Rumble channel shows each upload’s views to date, and a video keeps collecting views after it goes up. The newest
            weeks therefore look smaller than older ones even when nothing has changed. To compare a new week with a channel’s average, young
            weeks are scaled to where they are heading, using the constant-scaling model of{' '}
            <a href="https://arxiv.org/abs/0811.0405">Szabo and Huberman</a>: views at a later age are views at an earlier age times a factor
            that depends only on the two ages.
          </p>
          <div className="formula"><var>A</var> = <var>V</var>(<var>a</var>) ÷ <var>m</var>(<var>a</var>), &nbsp; 0 &lt; <var>m</var> ≤ 1</div>
          <p>
            <var>V</var>(<var>a</var>) is the recorded views on a week’s uploads at age <var>a</var>, counted in whole weeks since the upload
            week ended, and <var>m</var>(<var>a</var>) is the share of its settled views a week has typically reached by that age. The factors
            are estimated from this project’s own Rumble readings, never borrowed from another platform, in one of two ways.
          </p>
          <p>
            <b>Measured growth</b>, used once two captures about a week apart exist. Every upload week seen in both captures with the same
            number of uploads gives a growth ratio; the median ratio at each age chains to the horizon of{' '}
            {mat ? mat.horizon : 12} weeks, after which a week counts as settled.
          </p>
          <div className="formula"><var>g</var>(<var>a</var>) = median of <var>V</var><sub>later</sub> ÷ <var>V</var><sub>earlier</sub></div>
          <div className="formula"><var>m</var>(<var>a</var>) = 1 ÷ [ <var>g</var>(<var>a</var>) × <var>g</var>(<var>a</var>+1) × … × <var>g</var>({mat ? mat.horizon - 1 : 11}) ]</div>
          <p>
            <b>Provisional factor</b>, used while there is only one capture. With nothing to follow through time, the factor is read across
            weeks: views per video in a young week, against the same channel’s views per video in weeks{' '}
            {mat ? `${mat.reference_ages[0]} to ${mat.reference_ages[1]}` : '3 to 8'} weeks old, then the median across channels.
          </p>
          <div className="formula"><var>r</var><sub>channel</sub>(<var>a</var>) = views per video at age <var>a</var> ÷ views per video at the reference ages</div>
          <div className="formula"><var>m</var>(<var>a</var>) = min( 1, median<sub>channels</sub> <var>r</var> )</div>
          <p>
            This assumes each channel’s typical video drew a steady audience over those two months. Where a channel was really rising or
            falling, the factor absorbs some of that change, which is why it is marked provisional, shown with its range across channels, and
            replaced automatically. An age gets a factor only if at least three channels can supply one; otherwise weeks of that age are left
            as recorded and are not judged.
          </p>

          <h3>A channel’s average week</h3>
          <p>
            Each week is set against the channel’s own recent normal: the mean adjusted views of the {mat ? mat.baseline_weeks : 12} weeks
            before it (at least {mat ? mat.baseline_min_weeks : 4}), with weeks without uploads counted as zero.
          </p>
          <div className="formula"><var>B</var><sub>week</sub> = mean( <var>A</var> over the {mat ? mat.baseline_weeks : 12} weeks before )</div>
          <div className="formula">change = <var>A</var><sub>week</sub> ÷ <var>B</var><sub>week</sub> − 1</div>
          <p>
            A week is called above its usual range only if the low end of its adjusted range is higher than the 90th percentile of those
            earlier weeks, and below only if its high end is lower than the 10th percentile. Anything else is reported as inside the usual
            range, so a week is not called a rise or a fall on the strength of an uncertain correction.
          </p>

          <h3>Views gained between captures</h3>
          <p>
            Two captures also give a figure that needs no model at all: the views a channel actually drew in between, across everything it
            uploaded in the last year.
          </p>
          <div className="formula">gained = Σ<sub>upload weeks in both</sub> ( <var>V</var><sub>later</sub> − <var>V</var><sub>earlier</sub> ) + views on weeks uploaded since</div>

          <h3 id="offline">Recorded incidents offline</h3>
          <p>
            The front page shows counts of incidents recorded by the ADL beside the index. They are counts, not a model: each record in the
            ADL’s published map data is tallied by month and type. A record can carry more than one type, so types are not added together.
            These counts are kept out of the index on purpose. They arrive months late, they depend on what gets reported and on the ADL’s
            definitions, and the reason to have them is to test whether the online reading moves before offline harm does. Folding them into
            the index would make that test circular.
          </p>

          <h3>What this does not measure</h3>
          <p>
            Audience is not agreement, and followers are not all in the United States or all human. The index does not read content, so it cannot
            tell a critic’s audience from a supporter’s. It is a measure of audience and attention online; offline incidents are shown beside
            it, not inside it. The coefficients for moderation
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
                <dt>Growth comparison</dt><dd>{p.growth_lag} days back</dd>
                {mat && <><dt>Weekly average window</dt><dd>{mat.baseline_weeks} weeks</dd></>}
                {mat && <><dt>Views settled after</dt><dd>{mat.method === 'longitudinal' ? mat.horizon : mat.settled_age} weeks</dd></>}
              </dl>
            </div>
          </aside>
        )}
      </div>
    </>
  )
}

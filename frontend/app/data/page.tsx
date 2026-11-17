import type { Metadata } from 'next'
import { loadData } from '@/lib/data'
import { PLATFORM_NAME, longDate, whole } from '@/lib/format'

export const metadata: Metadata = { title: 'Data quality | Dissident Resonance Index' }

function Icon({ kind }: { kind: 'ok' | 'part' | 'off' }) {
  if (kind === 'ok')
    return (
      <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
        <circle cx="7" cy="7" r="7" fill="#0a6b3a" />
        <path d="M3.8 7.2l2.2 2.2 4.2-4.6" fill="none" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    )
  if (kind === 'part')
    return (
      <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
        <path d="M7 0.8l6.4 12H0.6z" fill="#b26a00" />
        <path d="M7 5v3.6M7 10.6v0.1" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    )
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      <rect width="14" height="14" rx="3" fill="#a3261f" />
      <path d="M4 4l6 6M10 4l-6 6" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

export default function Page() {
  const data = loadData()
  if (!data) return <p className="empty">No dataset has been built yet.</p>
  const names = Object.fromEntries(data.constituents.map((c) => [c.id, c.name]))
  const failures = data.sources.flatMap((s) => s.failed.map((f) => ({ ...f, source: s.source })))
  return (
    <>
      <div className="page-head">
        <h1>What was read, and what could not be</h1>
        <p>
          A source that cannot be read is reported here and leaves a gap in the index. It is never replaced with an estimate. The last
          collection ran on {data.meta.last_run ? longDate(data.meta.last_run) : 'an unknown date'}.
        </p>
      </div>

      <section className="section">
        <h2>Sources</h2>
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Last run</th>
                <th>How it is read</th>
                <th className="num">Observations stored</th>
                <th>Covers</th>
              </tr>
            </thead>
            <tbody>
              {data.sources.map((s) => {
                const manual = s.rows > 0 && !s.ok && Boolean(s.skipped || s.failed.length)
                const state: 'ok' | 'part' | 'off' = s.rows === 0 ? 'off' : manual || s.failed.length ? 'part' : 'ok'
                const text =
                  state === 'off' ? (s.skipped ? 'Not collected' : s.failed.length ? 'Failed' : 'No data yet') : manual ? 'Read by hand or in a browser, not by the collector' : state === 'part' ? `${s.ok} read, ${s.failed.length} failed` : s.ok !== null ? `${s.ok} read` : 'Stored'
                return (
                  <tr key={s.source}>
                    <td><span className="who">{PLATFORM_NAME[s.source] ?? s.source}</span></td>
                    <td>
                      <span className="status"><Icon kind={state} /> {text}</span>
                      {s.skipped && <div className="muted">{s.skipped}</div>}
                    </td>
                    <td className="muted">{s.note}</td>
                    <td className="num">{whole(s.rows)}</td>
                    <td className="muted">{s.first ? `${s.first} to ${s.last}` : 'nothing yet'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section">
        <h2>Pillar inputs</h2>
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Pillar</th>
                <th>Status</th>
                <th className="num">Inputs observed</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {data.pillars.map((p) => (
                <tr key={p.id}>
                  <td><span className="who">{p.label}</span></td>
                  <td><span className="status"><Icon kind={p.available ? (p.coverage < 0.6 ? 'part' : 'ok') : 'off'} /> {p.available ? 'Published' : 'Withheld'}</span></td>
                  <td className="num">{Math.round(p.coverage * 100)}%</td>
                  <td className="muted">{p.reason ? p.reason.charAt(0).toUpperCase() + p.reason.slice(1) : p.explain}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {failures.length > 0 && (
        <section className="section">
          <h2>Readings that failed in the last run</h2>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Constituent</th>
                  <th>Account or article</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {failures.map((f, i) => (
                  <tr key={i}>
                    <td>{PLATFORM_NAME[f.source] ?? f.source}</td>
                    <td>{names[f.entity] ?? f.entity}</td>
                    <td className="muted">{f.account}</td>
                    <td>{f.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="section">
        <h2>Reproducing this reading</h2>
        <div className="panel" style={{ marginTop: '1.3rem', maxWidth: '52rem' }}>
          <p className="sub" style={{ fontSize: '0.94rem' }}>
            The dataset behind this site is a pure function of the observation files in the repository, the registry and the model parameters.
            Rebuilding from the same commit gives the same bytes. The fingerprint below is the SHA-256 of every observation file.
          </p>
          <dl className="kv">
            <dt>Reading date</dt><dd>{data.meta.as_of}</dd>
            <dt>Model</dt><dd>{data.meta.model_version}</dd>
            <dt>Registry</dt><dd>{data.meta.registry_version}</dd>
            <dt>Input fingerprint</dt><dd className="digest">{data.meta.input_digest}</dd>
            <dt>Dataset</dt><dd><a href="../data/index.json">index.json</a></dd>
          </dl>
        </div>
      </section>
    </>
  )
}

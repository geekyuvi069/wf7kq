import { useEffect, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

const MIN_DAY = '2026-01-02', MAX_DAY = '2026-02-01' // delivery days for January decisions
const gw = (mw, d = 2) => (mw == null ? '–' : `${(mw / 1000).toFixed(d)} GW`)
const signed = (mw) => (mw == null ? '–' : `${mw > 0 ? '+' : ''}${gw(mw)}`)
const fmtTime = (t) => new Date(t).toLocaleString('en-GB', { timeZone: 'Europe/London', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
const fmtDay = (t) => new Date(t).toLocaleDateString('en-GB', { timeZone: 'Europe/London', day: 'numeric', month: 'short' })
const axis = { stroke: 'var(--axis)', tick: { fill: 'var(--muted)', fontSize: 12 }, tickLine: false }
// Y axis in GW with round ticks (0.5/1/2/5/10 GW steps) spanning `values` (MW) and zero.
function yGW(values) {
  const v = values.filter((x) => x != null)
  const lo = Math.min(0, ...v), hi = Math.max(1, ...v)
  const step = [500, 1000, 2000, 5000].find((s) => (hi - lo) / s <= 6) ?? 10000
  const ticks = []
  for (let t = Math.floor(lo / step) * step; t < hi + step; t += step) ticks.push(t)
  return { ...axis, ticks, domain: [ticks[0], ticks.at(-1)], tickFormatter: (x) => +(x / 1000).toFixed(1), width: 36 }
}

function useJson(url) {
  const [state, setState] = useState({ data: null, error: null })
  useEffect(() => {
    const ctrl = new AbortController()
    fetch(url, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
      .then((data) => setState({ data, error: null }))
      .catch((e) => e.name !== 'AbortError' && setState((s) => ({ ...s, error: e.message })))
    return () => ctrl.abort()
  }, [url])
  return state
}

function Tip({ active, payload, label, labelFormatter, rows }) {
  if (!active || !payload?.length) return null
  return (
    <div className="tip">
      <b>{labelFormatter ? labelFormatter(label) : label}</b>
      {rows(payload[0].payload).map(([k, v]) => <div key={k}>{k}: <b>{v}</b></div>)}
    </div>
  )
}

const Legend = ({ items }) => (
  <div className="legend">{items.map(([name, color]) => (
    <span key={name}><i style={{ background: color }} />{name}</span>
  ))}</div>
)

const Card = ({ label, value, hint, keyCard }) => (
  <div className={`card${keyCard ? ' key' : ''}`}>
    <div className="label">{label}</div>
    <div className="value">{value}</div>
    <div className="hint">{hint}</div>
  </div>
)

export default function App() {
  const [start, setStart] = useState(MIN_DAY)
  const [end, setEnd] = useState(MAX_DAY)
  const [mode, setMode] = useState('decision')
  const [decision, setDecision] = useState('09:20')
  const [horizon, setHorizon] = useState(24)

  const range = `start=${start}&end=${end}`
  const q = `${range}&${mode === 'decision' ? `decision=${decision}` : `horizon=${horizon}`}`
  const series = useJson(`/api/series?${q}`)
  const stats = useJson(`/api/stats?${q}`)
  const hz = useJson(`/api/horizon?${range}`)
  const error = series.error || stats.error || hz.error

  const rows = (series.data || []).map((r) => ({
    ...r, t: Date.parse(r.time),
    lead: r.publishTime ? (Date.parse(r.time) - Date.parse(r.publishTime)) / 36e5 : null,
  }))
  const leads = rows.map((r) => r.lead).filter((x) => x != null)
  const s = stats.data

  return (
    <main>
      <h1>GB Wind Forecast Monitor</h1>
      <p className="sub">National wind generation: what the forecast said when you had to buy, vs what actually blew. Day-ahead purchases made in January 2026.</p>

      <div className="controls">
        <label>Delivery from
          <input type="date" value={start} min={MIN_DAY} max={end} onChange={(e) => e.target.value && setStart(e.target.value)} />
        </label>
        <label>to
          <input type="date" value={end} min={start} max={MAX_DAY} onChange={(e) => e.target.value && setEnd(e.target.value)} />
        </label>
        <div className="field" role="group" aria-labelledby="mode-label">
          <span id="mode-label">Forecast used</span>
          <span className="seg">
            <button aria-pressed={mode === 'decision'} onClick={() => setMode('decision')}>At decision time</button>
            <button aria-pressed={mode === 'horizon'} onClick={() => setMode('horizon')}>Fixed horizon</button>
          </span>
        </div>
        {mode === 'decision' ? (
          <label>Decision time on D-1 (UK)
            <input type="time" value={decision} onChange={(e) => e.target.value && setDecision(e.target.value)} />
          </label>
        ) : (
          <label>Published ≥ {horizon} h before delivery
            <input type="range" min="1" max="48" value={horizon} onChange={(e) => setHorizon(+e.target.value)} />
          </label>
        )}
      </div>
      {mode === 'decision' && <p className="note">Default 09:20 UK = EPEX GB day-ahead auction gate closure (N2EX closes 09:50). The latest forecast published by then is used for every hour of day D.</p>}
      {error && <p className="error">Could not load data: {error}</p>}

      {s && s.n > 0 && (
        <div className="cards">
          <Card keyCard label="Wind you can count on" value={`${Math.round(s.ratio_p10 * 100)}%`} hint="of forecast: actual reached this in 9 of 10 hours" />
          <Card keyCard label="Extra to buy (90% cover)" value={gw(s.shortfall_p90)} hint="wind fell short of forecast by more than this in only 1 in 10 hours" />
          <Card label="Bias" value={signed(s.bias)} hint={s.bias > 0 ? 'forecast too high on average' : 'forecast too low on average'} />
          <Card label="Mean absolute error" value={gw(s.mae)} hint={`MAPE ${s.mape?.toFixed(1)}% · RMSE ${gw(s.rmse)}`} />
          <Card label="Median absolute error" value={gw(s.median_ae)} hint={`P90 ${gw(s.p90_ae)} · P99 ${gw(s.p99_ae)}`} />
          <Card label="Hours compared" value={s.n} hint={`mean actual ${gw(s.mean_actual, 1)} · forecast ${gw(s.mean_forecast, 1)}`} />
        </div>
      )}

      <section className="panel">
        <h2>Actual vs forecast (GW)</h2>
        <Legend items={[['Actual', 'var(--series-1)'], ['Forecast used', 'var(--series-2)']]} />
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={fmtDay} minTickGap={40} {...axis} />
            <YAxis {...yGW(rows.flatMap((r) => [r.actual, r.forecast]))} />
            <Tooltip labelFormatter={fmtTime} content={<Tip rows={(r) => [
              ['Actual', gw(r.actual)], ['Forecast', gw(r.forecast)],
              ['Error', r.forecast == null ? '–' : signed(r.forecast - r.actual)],
              ['Published', r.publishTime ? `${fmtTime(r.publishTime)} (${r.lead.toFixed(1)} h ahead)` : '–'],
            ]} />} />
            <Line dataKey="actual" stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="forecast" stroke="var(--series-2)" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
        <details>
          <summary>Show table</summary>
          <div className="tablewrap"><table>
            <thead><tr><th>Delivery (UK)</th><th>Actual MW</th><th>Forecast MW</th><th>Error MW</th><th>Published (UK)</th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.time}><td>{fmtTime(r.time)}</td><td>{r.actual}</td><td>{r.forecast ?? '–'}</td>
                <td>{r.forecast == null ? '–' : r.forecast - r.actual}</td><td>{r.publishTime ? fmtTime(r.publishTime) : '–'}</td></tr>
            ))}</tbody>
          </table></div>
        </details>
      </section>

      <div className="grid2">
        <section className="panel">
          <h2>Error by hour of day (GW)</h2>
          <Legend items={[['Mean absolute error', 'var(--series-1)'], ['Bias (forecast − actual)', 'var(--series-2)']]} />
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={s?.by_hour || []} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={2}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="hour" {...axis} tickFormatter={(h) => String(h).padStart(2, '0')} interval={2} />
              <YAxis {...yGW((s?.by_hour || []).flatMap((r) => [r.mae, r.bias]))} />
              <ReferenceLine y={0} stroke="var(--axis)" />
              <Tooltip cursor={{ fill: 'var(--band)' }} labelFormatter={(h) => `${String(h).padStart(2, '0')}:00 UK`}
                content={<Tip rows={(r) => [['MAE', gw(r.mae)], ['Bias', signed(r.bias)], ['Hours', r.n]]} />} />
              <Bar dataKey="mae" fill="var(--series-1)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="bias" fill="var(--series-2)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="panel">
          <h2>Error vs forecast horizon (GW)</h2>
          <Legend items={[['Mean absolute error', 'var(--series-1)'], ['P90 absolute error', 'var(--series-2)']]} />
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={hz.data || []} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="horizon" type="number" domain={[1, 48]} ticks={[1, 6, 12, 18, 24, 30, 36, 42, 48]} unit="h" {...axis} />
              <YAxis {...yGW((hz.data || []).flatMap((r) => [r.mae, r.p90_ae]))} />
              {mode === 'decision' && leads.length > 0 && (
                <ReferenceArea x1={Math.max(1, Math.min(...leads))} x2={Math.min(48, Math.max(...leads))} fill="var(--band)" stroke="none" />
              )}
              {mode === 'horizon' && <ReferenceLine x={horizon} stroke="var(--muted)" strokeDasharray="3 3" />}
              <Tooltip labelFormatter={(h) => `${h} h ahead`}
                content={<Tip rows={(r) => [['MAE', gw(r.mae)], ['P90', gw(r.p90_ae)], ['Bias', signed(r.bias)], ['Hours', r.n]]} />} />
              <Line dataKey="mae" stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line dataKey="p90_ae" stroke="var(--series-2)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
          <p className="note">{mode === 'decision'
            ? 'Shaded: how far ahead your decision-time forecast was for day D.'
            : 'Dashed: the horizon selected above.'} Closer to delivery means smaller error.</p>
        </section>
      </div>
    </main>
  )
}

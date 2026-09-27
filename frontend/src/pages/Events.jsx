import { useEffect, useState } from 'react';
import { api, display, formatConfidence, prettyId, statusColor } from '../services/api.js';
import EventLog from '../components/EventLog.jsx';

export default function Events() {
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filter, setFilter] = useState('ALL');
  const [limit, setLimit] = useState(200);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const [ev, sum] = await Promise.all([
        api.events(limit).catch(() => []),
        api.missionSummary().catch(() => null),
      ]);
      setEvents(Array.isArray(ev) ? ev : []);
      setSummary(sum);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 1000);
    return () => clearInterval(t);
  }, [limit]);

  const filtered = filter === 'ALL'
    ? events
    : events.filter((e) => String(e.status ?? e.decision?.status ?? '').toUpperCase() === filter);

  const counts = { ALL: events.length };
  for (const e of events) {
    const s = String(e.status ?? e.decision?.status ?? 'OTHER').toUpperCase();
    counts[s] = (counts[s] ?? 0) + 1;
  }

  const filters = ['ALL', 'CORRECT', 'DEVIATION', 'UNCERTAIN', 'COMPLETED', 'RECOVERED'];

  return (
    <div className="pages-wrap">
      <header className="page-head">
        <div>
          <h2>Events</h2>
          <p>Real-time perception events, decisions and deviation notifications.</p>
        </div>
        <div className="page-actions">
          <label className="field">
            <span>Limit</span>
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              {[50, 100, 200, 500, 1000].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <button className="btn btn-primary" type="button" onClick={refresh}>Refresh</button>
        </div>
      </header>

      <section className="card">
        <div className="card-head">
          <h3>Summary</h3>
          <span>{display(counts.ALL)} events</span>
        </div>
        <div className="summary-grid">
          <div className="summary-cell">
            <span className="mono">{display(summary?.total_events ?? counts.ALL)}</span>
            <label>Total events</label>
          </div>
          <div className="summary-cell" style={{ borderLeftColor: 'var(--color-correct)' }}>
            <span className="mono" style={{ color: 'var(--color-correct)' }}>{display(summary?.correct ?? counts.CORRECT ?? 0)}</span>
            <label>Correct</label>
          </div>
          <div className="summary-cell" style={{ borderLeftColor: 'var(--color-alert)' }}>
            <span className="mono" style={{ color: 'var(--color-alert)' }}>{display(summary?.deviations ?? counts.DEVIATION ?? 0)}</span>
            <label>Deviations</label>
          </div>
          <div className="summary-cell" style={{ borderLeftColor: 'var(--color-warn)' }}>
            <span className="mono" style={{ color: 'var(--color-warn)' }}>{display(summary?.uncertain ?? counts.UNCERTAIN ?? 0)}</span>
            <label>Uncertain</label>
          </div>
          <div className="summary-cell" style={{ borderLeftColor: 'var(--color-info)' }}>
            <span className="mono" style={{ color: 'var(--color-info)' }}>{display(summary?.completed ?? counts.COMPLETED ?? 0)}</span>
            <label>Completed</label>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h3>Filters</h3>
          <span className="mono">{display(filtered.length)} shown</span>
        </div>
        <div className="filter-bar">
          {filters.map((f) => (
            <button key={f} type="button"
              className={filter === f ? 'chip chip-active' : 'chip'}
              style={filter === f ? { background: statusColor(f), color: '#0b1020' } : {}}
              onClick={() => setFilter(f)}>
              {prettyId(f)} <span className="mono">{display(counts[f] ?? 0)}</span>
            </button>
          ))}
        </div>
      </section>

      <EventLog events={filtered} limit={limit} />
    </div>
  );
}

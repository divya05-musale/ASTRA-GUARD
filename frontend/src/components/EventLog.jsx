import { display, formatConfidence, prettyId, statusColor, stepNumber } from '../services/api.js';

function tsDisplay(ts) {
  if (!ts) return '--';
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return String(ts).slice(0, 19);
    return d.toLocaleTimeString();
  } catch {
    return String(ts).slice(0, 19);
  }
}

export default function EventLog({ events, limit = 80 }) {
  const rows = (Array.isArray(events) ? events : []).slice().reverse().slice(0, limit);
  return (
    <section className="card log-card">
      <div className="card-head">
        <h3>Event Log</h3>
        <span className="mono">{display(rows.length)} rows</span>
      </div>
      <div className="log-wrap">
        <table className="log-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Step</th>
              <th>Status</th>
              <th>Activity</th>
              <th>Object</th>
              <th>Conf.</th>
              <th>Deviation</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan="7" className="log-empty">No events yet. Start the perception pipeline to populate the log.</td></tr>
            ) : rows.map((e, idx) => {
              const st = e.status ?? e.decision?.status;
              return (
                <tr key={idx} className={st ? `log-${String(st).toLowerCase()}` : ''}>
                  <td className="mono">{tsDisplay(e.timestamp ?? e.decision?.timestamp)}</td>
                  <td className="mono">{display(e.step_id ?? e.decision?.step_id)}</td>
                  <td><span className="badge" style={{ background: statusColor(st), color: '#0b1020' }}>{prettyId(st ?? 'EVENT')}</span></td>
                  <td>{prettyId(e.activity ?? e.decision?.activity)}</td>
                  <td>{display(e.object ?? e.detected_object ?? e.decision?.object)}</td>
                  <td className="mono">{formatConfidence(e.confidence ?? e.decision?.confidence)}</td>
                  <td style={{ color: statusColor(e.deviation_type ?? e.decision?.deviation_type) }}>
                    {prettyId(e.deviation_type ?? e.decision?.deviation_type ?? '--')}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

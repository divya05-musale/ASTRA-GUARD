import { display, formatConfidence, pillClass, prettyId } from './flightdeck.js';

export default function RecentEvents({ events }) {
  const rows = [...(events || [])].reverse();
  return (
    <section className="card events-card">
      <div className="card-head"><h3>Recent Mission Events</h3><span className="card-tag">{rows.length} shown</span></div>
      {rows.length === 0 ? (
        <div className="empty">No mission events yet — session is IDLE. Run the Python pipeline to generate real events.</div>
      ) : (
        <div className="table-wrap">
          <table className="etable">
            <thead>
              <tr>
                <th>Time</th><th>Status</th><th>Step</th><th>Activity</th>
                <th>Detected Object</th><th>Confidence</th><th>Guidance</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e, i) => (
                <tr key={i}>
                  <td className="mono">{display(e.timestamp)}</td>
                  <td><span className={pillClass(e.status)}>{display(e.status)}</span></td>
                  <td className="mono">{display(e.step_id)}</td>
                  <td>{prettyId(e.activity)}</td>
                  <td>{prettyId(e.detected_object)}</td>
                  <td className="mono">{formatConfidence(e.confidence)}</td>
                  <td className="guide-cell">{display(e.guidance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

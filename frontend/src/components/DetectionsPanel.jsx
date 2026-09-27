import { display, formatConfidence, prettyId } from '../services/api.js';

export default function DetectionsPanel({ objects, hands, status, event }) {
  const objList = Array.isArray(objects) ? objects : [];
  const handList = Array.isArray(hands) ? hands : [];
  return (
    <section className="card detections-card">
      <div className="card-head">
        <h3>Detections</h3>
        <span className="live-meta">
          <span className={objList.length + handList.length > 0 ? 'dot dot-on' : 'dot dot-off'}>●</span>
          <span>{objList.length + handList.length} signals</span>
        </span>
      </div>
      <div className="detection-section">
        <h4>Objects ({display(objList.length)})</h4>
        {objList.length === 0 ? (
          <p className="detections-empty">No objects detected yet.</p>
        ) : (
          <ul className="detection-list">
            {objList.slice(0, 20).map((o, idx) => (
              <li key={`o-${idx}`}>
                <span className="badge badge-obj">{prettyId(o.class_name ?? o.class_id)}</span>
                <span className="mono">{formatConfidence(o.confidence)}</span>
                {o.track_id ? <span className="mono">T{display(o.track_id)}</span> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="detection-section">
        <h4>Hands ({display(handList.length)})</h4>
        {handList.length === 0 ? (
          <p className="detections-empty">No hands detected yet.</p>
        ) : (
          <ul className="detection-list">
            {handList.slice(0, 6).map((h, idx) => (
              <li key={`h-${idx}`}>
                <span className="badge badge-hand">{display(h.handedness ?? 'Hand')}</span>
                <span className="mono">{formatConfidence(h.score)}</span>
                {Array.isArray(h.landmarks) ? <span className="mono">{display(h.landmarks.length)} LM</span> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
      {(event || status?.detected_object) && (
        <div className="detection-section">
          <h4>Interpreted Event</h4>
          <dl className="event-grid">
            <div><dt>Activity</dt><dd>{prettyId(event?.activity ?? status?.activity)}</dd></div>
            <div><dt>Object</dt><dd>{display(event?.object ?? status?.detected_object)}</dd></div>
            <div><dt>Confidence</dt><dd>{formatConfidence(event?.confidence ?? status?.confidence)}</dd></div>
            <div><dt>Reason</dt><dd>{display(event?.reason ?? status?.reason)}</dd></div>
          </dl>
        </div>
      )}
    </section>
  );
}

import { display, pillClass } from './flightdeck.js';

export default function DecisionSequence({ events }) {
  const seq = (events || []).slice(-12);
  return (
    <section className="card">
      <div className="card-head"><h3>Decision Sequence</h3><span className="card-tag">{seq.length} recent</span></div>
      {seq.length === 0 ? (
        <div className="empty">No decisions yet.</div>
      ) : (
        <div className="seq">
          {seq.map((e, i) => (
            <span key={i} className={pillClass(e.status)} title={`${display(e.step_id)} · ${display(e.status)}`}>
              {display(e.status)}
            </span>
          ))}
        </div>
      )}
      <div className="seq-note">Real event statuses, newest last.</div>
    </section>
  );
}

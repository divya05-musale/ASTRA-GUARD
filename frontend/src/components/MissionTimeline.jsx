import { display, prettyId, stepNumber } from './flightdeck.js';

function stepState(step, currentId, currentNum, events) {
  const num = Number(step?.order ?? stepNumber(step?.step_id));
  if (currentNum !== null && num < currentNum) return 'done';
  // Deviation/uncertain observed at the current step (from live events).
  const mine = (events || []).filter((e) => e.step_id === step?.step_id);
  const last = mine[mine.length - 1];
  if (step?.step_id === currentId) {
    if (last?.status === 'DEVIATION' || last?.deviation) return 'deviation';
    if (last?.status === 'UNCERTAIN') return 'uncertain';
    return 'current';
  }
  if (currentNum !== null && num > currentNum) return 'pending';
  return 'pending';
}

export default function MissionTimeline({ protocol, progress, events }) {
  const steps = protocol?.steps ?? [];
  const currentId = progress?.current_step ?? null;
  const currentNum = stepNumber(currentId);
  return (
    <section className="card">
      <div className="card-head"><h3>Mission Timeline</h3><span className="card-tag">{steps.length} steps</span></div>
      {steps.length === 0 ? (
        <div className="empty">Protocol steps unavailable.</div>
      ) : (
        <ol className="timeline">
          {steps.map((s) => {
            const st = stepState(s, currentId, currentNum, events);
            return (
              <li key={s.step_id} className={`tl tl-${st}`}>
                <span className="tl-mark">
                  {st === 'done' ? '✓' : st === 'deviation' ? '!' : st === 'uncertain' ? '?' : st === 'current' ? '●' : '○'}
                </span>
                <span className="tl-body">
                  <b>{display(s.order)}. {prettyId(s.activity)}</b>
                  <span className="tl-sub">
                    {s.step_id} · {prettyId(s.expected_object)}
                    {st === 'current' ? ' · CURRENT' : ''}
                    {st === 'deviation' ? ' · Deviation detected' : ''}
                    {st === 'done' ? ' · Completed' : st === 'pending' ? ' · Pending' : ''}
                  </span>
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

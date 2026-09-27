import { display, prettyId, statusColor } from '../services/api.js';

export default function ProtocolSteps({ protocol, progress, events, currentStepId }) {
  const steps = Array.isArray(protocol?.steps) ? protocol.steps : [];
  const completedCount = Number(progress?.completed_steps ?? 0);
  const current = currentStepId ?? progress?.current_step ?? null;
  const eventByStep = new Map();
  for (const ev of (events ?? []).slice().reverse()) {
    const sid = ev?.step_id;
    if (sid && !eventByStep.has(sid)) eventByStep.set(sid, ev);
  }
  return (
    <section className="card steps-card">
      <div className="card-head">
        <h3>Protocol Steps</h3>
        <span className="mono">{display(steps.length)} steps</span>
      </div>
      <ol className="steps-list">
        {steps.map((s, idx) => {
          const sid = String(s.step_id ?? '');
          const order = Number(s.order ?? idx + 1);
          const isCompleted = order <= completedCount;
          const isCurrent = current === sid;
          const ev = eventByStep.get(sid);
          const st = ev?.status ?? (isCompleted ? 'CORRECT' : isCurrent ? 'PENDING' : 'PENDING');
          return (
            <li
              key={sid}
              className={`step-row ${isCurrent ? 'step-current' : ''} ${isCompleted ? 'step-done' : ''}`}
            >
              <div className="step-indicator" style={{ background: isCurrent ? 'var(--color-info)' : isCompleted ? 'var(--color-correct)' : 'transparent' }}>
                {display(order)}
              </div>
              <div className="step-body">
                <div className="step-title">
                  <span className="mono">{display(sid)}</span>
                  <span>{prettyId(s.activity ?? '')}</span>
                  <span className="badge" style={{ background: statusColor(st), color: '#0b1020' }}>
                    {prettyId(st)}
                  </span>
                </div>
                <div className="step-sub">
                  <span>Expected object: {display(s.expected_object)}</span>
                  {s.timeout_sec ? <span>· Timeout {display(s.timeout_sec)}s</span> : null}
                </div>
                {s.description ? <p className="step-desc">{display(s.description)}</p> : null}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

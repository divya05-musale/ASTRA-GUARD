import { stepNumber, display, prettyId, statusColor } from '../services/api.js';

export default function MissionProgress({ progress, summary, status }) {
  const total = Number(progress?.total_steps ?? 0);
  const completed = Number(progress?.completed_steps ?? 0);
  const current = progress?.current_step ?? status?.step_id ?? null;
  const pct = total > 0 ? Math.min(100, Math.max(0, Number(progress?.progress_percent ?? (completed / total) * 100))) : 0;
  const complete = Boolean(progress?.completed);
  const eventsTotal = Number(summary?.total_events ?? 0);
  const correct = Number(summary?.correct ?? 0);
  const deviations = Number(summary?.deviations ?? 0);
  const uncertain = Number(summary?.uncertain ?? 0);
  return (
    <section className="card progress-card">
      <div className="card-head">
        <h3>Mission Progress</h3>
        <span className={complete ? 'conn conn-on' : 'conn conn-off'}>
          ● {complete ? 'COMPLETE' : 'IN PROGRESS'}
        </span>
      </div>
      <div className="progress-row">
        <div className="progress-label">
          <span>Step {display(stepNumber(current) ?? '--')} of {display(total || '--')}</span>
          <span className="mono">{pct.toFixed(0)}%</span>
        </div>
        <div className="progress-bar"><div className="progress-fill" style={{ width: `${pct}%` }} /></div>
      </div>
      <div className="progress-stats">
        <div>
          <span>Events</span><b>{display(eventsTotal || 0)}</b>
        </div>
        <div>
          <span>Correct</span><b style={{ color: 'var(--color-correct)' }}>{display(correct || 0)}</b>
        </div>
        <div>
          <span>Deviations</span><b style={{ color: 'var(--color-alert)' }}>{display(deviations || 0)}</b>
        </div>
        <div>
          <span>Uncertain</span><b style={{ color: 'var(--color-warn)' }}>{display(uncertain || 0)}</b>
        </div>
      </div>
      {status?.step_id && (
        <div className="progress-current">
          <span className="badge" style={{ background: statusColor(status?.status) }}>
            {prettyId(status?.status ?? 'PENDING')}
          </span>
          <span className="mono">{display(status?.step_id)}</span>
          <span>{display(status?.activity ?? status?.next_activity)}</span>
        </div>
      )}
    </section>
  );
}

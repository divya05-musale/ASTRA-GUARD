import { display } from './flightdeck.js';
import { formatConfidence, prettyId } from '../services/api.js';

export default function MissionStatusCard({ progress, summary, status }) {
  const pct = Number(progress?.progress_percent ?? 0);
  const done = Number(progress?.completed_steps ?? 0);
  const total = Number(progress?.total_steps ?? 0);
  const dev = Number(summary?.deviations ?? 0);
  return (
    <section className="card">
      <div className="card-head">
        <h3>Mission Status</h3>
        <span className="card-tag">{progress?.completed ? 'MISSION COMPLETE' : 'IN PROGRESS'} · {display(pct)}%</span>
      </div>
      <div className="bar"><div className="bar-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} /></div>
      <div className="metric-grid">
        <div className="metric"><span>Active Step</span><b>{display(progress?.current_step)} of {display(total)}</b></div>
        <div className="metric"><span>Completed</span><b>{display(done)} steps</b></div>
        <div className="metric"><span>Decision</span><b>{prettyId(status?.status)}</b></div>
        <div className="metric"><span>Confidence</span><b>{formatConfidence(status?.confidence)}</b></div>
        <div className="metric"><span>Current Deviation</span><b>{prettyId(status?.deviation ?? 'NONE')}</b></div>
        <div className="metric"><span>Recorded Deviations</span><b>{dev}</b></div>
      </div>
    </section>
  );
}

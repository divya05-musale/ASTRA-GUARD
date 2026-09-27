import { display } from './flightdeck.js';

export default function EventStatistics({ summary }) {
  const cells = [
    ['Correct', summary?.correct],
    ['Deviations', summary?.deviations],
    ['Uncertain', summary?.uncertain],
    ['Completed', summary?.completed],
  ];
  return (
    <section className="card">
      <div className="card-head"><h3>Event Statistics</h3><span className="card-tag">{display(summary?.total_events)} events</span></div>
      <div className="stat4">
        {cells.map(([k, v]) => (
          <div key={k} className="stat4-cell"><span>{k}</span><b>{display(v ?? 0)}</b></div>
        ))}
      </div>
    </section>
  );
}

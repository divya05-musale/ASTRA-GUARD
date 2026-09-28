import {
  demoMission,
  demoProtocol,
  demoProgress,
  demoStatus,
  demoSummary,
  demoEvents,
} from '../services/demoData.js';

export default function DemoDashboard() {
  const progress = demoProgress.progress_percent;

  return (
    <div className="deck-shell">
      {/* Top Navigation */}
      <header className="topnav">
        <div className="topnav-left">
          <span className="brand">ASTRA-DRISHTI</span>
          <span className="sep">|</span>
          <span className="deck">FLIGHT DECK</span>
        </div>

        <div className="topnav-right">
          <span className="badge">DEMO MODE</span>
          <span className="conn conn-off">OFFLINE</span>
        </div>
      </header>

      <main className="deck-main">
        {/* Mission Control */}
        <section className="card demo-mission-card">
          <div className="card-head">
            <h2>Mission Control</h2>
            <span className="badge">SYNTHETIC DATA</span>
          </div>

          <h3>{demoMission.mission_name}</h3>

          <p>
            Experiment: {demoMission.experiment_id}
          </p>

          <p>
            Mission Status: {demoStatus.status}
          </p>

          <p>
            Current Step: {demoProgress.current_step} of{' '}
            {demoProgress.total_steps}
          </p>

          {/* Protocol Progress */}
          <div className="card demo-progress-card">
            <div className="card-head">
              <h3>Protocol Progress</h3>
              <strong>{progress}%</strong>
            </div>

            <div
              className="bar"
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Demo protocol progress"
            >
              <div
                className="bar-fill"
                style={{
                  width: `${progress}%`,
                  background: '#22c55e',
                }}
              />
            </div>

            <p>{progress}% completed</p>
          </div>
        </section>

        {/* Main Two-Column Layout */}
        <div className="deck-grid demo-grid">
          {/* Protocol Steps */}
          <section className="card">
            <div className="card-head">
              <h3>Protocol Steps</h3>
              <span>{demoProtocol.steps.length} Steps</span>
            </div>

            <ol className="demo-protocol-list">
              {demoProtocol.steps.map((step) => (
                <li key={step.step_id}>
                  <strong>
                    Step {step.order}: {step.activity}
                  </strong>

                  <p>
                    Expected Object: {step.expected_object}
                  </p>
                </li>
              ))}
            </ol>
          </section>

          {/* Mission Summary and Camera Feed */}
          <section className="card">
            <div className="card-head">
              <h3>Mission Summary</h3>
            </div>

            <div className="demo-summary-grid">
              <div className="demo-summary-item">
                <span>Completed Steps</span>
                <strong>
                  {demoSummary.completed_steps}/{demoSummary.total_steps}
                </strong>
              </div>

              <div className="demo-summary-item">
                <span>Recorded Demo Events</span>
                <strong>{demoSummary.total_events}</strong>
              </div>

              <div className="demo-summary-item">
                <span>Demo Deviations</span>
                <strong>{demoSummary.deviations}</strong>
              </div>

              <div className="demo-summary-item">
                <span>Mission Status</span>
                <strong>{demoStatus.status}</strong>
              </div>
            </div>

            {/* Camera Feed */}
            <div className="card camera-card demo-camera-card">
              <div className="card-head">
                <h3>Camera Feed</h3>
                <span className="conn conn-off">UNAVAILABLE</span>
              </div>

              <div className="demo-camera-placeholder">
                <div>
                  <strong>CAMERA UNAVAILABLE</strong>

                  <p>
                    Demo Mode is active.
                    <br />
                    No live video is being processed.
                  </p>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Demo Events */}
        <section className="card">
          <div className="card-head">
            <h3>Demo Events</h3>
            <span>{demoEvents.length} Events</span>
          </div>

          <div className="demo-events-grid">
            {demoEvents.map((event, index) => (
              <div
                className="demo-event"
                key={`${event.step_id}-${index}`}
              >
                <div className="demo-event-head">
                  <strong>{event.status}</strong>
                  <span>{event.step_id}</span>
                </div>

                <p className="demo-event-activity">
                  {event.activity}
                </p>

                <p className="demo-event-guidance">
                  {event.guidance}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Footer */}
        <footer className="deck-foot">
          <span>ASTRA-DRISHTI · Demo Dashboard</span>
          <span>DEMO MODE · Synthetic Data</span>
          <span>Live Camera: Unavailable</span>
        </footer>
      </main>
    </div>
  );
}
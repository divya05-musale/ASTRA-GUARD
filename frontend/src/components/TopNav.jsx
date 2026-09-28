import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from '../services/api.js';
import { display, stepNumber, utcNow } from './flightdeck.js';

export default function TopNav({ connected, health, active, onNav }) {
  const [now, setNow] = useState(utcNow());
  const timer = useRef(null);

  useEffect(() => {
    timer.current = setInterval(() => setNow(utcNow()), 1000);
    return () => clearInterval(timer.current);
  }, []);

  const items = ['Mission', 'Live Feed', 'Memory', 'Analytics', 'Settings'];
  const resetMission = useCallback(async () => {
    try { await api.resetMission(); } catch { /* surface via next poll */ }
  }, []);

  return (
    <header className="topnav">
      <div className="topnav-left">
        <span className="brand">ASTRA-DRISHTI</span>
        <span className="sep">|</span>
        <span className="deck">FLIGHT DECK</span>
        <nav className="tabs">
          {items.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => onNav(n)}
              className={n === active ? 'tab tab-active' : 'tab'}
            >
              {n}
            </button>
          ))}
        </nav>
      </div>
      <div className="topnav-right">
        <button type="button" className="btn btn-ghost" onClick={resetMission} title="POST /api/mission/reset">
          Reset
        </button>
        <span className={connected ? 'conn conn-on' : 'conn conn-off'}>
          ● {connected ? 'NOMINAL' : 'OFFLINE'}
        </span>
        <span className="clock mono">{now}</span>
        <span className="link mono">{display(api.base)}</span>
      </div>
    </header>
  );
}

export function MissionHeader({ overview, progress, status, onExperimentSelected }) {
  const [experiments, setExperiments] = useState([]);
  const [selecting, setSelecting] = useState(false);
  const [canceling, setCanceling] = useState(false);
  const [selectionError, setSelectionError] = useState('');
  const total = Number(progress?.total_steps ?? 0);
  const num = stepNumber(progress?.current_step ?? status?.step_id);
  const active = status?.active;
  const complete = status?.status === 'COMPLETED' || progress?.completed;

  useEffect(() => {
    let mounted = true;
    api.experiments()
      .then((result) => {
        if (mounted) setExperiments((result?.experiments ?? []).filter((item) => item.available));
      })
      .catch(() => {
        if (mounted) setSelectionError('Experiment registry is unavailable.');
      });
    return () => { mounted = false; };
  }, []);

  const selectExperiment = async (experimentId) => {
    if (!experimentId || experimentId === overview?.protocol_id) return;
    setSelecting(true);
    setSelectionError('');
    try {
      await api.selectExperiment(experimentId);
      await onExperimentSelected?.();
    } catch (error) {
      setSelectionError(error instanceof Error ? error.message : String(error));
    } finally {
      setSelecting(false);
    }
  };

  const cancelSession = async () => {
    if (!status?.session_id || !window.confirm('Cancel this active session? Its history, events, and evidence will be kept.')) return;
    setCanceling(true);
    setSelectionError('');
    try {
      await api.endSession(status.session_id, 'CANCELLED');
      await onExperimentSelected?.();
    } catch (error) {
      setSelectionError(error instanceof Error ? error.message : String(error));
    } finally {
      setCanceling(false);
    }
  };

  return (
    <div className="mission-head">
      <div>
        <div className="mission-kicker">
          <h2>Mission Control</h2>
          <span className={active || complete ? 'conn conn-on' : 'conn conn-off'}>
            ● {complete ? 'COMPLETE' : active ? 'IN PROGRESS' : 'STANDBY'}
          </span>
        </div>
        <div className="mission-step">
          {active && num && total ? `Step ${num} of ${total}` : complete ? 'Mission complete' : 'Awaiting mission start'}
        </div>
        <p className="mission-sub">Real-time perception, decision and guidance for the active mission.</p>
      </div>
      <div className="profile card">
        <div className="profile-kicker">Profile</div>
        <label className="profile-selector">
          Experiment
          <select
            className="profile-select"
            aria-label="Select experiment"
            value={overview?.protocol_id ?? ''}
            disabled={selecting || experiments.length === 0}
            onChange={(event) => selectExperiment(event.target.value)}
          >
            {experiments.length === 0 ? <option value="">Loading experiments…</option> : null}
            {experiments.map((experiment) => (
              <option key={experiment.experiment_id} value={experiment.experiment_id}>
                {experiment.experiment_id} · {experiment.name}
              </option>
            ))}
          </select>
        </label>
        {selectionError ? <div className="profile-error" role="alert">{selectionError}</div> : null}
        {active && status?.session_id ? (
          <button className="btn btn-ghost" type="button" onClick={cancelSession} disabled={canceling || selecting}>
            {canceling ? 'Cancelling…' : 'Cancel Session'}
          </button>
        ) : null}
        <div className="profile-title">
          {display(overview?.protocol_id)} · {display(overview?.protocol_name)}
        </div>
        <div className="badges">
          <span className="badge">{display(overview?.environment)}</span>
          <span className="badge">{display(overview?.protocol_type)} Protocol</span>
          <span className="badge">{display(total)} Steps</span>
        </div>
      </div>
    </div>
  );
}

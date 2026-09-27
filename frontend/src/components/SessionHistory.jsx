import { useEffect, useState } from 'react';
import { api, display, prettyId } from '../services/api.js';

export default function SessionHistory() {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');
  const [actionBusy, setActionBusy] = useState(false);

  const refresh = async () => {
    try {
      const result = await api.sessions();
      setSessions(Array.isArray(result?.sessions) ? result.sessions : []);
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (selected?.status !== 'IN_PROGRESS') return undefined;
    const timer = setInterval(async () => {
      try {
        setSelected(await api.session(selected.session_id));
        await refresh();
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : String(reason));
      }
    }, 1500);
    return () => clearInterval(timer);
  }, [selected?.session_id, selected?.video_processing?.status]);

  const openSession = async (sessionId) => {
    try {
      setSelected(await api.session(sessionId));
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const cancelSession = async () => {
    if (!selected?.session_id) return;
    try {
      const result = await api.endSession(selected.session_id);
      setSelected(result.session);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const runSessionAction = async (action) => {
    if (!selected?.session_id) return;
    setActionBusy(true);
    try {
      await api.sessionAction(selected.session_id, action);
      setSelected(await api.session(selected.session_id));
      await refresh();
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setActionBusy(false);
    }
  };

  const currentStep = (selected?.protocol?.steps ?? []).find(
    (step) => step.step_id === selected?.current_step,
  );

  return (
    <section className="card">
      <div className="card-head">
        <h3>Saved Sessions</h3>
        <button className="btn" type="button" onClick={refresh}>Refresh</button>
      </div>
      {error ? <div className="panel-alert panel-warn">{error}</div> : null}
      {sessions.length === 0 ? <p>No saved experiment sessions.</p> : (
        <ul className="exp-list">
          {sessions.map((session) => (
            <li className="exp-row" key={session.session_id}>
              <div className="exp-title">
                <button className="btn" type="button" onClick={() => openSession(session.session_id)}>
                  {display(session.experiment_id)} · {display(session.started_at)}
                </button>
                <span>{prettyId(session.status)}</span>
                <span>{prettyId(session.input_source)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
      {selected ? (
        <div className="session-detail">
          <div className="card-head">
            <h4>{display(selected.experiment_name)}</h4>
            <span className="mono">{display(selected.session_id)}</span>
          </div>
          <dl className="meta-grid">
            <div><dt>Started</dt><dd>{display(selected.started_at)}</dd></div>
            <div><dt>Completed</dt><dd>{display(selected.completed_at)}</dd></div>
            <div><dt>Input</dt><dd>{prettyId(selected.input_source)}</dd></div>
            <div><dt>Status</dt><dd>{prettyId(selected.status)}</dd></div>
            {selected.video_processing ? (
              <div><dt>Video processing</dt><dd>{prettyId(selected.video_processing.status)} · {display(selected.video_processing.frames_processed)} / {display(selected.video_processing.total_frames)} frames</dd></div>
            ) : null}
          </dl>
          <ul className="kv-list">
            {(selected.events ?? []).map((entry, index) => {
              const decision = entry.decision ?? {};
              const perception = entry.perception ?? {};
              return (
                <li key={`${entry.timestamp}-${index}`}>
                  <span>{display(entry.timestamp)}</span>
                  <span>{display(decision.step_id)}</span>
                  <span>{prettyId(decision.status)}</span>
                  <span>{prettyId(entry.decision_source)}</span>
                  <span>{display(perception.activity)} · {display(perception.object)}</span>
                  {entry.manual_confirmation ? <span>Confirmed by {display(entry.manual_confirmation.operator)}</span> : null}
                  <span>{display(decision.guidance)}</span>
                </li>
              );
            })}
          </ul>
          <div className="page-actions">
            <a className="btn" href={api.sessionExportUrl(selected.session_id, 'json')}>Export JSON</a>
            <a className="btn" href={api.sessionExportUrl(selected.session_id, 'csv')}>Export CSV</a>
            {selected.status === 'IN_PROGRESS' ? (
              <button className="btn" type="button" onClick={cancelSession}>Cancel session</button>
            ) : null}
            {selected.status === 'IN_PROGRESS' && currentStep?.session_action ? (
              <button
                className="btn btn-primary"
                type="button"
                disabled={actionBusy}
                onClick={() => runSessionAction(currentStep.session_action)}
              >
                {actionBusy ? 'Saving…' : currentStep.session_action === 'capture_evidence' ? 'Capture evidence' : 'Save observation'}
              </button>
            ) : null}
          </div>
          {(selected.evidence ?? []).some((item) => item.kind === 'video') ? (
            <video className="camera-feed" controls preload="metadata" src={api.sessionVideoUrl(selected.session_id)} />
          ) : null}
          {(selected.evidence ?? []).map((evidence) => (
            <div key={evidence.path}>
              <p className="kv-note">Evidence: {display(evidence.path)}</p>
              {evidence.kind === 'image' ? (
                <img className="camera-feed" src={api.sessionEvidenceUrl(selected.session_id, evidence.path)} alt="Saved experiment evidence" />
              ) : null}
            </div>
          ))}
          {selected.report_path ? <p className="kv-note">Local report: {display(selected.report_path)}</p> : null}
        </div>
      ) : null}
    </section>
  );
}
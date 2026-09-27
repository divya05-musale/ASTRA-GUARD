import { alertTone, display, formatConfidence, pillClass, prettyId, statusTone } from './flightdeck.js';

export default function DecisionAlert({ status, onManualConfirm, confirming = false }) {
  const s = statusTone(status?.status);
  const actionable = s === 'DEVIATION' || s === 'UNCERTAIN';
  return (
    <section className={alertTone(s)}>
      <div className="alert-top">
        <span className={pillClass(s)}>
          ● {s} · {display(status?.step_id ?? '—')}
        </span>
        <h3 className="alert-title">Mission Control</h3>
        <span className="alert-action-label">
          {s === 'DEVIATION' ? 'INTERVENTION REQUIRED'
            : s === 'UNCERTAIN' ? 'VERIFICATION REQUIRED'
            : s === 'COMPLETED' ? 'MISSION COMPLETE'
            : s === 'CORRECT' ? 'NOMINAL'
            : 'STANDBY'}
        </span>
      </div>
      <div className="alert-grid">
        <div className="alert-field"><span>Current Step</span><b>{display(status?.step_id)}</b></div>
        <div className="alert-field"><span>Expected Activity</span><b>{prettyId(status?.expected_activity)}</b></div>
        <div className="alert-field"><span>Expected Object</span><b>{prettyId(status?.expected_object)}</b></div>
        <div className="alert-field"><span>Detected Object</span><b>{prettyId(status?.detected_object)}</b></div>
        <div className="alert-field"><span>Confidence</span><b>{formatConfidence(status?.confidence)}</b></div>
        <div className="alert-field"><span>Deviation</span><b>{display(status?.deviation)}</b></div>
      </div>
      {actionable && <div className="alert-hint">Resolve on station, then continue the protocol. Voice guidance mirrors this message.</div>}
      {s === 'UNCERTAIN' && status?.manual_confirmation_allowed && status?.session_id ? (
        <div className="page-actions">
          <button className="btn btn-primary" type="button" disabled={confirming} onClick={onManualConfirm}>
            {confirming ? 'Recording confirmation…' : 'Confirm action manually'}
          </button>
        </div>
      ) : null}
    </section>
  );
}

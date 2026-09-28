import { useEffect, useState } from 'react';
import { api, display, prettyId, stepNumber } from '../services/api.js';

export default function Experiments() {
  const [protocols, setProtocols] = useState(null);
  const [summary, setSummary] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);
  const [selecting, setSelecting] = useState(null);
  const [selectionError, setSelectionError] = useState('');
  const [starting, setStarting] = useState(false);
  const [videoFile, setVideoFile] = useState(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const [exp, sum, v] = await Promise.all([
        api.experiments().catch(() => null),
        api.protocolSummary().catch(() => null),
        api.protocolValidate().catch(() => null),
      ]);
      setProtocols(exp);
      setSummary(sum);
      setValidation(v);
    } finally {
      setLoading(false);
    }
  };

  const reloadProtocol = async () => {
    setReloading(true);
    try {
      await api.protocolReload();
      await refresh();
    } finally {
      setReloading(false);
    }
  };

  const selectExperiment = async (experimentId) => {
    setSelecting(experimentId);
    setSelectionError('');
    try {
      await api.selectExperiment(experimentId);
      await refresh();
    } catch (error) {
      setSelectionError(error instanceof Error ? error.message : String(error));
    } finally {
      setSelecting(null);
    }
  };

  const startSession = async () => {
    const experimentId = summary?.experiment?.experiment_id;
    if (!experimentId) return;
    setStarting(true);
    setSelectionError('');
    try {
      await api.startSession(experimentId);
      await refresh();
    } catch (error) {
      setSelectionError(error instanceof Error ? error.message : String(error));
    } finally {
      setStarting(false);
    }
  };

  const startVideoSession = async () => {
    const experimentId = summary?.experiment?.experiment_id;
    if (!experimentId || !videoFile) return;
    setStarting(true);
    setSelectionError('');
    try {
      await api.uploadVideo(experimentId, videoFile);
      setVideoFile(null);
      await refresh();
    } catch (error) {
      setSelectionError(error instanceof Error ? error.message : String(error));
    } finally {
      setStarting(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const steps = summary?.experiment?.steps ?? null;
  return (
    <div className="pages-wrap">
      <header className="page-head">
        <div>
          <h2>Experiments</h2>
          <p>Registered ASTRA-DRISHTI protocols and their validation status.</p>
        </div>
        <div className="page-actions">
          <button className="btn btn-primary" type="button" onClick={refresh} disabled={loading}>Refresh</button>
          <button className="btn" type="button" onClick={reloadProtocol} disabled={reloading || loading}>
            {reloading ? 'Reloading…' : 'Reload Protocol'}
          </button>
        </div>
      </header>

      <section className="card">
        <div className="card-head">
          <h3>Registered Experiments</h3>
          <span className="mono">{display(protocols?.count ?? 0)}</span>
        </div>
        {loading && !protocols ? <p>Loading…</p> : null}
        {selectionError ? <div className="panel-alert panel-warn">{selectionError}</div> : null}
        <ul className="exp-list">
          {(protocols?.experiments ?? []).map((exp) => {
            const id = display(exp?.experiment_id ?? exp?.id);
            const name = display(exp?.name ?? id);
            const active = summary?.experiment?.experiment_id === id;
            return (
              <li key={id} className={`exp-row ${active ? 'exp-active' : ''}`}>
                <div className="exp-title">
                  <span className="mono">{display(id)}</span>
                  <span>{display(name)}</span>
                  {active ? <span className="badge">Active</span> : null}
                  {!exp.available ? <span className="badge">Incomplete</span> : null}
                </div>
                {!exp.available && exp.error ? <p className="kv-note">{display(exp.error)}</p> : null}
                {exp.available && !active ? (
                  <button className="btn" type="button" disabled={selecting !== null} onClick={() => selectExperiment(id)}>
                    {selecting === id ? 'Selecting…' : 'Select'}
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="card">
        <div className="card-head">
          <h3>Experiment Session</h3>
          <span className="mono">{display(summary?.experiment?.experiment_id)}</span>
        </div>
        <p>Start a local webcam session with the active validated protocol.</p>
        <button className="btn btn-primary" type="button" onClick={startSession} disabled={!summary?.experiment?.experiment_id || starting}>
          {starting ? 'Starting…' : 'Start webcam session'}
        </button>
        <label className="field">
          <span>Local video file</span>
          <input
            type="file"
            accept="video/avi,video/mp4,video/quicktime,video/x-matroska,video/x-msvideo,video/x-ms-wmv,.m4v,.mpeg,.mpg"
            onChange={(event) => setVideoFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <button className="btn" type="button" onClick={startVideoSession} disabled={!videoFile || !summary?.experiment?.experiment_id || starting}>
          {starting ? 'Uploading…' : 'Process local video'}
        </button>
      </section>

      <section className="card">
        <div className="card-head">
          <h3>Active Protocol Metadata</h3>
          <span className={validation?.valid ? 'conn conn-on' : 'conn conn-off'}>
            ● {validation?.valid ? 'VALID' : validation?.error ? 'INVALID' : 'UNKNOWN'}
          </span>
        </div>
        {!summary ? <p>Protocol summary not available.</p> : (
          <dl className="meta-grid">
            <div><dt>Experiment ID</dt><dd className="mono">{display(summary.experiment?.experiment_id)}</dd></div>
            <div><dt>Name</dt><dd>{display(summary.experiment?.name)}</dd></div>
            <div><dt>Type</dt><dd>{display(summary.experiment?.type)}</dd></div>
            <div><dt>Environment</dt><dd>{display(summary.experiment?.environment)}</dd></div>
            <div><dt>Steps</dt><dd>{display(summary.steps_count)}</dd></div>
            <div><dt>Activities</dt><dd>{display(summary.activities_count)}</dd></div>
            <div><dt>Objects</dt><dd>{display(summary.objects_count)}</dd></div>
            <div><dt>Rules</dt><dd>{display(summary.rules_count)}</dd></div>
            <div><dt>Loaded</dt><dd className="mono">{display(summary.loaded_at)}</dd></div>
          </dl>
        )}
        {validation?.error ? (
          <div className="panel-alert panel-warn">
            <b>Validation error: </b>{display(validation.error)}
          </div>
        ) : null}
      </section>
    </div>
  );
}

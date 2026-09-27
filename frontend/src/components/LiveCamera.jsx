import { useState, useEffect, useRef } from 'react';
import { api, CAMERA_STREAM_URL } from '../services/api.js';
import { display, utcNow } from './flightdeck.js';

export default function LiveCamera({ camera, onCameraChanged }) {
  const [imgOk, setImgOk] = useState(true);
  const [streamKey, setStreamKey] = useState(0);
  const [cameraBusy, setCameraBusy] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const lastRetryRef = useRef(Date.now());
  const frameTimesRef = useRef([]);
  const lastMetricsReportRef = useRef(0);
  const hasBackend = camera !== null && camera !== undefined;
  const backendOnline = hasBackend ? Boolean(camera.connected) : true;
  const camOnline = backendOnline && imgOk;
  const framesCaptured = camera?.frames_captured ?? 0;
  const streamHasFrames = framesCaptured > 0;
  const externalOwner = Boolean(camera?.external_stream);
  const cameraEnabled = Boolean(camera?.enabled);
  const effectiveUrl = `${CAMERA_STREAM_URL}${CAMERA_STREAM_URL.includes('?') ? '&' : '?'}k=${streamKey}`;

  const toggleCamera = async () => {
    setCameraBusy(true);
    setCameraError('');
    try {
      if (cameraEnabled) await api.stopCamera();
      else await api.startCamera();
      await onCameraChanged?.();
    } catch (error) {
      setCameraError(error instanceof Error ? error.message : String(error));
    } finally {
      setCameraBusy(false);
    }
  };

  useEffect(() => {
    if (!imgOk) {
      const now = Date.now();
      if (now - lastRetryRef.current > 2500) {
        lastRetryRef.current = now;
        setStreamKey((k) => k + 1);
        setImgOk(true);
      }
    }
  }, [imgOk]);

  const onRetryClick = () => {
    lastRetryRef.current = Date.now();
    setStreamKey((k) => k + 1);
    setImgOk(true);
  };

  const onFrameLoad = () => {
    const now = Date.now();
    const samples = [...frameTimesRef.current, now].filter((time) => now - time <= 3000);
    frameTimesRef.current = samples;
    if (samples.length > 1 && now - lastMetricsReportRef.current >= 1000) {
      const displayedFps = (samples.length - 1) * 1000 / (samples[samples.length - 1] - samples[0]);
      lastMetricsReportRef.current = now;
      api.reportDashboardDisplay(displayedFps, now / 1000).catch(() => {});
    }
    setImgOk(true);
  };

  return (
    <section className="card camera-card">
      <div className="card-head">
        <h3>Live Camera Feed</h3>
        <button
          className={cameraEnabled ? 'btn btn-ghost' : 'btn btn-primary'}
          type="button"
          onClick={toggleCamera}
          disabled={cameraBusy || externalOwner || !hasBackend}
          title={externalOwner ? 'Camera is controlled by the external perception pipeline' : undefined}
        >
          {cameraBusy ? 'Working…' : externalOwner ? 'Pipeline active' : cameraEnabled ? 'Turn camera off' : 'Turn camera on'}
        </button>
        <span className="live-meta">
          <span className={camOnline ? 'dot dot-on' : 'dot dot-off'}>●</span>
          <span>{camOnline ? 'LIVE' : 'OFFLINE'} · {utcNow()}</span>
        </span>
      </div>
      {cameraError ? <div className="camera-control-error" role="alert">{cameraError}</div> : null}
      {camOnline ? (
        <div className="camera-feed-wrap">
          <img
            key={streamKey}
            src={effectiveUrl}
            alt="ASTRA-GUARD live camera feed"
            className="camera-feed"
            onLoad={onFrameLoad}
            onError={() => setImgOk(false)}
          />
          {!streamHasFrames && (
            <div className="camera-waiting">
              <div className="spinner" />
              <div>Waiting for perception pipeline frames…</div>
              <button className="btn btn-primary" type="button" onClick={onRetryClick}>Refresh stream</button>
            </div>
          )}
        </div>
      ) : (
        <div className="camera-offline">
          <div className="camera-offline-title">CAMERA OFFLINE</div>
          <div className="camera-offline-note">
            {hasBackend
              ? 'No live frame from the perception pipeline yet. Start run_live.py in backend mode (ASTRA_GUARD_MODE=backend) to feed the real webcam.'
              : 'Unable to reach the backend camera stream.'}
            {camera?.error ? `\nError: ${String(camera.error)}` : ''}
          </div>
          <button className="btn btn-primary" type="button" onClick={onRetryClick}>Retry</button>
        </div>
      )}
      <div className="camera-meta">
        <div><span>Source</span><b>{display(camera?.external_stream ? 'Perception pipeline' : 'Webcam')}</b></div>
        <div><span>Resolution</span><b>{display(camera?.width ? `${camera.width}x${camera.height}` : 'N/A')}</b></div>
        <div><span>Frame Count</span><b>{display(framesCaptured)}</b></div>
        <div><span>Capture State</span><b>{externalOwner ? 'External pipeline' : camera?.camera_open ? 'Camera open' : cameraEnabled ? 'Starting' : 'Off'}</b></div>
      </div>
    </section>
  );
}

import { useState, useEffect, useRef } from 'react';
import { api, CAMERA_STREAM_URL } from '../services/api.js';
import { display, utcNow } from './flightdeck.js';

const CAMERA_OFFLINE_GRACE_MS = 4000;
const FRESH_FRAME_MAX_AGE_SEC = 2.5;

export default function LiveCamera({ camera, onCameraChanged }) {
  const [cameraOnline, setCameraOnline] = useState(null);
  const [streamOnline, setStreamOnline] = useState(true);
  const [streamKey, setStreamKey] = useState(0);
  const [cameraBusy, setCameraBusy] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [cameraSource, setCameraSource] = useState(camera?.camera_source ?? 'laptop');
  const [cameraSourceName, setCameraSourceName] = useState(camera?.camera_source_name ?? 'Laptop Webcam');
  const [cameraIndex, setCameraIndex] = useState(String(camera?.camera_index ?? 0));
  const [cameraBackend, setCameraBackend] = useState(camera?.camera_backend_requested ?? 'dshow');
  const [discoveryResults, setDiscoveryResults] = useState([]);
  const [discoveryBusy, setDiscoveryBusy] = useState(false);
  const frameTimesRef = useRef([]);
  const lastMetricsReportRef = useRef(0);
  const lastFreshFrameAtRef = useRef(0);
  const cameraGraceTimerRef = useRef(null);
  const streamGraceTimerRef = useRef(null);
  const streamRetryTimerRef = useRef(null);
  const hasBackend = camera !== null && camera !== undefined;
  const camOnline = cameraOnline === true && streamOnline;
  const framesCaptured = camera?.frames_captured ?? 0;
  const streamHasFrames = framesCaptured > 0;
  const externalOwner = Boolean(camera?.external_stream);
  const cameraEnabled = Boolean(camera?.enabled);
  const effectiveUrl = `${CAMERA_STREAM_URL}${CAMERA_STREAM_URL.includes('?') ? '&' : '?'}k=${streamKey}`;

  useEffect(() => {
    if (camera) {
      setCameraSource(camera.camera_source ?? 'laptop');
      setCameraSourceName(camera.camera_source_name ?? (camera.camera_source === 'usb' ? 'USB External Camera' : 'Laptop Webcam'));
      setCameraIndex(String(camera.camera_index ?? 0));
      setCameraBackend(String(camera.camera_backend_requested ?? 'dshow').toLowerCase());
    }
  }, [camera?.camera_source, camera?.camera_source_name, camera?.camera_index, camera?.camera_backend_requested]);

  useEffect(() => {
    if (camera?.camera_switch_error) setCameraError(camera.camera_switch_error);
  }, [camera?.camera_switch_error]);

  useEffect(() => {
    const frameAge = Number(camera?.frame_age_seconds);
    const hasFreshFrame = Boolean(
      camera?.connected
      && camera?.has_frame
      && Number.isFinite(frameAge)
      && frameAge <= FRESH_FRAME_MAX_AGE_SEC
    );

    if (hasFreshFrame) {
      lastFreshFrameAtRef.current = Date.now();
      setCameraOnline(true);
      if (cameraGraceTimerRef.current !== null) {
        clearTimeout(cameraGraceTimerRef.current);
        cameraGraceTimerRef.current = null;
      }
      return;
    }

    if (cameraGraceTimerRef.current !== null) return;
    const elapsed = lastFreshFrameAtRef.current
      ? Date.now() - lastFreshFrameAtRef.current
      : 0;
    const delay = Math.max(0, CAMERA_OFFLINE_GRACE_MS - elapsed);
    cameraGraceTimerRef.current = setTimeout(() => {
      cameraGraceTimerRef.current = null;
      const lastFreshFrameAt = lastFreshFrameAtRef.current;
      if (!lastFreshFrameAt || Date.now() - lastFreshFrameAt >= CAMERA_OFFLINE_GRACE_MS) {
        setCameraOnline(false);
      }
    }, delay);
  }, [camera]);

  useEffect(() => () => {
    if (cameraGraceTimerRef.current !== null) clearTimeout(cameraGraceTimerRef.current);
    if (streamGraceTimerRef.current !== null) clearTimeout(streamGraceTimerRef.current);
    if (streamRetryTimerRef.current !== null) clearTimeout(streamRetryTimerRef.current);
  }, []);

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

  const applyCameraSelection = async () => {
    const selectedIndex = Number(cameraIndex);
    if (!Number.isInteger(selectedIndex) || selectedIndex < 0) {
      setCameraError('Camera index must be zero or greater.');
      return;
    }
    setCameraBusy(true);
    setCameraError('');
    try {
      await api.selectCamera(selectedIndex, cameraSource, cameraBackend, cameraSourceName);
      await onCameraChanged?.();
      setStreamKey((key) => key + 1);
      setStreamOnline(true);
    } catch (error) {
      setCameraError(error instanceof Error ? error.message : String(error));
    } finally {
      setCameraBusy(false);
    }
  };

  const discoverCameras = async () => {
    setDiscoveryBusy(true);
    setCameraError('');
    try {
      const result = await api.discoverCameras(5);
      setDiscoveryResults(result.results ?? []);
    } catch (error) {
      setCameraError(error instanceof Error ? error.message : String(error));
    } finally {
      setDiscoveryBusy(false);
    }
  };

  const cameraState = camera?.camera_switch_pending
    ? 'Switching camera'
    : camera?.camera_switch_error || camera?.error
      ? 'Camera unavailable'
      : cameraOnline === null
        ? 'Checking camera'
      : camOnline
        ? 'Connected'
        : camera?.camera_open || camera?.external_stream
          ? 'No frames received'
          : 'Camera disconnected';

  const onRetryClick = () => {
    setStreamKey((k) => k + 1);
    setStreamOnline(true);
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
    setStreamOnline(true);
    if (streamGraceTimerRef.current !== null) {
      clearTimeout(streamGraceTimerRef.current);
      streamGraceTimerRef.current = null;
    }
  };

  const onFrameError = () => {
    if (streamGraceTimerRef.current === null) {
      streamGraceTimerRef.current = setTimeout(() => {
        streamGraceTimerRef.current = null;
        setStreamOnline(false);
      }, CAMERA_OFFLINE_GRACE_MS);
    }
    if (streamRetryTimerRef.current === null) {
      streamRetryTimerRef.current = setTimeout(() => {
        streamRetryTimerRef.current = null;
        setStreamKey((key) => key + 1);
      }, 2500);
    }
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
          {cameraBusy ? 'Working…' : externalOwner ? 'Pipeline active' : cameraEnabled && !camera?.camera_open ? 'Retry camera' : cameraEnabled ? 'Turn camera off' : 'Turn camera on'}
        </button>
        <span className="live-meta">
          <span className={camOnline ? 'dot dot-on' : 'dot dot-off'}>●</span>
          <span>{cameraState.toUpperCase()} · {utcNow()}</span>
        </span>
      </div>
      {cameraError ? <div className="camera-control-error" role="alert">{cameraError}</div> : null}
      <div className="camera-source-controls">
        <label className="camera-source-field">
          <span>Camera source</span>
          <select
            value={cameraSource}
            onChange={(event) => {
              const source = event.target.value;
              setCameraSource(source);
              setCameraSourceName(source === 'usb' ? 'USB External Camera' : 'Laptop Webcam');
            }}
            disabled={cameraBusy || camera?.camera_switch_pending || !hasBackend}
          >
            <option value="laptop">Laptop Webcam</option>
            <option value="usb">USB External Camera</option>
          </select>
        </label>
        <label className="camera-source-field">
          <span>Camera name</span>
          <input
            type="text"
            value={cameraSourceName}
            onChange={(event) => setCameraSourceName(event.target.value)}
            disabled={cameraBusy || camera?.camera_switch_pending || !hasBackend}
          />
        </label>
        <label className="camera-source-field camera-index-field">
          <span>OpenCV device index</span>
          <input
            type="number"
            min="0"
            step="1"
            value={cameraIndex}
            onChange={(event) => setCameraIndex(event.target.value)}
            disabled={cameraBusy || camera?.camera_switch_pending || !hasBackend}
          />
        </label>
        <label className="camera-source-field">
          <span>Capture backend</span>
          <select
            value={cameraBackend}
            onChange={(event) => setCameraBackend(event.target.value)}
            disabled={cameraBusy || camera?.camera_switch_pending || !hasBackend}
          >
            <option value="auto">Automatic</option>
            <option value="dshow">DirectShow</option>
            <option value="msmf">Media Foundation</option>
          </select>
        </label>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={applyCameraSelection}
          disabled={cameraBusy || camera?.camera_switch_pending || !hasBackend}
        >
          {camera?.camera_switch_pending ? 'Applying…' : 'Apply device'}
        </button>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={discoverCameras}
          disabled={discoveryBusy || cameraBusy || cameraEnabled || externalOwner || !hasBackend}
          title={cameraEnabled || externalOwner ? 'Stop camera capture before discovery' : undefined}
        >
          {discoveryBusy ? 'Scanning…' : 'Discover cameras'}
        </button>
      </div>
      {discoveryResults.length > 0 ? (
        <details className="camera-discovery" open>
          <summary>Camera discovery results</summary>
          <ul>
            {discoveryResults.map((item) => (
              <li key={`${item.camera_index}-${item.backend_tested}`}>
                <span>
                  Index {item.camera_index} · {item.backend_tested.toUpperCase()} ·{' '}
                  {item.frame_received ? `${item.width}x${item.height}` : item.opened ? 'No frames' : 'Unavailable'}
                </span>
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() => {
                    setCameraIndex(String(item.camera_index));
                    setCameraBackend(item.backend_tested);
                  }}
                  disabled={!item.frame_received}
                >
                  Use configuration
                </button>
                {item.error ? <small>{item.error}</small> : null}
              </li>
            ))}
          </ul>
          <small>OpenCV device indices do not reliably identify camera names.</small>
        </details>
      ) : null}
      <div className="camera-feed-wrap">
        <img
          key={streamKey}
          src={effectiveUrl}
          alt="ASTRA-DRISHTI live camera feed"
          className="camera-feed"
          onLoad={onFrameLoad}
          onError={onFrameError}
        />
        {!streamHasFrames && (
          <div className="camera-waiting">
            <div className="spinner" />
            <div>Waiting for perception pipeline frames…</div>
          </div>
        )}
      </div>
      {cameraOnline !== null && !camOnline ? (
        <div className="camera-offline">
          <div className="camera-offline-title">CAMERA OFFLINE</div>
          <div className="camera-offline-note">
            {hasBackend
              ? `No fresh camera frame from device index ${camera?.camera_index ?? 0}. The stream remains connected while camera status recovers.`
              : 'Camera status is unavailable. The live stream remains mounted while the backend reconnects.'}
            {camera?.error ? `\nError: ${String(camera.error)}` : ''}
          </div>
          <button className="btn btn-primary" type="button" onClick={onRetryClick}>Retry stream</button>
        </div>
      ) : null}
      <div className="camera-meta">
        <div><span>Source</span><b>{display(camera?.camera_source_name ?? (camera?.camera_source === 'usb' ? 'USB External Camera' : 'Laptop Webcam'))}</b></div>
        <div><span>Device Index</span><b>{display(camera?.camera_index ?? 0)}</b></div>
        <div><span>Active Backend</span><b>{display(camera?.camera_backend ?? 'N/A')}</b></div>
        <div><span>Resolution</span><b>{display(camera?.width ? `${camera.width}x${camera.height}` : 'N/A')}</b></div>
        <div><span>Frame Count</span><b>{display(framesCaptured)}</b></div>
        <div><span>Capture State</span><b>{externalOwner ? 'External pipeline' : camera?.camera_open ? 'Camera open' : camera?.error ? 'Error' : cameraEnabled ? 'Starting' : 'Off'}</b></div>
      </div>
    </section>
  );
}

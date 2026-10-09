import { useState, useEffect, useRef } from 'react';
import { api, CAMERA_STREAM_URL } from '../services/api.js';
import { display, utcNow } from './flightdeck.js';

const CAMERA_OFFLINE_GRACE_MS = 4000;
const FRESH_FRAME_MAX_AGE_SEC = 2.5;
const BROWSER_FRAME_INTERVAL_MS = 200;
const BROWSER_FRAME_RETRY_INTERVAL_MS = 1500;
const BROWSER_FRAME_MAX_WIDTH = 640;
const BROWSER_FRAME_MAX_HEIGHT = 480;
const BROWSER_FRAME_JPEG_QUALITY = 0.75;

async function listBrowserVideoInputs() {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices.filter((device) => device.kind === 'videoinput' && device.deviceId);
}

function browserCameraErrorDetails(error) {
  switch (error?.name) {
    case 'NotAllowedError':
    case 'SecurityError':
      return {
        state: 'permission-denied',
        message: 'Camera permission was denied. Allow camera access in your browser settings and try again.',
      };
    case 'NotFoundError':
    case 'DevicesNotFoundError':
      return { state: 'no-camera', message: 'No camera was found on this device.' };
    case 'NotReadableError':
    case 'TrackStartError':
      return {
        state: 'camera-in-use',
        message: 'The camera is unavailable or already in use by another app or browser tab.',
      };
    case 'OverconstrainedError':
      return {
        state: 'selected-device-unavailable',
        message: 'The selected browser camera is no longer available. Choose another camera.',
      };
    default:
      return {
        state: 'unavailable',
        message: error instanceof Error ? error.message : 'Unable to access the browser camera.',
      };
  }
}

function browserFrameErrorMessage(error) {
  const detail = error instanceof Error ? error.message : String(error);
  if (error?.name === 'TypeError' || /timed out|failed to fetch|networkerror/i.test(detail)) {
    return `Backend unavailable: ${detail}`;
  }
  if (/\b5\d{2}\b|perception is unavailable/i.test(detail)) {
    return `Backend perception unavailable: ${detail}`;
  }
  return `Frame upload failed: ${detail}`;
}

const BROWSER_CAPTURE_STATE_LABELS = {
  off: 'Off',
  requesting: 'Requesting camera',
  active: 'Browser camera open',
  'permission-denied': 'Permission denied',
  'no-camera': 'No camera found',
  'camera-in-use': 'Camera in use',
  'selected-device-unavailable': 'Selected camera unavailable',
  stopped: 'Stream stopped',
  unavailable: 'Camera unavailable',
};

export default function LiveCamera({ camera, onCameraChanged }) {
  const [cameraOnline, setCameraOnline] = useState(null);
  const [streamOnline, setStreamOnline] = useState(true);
  const [streamKey, setStreamKey] = useState(0);
  const [localStream, setLocalStream] = useState(null);
  const [cameraBusy, setCameraBusy] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [browserCameraState, setBrowserCameraState] = useState('off');
  const [browserCameraError, setBrowserCameraError] = useState('');
  const [frameUploadError, setFrameUploadError] = useState('');
  const [browserDevices, setBrowserDevices] = useState([]);
  const [selectedBrowserDeviceId, setSelectedBrowserDeviceId] = useState('');
  const [cameraSource, setCameraSource] = useState(camera?.camera_source ?? 'laptop');
  const [cameraSourceName, setCameraSourceName] = useState(camera?.camera_source_name ?? 'Laptop Webcam');
  const [cameraIndex, setCameraIndex] = useState(String(camera?.camera_index ?? 0));
  const [cameraBackend, setCameraBackend] = useState(camera?.camera_backend_requested ?? 'dshow');
  const [discoveryResults, setDiscoveryResults] = useState([]);
  const [discoveryBusy, setDiscoveryBusy] = useState(false);
  const frameTimesRef = useRef([]);
  const lastMetricsReportRef = useRef(0);
  const lastFreshFrameAtRef = useRef(0);
  const localStreamRef = useRef(null);
  const videoRef = useRef(null);
  const frameCanvasRef = useRef(null);
  const uploadInFlightRef = useRef(false);
  const mountedRef = useRef(true);
  const cameraGraceTimerRef = useRef(null);
  const streamGraceTimerRef = useRef(null);
  const streamRetryTimerRef = useRef(null);
  const hasBackend = camera !== null && camera !== undefined;
  const browserSource = cameraSource === 'laptop';
  const cameraEnabled = Boolean(camera?.enabled);
  const selectedCameraEnabled = browserSource ? Boolean(localStream) : cameraEnabled;
  const camOnline = browserSource ? Boolean(localStream) : cameraOnline === true && streamOnline;
  const framesCaptured = camera?.frames_captured ?? 0;
  const streamHasFrames = framesCaptured > 0;
  const externalOwner = Boolean(camera?.external_stream);
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
    if (!browserSource && camera?.camera_switch_error) setCameraError(camera.camera_switch_error);
  }, [browserSource, camera?.camera_switch_error]);

  useEffect(() => {
    if (!browserSource || !navigator.mediaDevices?.enumerateDevices) return undefined;
    let cancelled = false;
    const refreshDevices = async () => {
      try {
        const devices = await listBrowserVideoInputs();
        if (!cancelled) setBrowserDevices(devices);
      } catch {
        if (!cancelled) setBrowserDevices([]);
      }
    };
    const mediaDevices = navigator.mediaDevices;
    const handleDeviceChange = () => { void refreshDevices(); };
    void refreshDevices();
    mediaDevices.addEventListener?.('devicechange', handleDeviceChange);
    return () => {
      cancelled = true;
      mediaDevices.removeEventListener?.('devicechange', handleDeviceChange);
    };
  }, [browserSource]);

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

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (cameraGraceTimerRef.current !== null) clearTimeout(cameraGraceTimerRef.current);
      if (streamGraceTimerRef.current !== null) clearTimeout(streamGraceTimerRef.current);
      if (streamRetryTimerRef.current !== null) clearTimeout(streamRetryTimerRef.current);
      localStreamRef.current?.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return undefined;
    video.srcObject = localStream;
    if (localStream) video.play().catch(() => {});
    return () => {
      if (video.srcObject === localStream) video.srcObject = null;
    };
  }, [localStream]);

  useEffect(() => {
    if (!browserSource || !localStream) return undefined;
    let cancelled = false;
    let timer = null;

    const uploadFrame = async () => {
      if (cancelled) return;
      let nextDelay = BROWSER_FRAME_INTERVAL_MS;
      const video = videoRef.current;
      const canvas = frameCanvasRef.current;
      if (video && canvas && video.readyState >= 2 && !uploadInFlightRef.current) {
        const width = video.videoWidth;
        const height = video.videoHeight;
        if (width > 0 && height > 0) {
          const scale = Math.min(
            1,
            BROWSER_FRAME_MAX_WIDTH / width,
            BROWSER_FRAME_MAX_HEIGHT / height,
          );
          canvas.width = Math.round(width * scale);
          canvas.height = Math.round(height * scale);
          const context = canvas.getContext('2d');
          uploadInFlightRef.current = true;
          let stage = 'capture';
          try {
            if (!context) throw new Error('Browser frame capture is unavailable.');
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            const frame = await new Promise((resolve) => {
              canvas.toBlob(resolve, 'image/jpeg', BROWSER_FRAME_JPEG_QUALITY);
            });
            if (!frame) throw new Error('Could not encode a browser camera frame.');
            stage = 'upload';
            await api.processBrowserFrame(frame);
            if (!cancelled && mountedRef.current) setFrameUploadError('');
          } catch (error) {
            if (error?.status === 429) {
              nextDelay = error.retryAfterMs ?? BROWSER_FRAME_RETRY_INTERVAL_MS;
            } else if (!cancelled && mountedRef.current) {
              const detail = error instanceof Error ? error.message : String(error);
              setFrameUploadError(stage === 'capture'
                ? `Frame capture failed: ${detail}`
                : browserFrameErrorMessage(error));
              nextDelay = BROWSER_FRAME_RETRY_INTERVAL_MS;
            }
          } finally {
            uploadInFlightRef.current = false;
          }
        }
      }
      if (!cancelled) timer = setTimeout(uploadFrame, nextDelay);
    };

    uploadFrame();
    return () => {
      cancelled = true;
      if (timer !== null) clearTimeout(timer);
    };
  }, [browserSource, localStream]);

  const stopBrowserCamera = () => {
    const stream = localStreamRef.current;
    localStreamRef.current = null;
    stream?.getTracks().forEach((track) => track.stop());
    setLocalStream(null);
    setBrowserCameraState('off');
    setBrowserCameraError('');
    setFrameUploadError('');
    setCameraOnline(false);
  };

  const startBrowserCamera = async (deviceId = selectedBrowserDeviceId) => {
    if (!navigator.mediaDevices?.getUserMedia) {
      const details = browserCameraErrorDetails(new Error(
        'Browser camera access is unavailable. Open this dashboard over HTTPS in a supported browser.',
      ));
      setBrowserCameraState(details.state);
      setBrowserCameraError(details.message);
      return;
    }

    setBrowserCameraState('requesting');
    setBrowserCameraError('');
    setFrameUploadError('');
    try {
      const constraints = deviceId
        ? { video: { deviceId: { exact: deviceId } }, audio: false }
        : { video: true, audio: false };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      if (!mountedRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      const previousStream = localStreamRef.current;
      localStreamRef.current = stream;
      stream.getVideoTracks().forEach((track) => {
        track.addEventListener('ended', () => {
          if (localStreamRef.current !== stream) return;
          localStreamRef.current = null;
          setLocalStream(null);
          setCameraOnline(false);
          setBrowserCameraState('stopped');
          setBrowserCameraError('The browser camera stream stopped. Turn the camera on to reconnect.');
        }, { once: true });
      });
      setLocalStream(stream);
      setCameraOnline(true);
      setStreamOnline(true);
      setBrowserCameraState('active');
      previousStream?.getTracks().forEach((track) => track.stop());
      try {
        setBrowserDevices(await listBrowserVideoInputs());
      } catch {
        setBrowserDevices([]);
      }
    } catch (error) {
      const details = browserCameraErrorDetails(error);
      setBrowserCameraState(details.state);
      setBrowserCameraError(details.message);
      setCameraOnline(false);
    }
  };

  const toggleCamera = async () => {
    setCameraBusy(true);
    try {
      if (browserSource) {
        if (localStreamRef.current) {
          stopBrowserCamera();
          return;
        }
        await startBrowserCamera();
        return;
      }
      setCameraError('');
      if (cameraEnabled) await api.stopCamera();
      else await api.startCamera();
      await onCameraChanged?.();
    } catch (error) {
      if (mountedRef.current) {
        setCameraError(error instanceof Error ? error.message : String(error));
      }
    } finally {
      if (mountedRef.current) setCameraBusy(false);
    }
  };

  const selectBrowserDevice = async (deviceId) => {
    setSelectedBrowserDeviceId(deviceId);
    if (!localStreamRef.current) return;
    setCameraBusy(true);
    stopBrowserCamera();
    try {
      await startBrowserCamera(deviceId);
    } finally {
      if (mountedRef.current) setCameraBusy(false);
    }
  };

  const applyCameraSelection = async () => {
    if (browserSource) return;
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
    if (browserSource) return;
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

  const cameraState = browserSource
    ? localStream
      ? 'Connected'
      : BROWSER_CAPTURE_STATE_LABELS[browserCameraState] ?? 'Camera disconnected'
    : camera?.camera_switch_pending
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
          className={selectedCameraEnabled ? 'btn btn-ghost' : 'btn btn-primary'}
          type="button"
          onClick={toggleCamera}
          disabled={cameraBusy || (!browserSource && (externalOwner || !hasBackend))}
          title={!browserSource && externalOwner ? 'Camera is controlled by the external perception pipeline' : undefined}
        >
          {cameraBusy ? 'Working…' : !browserSource && externalOwner ? 'Pipeline active' : selectedCameraEnabled && !browserSource && !camera?.camera_open ? 'Retry camera' : selectedCameraEnabled ? 'Turn camera off' : 'Turn camera on'}
        </button>
        <span className="live-meta">
          <span className={camOnline ? 'dot dot-on' : 'dot dot-off'}>●</span>
          <span>{cameraState.toUpperCase()} · {utcNow()}</span>
        </span>
      </div>
      {!browserSource && cameraError ? <div className="camera-control-error" role="alert">{cameraError}</div> : null}
      {browserSource && browserCameraError ? <div className="camera-control-error" role="alert">Browser camera: {browserCameraError}</div> : null}
      {browserSource && frameUploadError ? <div className="camera-control-error" role="alert">{frameUploadError}</div> : null}
      <div className="camera-source-controls">
        <label className="camera-source-field">
          <span>Camera source</span>
          <select
            value={cameraSource}
            onChange={async (event) => {
              const source = event.target.value;
              if (source === 'laptop' && cameraSource !== 'laptop' && cameraEnabled && !externalOwner) {
                setCameraBusy(true);
                setCameraError('');
                try {
                  await api.stopCamera();
                  await onCameraChanged?.();
                } catch (error) {
                  setCameraError(error instanceof Error ? error.message : String(error));
                  return;
                } finally {
                  setCameraBusy(false);
                }
              }
              if (source !== 'laptop') stopBrowserCamera();
              setCameraSource(source);
              setCameraSourceName(source === 'usb' ? 'USB External Camera' : 'Laptop Webcam');
            }}
            disabled={cameraBusy || camera?.camera_switch_pending}
          >
            <option value="laptop">Laptop Webcam</option>
            <option value="usb">USB External Camera</option>
          </select>
        </label>
        {browserSource ? (
          <label className="camera-source-field">
            <span>Browser camera</span>
            <select
              value={selectedBrowserDeviceId}
              onChange={(event) => { void selectBrowserDevice(event.target.value); }}
              disabled={cameraBusy}
            >
              <option value="">Default camera</option>
              {browserDevices.map((device, index) => (
                <option key={device.deviceId} value={device.deviceId}>
                  {device.label || `Camera ${index + 1}`}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="camera-source-field">
          <span>Camera name</span>
          <input
            type="text"
            value={cameraSourceName}
            onChange={(event) => setCameraSourceName(event.target.value)}
            disabled={cameraBusy || camera?.camera_switch_pending}
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
            disabled={cameraBusy || camera?.camera_switch_pending || !hasBackend || browserSource}
          />
        </label>
        <label className="camera-source-field">
          <span>Capture backend</span>
          <select
            value={cameraBackend}
            onChange={(event) => setCameraBackend(event.target.value)}
            disabled={cameraBusy || camera?.camera_switch_pending || !hasBackend || browserSource}
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
          disabled={cameraBusy || camera?.camera_switch_pending || !hasBackend || browserSource}
        >
          {camera?.camera_switch_pending ? 'Applying…' : 'Apply device'}
        </button>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={discoverCameras}
          disabled={discoveryBusy || cameraBusy || cameraEnabled || externalOwner || !hasBackend || browserSource}
          title={browserSource ? 'Camera discovery is for backend-connected USB cameras' : cameraEnabled || externalOwner ? 'Stop camera capture before discovery' : undefined}
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
        {browserSource ? (
          <>
            <video ref={videoRef} autoPlay playsInline muted className="camera-feed" />
            <canvas ref={frameCanvasRef} hidden />
            {!localStream && (
              <div className="camera-waiting">
                <div className="spinner" />
                <div>Turn camera on to start the browser webcam.</div>
              </div>
            )}
          </>
        ) : (
          <>
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
          </>
        )}
      </div>
      {!browserSource && cameraOnline !== null && !camOnline ? (
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
        <div><span>Capture State</span><b>{browserSource ? BROWSER_CAPTURE_STATE_LABELS[browserCameraState] ?? 'Camera unavailable' : externalOwner ? 'External pipeline' : camera?.camera_open ? 'Camera open' : camera?.error ? 'Error' : cameraEnabled ? 'Starting' : 'Off'}</b></div>
      </div>
    </section>
  );
}

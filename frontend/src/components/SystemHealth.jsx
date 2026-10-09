function MetricGroup({ title, items }) {
  return (
    <section className="performance-group">
      <h4>{title}</h4>
      <dl className="performance-grid">
        {items.map(([label, value]) => (
          <div className="performance-metric" key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default function SystemHealth({ health, camera, voice, performance, perception, status }) {
  const cam = camera?.connected ? 'ONLINE' : 'OFFLINE';
  const inference = perception?.processing ? 'PROCESSING' : perception?.inference_active ? 'ACTIVE' : 'IDLE';
  const publishing = perception?.frame_publishing ? 'PUBLISHING' : 'IDLE';
  const frameCounts = `${perception?.frames_accepted ?? 0} / ${perception?.frames_processed ?? 0}`;
  const latestDetections = perception?.detections_fresh
    ? `${perception.last_object_count ?? 0} objects · ${perception.last_hand_count ?? 0} hands`
    : 'No recent inference output';
  const perceptionDiagnostic = perception?.error
    ? { message: `Perception failed: ${perception.error}`, isError: true }
    : perception?.mediapipe_status === 'UNAVAILABLE' && perception?.mediapipe_error
      ? { message: `Hand detection unavailable: ${perception.mediapipe_error}`, isError: false }
      : null;
  const rows = [
    ['Camera', cam],
    ['YOLO + MediaPipe', inference],
    ['YOLO', perception?.yolo_status ?? (perception?.inference_active ? 'ONLINE' : 'IDLE')],
    ['MediaPipe', perception?.mediapipe_status ?? (perception?.inference_active ? 'ONLINE' : 'IDLE')],
    ['Pipeline frames', publishing],
    ['Accepted / processed', frameCounts],
    ['Latest detections', latestDetections],
    ['Mission Engine', status ? 'ONLINE' : health?.status === 'ok' ? 'AVAILABLE' : 'OFFLINE'],
    ['Voice', voice?.engine_ready ? 'ONLINE' : 'OFFLINE'],
  ];
  return (
    <section className="card">
      <div className="card-head"><h3>System Health</h3></div>
      <ul className="health">
        {rows.map(([k, v]) => (
          <li key={k}>
            <span>{k}</span>
            <b className={k === 'Accepted / processed'
              ? perception?.frames_processed > 0 ? 'ok' : 'bad'
              : ['ONLINE', 'AVAILABLE', 'ACTIVE', 'PROCESSING', 'PUBLISHING'].includes(v) ? 'ok' : 'bad'}>{v}</b>
          </li>
        ))}
      </ul>
      {perceptionDiagnostic ? (
        <div className={`perception-diagnostic${perceptionDiagnostic.isError ? ' perception-diagnostic-error' : ''}`} role={perceptionDiagnostic.isError ? 'alert' : 'status'}>
          {perceptionDiagnostic.message}
        </div>
      ) : null}
      <details className="performance-details" open>
        <summary>Performance</summary>
        <div className="performance-groups">
          <MetricGroup title="Camera" items={[
            ['Capture FPS', performance?.capture_fps == null ? 'N/A' : `${performance.capture_fps} FPS`],
            ['Capture to backend', performance?.end_to_end_latency_ms == null ? 'N/A' : `${performance.end_to_end_latency_ms} ms`],
            ['Capture to display', performance?.end_to_end_display_latency_ms == null ? 'N/A' : `${performance.end_to_end_display_latency_ms} ms`],
            ['Frame delay', performance?.display_latency_ms == null ? 'N/A' : `${performance.display_latency_ms} ms`],
          ]} />
          <MetricGroup title="Inference" items={[
            ['YOLO', performance?.yolo_ms == null ? 'N/A' : `${performance.yolo_ms} ms`],
            ['MediaPipe', performance?.mediapipe_ms == null ? 'N/A' : `${performance.mediapipe_ms} ms`],
            ['Mission event', performance?.mission_event_ms == null ? 'N/A' : `${performance.mission_event_ms} ms`],
            ['Processor total', performance?.process_frame_ms == null ? 'N/A' : `${performance.process_frame_ms} ms`],
          ]} />
          <MetricGroup title="Streaming" items={[
            ['JPEG encoding', performance?.jpeg_encode_ms == null ? 'N/A' : `${performance.jpeg_encode_ms} ms`],
            ['Annotation', performance?.annotation_ms == null ? 'N/A' : `${performance.annotation_ms} ms`],
            ['Publishing', performance?.frame_publish_ms == null ? 'N/A' : `${performance.frame_publish_ms} ms`],
            ['Backend stream', performance?.backend_stream_fps == null ? 'N/A' : `${performance.backend_stream_fps} FPS`],
            ['Dashboard', performance?.dashboard_display_fps == null ? 'N/A' : `${performance.dashboard_display_fps} FPS`],
          ]} />
          <MetricGroup title="System Resources" items={[
            ['CPU usage', performance?.system_cpu_percent == null ? 'N/A' : `${performance.system_cpu_percent.toFixed(1)}%`],
            ['RAM usage', performance?.system_ram_used_mb == null || performance?.system_ram_total_mb == null
              ? 'N/A'
              : `${performance.system_ram_used_mb} / ${performance.system_ram_total_mb} MB`],
          ]} />
        </div>
      </details>
    </section>
  );
}

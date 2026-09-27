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

export default function SystemHealth({ health, camera, voice, connected, performance }) {
  const cam = camera?.connected ? 'ONLINE' : 'OFFLINE';
  const rows = [
    ['Camera', cam],
    ['Perception', connected ? 'ONLINE' : 'OFFLINE'],
    ['Mission Engine', health?.status === 'ok' ? 'ONLINE' : 'OFFLINE'],
    ['Voice', voice?.engine_ready ? 'ONLINE' : 'OFFLINE'],
  ];
  return (
    <section className="card">
      <div className="card-head"><h3>System Health</h3></div>
      <ul className="health">
        {rows.map(([k, v]) => (
          <li key={k}>
            <span>{k}</span>
            <b className={v === 'ONLINE' ? 'ok' : 'bad'}>{v}</b>
          </li>
        ))}
      </ul>
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
          ]} />
          <MetricGroup title="Streaming" items={[
            ['JPEG encoding', performance?.jpeg_encode_ms == null ? 'N/A' : `${performance.jpeg_encode_ms} ms`],
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

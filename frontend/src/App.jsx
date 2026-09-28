
import { DEMO_MODE } from './services/demoData.js';
import DemoDashboard from './components/DemoDashboard.jsx';
import { useCallback, useEffect, useRef, useState } from 'react';

import './dashboard.css';
import { api } from './services/api.js';
import TopNav, { MissionHeader } from './components/TopNav.jsx';
import DecisionAlert from './components/DecisionAlert.jsx';
import LiveCamera from './components/LiveCamera.jsx';
import MissionStatusCard from './components/MissionStatusCard.jsx';
import MissionTimeline from './components/MissionTimeline.jsx';
import EventStatistics from './components/EventStatistics.jsx';
import DecisionSequence from './components/DecisionSequence.jsx';
import LiveGuidance from './components/LiveGuidance.jsx';
import RecentEvents from './components/RecentEvents.jsx';
import SystemHealth from './components/SystemHealth.jsx';
import MissionProgress from './components/MissionProgress.jsx';
import ProtocolSteps from './components/ProtocolSteps.jsx';
import DetectionsPanel from './components/DetectionsPanel.jsx';
import Protocol from './pages/Protocol.jsx';
import Events from './pages/Events.jsx';
import Experiments from './pages/Experiments.jsx';
import { display } from './services/api.js';
import SessionHistory from './components/SessionHistory.jsx';

const POLL_MS = 750;
const CAMERA_STATUS_UNAVAILABLE = 'camera_status_unavailable';

function LiveFeedTab({ health, status, camera, events, performance, perception, onCameraChanged }) {
  const lastEvent = (Array.isArray(events) && events.length) ? events[events.length - 1] : null;
  const objects = lastEvent?.objects ?? status?.objects ?? [];
  const hands = lastEvent?.hands ?? status?.hands ?? [];
  return (
    <div className="deck-grid deck-grid-live">
      <div className="deck-left">
        <LiveCamera camera={camera} onCameraChanged={onCameraChanged} />
        <LiveGuidance status={status} />
      </div>
      <aside className="deck-right">
        <DetectionsPanel objects={objects} hands={hands} status={status} event={lastEvent} />
        <SystemHealth health={health} camera={camera} performance={performance} perception={perception} status={status} />
      </aside>
    </div>
  );
}

function MemoryTab({ protocol, progress, events }) {
  return (
    <div className="deck-grid">
      <div className="deck-left">
        <ProtocolSteps protocol={protocol} progress={progress} events={events} currentStepId={progress?.current_step} />
        <SessionHistory />
      </div>
      <aside className="deck-right"><DecisionSequence events={events} /><RecentEvents events={events} /></aside>
    </div>
  );
}

function AnalyticsTab({ progress, summary, status, events }) {
  return (
    <div className="deck-grid">
      <div className="deck-left">
        <MissionProgress progress={progress} summary={summary} status={status} />
        <EventStatistics summary={summary} />
      </div>
      <aside className="deck-right"><MissionTimeline protocol={protocol} progress={progress} events={events} /><DecisionSequence events={events} /></aside>
    </div>
  );
}

function SettingsTab({ voice, setVoice, voiceBusy, setVoiceBusy }) {
  const changeVoiceLanguage = useCallback(async (language) => {
    setVoiceBusy(true);
    try {
      await api.setVoiceLanguage(language);
      setVoice(await api.voiceStatus().catch(() => null));
    } finally { setVoiceBusy(false); }
  }, [setVoice, setVoiceBusy]);

  const toggleVoiceEnabled = useCallback(async () => {
    setVoiceBusy(true);
    try {
      await api.setVoiceEnabled(!(voice?.enabled ?? true));
      setVoice(await api.voiceStatus().catch(() => null));
    } finally { setVoiceBusy(false); }
  }, [voice, setVoice, setVoiceBusy]);

  return (
    <div className="deck-grid">
      <div className="deck-left">
        <section className="card"><div className="card-head"><h3>Voice Guidance</h3></div>
          <LiveGuidance voice={voice} busy={voiceBusy} onLanguage={changeVoiceLanguage} onToggle={toggleVoiceEnabled} />
        </section>
        <section className="card"><div className="card-head"><h3>System</h3></div>
          <dl className="meta-grid">
            <div><dt>Backend base</dt><dd className="mono">{display(api.base)}</dd></div>
            <div><dt>Poll interval</dt><dd className="mono">{display(POLL_MS)}ms</dd></div>
          </dl>
        </section>
      </div>
      <aside className="deck-right"><SystemHealth /></aside>
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [overview, setOverview] = useState(null);
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(null);
  const [summary, setSummary] = useState(null);
  const [protocol, setProtocol] = useState(null);
  const [camera, setCamera] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [perception, setPerception] = useState(null);
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [activeNav, setActiveNav] = useState('Mission');
  const [voice, setVoice] = useState(null);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const timer = useRef(null);
  const refreshInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (DEMO_MODE) return;
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    try {
      const [h, o, s, p, sum, ev, v, proto, cam, perf, perceptionStatus] = await Promise.all([
        api.health().catch(() => null),
        api.mission().catch(() => null),
        api.missionStatus().catch(() => null),
        api.missionProgress().catch(() => null),
        api.missionSummary().catch(() => null),
        api.events(30).catch(() => []),
        api.voiceStatus().catch(() => null),
        api.missionProtocol().catch(() => null),
        api.cameraStatus().catch(() => null),
        api.performance().catch(() => null),
        api.perceptionStatus().catch(() => null),
      ]);
      setHealth(h); setOverview(o); setStatus(s);
      setProgress(p); setSummary(sum);
      setEvents(Array.isArray(ev) ? ev : (Array.isArray(ev?.events) ? ev.events : []));
      setVoice(v); setProtocol(proto); setPerformance(perf);
      if (cam) {
        setCamera(cam);
      } else {
        setCamera((previous) => previous
          ? {
              ...previous,
              connected: false,
              has_frame: false,
              frame_age_seconds: null,
              [CAMERA_STATUS_UNAVAILABLE]: true,
            }
          : null);
      }
      setPerception(perceptionStatus);
      setConnected(Boolean(h || o || s));
    } catch { setConnected(false); }
    finally { refreshInFlight.current = false; }
  }, []);

  const changeVoiceLanguage = useCallback(async (language) => {
    setVoiceBusy(true);
    try {
      await api.setVoiceLanguage(language);
      setVoice(await api.voiceStatus().catch(() => null));
    } finally { setVoiceBusy(false); }
  }, []);

  const toggleVoiceEnabled = useCallback(async () => {
    setVoiceBusy(true);
    try {
      await api.setVoiceEnabled(!(voice?.enabled ?? true));
      setVoice(await api.voiceStatus().catch(() => null));
    } finally { setVoiceBusy(false); }
  }, [voice]);

  const confirmUncertain = useCallback(async () => {
    if (!status?.session_id) return;
    const operator = window.prompt('Operator name for the session record:');
    if (!operator?.trim()) return;
    setConfirming(true);
    try {
      await api.confirmSessionStep(status.session_id, operator.trim());
      await refresh();
    } finally {
      setConfirming(false);
    }
  }, [status, refresh]);

useEffect(() => {
    if (DEMO_MODE) return;

    refresh();
    timer.current = setInterval(refresh, POLL_MS);

    return () => clearInterval(timer.current);
}, [refresh]);
  if (DEMO_MODE) {
    return <DemoDashboard />;
  }
  let pageContent = null;
  switch (activeNav) {
    case 'Mission':
      pageContent = (
        <div className="deck-grid">
          <div className="deck-left">
            <DecisionAlert status={status} onManualConfirm={confirmUncertain} confirming={confirming} />
            <LiveCamera camera={camera} onCameraChanged={refresh} />
            <LiveGuidance voice={voice} status={status} busy={voiceBusy} onLanguage={changeVoiceLanguage} onToggle={toggleVoiceEnabled} />
            <RecentEvents events={events} />
          </div>
          <aside className="deck-right">
            <MissionStatusCard progress={progress} summary={summary} status={status} />
            <MissionTimeline protocol={protocol} progress={progress} events={events} />
            <EventStatistics summary={summary} />
            <DecisionSequence events={events} />
            <SystemHealth health={health} camera={camera} voice={voice} performance={performance} perception={perception} status={status} />
          </aside>
        </div>
      );
      break;
    case 'Live Feed':
      pageContent = <LiveFeedTab health={health} status={status} camera={camera} events={events} performance={performance} perception={perception} onCameraChanged={refresh} />;
      break;
    case 'Memory':
      pageContent = <MemoryTab protocol={protocol} progress={progress} events={events} />;
      break;
    case 'Analytics':
      pageContent = <AnalyticsTab progress={progress} summary={summary} status={status} events={events} />;
      break;
    case 'Settings':
      pageContent = <SettingsTab voice={voice} setVoice={setVoice} voiceBusy={voiceBusy} setVoiceBusy={setVoiceBusy} />;
      break;
    case 'Protocol':
      pageContent = <Protocol />;
      break;
    case 'Events':
      pageContent = <Events />;
      break;
    case 'Experiments':
      pageContent = <Experiments />;
      break;
    default:
      pageContent = null;
  }

  return (
    <div className="deck-shell">
      <TopNav connected={connected} health={health} active={activeNav} onNav={setActiveNav} />
      <main className="deck-main">
        <MissionHeader
          overview={overview}
          progress={progress}
          status={status}
          onExperimentSelected={refresh}
        />
        {pageContent}
        <footer className="deck-foot">
          <span>ASTRA-DRISHTI · Local Mission System</span>
          <span>Backend {display(api.base)} · Health {display(health?.status)}</span>
          <span>Voice {(voice?.language ?? 'en').toUpperCase()} · {(voice?.enabled ?? true) ? 'ON' : 'OFF'}</span>
        </footer>
      </main>
    </div>
  );
}

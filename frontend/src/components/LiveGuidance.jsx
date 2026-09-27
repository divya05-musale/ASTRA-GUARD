import { display } from './flightdeck.js';

export default function LiveGuidance({ voice, status, busy, onLanguage, onToggle }) {
  const state = String(status?.status ?? '').toUpperCase();
  const voiceReady = Boolean(voice?.engine_ready);
  const fallbackGuidance = {
    CORRECT: 'Mission operating normally. Continue with the current protocol step.',
    DEVIATION: 'Deviation detected. Check the expected activity and object before continuing.',
    UNCERTAIN: 'Verification required. Confirm the current activity and object.',
    COMPLETED: 'Mission complete.',
  }[state] ?? (status ? 'Awaiting mission events from the perception pipeline.' : voice?.last_guidance);
  const guidance = status?.guidance || fallbackGuidance || 'Awaiting mission events from the perception pipeline.';
  const guidanceTone = state === 'DEVIATION' ? 'deviation' : state === 'UNCERTAIN' ? 'uncertain' : 'normal';
  return (
    <section className="card">
      <div className="card-head">
        <h3>Live Guidance</h3>
        <span className={voice?.enabled && voiceReady ? 'conn conn-on' : 'conn conn-off'}>
          {!voiceReady ? 'Local voice unavailable' : voice?.enabled ? '● Voice guidance active' : 'Voice muted'}
        </span>
      </div>
      <div className="tts-row"><span>Local text-to-speech</span><span>{voiceReady ? 'Output: Local' : 'Written guidance active'}</span></div>
      <div className={`guidance-quote guidance-${guidanceTone}`} aria-live="polite">{display(guidance)}</div>
      <div className="voice-row">
        <label>
          Voice enabled
          <button type="button" className={voice?.enabled ? 'btn btn-primary' : 'btn'} disabled={busy} onClick={onToggle}>
            {voice?.enabled ? 'ON' : 'OFF'}
          </button>
        </label>
        <label>
          Language
          <select value={voice?.language ?? 'en'} disabled={busy} onChange={(e) => onLanguage(e.target.value)}>
            <option value="en">English</option>
            <option value="hi">Hindi</option>
          </select>
        </label>
      </div>
      {!voice?.hindi_voice_available && (
        <div className="note">Hindi voice not installed — Hindi guidance uses the default voice.</div>
      )}
    </section>
  );
}

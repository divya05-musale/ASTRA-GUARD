import { useEffect, useState } from 'react';
import { api, display, prettyId, statusColor, stepNumber } from '../services/api.js';
import ProtocolSteps from '../components/ProtocolSteps.jsx';

export default function Protocol() {
  const [summary, setSummary] = useState(null);
  const [steps, setSteps] = useState([]);
  const [activities, setActivities] = useState([]);
  const [objects, setObjects] = useState([]);
  const [rules, setRules] = useState([]);
  const [progress, setProgress] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('steps');

  const refresh = async () => {
    setLoading(true);
    try {
      const [sum, stp, act, obj, rl, prg, ev] = await Promise.all([
        api.protocolSummary().catch(() => null),
        api.protocolSteps().catch(() => ({ steps: [] })),
        api.protocolActivities().catch(() => ({ activities: [] })),
        api.protocolObjects().catch(() => ({ objects: [] })),
        api.protocolRules().catch(() => ({ rules: [] })),
        api.missionProgress().catch(() => null),
        api.events(100).catch(() => []),
      ]);
      setSummary(sum);
      setSteps(Array.isArray(stp?.steps) ? stp.steps : []);
      setActivities(Array.isArray(act?.activities) ? act.activities : []);
      setObjects(Array.isArray(obj?.objects) ? obj.objects : []);
      setRules(Array.isArray(rl?.rules) ? rl.rules : []);
      setProgress(prg);
      setEvents(Array.isArray(ev) ? ev : []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 1500);
    return () => clearInterval(t);
  }, []);

  const tabs = [
    { id: 'steps', label: 'Steps' },
    { id: 'activities', label: 'Activities' },
    { id: 'objects', label: 'Objects' },
    { id: 'rules', label: 'Rules' },
  ];

  return (
    <div className="pages-wrap">
      <header className="page-head">
        <div>
          <h2>Protocol</h2>
          <p>{display(summary?.experiment?.name ?? 'EXP001')} — {display(summary?.experiment?.description ?? '')}</p>
        </div>
        <div className="page-actions">
          <button className="btn btn-primary" type="button" onClick={refresh}>Refresh</button>
        </div>
      </header>

      <div className="tab-switch">
        {tabs.map((t) => (
          <button key={t.id} type="button"
            className={tab === t.id ? 'tab tab-active' : 'tab'}
            onClick={() => setTab(t.id)}>{t.label}</button>
        ))}
      </div>

      {tab === 'steps' ? (
        <ProtocolSteps
          protocol={{ steps }}
          progress={progress}
          events={events}
          currentStepId={progress?.current_step}
        />
      ) : null}

      {tab === 'activities' ? (
        <section className="card">
          <div className="card-head"><h3>Activities</h3><span>{display(activities.length)}</span></div>
          <ul className="kv-list">
            {activities.map((a) => (
              <li key={display(a.activity_id ?? a.id)}>
                <span className="mono">{display(a.activity_id)}</span>
                <span>{display(a.name ?? a.description)}</span>
                {a.hand_required ? <span className="badge">Hand interaction</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {tab === 'objects' ? (
        <section className="card">
          <div className="card-head"><h3>Expected Objects</h3><span>{display(objects.length)}</span></div>
          <ul className="kv-list">
            {objects.map((o) => (
              <li key={display(o.object_id ?? o.id)}>
                <span className="mono">{display(o.object_id)}</span>
                <span>{display(o.display_name ?? o.name)}</span>
                {o.aliases ? <span className="badge">{display(o.aliases.length)} aliases</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {tab === 'rules' ? (
        <section className="card">
          <div className="card-head"><h3>Validation Rules</h3><span>{display(rules.length)}</span></div>
          <ul className="kv-list kv-wide">
            {rules.map((r) => (
              <li key={display(r.rule_id)}>
                <div>
                  <span className="mono">{display(r.rule_id)}</span>
                  <span>{prettyId(r.rule_type ?? '')} on step {display(r.step_id)}</span>
                </div>
                <div>
                  <span className="badge" style={{ background: statusColor(r.result), color: '#0b1020' }}>
                    {prettyId(r.result)}
                  </span>
                  <span style={{ color: statusColor(r.severity) }}>{prettyId(r.severity)}</span>
                  <p>{display(r.condition)}</p>
                  <p className="kv-note">{display(r.guidance)}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

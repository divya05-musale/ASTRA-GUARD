import { display, formatConfidence, prettyId, stepNumber } from '../services/api.js';

export function statusTone(s) {
  return String(s || 'IDLE').toUpperCase();
}

export function pillClass(s) {
  const v = statusTone(s);
  if (v === 'CORRECT') return 'pill pill-correct';
  if (v === 'DEVIATION') return 'pill pill-deviation';
  if (v === 'UNCERTAIN') return 'pill pill-uncertain';
  if (v === 'COMPLETED') return 'pill pill-completed';
  return 'pill pill-idle';
}

export function alertTone(s) {
  const v = statusTone(s);
  if (v === 'DEVIATION') return 'alert alert-deviation';
  if (v === 'CORRECT') return 'alert alert-correct';
  if (v === 'UNCERTAIN') return 'alert alert-uncertain';
  if (v === 'COMPLETED') return 'alert alert-completed';
  return 'alert alert-idle';
}

export function utcNow() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())} UTC`;
}

export { display, formatConfidence, prettyId, stepNumber };

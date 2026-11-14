/** Safe display text for unknown values from the API (never '[object Object]'). */
export const text = (v: unknown): string =>
  typeof v === 'string' ? v : typeof v === 'number' || typeof v === 'boolean' || typeof v === 'bigint' ? `${v}` : v == null ? '' : JSON.stringify(v);

const usd0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

export const toNum = (v: unknown): number => (typeof v === 'number' ? v : Number(v ?? 0));
export const money = (v: unknown) => usd0.format(toNum(v));
export const signedMoney = (v: unknown) => `${toNum(v) >= 0 ? '+' : '−'}${usd0.format(Math.abs(toNum(v)))}`;
export const pct = (v: unknown, digits = 1) => `${(toNum(v) * 100).toFixed(digits)}%`;
export const int = (v: unknown) => Math.round(toNum(v)).toLocaleString('en-US');
export const days = (v: unknown) => `${Math.round(toNum(v))} days`;
export const ptmLabel = (v: unknown) => {
  const d = (toNum(v) - 1) * 100;
  return `${Math.abs(d).toFixed(1)}% ${d >= 0 ? 'above' : 'below'} market`;
};
export const when = (v: unknown) => (v ? new Date(text(v)).toLocaleString('en-AU', { dateStyle: 'medium', timeStyle: 'short' }) : '—');
export const label = (s: unknown) => text(s).replace(/_/g, ' ');

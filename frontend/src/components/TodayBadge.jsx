export default function TodayBadge({ streakDays, todaysProgressPct }) {
  const r = 15;
  const c = 2 * Math.PI * r;
  const offset = c - (todaysProgressPct / 100) * c;

  return (
    <div className="today-badge">
      <div className="ring-wrap" title={`${todaysProgressPct}% of today's plan done`}>
        <svg width="38" height="38" viewBox="0 0 38 38">
          <circle cx="19" cy="19" r={r} fill="none" stroke="var(--paper-alt)" strokeWidth="4" />
          <circle
            cx="19"
            cy="19"
            r={r}
            fill="none"
            stroke="var(--pen-red)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={offset}
            transform="rotate(-90 19 19)"
          />
        </svg>
        <span className="ring-label">{todaysProgressPct}%</span>
      </div>
      <div className="streak-chip" title={`${streakDays}-day streak`}>
        <span className="flame">🔥</span>
        <span className="streak-num">{streakDays}</span>
      </div>

      <style>{`
        .today-badge {
          display: flex;
          align-items: center;
          gap: 10px;
          background: var(--paper-card);
          border: 1px solid rgba(36,49,79,0.08);
          border-radius: 999px;
          padding: 6px 14px 6px 6px;
          box-shadow: var(--shadow-card);
        }
        .ring-wrap { position: relative; width: 38px; height: 38px; }
        .ring-label {
          position: absolute; inset: 0;
          display: flex; align-items: center; justify-content: center;
          font-family: var(--font-mono); font-size: 9px; font-weight: 600;
          color: var(--ink);
        }
        .streak-chip {
          display: flex; align-items: center; gap: 4px;
          font-family: var(--font-mono); font-weight: 600; color: var(--pen-red-dark);
          font-size: 14px;
        }
        .flame { font-size: 15px; }
      `}</style>
    </div>
  );
}

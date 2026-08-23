import { useNavigate } from "react-router-dom";
import PenProgress from "./PenProgress.jsx";

export default function SubjectCard({ subject }) {
  const navigate = useNavigate();

  return (
    <button className="subject-card" onClick={() => navigate(`/study/${subject.id}`)}>
      <div className="tab" style={{ background: subject.color }}>
        {subject.name}
      </div>
      <div className="body">
        <p className="chapter">
          {subject.completedChapters < subject.totalChapters ? "Running Chapter" : "Completed"}
        </p>
        <p className="chapter-name">{subject.runningChapter}</p>
        <PenProgress pct={subject.progressPct} color={subject.color} />
        <p className="pct">{subject.progressPct}%</p>
      </div>

      <style>{`
        .subject-card {
          all: unset;
          cursor: pointer;
          display: flex;
          flex-direction: column;
          width: 200px;
          background: var(--paper-card);
          border-radius: 10px 10px 4px 4px;
          box-shadow: var(--shadow-card);
          border: 1px solid rgba(36,49,79,0.06);
          overflow: hidden;
          flex-shrink: 0;
          transition: transform 0.15s ease;
        }
        .subject-card:hover { transform: translateY(-3px); }
        .subject-card:focus-visible { outline: 3px solid var(--ink-soft); outline-offset: 2px; }
        .tab {
          font-family: var(--font-display);
          color: #fff;
          font-size: 1.15rem;
          padding: 10px 14px;
        }
        .body { padding: 12px 14px 14px; text-align: left; }
        .chapter {
          margin: 0 0 2px;
          font-size: 0.7rem;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          color: var(--graphite-soft);
        }
        .chapter-name {
          margin: 0 0 10px;
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--ink);
          min-height: 2.4em;
        }
        .pct {
          margin: 4px 0 0;
          font-family: var(--font-mono);
          font-size: 0.75rem;
          color: var(--graphite-soft);
          text-align: right;
        }
      `}</style>
    </button>
  );
}

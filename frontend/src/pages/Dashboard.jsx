import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getDashboard } from "../api.js";
import SubjectCard from "../components/SubjectCard.jsx";
import PenProgress from "../components/PenProgress.jsx";
import TodayBadge from "../components/TodayBadge.jsx";
import ProfileModal from "../components/ProfileModal.jsx";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [doubtOpen, setDoubtOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="page">
        <p>
          Couldn't reach the backend. Make sure it's running on port 4000 (see README).
          <br />
          <span style={{ color: "var(--graphite-soft)" }}>{error}</span>
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page">
        <p className="hand-title" style={{ fontSize: "1.4rem" }}>
          loading your notebook…
        </p>
      </div>
    );
  }

  const { user, subjects, studyMaterial } = data;

  return (
    <div className="page">
      <header className="dash-header">
        <h1 className="hand-title welcome">
          Welcome, {user.registered ? user.name : "there"}
        </h1>

        <div className="header-right">
          <span className="eyebrow today-label">Today's Progress ↑</span>
          <TodayBadge streakDays={user.streakDays} todaysProgressPct={user.todaysProgressPct} />
          <button
            className="profile-btn"
            onClick={() => setProfileOpen(true)}
            aria-label="Profile"
          >
            👤
          </button>
        </div>
      </header>

      <div className="dash-grid">
        <div className="dash-left">
          <section className="section">
            <h2 className="section-tab">Your Subjects</h2>
            <div className="subject-row">
              {subjects.map((s) => (
                <SubjectCard key={s.id} subject={s} />
              ))}
              <span className="row-arrow">›</span>
            </div>
          </section>

          <section className="section">
            <h2 className="section-tab">Your Study Material</h2>
            <div className="material-row">
              {studyMaterial.map((m) => (
                <div key={m.id} className="material-card card">
                  <p className="material-title">{m.title}</p>
                  <p className="material-sub">{m.subtitle}</p>
                  <div className="material-thumb">{m.type === "book" ? "📘" : "📝"}</div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="dash-right card">
          {subjects.map((s) => (
            <div key={s.id} className="mini-row">
              <span className="mini-name" style={{ color: s.color }}>
                {s.name}
              </span>
              <PenProgress pct={s.progressPct} color={s.color} />
            </div>
          ))}
        </aside>
      </div>

      <button
        className="doubt-fab"
        onClick={() => setDoubtOpen((v) => !v)}
        aria-label="Ask a doubt"
      >
        ?
      </button>

      {profileOpen && (
        <ProfileModal
          user={user}
          subjects={subjects}
          onClose={() => setProfileOpen(false)}
          onUserUpdate={(updatedUser) => setData((d) => ({ ...d, user: updatedUser }))}
        />
      )}

      {doubtOpen && (
        <div className="doubt-popover card">
          <p className="hand-title" style={{ margin: "0 0 6px", fontSize: "1.05rem" }}>
            Raise a doubt
          </p>
          <p style={{ margin: "0 0 10px", fontSize: "0.85rem", color: "var(--graphite-soft)" }}>
            Doubts are best asked live, inside a subject's AI classroom, where the tutor
            can pause mid-explanation for you. Jump into a subject to try it.
          </p>
          <button
            className="cta-btn"
            onClick={() => navigate(`/study/${subjects[0].id}`)}
          >
            Open {subjects[0].name} classroom →
          </button>
        </div>
      )}

      <style>{`
        .dash-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          flex-wrap: wrap;
          gap: 14px;
          margin-bottom: 26px;
        }
        .welcome { font-size: 2rem; margin: 0; }
        .header-right { display: flex; align-items: center; gap: 12px; }
        .today-label { font-size: 0.95rem; }
        .profile-btn {
          all: unset; cursor: pointer;
          width: 42px; height: 42px; border-radius: 50%;
          background: var(--ink); color: #fff;
          display: flex; align-items: center; justify-content: center;
          font-size: 1.1rem;
          box-shadow: var(--shadow-card);
        }
        .dash-grid {
          display: grid;
          grid-template-columns: 1fr 220px;
          gap: 22px;
        }
        .section { margin-bottom: 26px; }
        .section-tab {
          display: inline-block;
          font-family: var(--font-display);
          font-size: 1.1rem;
          color: var(--ink);
          background: var(--paper-alt);
          padding: 4px 14px;
          border-radius: 8px 8px 0 0;
          margin: 0 0 -1px 6px;
          transform: rotate(-0.6deg);
        }
        .subject-row {
          display: flex;
          gap: 14px;
          overflow-x: auto;
          padding: 16px;
          background: var(--paper-alt);
          border-radius: 4px 12px 12px 12px;
        }
        .row-arrow {
          align-self: center;
          font-size: 1.6rem;
          color: var(--graphite-soft);
          padding: 0 4px;
        }
        .material-row {
          display: flex;
          gap: 14px;
          padding: 16px;
          background: var(--paper-alt);
          border-radius: 4px 12px 12px 12px;
        }
        .material-card {
          flex: 1;
          padding: 16px;
          min-height: 90px;
          position: relative;
        }
        .material-title { margin: 0; font-weight: 700; color: var(--ink); }
        .material-sub { margin: 4px 0 0; font-size: 0.8rem; color: var(--graphite-soft); }
        .material-thumb { position: absolute; right: 14px; bottom: 10px; font-size: 1.4rem; opacity: 0.6; }
        .dash-right {
          padding: 16px 14px;
          height: fit-content;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .mini-row { display: flex; flex-direction: column; gap: 6px; }
        .mini-name { font-family: var(--font-mono); font-weight: 700; font-size: 0.85rem; }

        .doubt-fab {
          all: unset;
          position: fixed;
          right: 32px;
          bottom: 32px;
          width: 56px; height: 56px;
          border-radius: 50%;
          background: var(--pen-red);
          color: #fff;
          font-family: var(--font-display);
          font-size: 1.6rem;
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 6px 18px rgba(183,80,62,0.45);
          cursor: pointer;
        }
        .doubt-popover {
          position: fixed;
          right: 32px;
          bottom: 100px;
          width: 260px;
          padding: 16px;
        }
        .cta-btn {
          all: unset; cursor: pointer;
          display: inline-block;
          background: var(--ink);
          color: #fff;
          padding: 8px 12px;
          border-radius: 8px;
          font-size: 0.85rem;
          font-weight: 600;
        }

        @media (max-width: 720px) {
          .dash-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}

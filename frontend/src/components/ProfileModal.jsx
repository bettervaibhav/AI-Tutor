import { useState } from "react";
import { updateUser } from "../api.js";

export default function ProfileModal({ user, subjects, onClose, onUserUpdate }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user.name);
  const [saving, setSaving] = useState(false);

  const totalChapters = subjects.reduce((sum, s) => sum + s.totalChapters, 0);
  const completedChapters = subjects.reduce((sum, s) => sum + s.completedChapters, 0);
  const overallPct = totalChapters ? Math.round((completedChapters / totalChapters) * 100) : 0;

  async function handleSave() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const updated = await updateUser({ name: name.trim() });
      onUserUpdate(updated);
      setEditing(false);
    } catch {
      // keep the modal open with the field editable so they can retry
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="profile-overlay" onClick={onClose}>
      <div className="profile-modal card" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose} aria-label="Close profile">
          ✕
        </button>

        <div className="profile-avatar">👤</div>

        {editing ? (
          <div className="name-edit">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              maxLength={40}
            />
            <div className="name-edit-actions">
              <button className="ghost-btn" onClick={() => { setEditing(false); setName(user.name); }}>
                Cancel
              </button>
              <button className="cta-btn" onClick={handleSave} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        ) : (
          <div className="name-row">
            <h2 className="hand-title profile-name">{user.name}</h2>
            <button className="edit-link" onClick={() => setEditing(true)}>
              Edit name
            </button>
          </div>
        )}

        <div className="profile-stats">
          <div className="stat">
            <span className="stat-num">{user.streakDays}🔥</span>
            <span className="stat-label">day streak</span>
          </div>
          <div className="stat">
            <span className="stat-num">{overallPct}%</span>
            <span className="stat-label">overall progress</span>
          </div>
          <div className="stat">
            <span className="stat-num">{subjects.length}</span>
            <span className="stat-label">subjects enrolled</span>
          </div>
        </div>

        <p className="eyebrow" style={{ display: "block", margin: "18px 0 8px" }}>
          your subjects
        </p>
        <ul className="profile-subjects">
          {subjects.map((s) => (
            <li key={s.id}>
              <span className="dot" style={{ background: s.color }} />
              <span className="sub-name">{s.fullName}</span>
              <span className="sub-pct">{s.progressPct}%</span>
            </li>
          ))}
        </ul>
      </div>

      <style>{`
        .profile-overlay {
          position: fixed; inset: 0; background: rgba(36,49,79,0.35);
          display: flex; align-items: center; justify-content: center;
          z-index: 50; padding: 20px;
        }
        .profile-modal {
          width: 100%; max-width: 380px; padding: 28px 24px; position: relative;
          text-align: center;
        }
        .close-btn {
          all: unset; cursor: pointer; position: absolute; top: 14px; right: 16px;
          color: var(--graphite-soft); font-size: 1rem;
        }
        .profile-avatar {
          width: 64px; height: 64px; border-radius: 50%; background: var(--ink);
          color: #fff; font-size: 1.8rem; display: flex; align-items: center;
          justify-content: center; margin: 0 auto 12px;
        }
        .name-row { display: flex; flex-direction: column; align-items: center; gap: 4px; }
        .profile-name { margin: 0; font-size: 1.5rem; }
        .edit-link {
          all: unset; cursor: pointer; font-size: 0.75rem; color: var(--ink-soft);
          font-weight: 600;
        }
        .name-edit { display: flex; flex-direction: column; align-items: center; gap: 8px; }
        .name-edit input {
          font-family: var(--font-body); font-size: 1rem; text-align: center;
          border: 1px solid var(--rule-line); border-radius: 8px; padding: 8px 10px;
          width: 100%;
        }
        .name-edit-actions { display: flex; gap: 8px; }
        .ghost-btn {
          all: unset; cursor: pointer; font-size: 0.8rem; color: var(--graphite-soft);
          padding: 8px 10px;
        }
        .cta-btn {
          all: unset; cursor: pointer; background: var(--ink); color: #fff;
          padding: 8px 14px; border-radius: 8px; font-size: 0.85rem; font-weight: 600;
        }
        .cta-btn:disabled { opacity: 0.6; }
        .profile-stats {
          display: flex; justify-content: space-around; margin-top: 20px;
          padding-top: 16px; border-top: 1px solid var(--rule-line);
        }
        .stat { display: flex; flex-direction: column; gap: 2px; }
        .stat-num { font-family: var(--font-mono); font-weight: 700; color: var(--ink); font-size: 1.1rem; }
        .stat-label { font-size: 0.68rem; color: var(--graphite-soft); }
        .profile-subjects { list-style: none; margin: 0; padding: 0; text-align: left; }
        .profile-subjects li {
          display: flex; align-items: center; gap: 8px; padding: 7px 4px;
          font-size: 0.85rem; border-bottom: 1px solid var(--paper-alt);
        }
        .dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
        .sub-name { flex: 1; color: var(--graphite); }
        .sub-pct { font-family: var(--font-mono); font-size: 0.75rem; color: var(--graphite-soft); }
      `}</style>
    </div>
  );
}

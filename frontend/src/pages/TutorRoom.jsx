import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { startLecture, askDoubt, getStatus } from "../api.js";
import LectureVisual from "../components/LectureVisual.jsx";
import { useSpeechSynthesis, useSpeechRecognition } from "../hooks/useSpeech.js";

const SPEEDS = [0.75, 1, 1.25, 1.5, 2];

export default function TutorRoom() {
  const { subjectId } = useParams();
  const navigate = useNavigate();

  const [entered, setEntered] = useState(false); // gate screen, needed so audio is allowed to play
  const [lecture, setLecture] = useState(null); // { topic, segments }
  const [index, setIndex] = useState(0);
  const [status, setStatus] = useState("loading"); // loading | speaking | paused | asking | answered | done
  const [speedIdx, setSpeedIdx] = useState(1);
  const [voiceOn, setVoiceOn] = useState(true);
  const [voiceURI, setVoiceURI] = useState(
    () => localStorage.getItem("tutor-voice-uri") || ""
  );
  const [aiEnabled, setAiEnabled] = useState(true); // assume true until checked
  const [question, setQuestion] = useState("");
  const [doubtLog, setDoubtLog] = useState([]); // {question, answer}
  const [answering, setAnswering] = useState(false);
  const fallbackTimer = useRef(null);

  const { supported: ttsSupported, speaking, speak, cancel: cancelSpeech, voices } =
    useSpeechSynthesis();
  const { supported: micSupported, listening, start: startListening, stop: stopListening } =
    useSpeechRecognition();

  useEffect(() => {
    getStatus()
      .then((s) => setAiEnabled(s.aiEnabled))
      .catch(() => setAiEnabled(true)); // fail open, don't show a false alarm
  }, []);

  function handleVoiceChange(uri) {
    setVoiceURI(uri);
    localStorage.setItem("tutor-voice-uri", uri);
  }

  // Fetch the lecture as soon as the page loads (text is ready before the
  // learner even clicks "Start class" — only the audio waits for a click).
  useEffect(() => {
    startLecture(subjectId)
      .then((data) => {
        setLecture(data);
        setIndex(0);
      })
      .catch(() => setStatus("error"));
    return () => {
      clearTimeout(fallbackTimer.current);
      cancelSpeech();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subjectId]);

  // Speak (or, if voice is off / unsupported, time-out) through segments
  // automatically while status is "speaking".
  useEffect(() => {
    if (status !== "speaking" || !lecture) return;
    const segment = lecture.segments[index];
    if (!segment) {
      setStatus("done");
      return;
    }

    const rate = SPEEDS[speedIdx];
    const goToNext = () => {
      setIndex((i) => {
        const next = i + 1;
        if (!lecture.segments[next]) {
          setStatus("done");
          return i;
        }
        return next;
      });
    };

    if (voiceOn && ttsSupported) {
      speak(segment.text, { rate, voiceURI, onEnd: goToNext });
    } else {
      const readMs = Math.min(9000, 2600 + segment.text.length * 35) / rate;
      fallbackTimer.current = setTimeout(goToNext, readMs);
    }

    return () => {
      clearTimeout(fallbackTimer.current);
      cancelSpeech();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, index, lecture, speedIdx, voiceOn]);

  // Speak the tutor's answer out loud as soon as it arrives.
  useEffect(() => {
    if (status !== "answered" || doubtLog.length === 0) return;
    if (voiceOn && ttsSupported) {
      speak(doubtLog[doubtLog.length - 1].answer, { rate: SPEEDS[speedIdx], voiceURI });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  function handleStartClass() {
    setEntered(true);
    setStatus("speaking");
  }

  function handlePause() {
    clearTimeout(fallbackTimer.current);
    cancelSpeech();
    setStatus("paused");
  }

  function handleResume() {
    setStatus("speaking");
  }

  function handleReplay() {
    const segment = lecture.segments[index];
    if (voiceOn && ttsSupported && segment) {
      speak(segment.text, { rate: SPEEDS[speedIdx], voiceURI });
    }
  }

  function handleRaiseHand() {
    clearTimeout(fallbackTimer.current);
    cancelSpeech();
    setStatus("asking");
  }

  function handleMicClick() {
    if (listening) {
      stopListening();
      return;
    }
    startListening((transcript) => setQuestion(transcript));
  }

  async function handleAskSubmit(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setAnswering(true);
    const segment = lecture.segments[index];
    try {
      const { answer } = await askDoubt({
        subjectId,
        topic: lecture.topic,
        segmentText: segment.text,
        question,
      });
      setDoubtLog((log) => [...log, { question, answer }]);
      setQuestion("");
      setStatus("answered");
    } catch {
      setDoubtLog((log) => [
        ...log,
        { question, answer: "Sorry, something went wrong reaching the tutor." },
      ]);
      setStatus("answered");
    } finally {
      setAnswering(false);
    }
  }

  function handleContinueAfterDoubt() {
    cancelSpeech();
    setStatus("speaking");
  }

  function changeSpeed(dir) {
    setSpeedIdx((i) => Math.max(0, Math.min(SPEEDS.length - 1, i + dir)));
  }

  if (status === "error") {
    return (
      <div className="page">
        <p>Couldn't start the lecture. Is the backend running on port 4000?</p>
        <button onClick={() => navigate("/")}>← Back</button>
      </div>
    );
  }

  // ---------- Gate screen: click to start (also unlocks audio) ----------
  if (!entered) {
    return (
      <div className="page room-page">
        <div className="gate card">
          <div className="gate-avatar">👩‍🏫</div>
          <h1 className="hand-title" style={{ fontSize: "1.7rem", margin: "6px 0 4px" }}>
            {lecture ? `Ready to learn ${lecture.topic}?` : "Setting up your class…"}
          </h1>
          <p style={{ color: "var(--graphite-soft)", margin: "0 0 18px" }}>
            Your tutor will teach out loud, step by step. You can pause any time and
            raise a doubt — by typing or by voice.
          </p>
          {!ttsSupported && (
            <p className="voice-warning">
              ⚠ Your browser doesn't support spoken audio (Web Speech API). The
              lecture will still work, just as text — try Chrome or Edge for voice.
            </p>
          )}
          {!aiEnabled && (
            <p className="voice-warning">
              🧪 Running in demo mode (no AI key on the backend) — you'll get solid
              built-in lecture content and doubt answers, not live AI ones.
            </p>
          )}
          <button className="cta-btn big" disabled={!lecture} onClick={handleStartClass}>
            {lecture ? "🔊 Start class" : "Loading…"}
          </button>
        </div>
        <style>{`
          .room-page { display: flex; align-items: center; justify-content: center; }
          .gate {
            max-width: 420px; text-align: center; padding: 36px 30px; margin-top: 40px;
          }
          .gate-avatar { font-size: 3rem; }
          .voice-warning {
            background: #fbe9d9; color: #a3611c; font-size: 0.8rem;
            padding: 8px 10px; border-radius: 8px; margin-bottom: 16px;
          }
          .cta-btn.big { padding: 12px 22px; border-radius: 10px; font-size: 1rem; }
        `}</style>
      </div>
    );
  }

  if (!lecture) {
    return (
      <div className="page">
        <p className="hand-title" style={{ fontSize: "1.4rem" }}>
          the tutor is walking to the board…
        </p>
      </div>
    );
  }

  const segment = lecture.segments[index];
  const isPausedForDoubt = status === "asking" || status === "answered";

  return (
    <div className="page room-page">
      <header className="room-header">
        <button className="back-btn" onClick={() => navigate("/")}>
          ← Dashboard
        </button>
        <h1 className="hand-title room-title">Let's study {lecture.topic}</h1>
        <div className="header-controls">
          <button
            className={`voice-toggle ${voiceOn ? "on" : "off"}`}
            onClick={() => {
              cancelSpeech();
              setVoiceOn((v) => !v);
            }}
            title={voiceOn ? "Turn tutor voice off" : "Turn tutor voice on"}
          >
            {voiceOn ? "🔊" : "🔇"}
          </button>
          {ttsSupported && voices.length > 0 && (
            <select
              className="voice-select"
              value={voiceURI}
              onChange={(e) => handleVoiceChange(e.target.value)}
              disabled={!voiceOn}
              title="Choose the tutor's voice"
            >
              <option value="">Default voice</option>
              {voices.map((v) => (
                <option key={v.voiceURI} value={v.voiceURI}>
                  {v.name.replace(/^Microsoft |^Google /, "")} {v.lang ? `(${v.lang})` : ""}
                </option>
              ))}
            </select>
          )}
          <div className="speed-control" aria-label="Playback speed">
            <button onClick={() => changeSpeed(-1)} aria-label="Slower">«</button>
            <span className="speed-val">{SPEEDS[speedIdx]}×</span>
            <button onClick={() => changeSpeed(1)} aria-label="Faster">»</button>
          </div>
        </div>
      </header>

      {!aiEnabled && (
        <p className="demo-banner">
          🧪 Demo mode: no ANTHROPIC_API_KEY configured on the backend, so lectures and
          doubt answers use built-in offline content instead of live AI. Add a key in
          <code> backend/.env</code> for full AI-generated teaching.
        </p>
      )}

      <div className="room-grid">
        <aside className="teacher-col card">
          <div className={`avatar ${speaking ? "talking" : ""}`}>👩‍🏫</div>
          <p className="teacher-name">AI Tutor</p>
          <p className={`status-pill status-${status}`}>
            {status === "speaking" && (speaking ? "Speaking…" : "Teaching…")}
            {status === "paused" && "Paused"}
            {status === "asking" && "Listening to your doubt…"}
            {status === "answered" && (speaking ? "Explaining…" : "Doubt cleared")}
            {status === "done" && "Lecture complete"}
          </p>
          {!voiceOn && <p className="voice-off-note">Voice muted</p>}
        </aside>

        <div className="board-col">
          <div className="board card">
            <LectureVisual kind={segment?.visual || "diagram"} />
          </div>

          <div className="caption-bar card">
            {status === "done" ? (
              <p className="caption">
                That's a wrap for this topic! Great job staying with it. Head back to your
                dashboard to pick up the next chapter, or ask a follow-up doubt below.
              </p>
            ) : (
              <p className="caption">{segment?.text}</p>
            )}
            {status !== "done" && (
              <button className="replay-btn" onClick={handleReplay} title="Replay this line">
                🔁 Replay
              </button>
            )}
          </div>

          {isPausedForDoubt && (
            <div className="doubt-panel card">
              {status === "asking" && (
                <form onSubmit={handleAskSubmit} className="doubt-form">
                  <p className="hand-title" style={{ margin: "0 0 8px", fontSize: "1rem" }}>
                    ✋ what's your doubt?
                  </p>
                  <div className="doubt-input-row">
                    <textarea
                      autoFocus
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      placeholder="Type, or tap the mic to speak your question…"
                      rows={2}
                    />
                    {micSupported && (
                      <button
                        type="button"
                        className={`mic-btn ${listening ? "listening" : ""}`}
                        onClick={handleMicClick}
                        title={listening ? "Stop recording" : "Speak your doubt"}
                      >
                        {listening ? "⏺" : "🎤"}
                      </button>
                    )}
                  </div>
                  {listening && <p className="listening-hint">Listening… speak now</p>}
                  <div className="doubt-form-actions">
                    <button type="button" className="ghost-btn" onClick={handleResume}>
                      Never mind, continue
                    </button>
                    <button type="submit" className="cta-btn" disabled={answering}>
                      {answering ? "Asking…" : "Ask the tutor"}
                    </button>
                  </div>
                </form>
              )}

              {status === "answered" && (
                <div>
                  <p className="doubt-q">You asked: “{doubtLog[doubtLog.length - 1].question}”</p>
                  <p className="doubt-a">
                    {speaking && <span className="speaking-dot">🔊</span>}
                    {doubtLog[doubtLog.length - 1].answer}
                  </p>
                  <button className="cta-btn" onClick={handleContinueAfterDoubt}>
                    Got it — continue lecture →
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="controls">
            {status === "speaking" && (
              <button className="pause-btn" onClick={handlePause}>
                ⏸ Pause
              </button>
            )}
            {status === "paused" && (
              <>
                <button className="resume-btn" onClick={handleResume}>
                  ▶ Resume
                </button>
                <button className="hand-btn" onClick={handleRaiseHand}>
                  ✋ Raise doubt
                </button>
              </>
            )}
            {status === "done" && (
              <button className="cta-btn" onClick={() => navigate("/")}>
                Back to dashboard
              </button>
            )}
          </div>
        </div>

        <aside className="notes-col card">
          <p className="eyebrow" style={{ display: "block", marginBottom: 8 }}>
            margin notes
          </p>
          <ol className="notes-list">
            {lecture.segments.map((s, i) => (
              <li
                key={i}
                className={i === index ? "active" : i < index ? "done" : "upcoming"}
              >
                {s.text.slice(0, 70)}
                {s.text.length > 70 ? "…" : ""}
              </li>
            ))}
          </ol>
          {doubtLog.length > 0 && (
            <>
              <p className="eyebrow" style={{ display: "block", margin: "14px 0 8px" }}>
                your doubts
              </p>
              <ul className="doubt-history">
                {doubtLog.map((d, i) => (
                  <li key={i}>❓ {d.question}</li>
                ))}
              </ul>
            </>
          )}
        </aside>
      </div>

      <style>{`
        .room-header {
          display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
          margin-bottom: 22px;
        }
        .back-btn { all: unset; cursor: pointer; color: var(--ink-soft); font-weight: 600; font-size: 0.85rem; }
        .room-title { margin: 0; font-size: 1.7rem; flex: 1; }
        .header-controls { display: flex; align-items: center; gap: 10px; }
        .voice-toggle {
          all: unset; cursor: pointer; font-size: 1.2rem;
          background: var(--paper-card); border-radius: 999px; padding: 8px 10px;
          box-shadow: var(--shadow-card); line-height: 1;
        }
        .voice-toggle.off { opacity: 0.6; }
        .voice-select {
          font-family: var(--font-body); font-size: 0.8rem; color: var(--ink);
          background: var(--paper-card); border: none; border-radius: 999px;
          padding: 8px 12px; box-shadow: var(--shadow-card); max-width: 160px;
        }
        .voice-select:disabled { opacity: 0.5; }
        .demo-banner {
          background: #fef3e2; color: #8a5a1a; border: 1px solid #f0d5a8;
          border-radius: 10px; padding: 10px 14px; font-size: 0.8rem;
          margin: -8px 0 18px;
        }
        .demo-banner code {
          background: rgba(0,0,0,0.06); padding: 1px 5px; border-radius: 4px;
        }
        .speed-control {
          display: flex; align-items: center; gap: 8px;
          background: var(--paper-card); border-radius: 999px; padding: 6px 12px;
          box-shadow: var(--shadow-card); font-family: var(--font-mono);
        }
        .speed-control button { all: unset; cursor: pointer; font-size: 1.1rem; color: var(--ink); padding: 0 4px; }
        .speed-val { min-width: 40px; text-align: center; font-weight: 600; }

        .room-grid {
          display: grid;
          grid-template-columns: 150px 1fr 240px;
          gap: 18px;
        }
        .teacher-col {
          padding: 18px 12px; text-align: center; height: fit-content;
        }
        .avatar { font-size: 2.4rem; display: inline-block; transition: transform 0.15s ease; }
        .avatar.talking { animation: talk-bounce 0.5s ease-in-out infinite; }
        @keyframes talk-bounce {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.12); }
        }
        .teacher-name { font-weight: 700; color: var(--ink); margin: 6px 0 10px; }
        .status-pill {
          font-size: 0.72rem; font-weight: 600; padding: 4px 8px; border-radius: 999px;
          background: var(--paper-alt); color: var(--graphite-soft); margin: 0;
        }
        .status-speaking { background: #e4f0e6; color: var(--green-check); }
        .status-asking, .status-paused { background: #fbe9d9; color: #a3611c; }
        .status-answered { background: #e4f0e6; color: var(--green-check); }
        .voice-off-note { font-size: 0.68rem; color: var(--pen-red); margin: 8px 0 0; }

        .board {
          background: #1f3a2c;
          aspect-ratio: 16/8;
          padding: 18px;
          display: flex; align-items: center; justify-content: center;
        }
        .caption-bar {
          margin-top: 12px; padding: 16px 18px;
          display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
        }
        .caption { margin: 0; line-height: 1.55; color: var(--graphite); }
        .replay-btn {
          all: unset; cursor: pointer; flex-shrink: 0; font-size: 0.78rem;
          color: var(--ink-soft); font-weight: 600; white-space: nowrap;
        }

        .doubt-panel { margin-top: 12px; padding: 16px 18px; border-color: var(--margin-line); }
        .doubt-input-row { display: flex; gap: 8px; align-items: flex-start; }
        .doubt-form textarea {
          flex: 1; font-family: var(--font-body); font-size: 0.9rem;
          border: 1px solid var(--rule-line); border-radius: 8px; padding: 8px 10px;
          resize: vertical;
        }
        .mic-btn {
          all: unset; cursor: pointer; font-size: 1.2rem;
          background: var(--paper-alt); border-radius: 50%; width: 40px; height: 40px;
          display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }
        .mic-btn.listening { background: var(--pen-red); animation: pulse 1s infinite; }
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(183,80,62,0.5); }
          50% { box-shadow: 0 0 0 8px rgba(183,80,62,0); }
        }
        .listening-hint { font-size: 0.75rem; color: var(--pen-red-dark); margin: 6px 0 0; }
        .doubt-form-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
        .ghost-btn {
          all: unset; cursor: pointer; font-size: 0.8rem; color: var(--graphite-soft);
          padding: 8px 10px;
        }
        .doubt-q { font-weight: 600; color: var(--ink); margin: 0 0 6px; }
        .doubt-a { margin: 0 0 12px; line-height: 1.5; }
        .speaking-dot { margin-right: 6px; }

        .controls { margin-top: 14px; display: flex; gap: 10px; flex-wrap: wrap; }
        .pause-btn, .resume-btn, .hand-btn {
          all: unset; cursor: pointer; padding: 10px 18px; border-radius: 999px;
          font-weight: 700; font-size: 0.9rem;
        }
        .pause-btn { background: var(--ink); color: #fff; }
        .resume-btn { background: var(--green-check); color: #fff; }
        .hand-btn { background: var(--pen-red); color: #fff; }

        .cta-btn {
          all: unset; cursor: pointer; background: var(--ink); color: #fff;
          padding: 9px 14px; border-radius: 8px; font-size: 0.85rem; font-weight: 600;
        }
        .cta-btn:disabled { opacity: 0.6; cursor: default; }

        .notes-col { padding: 16px 14px; height: fit-content; }
        .notes-list { margin: 0; padding-left: 18px; font-size: 0.78rem; line-height: 1.5; }
        .notes-list li { margin-bottom: 10px; color: var(--graphite-soft); }
        .notes-list li.active { color: var(--ink); font-weight: 700; }
        .notes-list li.done { color: var(--green-check); }
        .doubt-history { list-style: none; margin: 0; padding: 0; font-size: 0.78rem; }
        .doubt-history li { margin-bottom: 8px; color: var(--graphite-soft); }

        @media (max-width: 900px) {
          .room-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}

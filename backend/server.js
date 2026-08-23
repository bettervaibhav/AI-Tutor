import "dotenv/config";
import express from "express";
import cors from "cors";
import Anthropic from "@anthropic-ai/sdk";
import { user, subjects, studyMaterial, fallbackLectures, answerFallbackDoubt } from "./data.js";

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 4000;
const HAS_AI_KEY = !!process.env.ANTHROPIC_API_KEY;
const anthropic = HAS_AI_KEY
  ? new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  : null;
const MODEL = "claude-sonnet-4-6";

// ---------- Dashboard ----------

app.get("/api/dashboard", (req, res) => {
  res.json({ user, subjects, studyMaterial });
});

// Lets the frontend know whether real AI is configured, so it can show
// a clear "demo mode" note instead of silently giving canned answers.
app.get("/api/status", (req, res) => {
  res.json({ aiEnabled: HAS_AI_KEY });
});

// ---------- Profile ----------

app.get("/api/user", (req, res) => {
  res.json(user);
});

app.patch("/api/user", (req, res) => {
  const { name } = req.body;
  if (typeof name === "string" && name.trim()) {
    user.name = name.trim();
  }
  res.json(user);
});

// ---------- AI Tutor: start a lecture ----------
// Body: { subjectId, topic }
// Returns: { topic, segments: [{ text, visual }] }

app.post("/api/tutor/start", async (req, res) => {
  const { subjectId, topic } = req.body;
  const subject = subjects.find((s) => s.id === subjectId);
  const subjectLabel = subject ? subject.fullName : subjectId || "General";
  const lectureTopic = topic || subject?.runningChapter || "today's chapter";

  if (!HAS_AI_KEY) {
    const canned = fallbackLectures[subjectId] || fallbackLectures.default;
    return res.json(canned);
  }

  try {
    const prompt = `You are a warm, clear AI tutor teaching a live one-on-one class on "${lectureTopic}" (subject: ${subjectLabel}) to a school/college student.

Break your lecture into 4 to 6 short segments, each 2-3 sentences, building the idea up gradually like a real teacher speaking out loud (not a textbook).

For EACH segment also pick ONE visual keyword from this fixed list that best matches what's being explained: "vectors-2d", "right-hand-rule", "magnitude-formula", "applications", "graph", "diagram", "timeline", "molecule", "circuit".

Respond ONLY with valid JSON, no markdown fences, no preamble, in exactly this shape:
{"topic": "short topic title", "segments": [{"text": "...", "visual": "..."}]}`;

    const response = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 1200,
      messages: [{ role: "user", content: prompt }],
    });

    const raw = response.content
      .map((block) => (block.type === "text" ? block.text : ""))
      .join("")
      .trim()
      .replace(/^```json\s*|```$/g, "");

    const parsed = JSON.parse(raw);
    res.json(parsed);
  } catch (err) {
    console.error("tutor/start failed, falling back:", err.message);
    const canned = fallbackLectures[subjectId] || fallbackLectures.default;
    res.json(canned);
  }
});

// ---------- AI Tutor: student raises a doubt mid-lecture ----------
// Body: { subjectId, topic, segmentText, question }
// Returns: { answer }

app.post("/api/tutor/doubt", async (req, res) => {
  const { subjectId, topic, segmentText, question } = req.body;

  if (!question || !question.trim()) {
    return res.status(400).json({ error: "Question is required." });
  }

  if (!HAS_AI_KEY) {
    return res.json({ answer: answerFallbackDoubt(question), demo: true });
  }

  try {
    const prompt = `You are a patient AI tutor in the middle of live-teaching "${topic}". You just said this to the student:

"${segmentText}"

The student paused you and asked this doubt: "${question}"

Answer ONLY the doubt, directly and clearly, in 2-4 sentences, in a warm spoken-teacher tone. Do not repeat the whole lecture. End by briefly saying you'll continue the lecture now. Respond with plain text only, no JSON.`;

    const response = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 400,
      messages: [{ role: "user", content: prompt }],
    });

    const answer = response.content
      .map((block) => (block.type === "text" ? block.text : ""))
      .join("")
      .trim();

    res.json({ answer });
  } catch (err) {
    console.error("tutor/doubt failed:", err.message);
    // Fall back to the offline knowledge base rather than a dead end, and
    // include the raw error so it's visible in the browser console for debugging.
    res.json({
      answer: answerFallbackDoubt(question),
      demo: true,
      debugError: err.message,
    });
  }
});

app.listen(PORT, () => {
  console.log(`AI Tutor backend running on http://localhost:${PORT}`);
  console.log(
    HAS_AI_KEY
      ? "✓ ANTHROPIC_API_KEY detected — live AI lectures & doubt answers enabled."
      : "⚠ No ANTHROPIC_API_KEY found — running on built-in fallback lectures. See backend/.env.example."
  );
});

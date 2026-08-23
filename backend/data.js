// In-memory "database" so the project runs instantly with zero setup.
// Swap this for a real DB (Mongo/Postgres) later — the route shapes won't change.

export const user = {
  name: "Aditi",
  registered: true,
  streakDays: 11,
  todaysProgressPct: 62,
};

export const subjects = [
  {
    id: "sub-a",
    name: "Sub-A",
    fullName: "Physics — Mechanics",
    color: "#2B6CB0",
    progressPct: 78,
    runningChapter: "Ch. 6 — Rotational Motion",
    totalChapters: 12,
    completedChapters: 9,
  },
  {
    id: "sub-b",
    name: "Sub-B",
    fullName: "Chemistry — Organic",
    color: "#B7503E",
    progressPct: 41,
    runningChapter: "Ch. 3 — Alkyl Halides",
    totalChapters: 10,
    completedChapters: 4,
  },
  {
    id: "sub-c",
    name: "Sub-C",
    fullName: "Mathematics — Vectors",
    color: "#3E7A4C",
    progressPct: 55,
    runningChapter: "Ch. 4 — Cross Product",
    totalChapters: 9,
    completedChapters: 5,
  },
];

export const studyMaterial = [
  { id: "book-a", type: "book", title: "Book-A", subtitle: "NCERT Physics Vol. 1" },
  { id: "material-1", type: "notes", title: "Material", subtitle: "My notes from AI Tutor sessions" },
];

// Small hand-written doubt-answer knowledge base, used only when no
// ANTHROPIC_API_KEY is configured. Matches keywords in the student's
// question so the "offline demo mode" still gives a real, specific answer
// instead of just repeating the question back at them.
export const fallbackDoubtBank = [
  {
    keywords: ["perpendicular", "why perpendicular", "direction"],
    answer:
      "Good question — the cross product is defined that way on purpose. Multiplying two vectors could give infinitely many possible 'combined' vectors, so mathematicians picked the one perpendicular to both, because that's the direction that shows up naturally in rotation, torque, and magnetic force. It's a choice that turned out to be extremely useful, not a coincidence.",
  },
  {
    keywords: ["right hand rule", "right-hand", "thumb", "curl"],
    answer:
      "The right-hand rule is just a memory trick for the direction. Point your fingers along the first vector, curl them toward the second vector — the short way — and your thumb points along the cross product. If you used your left hand you'd get the opposite direction, which is why the rule matters: it fixes a consistent convention everyone agrees on.",
  },
  {
    keywords: ["theta", "angle", "sin"],
    answer:
      "Theta is just the angle between the two vectors, measured the short way, always between 0 and 180 degrees. We use sine of that angle because sine is largest when the vectors are perpendicular (most 'spread apart') and zero when they're parallel — which matches the idea that parallel vectors don't really combine into a new direction.",
  },
  {
    keywords: ["zero", "parallel", "same direction"],
    answer:
      "When two vectors are parallel, the angle between them is 0 degrees, and sin(0) is 0 — so the whole cross product becomes zero. Physically that makes sense too: there's no 'twisting' effect between two vectors pointing the same way, so there's nothing for the cross product to capture.",
  },
  {
    keywords: ["magnitude", "how big", "length"],
    answer:
      "The magnitude of the cross product tells you the area of the parallelogram formed by the two vectors. So |A × B| = |A||B|sin(theta) isn't an arbitrary formula — it's literally base times height of that parallelogram, which is a nice geometric way to picture it.",
  },
  {
    keywords: ["torque", "force", "physics"],
    answer:
      "Torque uses the cross product because turning force depends on both how hard you push and how far from the pivot you push, at what angle. Torque = r × F captures exactly that: the perpendicular 'twisting' direction, scaled by how effectively the force is angled to cause rotation.",
  },
  {
    keywords: ["difference", "dot product", "scalar"],
    answer:
      "The dot product and cross product answer different questions. The dot product (A·B) tells you how much two vectors point in the same direction and gives you a plain number. The cross product tells you the perpendicular direction they define together and gives you a whole new vector. Use dot product for 'how aligned', cross product for 'what new direction'.",
  },
];

export function answerFallbackDoubt(question) {
  const q = question.toLowerCase();
  const hit = fallbackDoubtBank.find((entry) =>
    entry.keywords.some((k) => q.includes(k))
  );
  if (hit) return hit.answer;

  return "That's a fair question to pause on. Since this demo is running without a live AI key right now, try breaking it into a smaller piece: which exact word or step in what I just said felt unclear? Re-read that one line slowly and picture the sketch on the board — often the confusion clears up once you isolate the single step. Add your ANTHROPIC_API_KEY in backend/.env any time for full, tailored AI answers to any question.";
}

// Very small canned "lecture scripts" used when no ANTHROPIC_API_KEY is set,
// so the demo still works fully offline (great for a hackathon judging room
// with flaky wifi).
export const fallbackLectures = {
  "sub-c": {
    topic: "Cross Product of Two Vectors",
    segments: [
      {
        text: "Let's talk about the cross product. Given two vectors A and B in 3D space, their cross product A x B gives us a brand new vector — not a number.",
        visual: "vectors-2d",
      },
      {
        text: "The direction of this new vector is perpendicular to both A and B. We find it using the right-hand rule: point your fingers along A, curl them toward B, and your thumb points along A x B.",
        visual: "right-hand-rule",
      },
      {
        text: "The magnitude of A x B equals |A| times |B| times sin(theta), where theta is the angle between them. So if A and B are parallel, the cross product is zero.",
        visual: "magnitude-formula",
      },
      {
        text: "This is why cross products are everywhere in physics — torque, angular momentum, and magnetic force all use this exact idea of a 'perpendicular effect'.",
        visual: "applications",
      },
    ],
  },
  default: {
    topic: "Introduction",
    segments: [
      {
        text: "Welcome! I'm your AI tutor. Today we'll build this topic up from first principles, one small idea at a time.",
        visual: "vectors-2d",
      },
      {
        text: "Here's the core idea we're working toward — keep this picture in your head as we go.",
        visual: "magnitude-formula",
      },
      {
        text: "Now let's see why this actually matters, with a real example.",
        visual: "applications",
      },
    ],
  },
};

const BASE = "/api";

export async function getDashboard() {
  const res = await fetch(`${BASE}/dashboard`);
  if (!res.ok) throw new Error("Failed to load dashboard");
  return res.json();
}

export async function startLecture(subjectId, topic) {
  const res = await fetch(`${BASE}/tutor/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subjectId, topic }),
  });
  if (!res.ok) throw new Error("Failed to start lecture");
  return res.json();
}

export async function askDoubt({ subjectId, topic, segmentText, question }) {
  const res = await fetch(`${BASE}/tutor/doubt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subjectId, topic, segmentText, question }),
  });
  if (!res.ok) throw new Error("Failed to get doubt answer");
  return res.json();
}

export async function getStatus() {
  const res = await fetch(`${BASE}/status`);
  if (!res.ok) throw new Error("Failed to load status");
  return res.json();
}

export async function getUser() {
  const res = await fetch(`${BASE}/user`);
  if (!res.ok) throw new Error("Failed to load user");
  return res.json();
}

export async function updateUser(patch) {
  const res = await fetch(`${BASE}/user`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error("Failed to update user");
  return res.json();
}

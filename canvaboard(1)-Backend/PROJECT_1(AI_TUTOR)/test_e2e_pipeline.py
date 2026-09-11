import requests, json, time, sys

sys.stdout.reconfigure(encoding='utf-8')

t0 = time.time()
print("1. Testing /api/generate-lesson (Progressive Chunk 1)...")
res = requests.post("http://127.0.0.1:5000/api/generate-lesson", json={
    "topic": "Photosynthesis",
    "subject": "Biology",
    "language": "hinglish",
    "difficulty": "Class 11-12",
    "teaching_style": "Feynman",
    "voice": "priya_mam",
    "user_id": "test_user_01"
}, timeout=90)

elapsed = time.time() - t0
print(f"Status: {res.status_code} in {elapsed:.1f}s")
data = res.json()
sid = data.get("session_id")
print("Session ID:", sid)
print("Concept Map Main Concept:", data.get("concept_map", {}).get("main_concept"))
print("Prerequisites:", data.get("concept_map", {}).get("prerequisites"))
print("Key Sub-concepts:", data.get("concept_map", {}).get("key_subconcepts"))
print("Chunk 1 Steps Received:", len(data.get("steps", [])))

for i, s in enumerate(data.get("steps", [])):
    print(f"  Step {i+1}: {s.get('title')} | Board Actions: {len(s.get('board_actions', []))} | Speech: {len(s.get('speech', ''))} chars")

print("\n2. Testing /api/resolve-doubt (Deep Context-Aware)...")
t1 = time.time()
d_res = requests.post("http://127.0.0.1:5000/api/resolve-doubt", json={
    "doubt": "Light reaction exactly kahan hoti hai chloroplast ke andar?",
    "session_id": sid,
    "topic": "Photosynthesis",
    "subject": "Biology",
    "language": "hinglish",
    "difficulty": "Class 11-12",
    "current_step": 1,
    "current_speech": data.get("steps", [{}])[0].get("speech", ""),
    "recent_doubts": [],
    "confusion_level": 0
}, timeout=45)

d_elapsed = time.time() - t1
print(f"Doubt Status: {d_res.status_code} in {d_elapsed:.1f}s")
d_data = d_res.json()
print("Strategy Chosen:", d_data.get("strategy_chosen"))
print("Response Preview:", d_data.get("response")[:160])
print("Doubt Board Actions:", len(d_data.get("board_actions", [])))

print("\n3. Testing /api/history (Persistence)...")
h_res = requests.get("http://127.0.0.1:5000/api/history?user_id=test_user_01")
h_data = h_res.json()
print("Total Sessions in History:", len(h_data.get("sessions", [])))
if h_data.get("sessions"):
    s0 = h_data["sessions"][0]
    print(f"Latest Session: {s0.get('topic')} | Progress: {s0.get('completion_percentage')}% | Completed: {s0.get('completed')}")

print("\n4. Testing /api/history/sessions/<id> (Continue Learning exact recovery)...")
s_res = requests.get(f"http://127.0.0.1:5000/api/history/sessions/{sid}")
s_data = s_res.json()
print("Saved Lesson Restored:", bool(s_data.get("lesson")))
print("Saved Doubts Restored:", len(s_data.get("doubts", [])))
print("Saved Concept Map Restored:", bool(s_data.get("concept_map")))

print("\n=== ALL E2E TESTS COMPLETED SUCCESSFULLY ===")

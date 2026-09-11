"""
tutor_script_generator.py — AI Tutor Deep Teaching Engine & Flask REST API
============================================================================
Architecture:
  Phase 1 → Curriculum Planner: builds concept map for any topic
  Phase 2 → Progressive Lesson: generates step 1-2 immediately, rest in background
  Phase 3 → Deep Doubt Resolver: context-aware, prerequisite-detecting, strategy-switching

Key features:
  - Concept map (prerequisites, sub-concepts, misconceptions, teaching order)
  - Progressive generation (student hears step 1 while steps 3-N generate in background)
  - Deep doubt resolution (detects prerequisites, changes strategy, never repeats same answer)
  - Model routing (complex tasks → lesson model, simple → fast model)
  - Persistent history via SQLite (history_service)
  - Real API diagnostics (diagnostics_service)
  - Sarvam TTS/STT integration with proper Hinglish support
"""

import os
import re
import json
import sys
import requests
import threading
import time

_AI_LIBS_PATH = r"C:\ai_libs"
if _AI_LIBS_PATH not in sys.path:
    sys.path.insert(0, _AI_LIBS_PATH)

try:
    from dotenv import load_dotenv
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _parent_dir = os.path.dirname(_script_dir)
    load_dotenv(os.path.join(_parent_dir, ".env"), override=True)
    load_dotenv(os.path.join(_script_dir, ".env"), override=True)
    load_dotenv(override=True)
except ImportError:
    pass

try:
    from mistralai import Mistral
except (ImportError, Exception):
    try:
        from mistralai.client import Mistral
    except (ImportError, Exception):
        Mistral = None

from tts_service import generate_speech, get_available_voices
from stt_service import transcribe_audio
from history_service import (
    create_session, update_session, save_lesson_content,
    update_lesson_content, save_doubt, get_session, get_concept_map,
    list_sessions, delete_session
)
from diagnostics_service import run_full_diagnostics

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
MISTRAL_API_KEY      = os.environ.get("MISTRAL_API_KEY", "")
SERPAPI_KEY          = os.environ.get("SERPAPI_KEY", "")
MISTRAL_LESSON_MODEL = os.environ.get("MISTRAL_LESSON_MODEL", "mistral-small-latest")
MISTRAL_FAST_MODEL   = os.environ.get("MISTRAL_FAST_MODEL", "mistral-small-latest")

# In-memory store for partial lesson prefetch sessions
_prefetch_store: dict[str, dict] = {}
_prefetch_lock = threading.Lock()


def get_mistral_client():
    if Mistral is None:
        raise ImportError("mistralai not installed. Run: pip install mistralai")
    key = os.environ.get("MISTRAL_API_KEY", "") or MISTRAL_API_KEY
    if not key:
        raise RuntimeError("MISTRAL_API_KEY not set in .env")
    return Mistral(api_key=key)


def call_mistral_chat(messages: list, model: str = None, response_format: dict = None) -> str:
    """Robust Mistral Chat Completion with direct REST API fallback on network issues."""
    key = os.environ.get("MISTRAL_API_KEY", "") or MISTRAL_API_KEY
    if not key:
        raise RuntimeError("MISTRAL_API_KEY not set in .env")
    model = model or MISTRAL_LESSON_MODEL

    # 1. Try via official Mistral SDK
    if Mistral is not None:
        try:
            client = Mistral(api_key=key)
            kwargs = {"model": model, "messages": messages}
            if response_format:
                kwargs["response_format"] = response_format
            resp = client.chat.complete(**kwargs)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Warning] Mistral SDK chat error ({e}), trying direct REST API...")

    # 2. REST API fallback with retries
    payload = {"model": model, "messages": messages}
    if response_format:
        payload["response_format"] = response_format

    for attempt in range(3):
        try:
            resp = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as err:
            if attempt == 2:
                raise err
            time.sleep(1.5)


# ─────────────────────────────────────────────
# WEB SEARCH (SerpAPI grounding)
# ─────────────────────────────────────────────
_SERPAPI_DISABLED = False

def search_educational_images(query: str, num: int = 4) -> list[dict]:
    global _SERPAPI_DISABLED
    if _SERPAPI_DISABLED:
        return []
    key = os.environ.get("SERPAPI_KEY", "") or SERPAPI_KEY
    if not key:
        return []
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={"q": f"{query} educational diagram scientific", "tbm": "isch",
                    "num": num, "safe": "active", "api_key": key},
            timeout=4,
        )
        if resp.status_code == 401:
            _SERPAPI_DISABLED = True
            return []
        resp.raise_for_status()
        images = []
        for item in resp.json().get("images_results", [])[:num]:
            url = item.get("original") or item.get("thumbnail")
            if url and url.startswith("http"):
                images.append({"url": url, "title": item.get("title", query),
                                "source": item.get("source", "")})
        return images
    except Exception as e:
        print(f"[Warning] Image search failed: {e}")
        return []


def search_web(query: str, num_results: int = 4) -> list[dict]:
    global _SERPAPI_DISABLED
    if _SERPAPI_DISABLED:
        return []
    key = os.environ.get("SERPAPI_KEY", "") or SERPAPI_KEY
    if not key:
        return []
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={"q": query, "num": num_results, "api_key": key},
            timeout=4,
        )
        if resp.status_code == 401:
            _SERPAPI_DISABLED = True
            return []
        resp.raise_for_status()
        return [
            {"title": i.get("title", ""), "snippet": i.get("snippet", ""), "link": i.get("link", "")}
            for i in resp.json().get("organic_results", [])[:num_results]
        ]
    except Exception as e:
        print(f"[Warning] Web search failed: {e}")
        return []



# ─────────────────────────────────────────────
# JSON PARSING
# ─────────────────────────────────────────────
def _clean_and_parse_json(raw_text: str) -> dict:
    text = raw_text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if m:
            text = m.group(1).strip()
        else:
            text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
        raise


# ─────────────────────────────────────────────
# PHASE 1 — CURRICULUM PLANNER
# ─────────────────────────────────────────────
CURRICULUM_PLANNER_PROMPT = """You are an expert educator and curriculum designer.
Your job is to build an INTERNAL CONCEPT MAP for the AI teacher — NOT for the student.
This map is the teacher's private reference sheet.

For the given topic, identify:
1. prerequisites — what the student MUST know first
2. main_concept — the core idea in one sentence
3. sub_concepts — ordered list of concepts to teach (in teaching order)
4. related_concepts — tangentially related ideas the teacher may reference
5. common_misconceptions — typical student errors to address proactively
6. likely_difficulties — where students usually get confused
7. examples — 2-3 concrete real-world or exam examples
8. exam_perspective — what exams test about this topic
9. teaching_progression — ordered list of what to teach FIRST to LAST (like chapters in a book)
10. depth_guide — for each sub_concept, the appropriate explanation depth (1=simple, 7=advanced)

Return ONLY valid JSON:
{
  "topic": "...",
  "main_concept": "...",
  "prerequisites": ["concept1", "concept2"],
  "sub_concepts": [
    {"name": "...", "description": "...", "order": 1, "depth": 3}
  ],
  "related_concepts": ["concept1", "concept2"],
  "common_misconceptions": ["misconception1", "misconception2"],
  "likely_difficulties": ["difficulty1", "difficulty2"],
  "examples": ["example1", "example2", "example3"],
  "exam_perspective": "...",
  "teaching_progression": ["step1", "step2", "step3", "step4", "step5"]
}"""


def generate_concept_map(topic: str, subject: str = "General",
                          language: str = "hinglish") -> dict:
    """Phase 1: Build the internal curriculum map for the topic."""
    client = get_mistral_client()

    # Lightweight web grounding for the concept map
    grounding = search_web(f"{topic} {subject} core concepts prerequisites", num_results=3)
    grounding_text = "\n".join(
        f"- {g['title']}: {g['snippet']}" for g in grounding
    ) or "(Use accurate domain knowledge)"

    try:
        content = call_mistral_chat(
            messages=[
                {"role": "system", "content": CURRICULUM_PLANNER_PROMPT},
                {"role": "user", "content":
                    f"Topic: {topic}\nSubject: {subject}\nLanguage context: {language}\n"
                    f"Web grounding:\n{grounding_text}\n\n"
                    f"Build the complete concept map. Return only JSON."}
            ],
            model=MISTRAL_LESSON_MODEL,
            response_format={"type": "json_object"},
        )
        return _clean_and_parse_json(content)
    except Exception as exc:
        print(f"[Warning] Concept map generation failed: {exc}")
        # Minimal fallback concept map
        return {
            "topic": topic,
            "main_concept": f"Understanding {topic} from first principles",
            "prerequisites": [],
            "sub_concepts": [{"name": topic, "description": "Core concept", "order": 1, "depth": 3}],
            "related_concepts": [],
            "common_misconceptions": [],
            "likely_difficulties": [],
            "examples": [],
            "exam_perspective": f"Examine {topic} conceptually and mathematically",
            "teaching_progression": [topic],
        }


# ─────────────────────────────────────────────
# PHASE 2 — DEEP LESSON GENERATOR
# ─────────────────────────────────────────────
DEEP_LESSON_SYSTEM_PROMPT = """You are an expert, passionate AI Teacher teaching a live blackboard lecture to an Indian student.

You have been given an INTERNAL CONCEPT MAP. Use it as your teaching plan.

TEACHING PHILOSOPHY:
1. Teach like a knowledgeable human teacher — understand the FULL concept tree, then decide what the student needs NOW.
2. Language: Natural Hinglish. Code-switch authentically: "Ab is formula ko board pe likhte hain", "Ye step thoda important hai, kyunki yahi se hume recurrence milti hai."
3. Depth over breadth: Cover fewer concepts deeply rather than many superficially.
4. Each step must have a clear teaching_intent: introduce / build_intuition / derive / demonstrate / connect / check / summarize.
5. BOARD WRITING: A real teacher NEVER writes full paragraphs on the board. Write ONLY:
   - Key terms, headings, labels
   - Short equations with variables labeled
   - Arrow diagrams showing flow/causality
   - Step-by-step numbered derivations
   - Concept maps with nodes
   - Examples in structured form
6. Generate 5-7 focused steps based on concept complexity.
7. Every step should feel like a different moment in a real classroom lecture.
8. Include at least one analogy, one worked example, and one checking question across all steps.
9. Prerequisite teaching: If a prerequisite is needed, first explain it BRIEFLY with its own board action (labeled "Prerequisite: "), then connect it to the main topic.

BOARD ACTIONS:
- action: WRITE_HEADING | WRITE_TEXT | WRITE_EQUATION | DRAW_ARROW | DRAW_LINE | DRAW_CIRCLE | DRAW_RECTANGLE | DRAW_AXIS | DRAW_GRAPH | DRAW_DIAGRAM | UNDERLINE | HIGHLIGHT | SHOW_IMAGE | CLEAR_SECTION | CLEAR_ALL
- content: Text or description
- x, y: 0-100 coordinate on board (percentage)
- zone: "heading" | "main" | "diagram" | "equation" (helps layout manager)
- chalk_color: "white" | "yellow" | "cyan" | "green" | "pink" | "orange"
- timing_ratio: 0.0 to 1.0 (when during speech this action starts)
- duration: seconds to draw (0.4 to 2.0)
- from, to: [x, y] for arrows/lines
- radius: for circles
- width, height: for rectangles/diagrams/axes
- graph_type: "parabola" | "sine" | "exponential" | "linear" | "bar"

ZONE GUIDELINES (use these x,y ranges):
- heading zone: y=5-14, x=5-95 (topic title, step titles)
- main zone: x=5-55, y=16-74 (main explanation, derivation steps)
- diagram zone: x=58-95, y=16-74 (diagrams, graphs, visuals)
- equation zone: x=5-95, y=76-86 (key formulas, results)
- (doubt_zone y=88-99 is reserved for doubts — do NOT use in lessons)

Return ONLY valid JSON:
{
  "topic": "string",
  "subject": "string",
  "language": "hinglish",
  "difficulty": "Class 10",
  "teaching_style": "Feynman",
  "overview": "2-sentence summary of this lesson",
  "key_terms": ["Term1", "Term2"],
  "concept_progression": ["concept1", "concept2"],
  "image_queries": ["search query1"],
  "steps": [
    {
      "id": 1,
      "teaching_intent": "introduce_concept",
      "concept_covered": "...",
      "speech": "Natural Hinglish teacher speech — rich, warm, pedagogically deep...",
      "board_actions": [
        {
          "action": "WRITE_HEADING",
          "content": "TOPIC NAME",
          "x": 50, "y": 8,
          "zone": "heading",
          "chalk_color": "yellow",
          "timing_ratio": 0.05,
          "duration": 1.2
        }
      ],
      "check_question": null
    }
  ]
}"""


def _build_lesson_user_prompt(topic: str, subject: str, language: str,
                               difficulty: str, teaching_style: str,
                               concept_map: dict, grounding_text: str,
                               step_range: tuple = None) -> str:
    concept_map_json = json.dumps(concept_map, indent=2)

    range_instruction = ""
    if step_range:
        start, end = step_range
        range_instruction = (
            f"\n\nIMPORTANT: Generate ONLY steps {start} to {end} of the lesson. "
            f"The first steps have already been sent. These steps should continue smoothly "
            f"from where the earlier steps ended. Do NOT re-introduce the topic."
        )

    return f"""Topic: {topic}
Subject: {subject}
Language: {language}
Difficulty: {difficulty}
Teaching Style: {teaching_style}

INTERNAL CONCEPT MAP (your teaching reference — do NOT dump this to students):
{concept_map_json}

Web grounding facts:
{grounding_text}

Generate a rich, deep blackboard lesson using this concept map as your internal plan.{range_instruction}

Return ONLY valid JSON."""


def _fetch_images_for_lesson(lesson: dict, topic: str, subject: str) -> dict:
    queries = set(lesson.get("image_queries", []))
    for step in lesson.get("steps", []):
        for act in step.get("board_actions", []):
            if act.get("action") == "SHOW_IMAGE":
                queries.add(act.get("content", f"{topic} diagram"))

    cache = {}
    for q in queries:
        results = search_educational_images(q, num=2)
        cache[q] = results[0]["url"] if results else None

    for step in lesson.get("steps", []):
        for act in step.get("board_actions", []):
            if act.get("action") == "SHOW_IMAGE":
                q = act.get("content", "")
                url = cache.get(q)
                if url:
                    act["image_url"] = url
                    act["image_query"] = q
                else:
                    act["action"] = "WRITE_TEXT"
                    act["content"] = f"[{q}]"

    lesson["topic_image_url"] = next(
        (v for v in cache.values() if v), None
    )
    return lesson


def generate_lesson_first_chunk(topic: str, subject: str = "General",
                                 language: str = "hinglish",
                                 difficulty: str = "Class 11-12",
                                 teaching_style: str = "Feynman",
                                 concept_map: dict = None) -> dict:
    """
    Generates ONLY the first 2 steps of the lesson.
    Called after concept_map is ready.
    Frontend starts playing immediately after this returns.
    """
    client = get_mistral_client()

    if concept_map is None:
        concept_map = generate_concept_map(topic, subject, language)

    grounding = search_web(f"{topic} {subject} key concepts explanation", num_results=3)
    grounding_text = "\n".join(
        f"- {g['title']}: {g['snippet']}" for g in grounding
    ) or "(Use domain expertise)"

    user_prompt = _build_lesson_user_prompt(
        topic, subject, language, difficulty, teaching_style,
        concept_map, grounding_text,
        step_range=(1, 2)
    )
    user_prompt += (
        "\n\nFor this initial chunk, generate exactly 2 steps. "
        "Make step 1 an engaging introduction that hooks the student. "
        "Make step 2 build the first key concept. "
        "Include a partial total_steps hint (e.g. 'total_steps': 6) so frontend knows more steps are coming."
    )

    content = call_mistral_chat(
        messages=[
            {"role": "system", "content": DEEP_LESSON_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        model=MISTRAL_LESSON_MODEL,
        response_format={"type": "json_object"},
    )
    chunk = _clean_and_parse_json(content)
    chunk["_partial"] = True
    chunk["_model"] = MISTRAL_LESSON_MODEL
    chunk["concept_map"] = concept_map  # Include for frontend context

    # Fetch images for first chunk
    chunk = _fetch_images_for_lesson(chunk, topic, subject)
    return chunk


def generate_lesson_remaining_steps(topic: str, subject: str, language: str,
                                     difficulty: str, teaching_style: str,
                                     concept_map: dict,
                                     completed_step_count: int = 2) -> list:
    """
    Generates steps 3-N in the background.
    Returns a list of step objects to append to the partial lesson.
    """
    client = get_mistral_client()

    grounding = search_web(f"{topic} {subject} advanced concepts examples", num_results=3)
    grounding_text = "\n".join(
        f"- {g['title']}: {g['snippet']}" for g in grounding
    ) or "(Use domain expertise)"

    user_prompt = _build_lesson_user_prompt(
        topic, subject, language, difficulty, teaching_style,
        concept_map, grounding_text,
        step_range=(completed_step_count + 1, completed_step_count + 5)
    )
    user_prompt += (
        f"\n\nGenerate steps {completed_step_count+1} to {completed_step_count+5}. "
        "These are the remaining steps of the lesson. "
        "Include derivation, examples, common mistakes, and a final summary/check question. "
        "The lesson should feel complete after these steps."
    )

    content = call_mistral_chat(
        messages=[
            {"role": "system", "content": DEEP_LESSON_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        model=MISTRAL_LESSON_MODEL,
        response_format={"type": "json_object"},
    )
    data = _clean_and_parse_json(content)
    steps = data.get("steps", [])

    # Re-number steps to continue from completed_step_count
    for i, step in enumerate(steps):
        step["id"] = completed_step_count + 1 + i

    return steps


# ─────────────────────────────────────────────
# PHASE 3 — DEEP DOUBT RESOLVER
# ─────────────────────────────────────────────
DEEP_DOUBT_SYSTEM_PROMPT = """You are an expert, deeply knowledgeable AI Teacher answering a student's live doubt during a blackboard lecture.

TEACHING PHILOSOPHY FOR DOUBTS:
1. First determine: What does the student ACTUALLY need to understand?
2. Check: Is a prerequisite concept missing? If yes, explain it briefly FIRST, then connect to the main question.
3. Choose the right explanation strategy based on the doubt:
   - "samajh nahi aaya" / repeated confusion → CHANGE STRATEGY (never repeat same explanation)
   - Simple factual doubt → concise, precise answer
   - Conceptual gap → analogy + visual board explanation
   - Formula/derivation doubt → step-by-step board derivation
   - "Why?" question → intuition + first principles
   - "Give example" → concrete worked example on board
4. Never artificially limit response length. Be as deep as the doubt requires.
5. However, deep ≠ long. Deep = correct + appropriately detailed + connected + useful.
6. After answering, always briefly acknowledge where in the lesson this connects: "Toh wapas lesson pe aate hain..."
7. Write board actions ONLY in the doubt_zone (y: 88-99). NEVER overwrite lesson content.

BOARD ACTIONS FOR DOUBTS:
- ALL board actions MUST have zone: "doubt_zone"
- Use x: 5-95, y: 89-98 for all doubt board elements
- Create a labeled section: First write "DOUBT:" header in pink at y:89
- Then write explanation below it (y: 92-98)
- If more space needed, use abbreviated key points only

RESPONSE JSON:
{
  "prerequisite_needed": true/false,
  "prerequisite_concept": "name if needed, else null",
  "prerequisite_brief": "1-2 sentence prerequisite explanation if needed",
  "explanation_depth": 3,
  "strategy": "analogy | visual | step_by_step | prerequisite_first | simple_example | first_principles",
  "response": "Full Hinglish teacher response — as deep as needed for this doubt",
  "board_actions": [
    {
      "action": "WRITE_TEXT",
      "content": "DOUBT ANSWER",
      "x": 50, "y": 89,
      "zone": "doubt_zone",
      "chalk_color": "pink",
      "timing_ratio": 0.1,
      "duration": 0.8
    }
  ],
  "board_clears_lesson": false,
  "follow_up": "Gentle check question to ensure understanding",
  "should_resume_lesson": true,
  "resume_hint": "Toh wapas aate hain humari main explanation pe..."
}"""


def _classify_doubt_complexity(doubt: str, recent_doubts: list) -> str:
    """Simple heuristic to route to fast vs lesson model."""
    doubt_lower = doubt.lower()

    # Confusion indicators → need stronger model
    confusion_words = ["samajh nahi", "confused", "don't understand", "kya matlab",
                       "explain", "why", "kyun", "derivation", "prove", "example dena"]
    is_complex = any(w in doubt_lower for w in confusion_words) or len(doubt) > 60

    # Repeated confusion in recent doubts → definitely needs more power
    if recent_doubts and len(recent_doubts) >= 2:
        is_complex = True

    return MISTRAL_LESSON_MODEL if is_complex else MISTRAL_FAST_MODEL


def generate_doubt_answer(doubt: str, topic: str = "", subject: str = "",
                           language: str = "hinglish", difficulty: str = "Class 11-12",
                           current_step: int = 1, current_speech: str = "",
                           board_state: str = "", recent_doubts: list = None,
                           strategy: str = "auto", concept_map: dict = None,
                           completed_concepts: list = None,
                           confusion_level: int = 0) -> dict:
    client = get_mistral_client()
    recent_doubts = recent_doubts or []
    completed_concepts = completed_concepts or []

    # Route to appropriate model based on complexity
    model = _classify_doubt_complexity(doubt, recent_doubts)

    # Build rich context for the teacher
    concept_map_summary = ""
    if concept_map:
        concept_map_summary = f"""
Lesson Concept Map (teacher's reference):
- Main concept: {concept_map.get('main_concept', topic)}
- Teaching progression: {', '.join(concept_map.get('teaching_progression', [])[:6])}
- Common misconceptions: {', '.join(concept_map.get('common_misconceptions', [])[:3])}
- Likely difficulties: {', '.join(concept_map.get('likely_difficulties', [])[:3])}
- Prerequisites: {', '.join(concept_map.get('prerequisites', [])[:4])}"""

    recent_doubts_str = json.dumps(recent_doubts[-5:]) if recent_doubts else "[]"
    completed_str = ", ".join(completed_concepts[-6:]) if completed_concepts else "none yet"

    # Detect if student is expressing repeated confusion
    confusion_hint = ""
    if confusion_level > 1 or any(
        w in doubt.lower() for w in ["samajh nahi aaya", "phir se", "again", "still confused"]
    ):
        confusion_hint = "\nNOTE: Student is expressing repeated confusion. CHANGE EXPLANATION STRATEGY — do NOT repeat the same explanation."

    user_msg = f"""Topic: {topic} | Subject: {subject} | Language: {language} | Difficulty: {difficulty}
Current Lesson Step: #{current_step}
Teacher was explaining: "{current_speech[:200]}"
Concepts already covered: {completed_str}
Board currently shows: "{board_state[:150]}"
{concept_map_summary}

Student's Recent Doubts: {recent_doubts_str}
Student Confusion Level: {confusion_level}/5
Forced Strategy Override: {strategy}{confusion_hint}

Student's Doubt: "{doubt}"

Respond as a deeply knowledgeable teacher. Detect if a prerequisite is missing.
Write board actions ONLY in doubt_zone (y: 89-98). Do NOT overwrite lesson content."""

    try:
        content = call_mistral_chat(
            messages=[
                {"role": "system", "content": DEEP_DOUBT_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            response_format={"type": "json_object"},
        )
        ans = _clean_and_parse_json(content)
        ans["_model"] = model

        # Ensure all board actions have zone: "doubt_zone" and y >= 88
        for act in ans.get("board_actions", []):
            act["zone"] = "doubt_zone"
            if isinstance(act.get("y"), (int, float)):
                act["y"] = max(88, act["y"])

        return ans
    except Exception as exc:
        print(f"[Error] Doubt resolution failed: {exc}")
        raise


# ─────────────────────────────────────────────
# IMAGE FETCHING
# ─────────────────────────────────────────────
def _fetch_real_images_for_lesson(lesson: dict, topic: str, subject: str) -> dict:
    return _fetch_images_for_lesson(lesson, topic, subject)


# ─────────────────────────────────────────────
# FLASK REST API
# ─────────────────────────────────────────────
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Health Check (basic, fast) ──────────────────────────
    @app.route("/api/health", methods=["GET"])
    def health():
        has_mistral = bool(os.environ.get("MISTRAL_API_KEY", "") or MISTRAL_API_KEY)
        has_sarvam  = bool(os.environ.get("SARVAM_API_KEY", "").strip())
        has_serpapi = bool(os.environ.get("SERPAPI_KEY", "").strip())
        return jsonify({
            "status": "ok",
            "mistral": has_mistral,
            "sarvam": has_sarvam,
            "serpapi": has_serpapi,
            "models": {
                "lesson_model": MISTRAL_LESSON_MODEL,
                "fast_model": MISTRAL_FAST_MODEL,
            },
            "speaker": os.environ.get("SARVAM_DEFAULT_SPEAKER", "meera"),
        })

    # ── Full Real Diagnostics (slow — makes actual API calls) ──
    @app.route("/api/diagnostics", methods=["GET"])
    def diagnostics():
        result = run_full_diagnostics(MISTRAL_LESSON_MODEL, MISTRAL_FAST_MODEL)
        return jsonify(result)

    # ── Voices ──────────────────────────────────────────────
    @app.route("/api/voices", methods=["GET"])
    def voices():
        return jsonify({
            "voices": get_available_voices(),
            "sarvam_available": bool(os.environ.get("SARVAM_API_KEY", "").strip()),
        })

    # ── PROGRESSIVE LESSON GENERATION (Phase 1: concept map + first 2 steps) ──
    @app.route("/api/generate-lesson", methods=["POST"])
    def api_generate_lesson():
        data = request.get_json(silent=True) or {}
        topic  = (data.get("topic") or "").strip()
        if not topic:
            return jsonify({"error": "Topic is required"}), 400

        subject        = data.get("subject", "General")
        language       = data.get("language", "hinglish")
        difficulty     = data.get("difficulty", "Class 11-12")
        teaching_style = data.get("teaching_style", "Feynman")
        voice          = data.get("voice", "prof_aether")
        user_id        = data.get("user_id", "anonymous")

        try:
            # Phase 1: Concept map
            concept_map = generate_concept_map(topic, subject, language)

            # Phase 2: First 2 steps only
            partial_lesson = generate_lesson_first_chunk(
                topic, subject, language, difficulty, teaching_style, concept_map
            )

            # Save to history DB
            session_data = create_session({
                "user_id": user_id,
                "topic": topic,
                "subject": subject,
                "language": language,
                "difficulty": difficulty,
                "teaching_style": teaching_style,
                "voice": voice,
                "total_steps": partial_lesson.get("total_steps") or len(partial_lesson.get("steps", [])),
            })
            session_id = session_data["id"]

            # Save partial lesson to DB
            save_lesson_content(session_id, topic, partial_lesson, concept_map)

            # Cache for background continuation
            with _prefetch_lock:
                _prefetch_store[session_id] = {
                    "topic": topic, "subject": subject, "language": language,
                    "difficulty": difficulty, "teaching_style": teaching_style,
                    "concept_map": concept_map,
                    "completed_steps": len(partial_lesson.get("steps", [])),
                    "status": "partial",
                }

            partial_lesson["session_id"] = session_id
            return jsonify(partial_lesson)

        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        except Exception as exc:
            return jsonify({"error": f"Lesson generation failed: {exc}"}), 500

    # ── BACKGROUND STEP CONTINUATION ─────────────────────────
    @app.route("/api/generate-lesson-continue", methods=["POST"])
    def api_generate_lesson_continue():
        data = request.get_json(silent=True) or {}
        session_id = (data.get("session_id") or "").strip()
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        with _prefetch_lock:
            prefetch = _prefetch_store.get(session_id)

        if not prefetch:
            # Try to load from DB
            db_data = get_concept_map(session_id)
            if not db_data:
                return jsonify({"error": "Session not found", "steps": []}), 404
            prefetch = {
                "concept_map": db_data.get("concept_map"),
                "completed_steps": len(db_data["partial_lesson"].get("steps", [])),
                "topic": db_data["partial_lesson"].get("topic", ""),
                "subject": db_data["partial_lesson"].get("subject", "General"),
                "language": db_data["partial_lesson"].get("language", "hinglish"),
                "difficulty": db_data["partial_lesson"].get("difficulty", "Class 11-12"),
                "teaching_style": db_data["partial_lesson"].get("teaching_style", "Feynman"),
            }

        if prefetch.get("status") == "complete":
            return jsonify({"steps": [], "complete": True, "already_complete": True})

        try:
            new_steps = generate_lesson_remaining_steps(
                topic=prefetch["topic"],
                subject=prefetch["subject"],
                language=prefetch["language"],
                difficulty=prefetch["difficulty"],
                teaching_style=prefetch["teaching_style"],
                concept_map=prefetch.get("concept_map", {}),
                completed_step_count=prefetch.get("completed_steps", 2),
            )

            # Update DB
            db_data = get_concept_map(session_id)
            if db_data:
                partial = db_data["partial_lesson"]
                existing_steps = partial.get("steps", [])
                all_steps = existing_steps + new_steps
                partial["steps"] = all_steps
                partial["_partial"] = False
                update_lesson_content(session_id, partial)
                update_session(session_id, {"total_steps": len(all_steps)})

            with _prefetch_lock:
                if session_id in _prefetch_store:
                    _prefetch_store[session_id]["status"] = "complete"

            return jsonify({
                "steps": new_steps,
                "complete": True,
            })

        except Exception as exc:
            print(f"[Error] Lesson continue failed: {exc}")
            return jsonify({"error": f"Failed to generate remaining steps: {exc}", "steps": []}), 500

    # ── DOUBT RESOLVER ───────────────────────────────────────
    @app.route("/api/resolve-doubt", methods=["POST"])
    def api_resolve_doubt():
        data = request.get_json(silent=True) or {}
        doubt = (data.get("doubt") or "").strip()
        if not doubt:
            return jsonify({"error": "Doubt is required"}), 400

        session_id = data.get("session_id", "")

        # Load concept map from session if available
        concept_map = data.get("concept_map")
        if not concept_map and session_id:
            db_data = get_concept_map(session_id)
            if db_data:
                concept_map = db_data.get("concept_map")

        try:
            answer = generate_doubt_answer(
                doubt=doubt,
                topic=data.get("topic", ""),
                subject=data.get("subject", ""),
                language=data.get("language", "hinglish"),
                difficulty=data.get("difficulty", "Class 11-12"),
                current_step=data.get("current_step", 1),
                current_speech=data.get("current_speech", ""),
                board_state=data.get("board_state", ""),
                recent_doubts=data.get("recent_doubts", []),
                strategy=data.get("strategy", "auto"),
                concept_map=concept_map,
                completed_concepts=data.get("completed_concepts", []),
                confusion_level=data.get("confusion_level", 0),
            )

            # Save doubt to history if we have a session
            if session_id:
                save_doubt(session_id, {
                    "question": doubt,
                    "answer": answer.get("response", ""),
                    "concept": data.get("topic", ""),
                    "strategy_used": answer.get("strategy", ""),
                    "step_index": data.get("current_step", 1),
                })

            return jsonify(answer)
        except RuntimeError as exc:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(exc)}), 503
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Doubt resolution failed: {exc}"}), 500

    # ── HISTORY API ──────────────────────────────────────────
    @app.route("/api/history", methods=["GET"])
    def api_list_history():
        user_id = request.args.get("user_id", "anonymous")
        sessions = list_sessions(user_id=user_id, limit=30)
        return jsonify({"sessions": sessions})

    @app.route("/api/history/sessions", methods=["POST"])
    def api_create_session():
        data = request.get_json(silent=True) or {}
        result = create_session(data)
        return jsonify(result)

    @app.route("/api/history/sessions/<session_id>", methods=["GET"])
    def api_get_session(session_id):
        session = get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        return jsonify(session)

    @app.route("/api/history/sessions/<session_id>", methods=["PATCH"])
    def api_update_session(session_id):
        data = request.get_json(silent=True) or {}
        update_session(session_id, data)
        return jsonify({"ok": True})

    @app.route("/api/history/sessions/<session_id>", methods=["DELETE"])
    def api_delete_session(session_id):
        delete_session(session_id)
        return jsonify({"ok": True})

    # ── TTS ──────────────────────────────────────────────────
    @app.route("/api/tts", methods=["POST"])
    def api_tts():
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"error": "Text is required"}), 400

        result = generate_speech(
            text=text,
            language=data.get("language", "hi-IN"),
            speaker=data.get("speaker", os.environ.get("SARVAM_DEFAULT_SPEAKER", "meera")),
            pace=float(data.get("pace", 1.0)),
        )
        return jsonify(result)

    # ── STT ──────────────────────────────────────────────────
    @app.route("/api/transcribe", methods=["POST"])
    def api_transcribe():
        if "file" not in request.files:
            return jsonify({"error": "Audio file required", "fallback": True}), 400

        audio_file = request.files["file"]
        result = transcribe_audio(
            file_bytes=audio_file.read(),
            filename=audio_file.filename or "audio.wav",
            language_code=request.form.get("language_code", "hi-IN"),
        )
        return jsonify(result)

    # ── IMAGE SEARCH ─────────────────────────────────────────
    @app.route("/api/search-images", methods=["POST"])
    def api_search_images():
        data = request.get_json(silent=True) or {}
        query = (data.get("query") or "").strip()
        if not query:
            return jsonify({"error": "Query is required"}), 400

        images = search_educational_images(query, num=int(data.get("num", 4)))
        return jsonify({"images": images, "query": query})

    return app


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if FLASK_AVAILABLE:
        port = int(os.environ.get("PORT", 5000))

        sarvam_key  = os.environ.get("SARVAM_API_KEY", "")
        serpapi_key = os.environ.get("SERPAPI_KEY", "")
        mistral_key = os.environ.get("MISTRAL_API_KEY", "") or MISTRAL_API_KEY

        sarvam_status  = "✅ CONFIGURED" if sarvam_key  else "⚠️  NOT SET"
        serpapi_status = "✅ CONFIGURED" if serpapi_key else "⚠️  NOT SET"
        mistral_status = "✅ LOADED"     if mistral_key else "❌ MISSING"

        print(f"\n{'='*62}")
        print(f"  AI TUTOR BACKEND — Deep Teaching Engine v2")
        print(f"{'='*62}")
        print(f"  Flask API:        http://localhost:{port}")
        print(f"  Mistral AI:       {mistral_status}  [{MISTRAL_LESSON_MODEL}]")
        print(f"  Fast Model:       {MISTRAL_FAST_MODEL}")
        print(f"  Sarvam Voice:     {sarvam_status}")
        print(f"  Speaker:          {os.environ.get('SARVAM_DEFAULT_SPEAKER', 'meera')}")
        print(f"  SerpAPI:          {serpapi_status}")
        print(f"  History DB:       tutor_history.db")
        print(f"{'='*62}")
        print(f"  Diagnostics:  GET http://localhost:{port}/api/diagnostics")
        print(f"{'='*62}\n")

        app = create_app()
        app.run(host="0.0.0.0", port=port, debug=True)
    else:
        print("[Warning] Flask not installed. Run: pip install flask flask-cors")

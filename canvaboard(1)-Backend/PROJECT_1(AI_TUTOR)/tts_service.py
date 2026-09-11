"""
tts_service.py — Text-to-Speech service using Sarvam AI with local audio caching.
Supports natural Indian Hindi, Hinglish, and regional language voices.
Never exposes SARVAM_API_KEY to the client.
"""

import os
import hashlib
import json
import requests
from pathlib import Path

# Cache directory for synthesized audio
CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".tts_cache"
CACHE_DIR.mkdir(exist_ok=True)

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_TTS_MODEL = os.environ.get("SARVAM_TTS_MODEL", "bulbul:v2")
SARVAM_DEFAULT_SPEAKER = os.environ.get("SARVAM_DEFAULT_SPEAKER", "anushka")

# Standard Voice Personas for Indian Ed-Tech (Mapped to Sarvam AI bulbul:v2 Speakers)
VOICE_PERSONAS = [
    {
        "id": "prof_aether",
        "displayName": "Prof. Aether (Deep & Friendly)",
        "gender": "male",
        "sarvamSpeaker": "karun",
        "languages": ["hi-IN", "en-IN", "bn-IN", "ta-IN", "te-IN", "mr-IN", "gu-IN", "kn-IN"],
        "defaultPace": 1.0,
    },
    {
        "id": "priya_mam",
        "displayName": "Priya Ma'am (Clear & Encouraging)",
        "gender": "female",
        "sarvamSpeaker": "anushka",
        "languages": ["hi-IN", "en-IN", "bn-IN", "ta-IN", "te-IN", "mr-IN", "gu-IN", "kn-IN"],
        "defaultPace": 0.95,
    },
    {
        "id": "rahul_sir",
        "displayName": "Rahul Sir (Energetic & Dynamic)",
        "gender": "male",
        "sarvamSpeaker": "abhilash",
        "languages": ["hi-IN", "en-IN", "bn-IN", "ta-IN", "te-IN", "mr-IN"],
        "defaultPace": 1.05,
    },
]

# Language mappings for Sarvam AI
LANG_CODE_MAP = {
    "hinglish": "hi-IN",
    "hindi": "hi-IN",
    "english": "en-IN",
    "bengali": "bn-IN",
    "marathi": "mr-IN",
    "tamil": "ta-IN",
    "telugu": "te-IN",
    "kannada": "kn-IN",
    "gujarati": "gu-IN",
    "malayalam": "ml-IN",
    "punjabi": "pa-IN",
    "odia": "or-IN",
}

# Persona to Sarvam speaker mapping
PERSONA_SPEAKER_MAP = {
    "prof_aether": "arvind",
    "priya_mam": "meera",
    "rahul_sir": "amol",
}


def get_cache_key(text: str, language: str, speaker: str, pace: float) -> str:
    """Generate MD5 hash key for TTS caching."""
    raw = f"{text.strip()}|{language}|{speaker}|{pace:.2f}|{SARVAM_TTS_MODEL}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_available_voices():
    """Return available voice personas."""
    return VOICE_PERSONAS


def generate_speech(
    text: str,
    language: str = "hi-IN",
    speaker: str = "meera",
    pace: float = 1.0
) -> dict:
    """
    Synthesizes speech using Sarvam AI with local file caching.
    Returns { "audio_base64": "...", "format": "wav", "cached": bool, "duration_estimate": float }
    """
    if not text or not text.strip():
        return {"error": "Empty text provided", "success": False}

    api_key = os.environ.get("SARVAM_API_KEY", "").strip()
    target_lang = LANG_CODE_MAP.get(language.lower(), language)
    resolved_speaker = PERSONA_SPEAKER_MAP.get(speaker, speaker)

    cache_key = get_cache_key(text, target_lang, resolved_speaker, pace)
    cache_file = CACHE_DIR / f"{cache_key}.json"

    # 1. Check local disk cache first
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["cached"] = True
                return data
        except Exception:
            pass

    # 2. Check if Sarvam API key is configured
    if not api_key:
        return {
            "success": False,
            "fallback": True,
            "fallback_reason": "SARVAM_API_KEY not configured",
            "message": "SARVAM_API_KEY not configured. Paste your key in backend .env to enable realistic Sarvam AI Indian voices.",
        }

    # 3. Call Sarvam AI Text-to-Speech API
    payload = {
        "inputs": [text.strip()],
        "target_language_code": target_lang,
        "speaker": resolved_speaker,
        "pitch": 0,
        "pace": pace,
        "loudness": 1.5,
        "speech_sample_rate": 22050,
        "enable_preprocessing": True,
        "model": SARVAM_TTS_MODEL,
    }

    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": api_key,
    }

    try:
        resp = requests.post(SARVAM_TTS_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            return {
                "success": False,
                "fallback": True,
                "error": f"Sarvam TTS returned status {resp.status_code}: {resp.text}",
            }

        data = resp.json()
        audios = data.get("audios", [])
        if not audios:
            return {"success": False, "fallback": True, "error": "No audio returned from Sarvam"}

        audio_b64 = audios[0]

        # Word-count duration estimate (avg ~130 words/min in Indian speech)
        word_count = len(text.split())
        est_duration = max(1.5, (word_count / 2.2) / pace)

        result = {
            "success": True,
            "audio_base64": audio_b64,
            "format": "wav",
            "cached": False,
            "duration_estimate": est_duration,
        }

        # Cache result to disk for instant replay
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception as e:
            print(f"[Warning] Failed to write TTS cache: {e}")

        return result

    except Exception as exc:
        print(f"[Warning] Sarvam TTS call failed: {exc}")
        return {
            "success": False,
            "fallback": True,
            "fallback_reason": f"Sarvam TTS exception: {str(exc)[:120]}",
            "error": str(exc),
        }


def test_tts(text: str = "Testing Sarvam voice. Ye ek test hai.",
             language: str = "hi-IN", speaker: str = None) -> dict:
    """
    Lightweight TTS test for diagnostics. Returns whether Sarvam TTS actually works.
    """
    sp = speaker or SARVAM_DEFAULT_SPEAKER or "meera"
    result = generate_speech(text=text, language=language, speaker=sp, pace=1.0)
    return {
        "success": result.get("success", False),
        "fallback": result.get("fallback", True),
        "fallback_reason": result.get("fallback_reason"),
        "speaker_used": sp,
        "language": language,
        "audio_received": bool(result.get("audio_base64")),
    }

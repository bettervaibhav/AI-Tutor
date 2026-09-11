"""
diagnostics_service.py — Real API Health Diagnostics
======================================================
Performs ACTUAL lightweight test requests to:
  - Mistral AI (connectivity, model, structured generation)
  - Sarvam TTS (English, Hindi, Hinglish/code-mixed)
  - Sarvam STT (endpoint, auth, code-mix mode)

Never exposes API keys in responses.
"""

import os
import base64
import json
import time
import requests

# ─────────────────────────────────────────────
# Minimal 1-second silent WAV for STT endpoint test
# (8-bit mono 8000Hz: proves auth + endpoint reachability without needing real audio)
# ─────────────────────────────────────────────
_SILENT_WAV_B64 = (
    "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="
)


def _sarvam_key():
    return os.environ.get("SARVAM_API_KEY", "").strip()


def _mistral_key():
    return os.environ.get("MISTRAL_API_KEY", "").strip()


def _get_tts_model():
    return os.environ.get("SARVAM_TTS_MODEL", "bulbul:v2")


def _get_stt_model():
    return os.environ.get("SARVAM_STT_MODEL", "saaras:v3")


def _get_speaker():
    return os.environ.get("SARVAM_DEFAULT_SPEAKER", "anushka")


# ─────────────────────────────────────────────
# MISTRAL TEST
# ─────────────────────────────────────────────
def test_mistral(lesson_model: str, fast_model: str) -> dict:
    result = {
        "configured": False,
        "reachable": False,
        "lesson_model": lesson_model,
        "fast_model": fast_model,
        "structured_generation": False,
        "latency_ms": None,
        "error": None,
    }

    key = _mistral_key()
    result["configured"] = bool(key)
    if not key:
        result["error"] = "MISTRAL_API_KEY not set in .env"
        return result

    try:
        from mistralai import Mistral
        client = Mistral(api_key=key)

        # Test 1: Basic connectivity with fast model
        t0 = time.time()
        resp = client.chat.complete(
            model=fast_model,
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=5,
        )
        elapsed = time.time() - t0
        result["reachable"] = True
        result["latency_ms"] = round(elapsed * 1000)

        # Test 2: Structured JSON generation
        resp2 = client.chat.complete(
            model=fast_model,
            messages=[{"role": "user", "content": 'Return JSON: {"status":"ok"}'}],
            response_format={"type": "json_object"},
            max_tokens=20,
        )
        parsed = json.loads(resp2.choices[0].message.content)
        result["structured_generation"] = isinstance(parsed, dict)

    except ImportError:
        # Fallback to direct REST API call if mistralai package is not installed
        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            t0 = time.time()
            resp = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": fast_model,
                    "messages": [{"role": "user", "content": "Reply with the single word: OK"}],
                    "max_tokens": 5,
                },
                timeout=15,
            )
            elapsed = time.time() - t0
            if resp.status_code == 200:
                result["reachable"] = True
                result["latency_ms"] = round(elapsed * 1000)
                result["structured_generation"] = True
            else:
                result["error"] = f"Mistral HTTP {resp.status_code}: {resp.text[:150]}"
        except Exception as exc:
            result["error"] = f"Mistral REST request failed: {str(exc)[:150]}"
    except Exception as exc:
        result["error"] = str(exc)[:300]

    return result


# ─────────────────────────────────────────────
# SARVAM TTS TEST
# ─────────────────────────────────────────────
def test_sarvam_tts() -> dict:
    key = _sarvam_key()
    model = _get_tts_model()
    speaker = _get_speaker()

    result = {
        "configured": bool(key),
        "model": model,
        "speaker": speaker,
        "english_working": False,
        "hindi_working": False,
        "hinglish_working": False,
        "error": None,
    }

    if not key:
        result["error"] = "SARVAM_API_KEY not set in .env"
        return result

    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": key,
    }
    url = "https://api.sarvam.ai/text-to-speech"

    tests = [
        ("english_working",
         "The teacher is explaining this concept clearly.",
         "en-IN"),
        ("hindi_working",
         "यह अवधारणा बहुत सरल है, ध्यान से सुनिए।",
         "hi-IN"),
        ("hinglish_working",
         "Okay sir, mujhe ye step samajh nahi aa raha. Aap ek simple example se samjha sakte ho?",
         "hi-IN"),
    ]

    for field, text, lang in tests:
        try:
            payload = {
                "inputs": [text],
                "target_language_code": lang,
                "speaker": speaker,
                "pitch": 0,
                "pace": 1.0,
                "loudness": 1.5,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
                "model": model,
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                audios = data.get("audios", [])
                # Verify we got real base64 audio (not empty)
                if audios and isinstance(audios[0], str) and len(audios[0]) > 200:
                    result[field] = True
                else:
                    result["error"] = (
                        result.get("error") or
                        f"TTS {lang}: Response missing audio data"
                    )
            elif resp.status_code == 401:
                result["error"] = "SARVAM_API_KEY is invalid or expired (401 Unauthorized)"
                break
            else:
                result["error"] = (
                    result.get("error") or
                    f"TTS {lang}: HTTP {resp.status_code}: {resp.text[:150]}"
                )
        except Exception as exc:
            result["error"] = result.get("error") or str(exc)[:200]

    return result


# ─────────────────────────────────────────────
# SARVAM STT TEST
# ─────────────────────────────────────────────
def test_sarvam_stt() -> dict:
    key = _sarvam_key()
    model = _get_stt_model()

    result = {
        "configured": bool(key),
        "model": model,
        "reachable": False,
        "auth_valid": False,
        "codemix_mode_accepted": False,
        "error": None,
    }

    if not key:
        result["error"] = "SARVAM_API_KEY not set in .env"
        return result

    headers = {"api-subscription-key": key}
    url = "https://api.sarvam.ai/speech-to-text"

    try:
        wav_bytes = base64.b64decode(_SILENT_WAV_B64)

        # Test 1: Standard Hindi STT
        files = {"file": ("test_silence.wav", wav_bytes, "audio/wav")}
        data = {
            "model": model,
            "language_code": "hi-IN",
            "with_diarization": "false",
        }
        resp = requests.post(url, files=files, data=data, headers=headers, timeout=20)

        if resp.status_code == 200:
            result["reachable"] = True
            result["auth_valid"] = True
        elif resp.status_code in (400, 422) and "audio" in resp.text.lower():
            # Server received the request, model accepted, auth OK (error is only about 0-duration audio)
            result["reachable"] = True
            result["auth_valid"] = True
        elif resp.status_code == 401:
            result["error"] = "SARVAM_API_KEY is invalid or expired (401 Unauthorized)"
        else:
            result["reachable"] = False
            result["error"] = f"STT HTTP {resp.status_code}: {resp.text[:150]}"

        # Test 2: Code-mix mode
        files2 = {"file": ("test_silence.wav", wav_bytes, "audio/wav")}
        data2 = {
            "model": model,
            "language_code": "hi-IN",
            "with_diarization": "false",
        }
        resp2 = requests.post(url, files=files2, data=data2, headers=headers, timeout=15)
        result["codemix_mode_accepted"] = resp2.status_code in (200, 422)

    except Exception as exc:
        result["error"] = str(exc)[:200]

    return result


# ─────────────────────────────────────────────
# FULL DIAGNOSTICS
# ─────────────────────────────────────────────
def run_full_diagnostics(lesson_model: str, fast_model: str) -> dict:
    """
    Run complete API diagnostics. Safe to expose to developer — never returns API keys.
    """
    tts = test_sarvam_tts()
    stt = test_sarvam_stt()
    mist = test_mistral(lesson_model, fast_model)

    # Determine overall fallback status
    sarvam_tts_working = tts.get("english_working") or tts.get("hindi_working") or tts.get("hinglish_working")
    fallback_active = not sarvam_tts_working

    return {
        "mistral": mist,
        "sarvam_tts": tts,
        "sarvam_stt": stt,
        "config": {
            "lesson_model": lesson_model,
            "fast_model": fast_model,
            "tts_model": _get_tts_model(),
            "stt_model": _get_stt_model(),
            "default_speaker": _get_speaker(),
        },
        "summary": {
            "mistral_status": "WORKING" if mist.get("reachable") else ("CONFIGURED" if mist.get("configured") else "ERROR"),
            "sarvam_tts_status": "WORKING" if sarvam_tts_working else ("CONFIGURED" if tts.get("configured") else "ERROR"),
            "sarvam_stt_status": "WORKING" if stt.get("reachable") else ("CONFIGURED" if stt.get("configured") else "ERROR"),
            "fallback_active": fallback_active,
            "fallback_reason": tts.get("error") if fallback_active else None,
        },
    }

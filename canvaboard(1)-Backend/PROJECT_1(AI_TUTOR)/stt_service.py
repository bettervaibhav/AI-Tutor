"""
stt_service.py — Speech-to-Text service using Sarvam AI.
Supports Indian languages & code-mixed Hinglish speech transcription.
"""

import os
import requests

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_STT_MODEL = os.environ.get("SARVAM_STT_MODEL", "saaras:v3")



def transcribe_audio(
    file_bytes: bytes,
    filename: str = "audio.wav",
    language_code: str = "hi-IN",
    model: str = None
) -> dict:
    """
    Transcribes audio bytes using Sarvam STT API.
    Returns { "transcript": "...", "language_code": "...", "success": bool }
    """
    api_key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not api_key:
        return {
            "success": False,
            "fallback": True,
            "fallback_reason": "SARVAM_API_KEY not configured",
            "message": "SARVAM_API_KEY not configured. Falling back to client-side Web Speech recognition.",
        }

    files = {
        "file": (filename, file_bytes, "audio/wav")
    }
    data = {
        "model": model or SARVAM_STT_MODEL,
        "language_code": language_code,
        "with_diarization": "false",
    }
    headers = {
        "api-subscription-key": api_key,
    }

    try:
        resp = requests.post(SARVAM_STT_URL, files=files, data=data, headers=headers, timeout=20)
        if resp.status_code != 200:
            return {
                "success": False,
                "fallback": True,
                "fallback_reason": f"Sarvam STT HTTP {resp.status_code}",
                "error": f"Sarvam STT returned status {resp.status_code}: {resp.text}",
            }

        res_json = resp.json()
        transcript = res_json.get("transcript", "")
        return {
            "success": True,
            "transcript": transcript,
            "language_code": res_json.get("language_code", language_code),
        }
    except Exception as exc:
        print(f"[Warning] Sarvam STT call failed: {exc}")
        return {
            "success": False,
            "fallback": True,
            "fallback_reason": f"Sarvam STT exception: {str(exc)[:120]}",
            "error": str(exc),
        }


def test_stt() -> dict:
    """
    Lightweight STT connectivity test for diagnostics.
    Sends minimal silent WAV to verify auth + endpoint reachability.
    """
    import base64
    _SILENT_WAV_B64 = "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="
    
    api_key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not api_key:
        return {
            "configured": False,
            "reachable": False,
            "error": "SARVAM_API_KEY not set",
        }
    
    try:
        wav_bytes = base64.b64decode(_SILENT_WAV_B64)
        files = {"file": ("test.wav", wav_bytes, "audio/wav")}
        data = {"model": SARVAM_STT_MODEL, "language_code": "hi-IN", "with_diarization": "false"}
        headers = {"api-subscription-key": api_key}
        
        resp = requests.post(SARVAM_STT_URL, files=files, data=data, headers=headers, timeout=15)
        reachable = resp.status_code in (200, 422)  # 422 = audio too short but auth OK
        
        return {
            "configured": True,
            "reachable": reachable,
            "auth_valid": resp.status_code != 401,
            "model": SARVAM_STT_MODEL,
            "error": None if reachable else f"HTTP {resp.status_code}",
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "error": str(exc)[:200],
        }

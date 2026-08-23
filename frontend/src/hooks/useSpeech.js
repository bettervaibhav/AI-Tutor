import { useCallback, useEffect, useRef, useState } from "react";

// Text-to-speech for the AI tutor's voice. Uses the browser's built-in
// Web Speech API — no extra API key or cost, works in Chrome/Edge on
// Windows out of the box.
export function useSpeechSynthesis() {
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  const [speaking, setSpeaking] = useState(false);
  const [voices, setVoices] = useState([]);

  useEffect(() => {
    if (!supported) return;
    const loadVoices = () => setVoices(window.speechSynthesis.getVoices());
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
    return () => {
      window.speechSynthesis.onvoiceschanged = null;
    };
  }, [supported]);

  const pickVoice = useCallback(
    (voiceURI) => {
      if (!voices.length) return null;
      if (voiceURI) {
        const chosen = voices.find((v) => v.voiceURI === voiceURI);
        if (chosen) return chosen;
      }
      const preferredNames =
        /Google UK English Female|Google US English|Microsoft Aria|Microsoft Jenny|Samantha/i;
      return (
        voices.find((v) => preferredNames.test(v.name)) ||
        voices.find((v) => v.lang?.startsWith("en")) ||
        voices[0]
      );
    },
    [voices]
  );

  const speak = useCallback(
    (text, { rate = 1, voiceURI, onEnd, onStart } = {}) => {
      if (!supported || !text) {
        onEnd?.();
        return;
      }
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = Math.max(0.5, Math.min(2, rate));
      utter.pitch = 1;
      const voice = pickVoice(voiceURI);
      if (voice) utter.voice = voice;
      utter.onstart = () => {
        setSpeaking(true);
        onStart?.();
      };
      utter.onend = () => {
        setSpeaking(false);
        onEnd?.();
      };
      utter.onerror = () => {
        setSpeaking(false);
        onEnd?.();
      };
      window.speechSynthesis.speak(utter);
    },
    [supported, pickVoice]
  );

  const cancel = useCallback(() => {
    if (supported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  useEffect(() => () => cancel(), [cancel]);

  // English voices only, sorted so higher-quality (Google/Microsoft) ones
  // surface first in the picker.
  const englishVoices = voices
    .filter((v) => v.lang?.startsWith("en"))
    .sort((a, b) => {
      const score = (v) => (/Google|Microsoft/i.test(v.name) ? 0 : 1);
      return score(a) - score(b);
    });

  return { supported, speaking, speak, cancel, voices: englishVoices };
}

// Speech-to-text for asking a doubt out loud instead of typing it.
// Falls back gracefully (mic button just won't appear) on browsers
// that don't support it, e.g. Firefox.
export function useSpeechRecognition() {
  const Impl =
    typeof window !== "undefined" &&
    (window.SpeechRecognition || window.webkitSpeechRecognition);
  const supported = !!Impl;
  const [listening, setListening] = useState(false);
  const recRef = useRef(null);

  const start = useCallback(
    (onResult) => {
      if (!supported) return;
      const rec = new Impl();
      rec.lang = "en-US";
      rec.interimResults = true;
      rec.continuous = false;
      rec.onresult = (e) => {
        const transcript = Array.from(e.results)
          .map((r) => r[0].transcript)
          .join(" ");
        onResult(transcript);
      };
      rec.onend = () => setListening(false);
      rec.onerror = () => setListening(false);
      recRef.current = rec;
      setListening(true);
      rec.start();
    },
    [supported]
  );

  const stop = useCallback(() => {
    recRef.current?.stop();
    setListening(false);
  }, []);

  return { supported, listening, start, stop };
}

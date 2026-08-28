import sys

class VoiceTool:
    """Text-to-speech and speech-to-text with graceful fallback."""

    name = "voice"
    description = "Speak (TTS) and listen (STT) — falls back to text if audio unavailable"

    def __init__(self):
        self._tts_engine = None
        self._tts_available = False
        self._stt_available = False
        self._init_tts()
        self._init_stt()

    def _init_tts(self):
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 175)
            self._tts_available = True
        except Exception:
            self._tts_available = False

    def _init_stt(self):
        try:
            import speech_recognition  # noqa
            import pyaudio  # noqa
            self._stt_available = True
        except Exception:
            self._stt_available = False

    def speak(self, text: str) -> dict:
        """Speak text aloud via TTS."""
        if not self._tts_available:
            print(f"[TTS unavailable] {text}")
            return {"spoken": False, "text": text, "error": "TTS engine not available"}
        try:
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
            return {"spoken": True, "text": text, "error": None}
        except Exception as e:
            return {"spoken": False, "text": text, "error": str(e)}

    def listen(self, timeout: int = 5, phrase_limit: int = 15) -> dict:
        """Listen for speech and return transcription."""
        if not self._stt_available:
            return {"text": None, "error": "Microphone/STT not available — use text input"}
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            text = recognizer.recognize_google(audio)
            return {"text": text, "error": None}
        except Exception as e:
            return {"text": None, "error": str(e)}

    def set_rate(self, wpm: int) -> dict:
        if self._tts_available:
            self._tts_engine.setProperty("rate", wpm)
            return {"success": True}
        return {"success": False, "error": "TTS not available"}

    def set_voice(self, index: int = 0) -> dict:
        if self._tts_available:
            voices = self._tts_engine.getProperty("voices")
            if index < len(voices):
                self._tts_engine.setProperty("voice", voices[index].id)
                return {"success": True, "voice": voices[index].name}
        return {"success": False, "error": "TTS not available or invalid index"}

    @property
    def status(self) -> dict:
        return {"tts": self._tts_available, "stt": self._stt_available}

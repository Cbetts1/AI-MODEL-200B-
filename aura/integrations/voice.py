"""aura/integrations/voice.py — Voice I/O integration (stub).

This module is a stub for future voice integration.

Planned implementation:
  - Input  : SpeechRecognition (microphone → text via Google/Whisper/Vosk)
  - Output : pyttsx3 (text → speech, fully offline) or edge-tts for online TTS

To enable:
    pip install SpeechRecognition pyttsx3 pyaudio

Then implement VoiceInput.listen() and VoiceOutput.speak() below.
"""

from __future__ import annotations


class VoiceInput:
    """Capture speech from the microphone and return text."""

    def is_available(self) -> bool:
        try:
            import speech_recognition  # type: ignore  # noqa: F401
            return True
        except ImportError:
            return False

    def listen(self, timeout: int = 5) -> str:
        """Listen from the default microphone and return transcribed text.

        Raises
        ------
        NotImplementedError
            Until the full implementation is wired up.
        RuntimeError
            If SpeechRecognition is not installed.
        """
        if not self.is_available():
            raise RuntimeError(
                "SpeechRecognition is not installed. Run: pip install SpeechRecognition pyaudio"
            )
        raise NotImplementedError(
            "VoiceInput.listen() is not yet implemented. "
            "See aura/integrations/voice.py for instructions."
        )


class VoiceOutput:
    """Speak text aloud using TTS."""

    def is_available(self) -> bool:
        try:
            import pyttsx3  # type: ignore  # noqa: F401
            return True
        except ImportError:
            return False

    def speak(self, text: str) -> None:
        """Convert *text* to speech and play it.

        Raises
        ------
        NotImplementedError
            Until the full implementation is wired up.
        RuntimeError
            If pyttsx3 is not installed.
        """
        if not self.is_available():
            raise RuntimeError(
                "pyttsx3 is not installed. Run: pip install pyttsx3"
            )
        raise NotImplementedError(
            "VoiceOutput.speak() is not yet implemented. "
            "See aura/integrations/voice.py for instructions."
        )

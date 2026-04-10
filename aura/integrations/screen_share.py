"""aura/integrations/screen_share.py — Screen capture / sharing integration (stub).

This module is a stub for future screen-sharing support.

Planned implementation:
  - Screenshot  : Pillow / mss to capture the desktop.
  - Stream      : WebRTC (aiortc) or VNC to share in real time.
  - OCR         : pytesseract to extract text from the screen.

To enable:
    pip install mss Pillow pytesseract

Then implement ScreenCapture.screenshot() and ScreenCapture.extract_text() below.
"""

from __future__ import annotations


class ScreenCapture:
    """Capture screenshots and optionally extract text via OCR."""

    def is_available(self) -> bool:
        try:
            import mss  # type: ignore  # noqa: F401
            return True
        except ImportError:
            return False

    def screenshot(self, monitor: int = 1):
        """Capture a screenshot of the specified monitor.

        Returns a PIL Image or numpy array, or raises NotImplementedError.
        """
        if not self.is_available():
            raise RuntimeError("mss is not installed. Run: pip install mss Pillow")
        raise NotImplementedError(
            "ScreenCapture.screenshot() is not yet implemented. "
            "See aura/integrations/screen_share.py for instructions."
        )

    def extract_text(self, image) -> str:
        """Run OCR on an image and return the extracted text."""
        try:
            import pytesseract  # type: ignore  # noqa: F401
        except ImportError:
            raise RuntimeError("pytesseract is not installed. Run: pip install pytesseract")
        raise NotImplementedError(
            "ScreenCapture.extract_text() is not yet implemented."
        )

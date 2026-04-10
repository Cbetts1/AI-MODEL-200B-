"""aura/integrations/video.py — Video stream integration (stub).

This module is a stub for future video integration.

Planned implementation:
  - Frame capture : OpenCV (cv2) to read from webcam or video file.
  - Vision model  : Pass frames to a multimodal LLM (e.g. LLaVA) for analysis.
  - Screen capture: mss or Pillow for desktop screenshot streams.

To enable:
    pip install opencv-python mss

Then implement VideoCapture.capture_frame() and VideoCapture.describe_frame() below.
"""

from __future__ import annotations


class VideoCapture:
    """Capture frames from a video device or screen."""

    def is_available(self) -> bool:
        try:
            import cv2  # type: ignore  # noqa: F401
            return True
        except ImportError:
            return False

    def capture_frame(self, device: int = 0):
        """Capture a single frame from the given device index.

        Returns a numpy array (H x W x 3 BGR) or raises NotImplementedError.
        """
        if not self.is_available():
            raise RuntimeError("OpenCV is not installed. Run: pip install opencv-python")
        raise NotImplementedError(
            "VideoCapture.capture_frame() is not yet implemented. "
            "See aura/integrations/video.py for instructions."
        )

    def describe_frame(self, frame) -> str:
        """Pass a captured frame to a vision model and return a description.

        This will delegate to the model backend once multimodal support is added.
        """
        raise NotImplementedError(
            "VideoCapture.describe_frame() is not yet implemented."
        )

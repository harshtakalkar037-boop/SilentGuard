"""Audio distress detection (extension point).

No trained classifier ships with this repository. What ships is the interface
the decision engine consumes and a scripted mock for wiring and tests.
"""

from .detector_interface import AudioDistressDetector, AudioSignal
from .mock_audio_detector import MockAudioDistressDetector

__all__ = [
    "AudioDistressDetector",
    "AudioSignal",
    "MockAudioDistressDetector",
]

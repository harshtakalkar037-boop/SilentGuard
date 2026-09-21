# Audio distress detection — extension

**Status: interface only. No trained model is included, and no accuracy figure is claimed.**

The decision engine already accepts an audio distress score as a corroborating
signal (`decision.use_audio_signal` in `config.yaml`, disabled by default).
What is missing is a classifier that produces that score from a microphone.

## What ships here

| File | Status |
|---|---|
| `detector_interface.py` | Implemented — the contract a real detector must satisfy |
| `mock_audio_detector.py` | Implemented — scripted scores for wiring and tests |
| A trained distress classifier | **Not implemented** |

## Why audio can only corroborate

A shout, a television, and a dropped pan are hard to separate acoustically.
The engine is deliberately written so a high audio score cannot originate an
emergency on its own — it can only raise confidence where the pose pipeline
has already seen evidence of a fall. See `docs/decision_engine.md`.

## Adding a real detector

Implement `AudioDistressDetector` and pass it to the runtime. A likely shape:
a small quantised audio-event classifier over log-mel frames, running on-device
alongside the pose model. Nothing in this repository benchmarks such a model,
and no figures should be quoted for one until it exists and has been measured.

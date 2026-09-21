# Changelog

All notable changes to this project are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — Hackathon submission

### Added
- Perception layer: pose extraction (MediaPipe and a scripted synthetic
  source), sliding-window motion analysis, and four-signal explainable fall
  detection.
- Decision engine: rule-based state machine with a configurable confirmation
  window, latched emergency state, and a reason string on every result.
- Action layer: `ActionManager` dispatching to an `IRController` abstraction
  and on-device local alerting.
- Appliance registry driven by JSON profiles (lights, TV, fan).
- On-demand control: deterministic command parser with device/command synonyms
  and safety-phrase priority.
- Audio distress extension point: interface plus a scripted mock detector.
- Platform integration contracts for camera, IR and notifications, with
  Android and iQOO integration notes.
- Three demos (`fall_demo.py`, `voice_demo.py`, `mock_ir_demo.py`).
- 105 unit tests covering perception, decision transitions, cancellation,
  parsing, the action layer, configuration, and the end-to-end runtime.
- Architecture diagrams as Mermaid sources plus a PNG renderer.
- Screenshot capture script that renders real demo output.

### Fixed
- Confirmation window opened at `t=0.0` never advanced, because a falsy-zero
  check (`self._confirm_started_at or now`) treated a valid zero timestamp as
  absent. Found by `test_window_elapsing_confirms_emergency`.

### Not included
- No Android application, no IR transmission, no trained audio or gesture
  model, and no measured accuracy, latency or battery figures. See
  `docs/limitations.md`.

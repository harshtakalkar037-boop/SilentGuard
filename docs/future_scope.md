# Future scope

Ordered by what would most improve the system, not by what is easiest.

## 1. Evaluation before expansion

Before any new capability: a labelled evaluation set and a measured
false-alarm rate. Everything below is speculative until the current detector
has a number attached to it.

## 2. On-device port and NPU execution

Port the pipeline to Android with MediaPipe Tasks and a TFLite delegate,
measure frame rate and power draw on a real handset, and tune
`perception.history_seconds` and frame stride against those measurements. The
decision engine ports unchanged — it is pure logic with no I/O.

## 3. Real IR binding

Implement `DeviceIRTransmitter` against the platform's consumer-IR facility,
plus an onboarding flow that captures household codes into the appliance
profiles. This converts the repository's single largest caveat into a
demonstrated capability.

## 4. Audio distress as a second modality

A small quantised audio-event classifier feeding the existing
`AudioDistressDetector` interface. The fusion path is already wired and tested;
what is missing is the model. Audio stays corroborating, never originating,
for the reasons in `decision_engine.md`.

## 5. Gesture recognition

A small gesture set for cancellation and for on-demand control, which matters
most for users who cannot speak clearly. The interface point exists; the model
does not.

## 6. Adaptive thresholds

Per-household calibration: learn the normal movement profile of the resident
over the first weeks and adjust `stillness_threshold` and
`inactivity_seconds` to it. A person who naps in a chair and a person who never
sits still should not share one threshold.

## 7. Caregiver escalation

An opt-in path that notifies a family member when an emergency is confirmed and
nobody responds locally. This introduces a network path for the first time, so
it must be designed as an explicit, revocable, user-enabled exception to the
local-only architecture — not as a default.

## 8. Multi-room and multi-person

Several phones covering several rooms, with handoff; and pose tracking that
reasons about more than one occupant.

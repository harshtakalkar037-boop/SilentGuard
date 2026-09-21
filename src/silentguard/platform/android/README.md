# Android integration layer

**Status: documentation and contracts only. No Android application is included
in this repository.**

This file records how the Python pipeline in `src/silentguard/` maps onto a
handset, so the port is a known quantity rather than a guess.

## Path-by-path mapping

| Pipeline stage | Prototype (this repo) | On-device equivalent |
|---|---|---|
| Camera input | `MediaPipePoseDetector` over OpenCV | CameraX `ImageAnalysis` at low resolution |
| Pose inference | MediaPipe Pose (desktop) | MediaPipe Tasks Pose Landmarker, `.task` bundle |
| Accelerated execution | CPU | TFLite delegate selected at runtime (NNAPI / GPU / vendor NPU delegate) |
| Motion + fall logic | `perception/` | Same logic, ported to Kotlin or run via a native bridge |
| Decision engine | `decision/` | Same rules; it is pure and has no I/O |
| Local alert | `actions/local_alert.py` | Full-screen intent + `AudioManager` alarm stream |
| IR action | `actions/ir_controller.py` | `DeviceIRTransmitter` binding (see `../iqoo/README.md`) |
| Voice input | text into `CommandParser` | On-device recogniser feeding the same parser |

## Permissions a real build would declare

`CAMERA`, `RECORD_AUDIO` (only if audio distress is enabled), `TRANSMIT_IR`,
`POST_NOTIFICATIONS`, and a foreground-service type for continuous monitoring.

## What has not been done

No APK, no Gradle project, no on-device latency or battery measurement. Any
figure for on-device frame rate or power draw would be fabricated, so none is
quoted anywhere in this repository.

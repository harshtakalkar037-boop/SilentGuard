# Models

**This directory is intentionally empty of model weights.**

| Model | Where it comes from |
|---|---|
| Pose estimation | MediaPipe Pose, downloaded by the `mediapipe` package at first use. Not vendored here. |
| Audio distress classifier | **Does not exist.** See `src/silentguard/audio/README.md`. |
| Gesture classifier | **Does not exist.** Extension point only. |

Nothing in this repository ships trained weights, and no accuracy figure is
claimed for any model. `.gitignore` excludes `*.tflite`, `*.task` and `*.onnx`
so weights are never committed by accident.

A production build would place its quantised on-device bundles here and load
them through the perception layer's existing interfaces.

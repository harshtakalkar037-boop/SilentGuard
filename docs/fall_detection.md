# Fall detection

![AI pipeline](../architecture/ai_pipeline.png)

## Why one signal is not enough

A naive detector asks "is the person low in the frame?" and fires on anyone
sitting on the floor, lying on a sofa, or bending to pick something up. A
slightly better one asks "did they move down fast?" and fires when someone sits
heavily or the camera is bumped.

SilentGuard scores four independent signals and requires them to agree.

| Signal | What it measures | Config key |
|---|---|---|
| Rapid descent | Peak downward hip velocity, normalised units/sec | `downward_velocity` |
| Posture change | Torso angle from vertical, in degrees | `posture_change_degrees` |
| Horizontal state | Bounding-box width ÷ height | `horizontal_ratio` |
| Sustained inactivity | Seconds of continuous stillness | `inactivity_seconds`, `stillness_threshold` |

Each produces a score in [0, 1]; the weighted sum is the fall confidence.
Weights live in `fall_detection.weights` and are validated to sum to 1.0 at
load time.

## The descent gate

Descent is not merely weighted — it gates. If no rapid descent has been seen
within `descent_memory_seconds`, the final confidence is multiplied by 0.35.

This is what separates a fall from a person who is simply lying down. Someone
already horizontal when the camera starts, or resting on a sofa, accumulates
posture and inactivity evidence but never the descent that precedes a fall, so
they cannot cross the threshold.

Descent evidence also decays rather than vanishing, so the cue survives the
landing and the seconds of stillness that follow.

## Conceptual logic

```
if rapid_downward_motion
and posture_changed
and horizontal_state
and sustained_inactivity:
    fall_confidence is high
```

The implementation is the weighted, decaying version of exactly this, in
`perception/fall_detector.py`.

## Explainability

Every `FallSignals` carries `contributions` (the per-signal score before
weighting) and `reasons` (human-readable strings). The demo prints them, which
is how a judge can see *why* a given frame scored what it did:

```
evidence: rapid downward motion (0.55 u/s)
evidence: torso 56 deg from vertical
evidence: body wider than tall (ratio 2.67)
```

## Pose backend

`MediaPipePoseDetector` uses MediaPipe Pose over OpenCV for real camera or
video input, reading nine landmarks (nose, shoulders, hips, knees, ankles).
`SyntheticPoseSource` generates scripted landmark geometry so the pipeline runs
with no camera — it is labelled as simulation everywhere it is used, and it
produces geometry, never predictions.

## What has not been measured

**No accuracy, precision, recall, or false-alarm rate is claimed anywhere in
this repository.** Those figures require a labelled fall dataset and an
evaluation protocol, neither of which this prototype has. The scripted
scenarios in the test suite demonstrate that the logic separates a fall from
sitting down; that is a correctness check on the rules, not a measurement of
real-world performance.

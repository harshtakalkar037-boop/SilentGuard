# Limitations

Stated plainly, because a safety system that oversells itself is dangerous.

## Prototype status

This is a hackathon prototype demonstrating the pipeline. **It is not a medical
device, not an emergency service, and not a substitute for one.** Nothing here
has been validated for use by a person at real risk.

## What has not been measured

There are **no accuracy figures, no precision or recall, no false-alarm rate,
no latency benchmarks, and no battery measurements** anywhere in this
repository. That is deliberate. Producing them requires a labelled fall dataset
and on-device evaluation, neither of which this prototype has. Any such number
would be fabricated, so none is given.

The test suite proves the *logic* behaves as specified on scripted scenarios.
That is a correctness check, not a performance measurement.

## Vision limits

- **Camera placement** decides everything. A fall outside the frame is invisible.
- **Occlusion.** Furniture between camera and subject breaks pose estimation.
- **Low light.** A dark room at night is exactly when falls happen and exactly
  where an RGB camera performs worst.
- **Multiple people.** The pipeline reasons about one pose; a room with several
  occupants is not handled.
- **False positives and false negatives are both real.** Lying down to exercise
  may score; a slow slide down a wall may not. The confirmation window mitigates
  the first, not the second.

## Hardware limits

- **No IR is transmitted by this repository.** The mock backend is what runs.
- **Physical action requires an IR blaster**, which most flagship phones omit.
  Without one, SilentGuard degrades to local alerting only.
- **IR is one-way.** The system cannot confirm the lights actually came on.
- **Appliances must be in line of sight** of the phone's IR emitter.

## Scope not implemented

- No Android application. No APK, no Gradle project.
- No gesture recognition model — extension point only.
- No audio distress classifier — interface and mock only.
- No caregiver notification, no multi-device support, no companion app.
- No on-device NPU execution has been performed or timed from this code. The
  architecture is written for it; the measurement has not been done.

## Real-world safeguards a deployment would need

A system that can summon help must also handle being wrong: escalation paths
when nobody responds, a way to reach a real emergency service, tested failure
modes when the phone is offline or out of battery, and informed consent from
the person being monitored. None of that is in scope here, and none of it
should be assumed.

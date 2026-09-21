# Technical architecture

    PERCEIVE  ->  UNDERSTAND  ->  DECIDE  ->  ACT

![System architecture](../architecture/system_architecture.png)

## Layer by layer

| Layer | Package | Responsibility |
|---|---|---|
| Perception | `src/silentguard/perception/` | Pose extraction, motion analysis, fall scoring |
| Audio (extension) | `src/silentguard/audio/` | Interface for a distress-sound signal |
| Voice | `src/silentguard/voice/` | Utterance → intent → validated appliance command |
| Decision | `src/silentguard/decision/` | Explainable state machine, confirmation window |
| Actions | `src/silentguard/actions/` | Dispatch to IR and local alerting |
| Appliances | `src/silentguard/appliances/` | Device profiles and IR command resolution |
| Platform | `src/silentguard/platform/` | Device integration contracts (no implementation) |
| Runtime | `src/silentguard/runtime.py` | Wires all of the above into one loop |

## Design rules the code follows

**The decision engine has no I/O.** It takes signals and a timestamp and
returns a state. It never reads a clock, opens a camera, or touches hardware.
That is why it is deterministic under test, and why the same rules can be
ported to a handset without change.

**The caller supplies time.** Every stage takes a timestamp from the frame
rather than calling `time.time()`. A 10-second confirmation window behaves the
same at 15 fps, at 30 fps, and in a test that jumps straight to t=11.

**Hardware sits behind an interface.** `ActionManager` talks to an
`IRController`, never to a device. Swapping the mock backend for a real one
changes one constructor argument.

**Nothing pretends to succeed.** Selecting a device IR backend with no binding
produces `UnavailableIRController`, which raises. For an emergency system, a
false success is worse than a visible failure.

**Every threshold lives in `config.yaml`.** No magic numbers are scattered
through the modules; `Config.with_overrides()` lets tests vary one value.

## The two modes share one action path

![Two modes](../architecture/two_modes.png)

Autonomous mode reaches `ActionManager.trigger_emergency_response()`.
On-demand mode reaches `ActionManager.dispatch()` or
`dispatch_device_command()`. Both terminate at the same `IRController`, so the
IR layer is exercised by both modes and tested once.

## Where speech recognition fits

`CommandParser` accepts a string. Any recogniser that produces a string —
on-device, streaming, or a platform API — is an adapter in front of it. A
speech model is deliberately not vendored here: it would add weight and a
model download without changing what this layer demonstrates.

## Data flow, and what is retained

Frames are read, converted to landmarks, scored, and dropped. The only state
kept between frames is a time-bounded deque of landmark coordinates (four
seconds by default) inside `MotionAnalyzer`. No frames, no audio, and no
recordings are written to disk by any code in this repository.

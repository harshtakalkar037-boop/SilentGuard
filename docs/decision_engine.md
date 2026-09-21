# Decision engine

![Decision flow](../architecture/decision_flow.png)

## States

| State | Meaning |
|---|---|
| `NORMAL` | No distress indicators |
| `FALL_SUSPECTED` | Confidence above `suspect_threshold`, still monitoring |
| `CONFIRMING` | Confidence above `confirm_threshold`; the cancel window is open |
| `EMERGENCY` | The window elapsed with no cancellation; actions dispatched |
| `CANCELLED` | Reserved for an explicit cancelled terminal state |

## The confirmation window

When confidence crosses `confirm_threshold`, the engine opens a window of
`confirmation_seconds` (12 by default; the 10–15 second range is the design
target). During it, the user can cancel by voice or gesture. If the window
elapses with no cancellation, the emergency is confirmed.

This is the false-alarm safeguard. A system that fires instantly will be
switched off by the second week; a system that never fires is useless. The
window is how both failures are avoided.

## Guarantees the tests enforce

**Actions fire exactly once.** `triggers_action` is true on the single update
that enters `EMERGENCY`, never again.

**Emergency is latched.** Once confirmed, a quiet frame cannot undo it. A
person who has fallen and lies still must not be un-rescued because the next
frame scored low.

**A cancel is honoured only while a window is open.** A cancel in `NORMAL` is a
no-op; a cancel after `EMERGENCY` does not unlatch.

**Every result carries a reason.** No state change is silent.

## Audio as corroboration, never as a trigger

Audio distress is disabled by default (`decision.use_audio_signal: false`).
When enabled, a score above `audio_distress_threshold` adds at most 0.10 to
confidence — and only where the pose pipeline already saw evidence. Audio alone
cannot raise an emergency, because a shout, a television and a dropped pan are
hard to separate acoustically. `test_audio_alone_cannot_raise_an_emergency`
pins this behaviour.

## Why the caller supplies the time

The engine never reads a clock. Timestamps arrive with the signals. That makes
a 12-second window testable in microseconds and identical at any frame rate.

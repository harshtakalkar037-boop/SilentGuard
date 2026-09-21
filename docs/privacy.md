# Privacy

## Local-first by architecture, not by policy

A privacy policy is a promise. An architecture with no upload path is a
property. SilentGuard is built as the second kind.

```
INPUT  ->  LOCAL INFERENCE  ->  LOCAL DECISION  ->  LOCAL ACTION
```

Designed around privacy-preserving on-device processing.

## What the code actually does

| Property | Status in this repository |
|---|---|
| Network calls | **None.** No module imports an HTTP client or opens a socket. |
| Frames written to disk | **None.** Frames are scored and dropped. |
| Audio written to disk | **None.** No audio is captured at all by default. |
| Accounts or credentials | **None.** No `.env` secret is required to run anything. |
| Retained state | A four-second deque of landmark coordinates, in memory only. |
| Telemetry or analytics | **None.** |

You can verify the first claim directly:

```bash
grep -rnE "requests|urllib|http|socket|boto3|firebase" src/
```

## Retention

`MotionAnalyzer` keeps landmark coordinates for `perception.history_seconds`
(4.0 by default) and evicts anything older on every update. Nothing else
persists between frames. Landmarks are nine `(x, y)` pairs — not an image, and
not enough to reconstruct one.

## User control

Monitoring is a mode the user enters, not a default state. The cancel window
means the system asks before it acts, and the person in the room can always
say no. `actions.on_emergency` is user-configurable: a household that wants
lights only, and no TV flash, edits one list.

## Honest limits

- A camera in a home is a meaningful intrusion even when nothing leaves the
  device. Placement, and whether to run at all, is the household's decision.
- These properties hold for the code in this repository. A production build
  that added a caregiver-notification feature would introduce a network path,
  and the claim above would have to be re-examined at that point rather than
  inherited.

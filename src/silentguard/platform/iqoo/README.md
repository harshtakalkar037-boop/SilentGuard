# iQOO hardware integration layer

**Status: integration contract only. This repository does not transmit IR.**

SilentGuard is designed around two hardware properties that a supported iQOO
handset provides and most flagships do not: an **IR blaster**, which lets the
phone act on the room rather than only notify about it, and **NPU headroom**,
which lets pose inference run locally with no cloud round-trip.

## Where the device implementation connects

One seam, defined in `../contracts.py`:

```python
class DeviceIRTransmitter(Protocol):
    def transmit(self, code_id: str, protocol: str, repeat: int = 1) -> bool: ...
    def is_available(self) -> bool: ...
```

A platform binding implements that Protocol and is wrapped by an
`IRController` (see `actions/ir_controller.py`). Nothing above that seam
changes: the decision engine, action manager, and appliance registry are
already device-agnostic.

## Honest statement of limits

- **No vendor API name is invented here.** IR transmission on Android is
  reached through the platform's consumer-IR facility where the OEM exposes
  it; the exact surface available on a given iQOO build must be confirmed
  against that device's documentation before it is written down.
- **No claim is made that this code has transmitted an IR command.** The
  shipped backend is `MockIRController`, and every line it prints is labelled
  `[MOCK IR]`.
- **Selecting `ir_backend: device` without a binding raises an error** rather
  than silently succeeding. That is deliberate: an emergency system that
  reports a fake success is worse than one that reports a failure.

## Setup step a real deployment needs

IR codes are per-household. A real build captures them during onboarding
(learn-from-existing-remote, or a code database lookup by appliance model) and
stores them against the `code_id` keys in `appliances/profiles/*.json`. The
identifiers in this repository are placeholders and are labelled as such in
every profile.

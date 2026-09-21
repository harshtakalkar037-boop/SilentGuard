# IR integration

## The layers

```
ActionManager
    -> CommandRegistry      resolves device + command -> code_id
    -> IRController         transmits (or refuses)
         MockIRController         development; prints, never transmits
         UnavailableIRController  selected but unbound; raises
         [device binding]         not implemented in this repository
```

## Appliance profiles

`src/silentguard/appliances/profiles/*.json`, one per device:

```json
{
  "device": "tv",
  "protocol": "NEC",
  "commands": {
    "SOS": {"code_id": "TV_NEC_SOS_FLASH", "repeat": 6}
  }
}
```

Adding an appliance is adding a file. No code changes.

## code_id values are placeholders

The identifiers shipped here are **names, not captured waveforms**, and every
profile says so. IR codes are specific to an appliance model, so a real
deployment captures them at setup — learning from the household's existing
remote, or a lookup by appliance model — and stores them against these keys.

## Where the device implementation attaches

One seam, `DeviceIRTransmitter` in `src/silentguard/platform/contracts.py`:

```python
def transmit(self, code_id: str, protocol: str, repeat: int = 1) -> bool: ...
def is_available(self) -> bool: ...
```

A platform binding implements it; an `IRController` wraps it. Nothing above
that seam changes.

## What this repository deliberately does not do

- **It does not transmit IR.** The shipped backend is the mock.
- **It does not name a vendor API.** Android reaches consumer IR through the
  platform facility where the OEM exposes it. The exact surface on a given iQOO
  build must be confirmed against that device's documentation before it is
  written down here, so it is not written down here.
- **It does not fail silently.** Setting `actions.ir_backend: device` with no
  binding yields a controller that raises `IRTransmissionError` naming this
  document. Try it:

```bash
python demo/mock_ir_demo.py --backend device
```

The local alert still fires in that run. Degraded, but never silent — that is
the intended failure mode for a safety system.

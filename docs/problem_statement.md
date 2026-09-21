# Problem statement

## Who this is for

- Elderly people living alone
- People with mobility limitations
- People recovering from surgery or illness at home
- Anyone who may be unable to reach a phone after an incident

## The gap

A person falls while alone. The failure is not that nobody *can* help — it is
that nobody *knows*. The person may be unable to reach a phone, unlock it, find
a contact, or speak loudly enough to be heard. The window in which help matters
most is the window in which they are least able to ask for it.

The existing options each give something up:

| Option | What it gives up |
|---|---|
| Wearable fall sensor | Gets taken off, forgotten, or left charging. Alerts, does not act. |
| Subscription camera | Needs internet and a monthly payment. Streams a private room off-site. |
| Generic voice assistant | Needs the user to speak a command — the exact thing a fall may prevent. |
| A phone with an SOS button | Needs the user to reach and press it. |

Every one of them assumes a user who can still act.

## What SilentGuard changes

SilentGuard removes that assumption. The phone watches, reasons about what it
saw, and initiates a response without waiting for a command.

The system is designed around five constraints, all of which shape the code in
this repository:

1. **No mandatory cloud.** Inference and decision-making happen on the device.
2. **No mandatory wearable.** The sensor is a phone that is already in the room.
3. **No mandatory subscription.** There is no recurring-revenue component.
4. **Privacy by architecture.** Frames are processed and discarded; there is no
   upload path to leak through.
5. **Physical action, not just notification.** A notification nobody is present
   to read is not a response. Turning the lights on and flashing the TV is.

## Why connectivity matters here specifically

Rural and low-income households are exactly where a cloud-dependent safety
product fails, and exactly where the need is growing. India had 149 million
people aged 60 and over in 2022, projected to reach 347 million by 2050
(UNFPA, *India Ageing Report 2023*). A safety system that stops working when
the router does is not a safety system for that population.

## Scope of this repository

This repository is the technical implementation behind the concept: a runnable
prototype of the perception → decision → action pipeline. It is not a shipping
consumer product. `limitations.md` states precisely what it does not do.

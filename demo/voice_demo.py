#!/usr/bin/env python3
"""On-Demand Control Mode demo.

    utterance -> intent parsing -> appliance command -> IR action

Speech-to-text is an adapter: anything that produces a string can feed this.
The demo takes strings directly, so it runs with no microphone and no model
download.

Examples:
    python demo/voice_demo.py                          # scripted utterances
    python demo/voice_demo.py --interactive            # type your own
    python demo/voice_demo.py --say "turn on the lights"
"""

from __future__ import annotations

import argparse
import sys

import _bootstrap  # noqa: F401

from silentguard.actions import ActionManager
from silentguard.config import load_config
from silentguard.voice import CommandParser, ParseError
from silentguard.voice.intent import IntentType

SCRIPTED = (
    "turn on the lights",
    "lights off",
    "fan off",
    "tv volume up",
    "make me a sandwich",
    "I am fine",
    "help me",
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SilentGuard on-demand control demo",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--say", default=None, help="Process a single utterance and exit.")
    parser.add_argument(
        "--interactive", action="store_true", help="Read utterances from stdin."
    )
    return parser


def handle(utterance: str, parser: CommandParser, actions: ActionManager) -> None:
    """Parse one utterance and route it, printing every stage."""
    print(f'\n> "{utterance}"')
    try:
        intent = parser.parse(utterance)
    except ParseError as exc:
        print(f"  [PARSE] rejected: {exc}")
        return

    print(f"  [INTENT] {intent.type}  confidence={intent.confidence:.2f}")
    print(f"           {intent.explanation}")

    if intent.type is IntentType.CANCEL_EMERGENCY:
        print("  [ROUTE ] cancellation signal -> decision engine (cancels the window)")
        return
    if intent.type is IntentType.RAISE_EMERGENCY:
        print("  [ROUTE ] manual emergency -> action manager")
        for result in actions.trigger_emergency_response():
            status = "ok" if result.succeeded else "FAILED"
            print(f"  [ACTION] {result.action:<12} {status:<7} via {result.via}")
        return
    if not intent.is_actionable:
        print("  [ACTION] none - no appliance command recognised")
        return

    named = parser.action_name(intent)
    if named:
        result = actions.dispatch(named)
        print(f"  [ROUTE ] mapped to named action {named}")
    else:
        result = actions.dispatch_device_command(intent.device, intent.command)
        print(f"  [ROUTE ] direct appliance command {intent.device}.{intent.command}")
    status = "ok" if result.succeeded else "FAILED"
    tag = " (simulated)" if result.simulated else ""
    print(f"  [ACTION] {status:<7} {result.detail}{tag}")


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = load_config()
    parser = CommandParser(config=config)
    actions = ActionManager(config, verbose=False)

    print("=" * 66)
    print("  SilentGuard - On-Demand Control Mode")
    print("  utterance -> intent -> appliance command -> IR")
    print("=" * 66)
    print(f"  known devices : {', '.join(parser.registry.devices)}")
    print(f"  ir backend    : {actions.ir.name} (simulated={not actions.ir.is_real_hardware})")

    if args.say:
        handle(args.say, parser, actions)
        return 0

    if args.interactive:
        print("  type an utterance, or 'quit' to exit")
        while True:
            try:
                line = input("\nsay> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if line.lower() in ("quit", "exit"):
                break
            if line:
                handle(line, parser, actions)
        return 0

    for utterance in SCRIPTED:
        handle(utterance, parser, actions)
    print("\n" + "=" * 66)
    print(f"  {len(actions.history)} action(s) dispatched, all simulated via the mock IR backend.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

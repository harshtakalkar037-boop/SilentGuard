#!/usr/bin/env python3
"""IR layer demo: appliance profiles, command resolution, mock transmission.

Shows what the action layer would send to hardware, and where the real
device binding attaches. Nothing here transmits IR.

Examples:
    python demo/mock_ir_demo.py
    python demo/mock_ir_demo.py --device tv --command SOS
    python demo/mock_ir_demo.py --backend device    # shows the honest failure
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from silentguard.actions import ActionManager
from silentguard.appliances import CommandRegistry
from silentguard.appliances.command_registry import ApplianceError
from silentguard.config import load_config


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SilentGuard IR layer demo",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--device", default=None, help="Send one command to this device.")
    parser.add_argument("--command", default=None, help="Command to send.")
    parser.add_argument(
        "--backend",
        choices=("mock", "device"),
        default=None,
        help="Override actions.ir_backend for this run.",
    )
    return parser


def show_registry(registry: CommandRegistry) -> None:
    """Print every loaded appliance profile and its commands."""
    print("\nLoaded appliance profiles")
    print("-" * 66)
    for device in registry.devices:
        profile = registry.profile(device)
        print(f"  {profile.device:<8} {profile.display_name:<22} protocol={profile.protocol}")
        for command in sorted(profile.commands):
            resolved = registry.resolve(device, command)
            repeat = f" x{resolved.repeat}" if resolved.repeat > 1 else ""
            print(f"      {command:<12} -> {resolved.code_id}{repeat}")
    print("-" * 66)
    print("  code_id values are placeholders; real codes are captured per")
    print("  household at setup. See docs/ir_integration.md.")


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = load_config()
    if args.backend:
        config = config.with_overrides(**{"actions.ir_backend": args.backend})

    registry = CommandRegistry()
    actions = ActionManager(config, registry=registry, verbose=True)

    print("=" * 66)
    print("  SilentGuard - IR Action Layer")
    print("=" * 66)
    print(f"  backend            : {actions.ir.name}")
    print(f"  real hardware      : {actions.ir.is_real_hardware}")
    print(f"  currently available: {actions.ir.available()}")

    show_registry(registry)

    if args.device and args.command:
        print(f"\nSending {args.device}.{args.command}")
        try:
            result = actions.dispatch_device_command(args.device, args.command)
        except ApplianceError as exc:
            print(f"  ERROR: {exc}")
            return 1
        print(f"  succeeded={result.succeeded} via={result.via} detail={result.detail}")
        return 0 if result.succeeded else 1

    print("\nDispatching the configured emergency action set")
    print("-" * 66)
    for result in actions.trigger_emergency_response():
        status = "ok" if result.succeeded else "FAILED"
        print(f"  {result.action:<12} {status:<7} via {result.via}")
        if not result.succeeded:
            print(f"      {result.detail}")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Autonomous Guardian Mode demo.

Runs the full pipeline and prints every stage:

    camera/synthetic pose -> fall signals -> decision engine -> actions

Examples:
    python demo/fall_demo.py                       # scripted fall (no camera)
    python demo/fall_demo.py --scenario sit_down   # must NOT trigger
    python demo/fall_demo.py --cancel-at 8         # user cancels in the window
    python demo/fall_demo.py --source mediapipe --video clip.mp4
    python demo/fall_demo.py --source mediapipe --camera 0
"""

from __future__ import annotations

import argparse
import sys

import _bootstrap  # noqa: F401  (import for its side effect: sys.path)

from silentguard.config import load_config
from silentguard.perception import build_pose_detector
from silentguard.perception.pose_detector import SyntheticPoseSource
from silentguard.runtime import GuardianRuntime

BAR_WIDTH = 24


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SilentGuard autonomous guardian demo",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=("synthetic", "mediapipe"),
        default="synthetic",
        help="Pose source. 'synthetic' needs no camera.",
    )
    parser.add_argument(
        "--scenario",
        choices=SyntheticPoseSource.SCENARIOS,
        default="fall",
        help="Scripted scenario (synthetic source only).",
    )
    parser.add_argument("--video", default=None, help="Video file (mediapipe source).")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (mediapipe source).")
    parser.add_argument(
        "--cancel-at",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Simulate the user cancelling at this timestamp.",
    )
    parser.add_argument(
        "--every",
        type=int,
        default=15,
        help="Print a status line every N frames.",
    )
    return parser


def confidence_bar(value: float) -> str:
    """Render a confidence value as a fixed-width text bar."""
    filled = int(round(min(max(value, 0.0), 1.0) * BAR_WIDTH))
    return "#" * filled + "." * (BAR_WIDTH - filled)


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = load_config()

    try:
        pose_source = build_pose_detector(
            source=args.source,
            scenario=args.scenario,
            video=args.video,
            camera=args.camera,
            min_visibility=float(config.get("perception.min_visibility", 0.5)),
        )
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    cancel_hook = None
    if args.cancel_at is not None:
        cancel_at = float(args.cancel_at)
        cancel_hook = lambda now: now >= cancel_at  # noqa: E731

    runtime = GuardianRuntime(
        config=config, pose_source=pose_source, cancel_hook=cancel_hook, verbose=False
    )

    simulated_pose = getattr(pose_source, "is_simulated", False)
    print("=" * 66)
    print("  SilentGuard - Autonomous Guardian Mode")
    print("  PERCEIVE -> UNDERSTAND -> DECIDE -> ACT")
    print("=" * 66)
    print(f"  pose source      : {args.source}" + (f" ({args.scenario})" if args.source == "synthetic" else ""))
    print(f"  ir backend       : {runtime.actions.ir.name} (simulated={not runtime.actions.ir.is_real_hardware})")
    print(f"  confirm window   : {runtime.engine.thresholds.confirmation_seconds:.0f}s")
    print(f"  confirm threshold: {runtime.engine.thresholds.confirm_threshold:.2f}")
    if simulated_pose:
        print("  NOTE: pose data is scripted simulation, not a recording of a person.")
    print("-" * 66)

    last_state = None
    for index, tick in enumerate(runtime.run()):
        decision = tick.decision
        show = decision.changed or index % max(args.every, 1) == 0
        if show:
            remaining = (
                f"  cancel-in={decision.seconds_remaining:>5.1f}s"
                if decision.seconds_remaining is not None
                else ""
            )
            print(
                f"t={tick.frame.timestamp:6.2f}s  "
                f"conf={decision.confidence:4.2f} [{confidence_bar(decision.confidence)}]  "
                f"{str(decision.state):<14}{remaining}"
            )
        if decision.changed and decision.state != last_state:
            print(f"           -> {decision.reason}")
            if decision.evidence:
                for item in decision.evidence:
                    print(f"              evidence: {item}")
            last_state = decision.state
        if tick.actions:
            print("-" * 66)
            print("[ACTION] emergency response dispatched:")
            for result in tick.actions:
                status = "ok" if result.succeeded else "FAILED"
                tag = " (simulated)" if result.simulated else ""
                print(f"  - {result.action:<12} {status:<7} via {result.via}{tag}")
            print("-" * 66)

    summary = runtime.summary()
    print("=" * 66)
    print("  RUN SUMMARY")
    print(f"  frames processed : {summary['frames']}")
    print(f"  peak confidence  : {summary['peak_confidence']:.2f}")
    print(f"  final state      : {summary['final_state']}")
    print(f"  transitions      : {' | '.join(summary['transitions']) or 'none'}")
    print(f"  actions          : {', '.join(summary['actions']) or 'none'}")
    if summary["actions"]:
        print("  NOTE: all actions above were simulated. No IR hardware was driven.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Regenerates the images in this directory from real demo output.

Every PNG here is a rendering of stdout captured by actually running the demo
commands in this repository. Nothing is mocked up in an image editor, and
nothing depicts hardware that was not used: the runs are on the synthetic pose
source with the mock IR backend, and the captured text says so on its face.

Usage:
    python screenshots/capture.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Sequence

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent

BG = (13, 24, 43)
CHROME = (24, 40, 66)
TEXT = (222, 232, 242)
TEAL = (78, 186, 200)
AMBER = (244, 163, 0)
GREEN = (126, 200, 140)
MUTED = (140, 158, 182)
CAPTION_BG = (30, 48, 80)

MONO_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
)
SANS_CANDIDATES = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",)


def load_font(candidates: Sequence[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:  # pragma: no cover
                continue
    return ImageFont.load_default()


def run_demo(args: Sequence[str]) -> List[str]:
    """Run a demo command from the repo root and return its stdout lines."""
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"demo failed: {' '.join(args)}\n{completed.stderr.strip()}"
        )
    return completed.stdout.splitlines()


def line_color(line: str) -> tuple[int, int, int]:
    stripped = line.strip()
    if stripped.startswith("[ACTION]") or "EMERGENCY" in stripped:
        return AMBER
    if stripped.startswith(("[MOCK IR]", "[LOCAL ALERT")):
        return AMBER
    if stripped.startswith(("[INTENT]", "[ROUTE ]")):
        return TEAL
    if stripped.startswith("=") or stripped.startswith("-"):
        return MUTED
    if "ok" in stripped.split() or "CONFIRMING" in stripped:
        return GREEN if "ok" in stripped.split() else TEXT
    if stripped.startswith("NOTE:") or "NOTE:" in stripped:
        return MUTED
    return TEXT


def render_terminal(
    lines: Sequence[str],
    title: str,
    caption: Sequence[str] | str,
    out_name: str,
) -> Path:
    """Render captured stdout as a terminal window image."""
    mono = load_font(MONO_CANDIDATES, 14)
    sans = load_font(SANS_CANDIDATES, 15)
    caption_font = load_font(SANS_CANDIDATES, 13)

    char_w = mono.getlength("M")
    longest = max((len(line) for line in lines), default=60)
    caption_px = max(
        (caption_font.getlength(text) for text in
         (caption if isinstance(caption, (list, tuple)) else [caption])),
        default=0,
    )
    width = int(max(char_w * (longest + 4), 720, caption_px + 56)) + 48
    line_h = 21
    chrome_h = 42
    caption_lines = caption if isinstance(caption, (list, tuple)) else [caption]
    caption_h = 26 + 18 * len(caption_lines)
    height = chrome_h + len(lines) * line_h + 32 + caption_h

    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    # Window chrome.
    draw.rectangle((0, 0, width, chrome_h), fill=CHROME)
    for index, color in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        draw.ellipse((18 + index * 20, 16, 30 + index * 20, 28), fill=color)
    draw.text((96, 13), title, font=sans, fill=MUTED)

    y = chrome_h + 14
    for line in lines:
        draw.text((24, y), line, font=mono, fill=line_color(line))
        y += line_h

    # Caption strip: states plainly what the image is.
    draw.rectangle((0, height - caption_h, width, height), fill=CAPTION_BG)
    caption_y = height - caption_h + 13
    for text in caption_lines:
        draw.text((24, caption_y), text, font=caption_font, fill=MUTED)
        caption_y += 18

    path = OUT_DIR / out_name
    image.save(path)
    return path


CAPTION = (
    "Captured from real terminal output of this repository.",
    "Synthetic pose source + mock IR backend - no hardware was driven.",
)


def main() -> int:
    fall = run_demo(["demo/fall_demo.py", "--every", "40"])
    cancel = run_demo(["demo/fall_demo.py", "--cancel-at", "8", "--every", "60"])
    voice = run_demo(["demo/voice_demo.py"])
    ir = run_demo(["demo/mock_ir_demo.py"])

    # Slice the captured output into focused views.
    confirm_end = next(
        (i for i, line in enumerate(fall) if "cancel-in" in line and "10." in line),
        18,
    )
    render_terminal(
        fall[: confirm_end + 1],
        "python demo/fall_demo.py",
        CAPTION,
        "fall_detected.png",
    )

    emergency_start = next(
        (i for i, line in enumerate(fall) if "EMERGENCY" in line), 0
    )
    render_terminal(
        fall[max(emergency_start - 2, 0) :],
        "python demo/fall_demo.py",
        CAPTION,
        "emergency_triggered.png",
    )

    cancel_start = next(
        (i for i, line in enumerate(cancel) if "CONFIRMING" in line), 0
    )
    render_terminal(
        cancel[max(cancel_start - 1, 0) :],
        "python demo/fall_demo.py --cancel-at 8",
        CAPTION,
        "confirmation_cancelled.png",
    )

    render_terminal(
        voice[:26],
        "python demo/voice_demo.py",
        CAPTION,
        "voice_control.png",
    )

    render_terminal(
        ir[:24],
        "python demo/mock_ir_demo.py",
        CAPTION,
        "ir_layer.png",
    )

    for path in sorted(OUT_DIR.glob("*.png")):
        print(f"wrote {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

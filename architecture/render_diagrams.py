#!/usr/bin/env python3
"""Renders the architecture diagrams to PNG.

The ``.mmd`` files in this directory are the source of truth and render
natively on GitHub. This script produces matching PNGs in the SilentGuard
palette for use outside GitHub (slides, PDFs, offline viewing).

Usage:
    python architecture/render_diagrams.py

Requires Pillow (see requirements.txt).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent

NAVY = (18, 33, 59)
NAVY_CARD = (30, 48, 80)
TEAL = (31, 122, 140)
AMBER = (244, 163, 0)
WHITE = (255, 255, 255)
MUTED = (167, 180, 196)
EDGE = (99, 118, 145)

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a bundled font, falling back to Pillow's default."""
    order = FONT_CANDIDATES if bold else tuple(reversed(FONT_CANDIDATES))
    for path in order:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:  # pragma: no cover - font-specific
                continue
    return ImageFont.load_default()


class Node:
    """A box in a diagram, positioned by pixel centre."""

    def __init__(
        self,
        key: str,
        label: str,
        center: Tuple[int, int],
        width: int = 190,
        height: int = 68,
        style: str = "default",
    ) -> None:
        self.key = key
        self.label = label
        self.cx, self.cy = center
        self.width = width
        self.height = height
        self.style = style

    @property
    def box(self) -> Tuple[int, int, int, int]:
        return (
            self.cx - self.width // 2,
            self.cy - self.height // 2,
            self.cx + self.width // 2,
            self.cy + self.height // 2,
        )

    def anchor(self, side: str) -> Tuple[int, int]:
        left, top, right, bottom = self.box
        return {
            "left": (left, self.cy),
            "right": (right, self.cy),
            "top": (self.cx, top),
            "bottom": (self.cx, bottom),
        }[side]


FILLS: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]] = {
    # style: (fill, outline, text)
    "default": (NAVY_CARD, (58, 80, 118), WHITE),
    "input": (NAVY_CARD, TEAL, WHITE),
    "ai": (TEAL, TEAL, WHITE),
    "decision": (AMBER, AMBER, NAVY),
    "action": (AMBER, AMBER, NAVY),
    "safe": (NAVY_CARD, TEAL, MUTED),
}


def wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Greedy word wrap to ``max_width`` pixels."""
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_node(draw: ImageDraw.ImageDraw, node: Node, font: ImageFont.FreeTypeFont) -> None:
    fill, outline, text_color = FILLS.get(node.style, FILLS["default"])
    left, top, right, bottom = node.box
    if node.style == "decision":
        # Diamond for decision points.
        draw.polygon(
            [(node.cx, top), (right, node.cy), (node.cx, bottom), (left, node.cy)],
            fill=fill,
            outline=outline,
        )
    else:
        draw.rounded_rectangle(node.box, radius=12, fill=fill, outline=outline, width=2)

    lines = wrap(node.label, font, node.width - 24, draw)
    line_height = font.size + 4
    start_y = node.cy - (len(lines) * line_height) // 2
    for index, line in enumerate(lines):
        width = draw.textlength(line, font=font)
        draw.text(
            (node.cx - width / 2, start_y + index * line_height),
            line,
            font=font,
            fill=text_color,
        )


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: Tuple[int, int],
    end: Tuple[int, int],
    label: str = "",
    font: ImageFont.FreeTypeFont | None = None,
    waypoints: Sequence[Tuple[int, int]] = (),
    label_at: Tuple[int, int] | None = None,
) -> None:
    points = [start, *waypoints, end]
    draw.line(points, fill=EDGE, width=3, joint="curve")

    # Arrow head on the final segment.
    (x1, y1), (x2, y2) = points[-2], points[-1]
    dx, dy = x2 - x1, y2 - y1
    length = max((dx * dx + dy * dy) ** 0.5, 1e-6)
    ux, uy = dx / length, dy / length
    size = 11
    left = (x2 - size * ux - size * 0.55 * uy, y2 - size * uy + size * 0.55 * ux)
    right = (x2 - size * ux + size * 0.55 * uy, y2 - size * uy - size * 0.55 * ux)
    draw.polygon([(x2, y2), left, right], fill=EDGE)

    if label and font is not None:
        anchor_point = label_at or points[len(points) // 2]
        width = draw.textlength(label, font=font)
        draw.text(
            (anchor_point[0] - width / 2, anchor_point[1] - 22),
            label,
            font=font,
            fill=AMBER,
        )


def render(
    name: str,
    title: str,
    size: Tuple[int, int],
    nodes: Sequence[Node],
    edges: Sequence[dict],
) -> Path:
    """Render one diagram and return the written path."""
    image = Image.new("RGB", size, NAVY)
    draw = ImageDraw.Draw(image)
    title_font = load_font(26, bold=True)
    node_font = load_font(15, bold=True)
    edge_font = load_font(13, bold=True)

    draw.text((34, 26), title, font=title_font, fill=WHITE)
    draw.text((34, 62), "SilentGuard", font=edge_font, fill=TEAL)

    index = {node.key: node for node in nodes}
    for edge in edges:
        source, target = index[edge["from"]], index[edge["to"]]
        draw_arrow(
            draw,
            source.anchor(edge.get("from_side", "right")),
            target.anchor(edge.get("to_side", "left")),
            label=edge.get("label", ""),
            font=edge_font,
            waypoints=edge.get("waypoints", ()),
            label_at=edge.get("label_at"),
        )
    for node in nodes:
        draw_node(draw, node, node_font)

    path = OUT_DIR / f"{name}.png"
    image.save(path)
    return path


def system_architecture() -> Path:
    nodes = [
        Node("cam", "Camera", (150, 170), style="input"),
        Node("mic", "Microphone", (150, 270), style="input"),
        Node("voice", "Voice / Gesture", (150, 370), style="input"),
        Node("pre", "Preprocessing", (400, 270)),
        Node("ai", "On-Device AI Inference", (650, 270), width=210, style="ai"),
        Node("dec", "Decision Engine", (920, 270), width=200, style="decision", height=96),
        Node("act", "Action Manager", (1180, 270), width=190, style="action"),
        Node("ir", "IR Controller", (1180, 400)),
        Node("alert", "Local Alert", (1180, 140)),
        Node("appl", "Lights / TV / Fan", (1180, 500), style="input"),
    ]
    edges = [
        {"from": "cam", "to": "pre", "to_side": "left"},
        {"from": "mic", "to": "pre", "to_side": "left"},
        {"from": "voice", "to": "pre", "to_side": "left"},
        {"from": "pre", "to": "ai"},
        {"from": "ai", "to": "dec"},
        {"from": "dec", "to": "act"},
        {"from": "act", "to": "ir", "from_side": "bottom", "to_side": "top"},
        {"from": "act", "to": "alert", "from_side": "top", "to_side": "bottom"},
        {"from": "ir", "to": "appl", "from_side": "bottom", "to_side": "top"},
    ]
    return render(
        "system_architecture",
        "System Architecture - local input to physical action",
        (1360, 600),
        nodes,
        edges,
    )


def ai_pipeline() -> Path:
    nodes = [
        Node("a", "Camera Input", (250, 150), style="input"),
        Node("b", "Pose Estimation", (250, 260), style="ai"),
        Node("c", "Motion + Posture Analysis", (250, 370), width=230, style="ai"),
        Node("d", "Fall Confidence", (250, 480), style="ai"),
        Node("e", "10-15s Confirmation Window", (250, 590), width=240),
        Node("f", "Cancelled?", (250, 715), width=200, height=110, style="decision"),
        Node("g", "Emergency Confirmed", (660, 845), width=210, style="action"),
        Node("h", "IR / SOS / Local Alert", (660, 955), width=210, style="action"),
        Node("i", "Return to Safe State", (660, 585), width=210, style="safe"),
    ]
    edges = [
        {"from": "a", "to": "b", "from_side": "bottom", "to_side": "top"},
        {"from": "b", "to": "c", "from_side": "bottom", "to_side": "top"},
        {"from": "c", "to": "d", "from_side": "bottom", "to_side": "top"},
        {"from": "d", "to": "e", "from_side": "bottom", "to_side": "top"},
        {"from": "e", "to": "f", "from_side": "bottom", "to_side": "top"},
        {"from": "f", "to": "i", "from_side": "right", "to_side": "left",
         "label": "YES", "waypoints": [(470, 715), (470, 585)],
         "label_at": (470, 660)},
        {"from": "f", "to": "g", "from_side": "bottom", "to_side": "left",
         "label": "NO", "waypoints": [(250, 845)], "label_at": (350, 870)},
        {"from": "g", "to": "h", "from_side": "bottom", "to_side": "top"},
    ]
    return render(
        "ai_pipeline",
        "Autonomous Safety Flow - detection to action",
        (960, 1060),
        nodes,
        edges,
    )


def two_modes() -> Path:
    nodes = [
        Node("a", "SilentGuard", (170, 250), width=200, style="ai"),
        Node("b", "Autonomous Guardian Mode", (500, 150), width=250),
        Node("c", "On-Demand Control Mode", (500, 360), width=250),
        Node("d", "Detect -> Confirm -> Act", (840, 150), width=250, style="action"),
        Node("e", "Voice / Gesture -> Intent -> IR", (840, 360), width=260, style="action"),
    ]
    edges = [
        {"from": "a", "to": "b"},
        {"from": "a", "to": "c"},
        {"from": "b", "to": "d"},
        {"from": "c", "to": "e"},
    ]
    return render("two_modes", "Two Modes. One Phone.", (1040, 500), nodes, edges)


def decision_flow() -> Path:
    nodes = [
        Node("a", "Fall Suspected", (240, 150), style="input"),
        Node("b", "Check Confidence", (240, 260)),
        Node("c", "Check Posture", (240, 370)),
        Node("d", "Check Inactivity", (240, 480)),
        Node("e", "Confirmation Window", (240, 590), width=220),
        Node("f", "User Cancels?", (240, 715), width=200, height=110, style="decision"),
        Node("g", "Emergency", (620, 845), style="action"),
        Node("h", "Safe State", (620, 585), style="safe"),
    ]
    edges = [
        {"from": "a", "to": "b", "from_side": "bottom", "to_side": "top"},
        {"from": "b", "to": "c", "from_side": "bottom", "to_side": "top"},
        {"from": "c", "to": "d", "from_side": "bottom", "to_side": "top"},
        {"from": "d", "to": "e", "from_side": "bottom", "to_side": "top"},
        {"from": "e", "to": "f", "from_side": "bottom", "to_side": "top"},
        {"from": "f", "to": "h", "from_side": "right", "to_side": "left",
         "label": "YES", "waypoints": [(440, 715), (440, 585)],
         "label_at": (440, 660)},
        {"from": "f", "to": "g", "from_side": "bottom", "to_side": "left",
         "label": "NO", "waypoints": [(240, 845)], "label_at": (330, 870)},
    ]
    return render(
        "decision_flow", "Decision Engine - explainable state machine", (880, 960), nodes, edges
    )


def main() -> int:
    for builder in (system_architecture, ai_pipeline, two_modes, decision_flow):
        print(f"wrote {builder().name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

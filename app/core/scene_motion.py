"""Safe scene motion settings and FFmpeg zoom/pan expressions."""

import math
from typing import Any, Dict, List


DEFAULT_MOTION = {"type": "none", "strength": "subtle"}
MOTION_TYPES = {
    "none", "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up",
    "pan_down", "drift_left", "drift_right", "shake",
}
MOTION_STRENGTHS = {"subtle", "medium"}


def normalize_motion(value: Any) -> Dict[str, str]:
    """Return a supported motion, falling back as a whole for malformed input."""
    if (not isinstance(value, dict)
            or not isinstance(value.get("type"), str)
            or not isinstance(value.get("strength"), str)
            or value["type"] not in MOTION_TYPES
            or value["strength"] not in MOTION_STRENGTHS):
        return DEFAULT_MOTION.copy()
    return {"type": value["type"], "strength": value["strength"]}


def _motion_range(motion: Dict[str, str]):
    kind, strength = motion["type"], motion["strength"]
    if kind == "zoom_in":
        return (1, 1.05 if strength == "subtle" else 1.10, 0, 0, 0, 0)
    if kind == "zoom_out":
        return (1.05 if strength == "subtle" else 1.10, 1, 0, 0, 0, 0)
    if kind.startswith("pan_"):
        distance = 0.03 if strength == "subtle" else 0.06
        # Six percent travel needs at least 1.12x to keep the image edge covered.
        scale = 1.06 if strength == "subtle" else 1.12
        x = distance * (1 if kind == "pan_right" else -1 if kind == "pan_left" else 0)
        y = distance * (1 if kind == "pan_down" else -1 if kind == "pan_up" else 0)
        return (scale, scale, 0, x, 0, y)
    if kind.startswith("drift_"):
        if strength == "subtle":
            start_scale, end_scale, start_x, end_x = 1.03, 1.06, 0.01, -0.02
        else:
            start_scale, end_scale, start_x, end_x = 1.04, 1.09, 0.02, -0.04
        direction = 1 if kind == "drift_left" else -1
        return (start_scale, end_scale, start_x * direction, end_x * direction, 0, 0)
    return (1, 1, 0, 0, 0, 0)


def get_motion_values(motion: Any, progress: float, frame: int, fps: int) -> Dict[str, float]:
    """Evaluate a motion at scene progress (translations are frame fractions or pixels)."""
    setting = normalize_motion(motion)
    progress = max(0.0, min(1.0, progress))
    eased = (1 - math.cos(math.pi * progress)) / 2
    start_scale, end_scale, start_x, end_x, start_y, end_y = _motion_range(setting)
    result = {
        "scale": start_scale + (end_scale - start_scale) * eased,
        "translate_x": start_x + (end_x - start_x) * eased,
        "translate_y": start_y + (end_y - start_y) * eased,
        "translate_x_px": 0.0,
        "translate_y_px": 0.0,
    }
    if setting["type"] == "shake" and fps > 0:
        amplitude = 2 if setting["strength"] == "subtle" else 4
        envelope = math.sin(math.pi * progress) ** 2
        result["translate_x_px"] = amplitude * envelope * math.sin(2 * math.pi * 11 * frame / fps)
        result["translate_y_px"] = amplitude * envelope * math.cos(2 * math.pi * 13 * frame / fps)
    return result


def _number(value: float) -> str:
    return f"{value:.8g}"


def _scene_expressions(motion: Dict[str, str], progress: str, frame: str,
                       width: int, height: int, fps: int):
    kind = motion["type"]
    if kind == "shake":
        amplitude = 2 if motion["strength"] == "subtle" else 4
        envelope = f"pow(sin(PI*({progress})),2)"
        scale = _number(1 + 2 * amplitude / min(width, height))
        x = f"({amplitude}/{width})*({envelope})*sin(2*PI*11*({frame})/{fps})"
        y = f"({amplitude}/{height})*({envelope})*cos(2*PI*13*({frame})/{fps})"
        return scale, x, y

    s0, s1, x0, x1, y0, y1 = _motion_range(motion)
    eased = f"(1-cos(PI*({progress})))/2"

    def between(start: float, end: float) -> str:
        if start == end:
            return _number(start)
        return f"({_number(start)}+({_number(end - start)})*({eased}))"

    return between(s0, s1), between(x0, x1), between(y0, y1)


def build_motion_filter(timeline: List[Dict[str, Any]], width: int, height: int, fps: int) -> str:
    """Build one FFmpeg filter for the existing concat stream and its scene frame ranges."""
    if fps <= 0:
        raise ValueError("fps must be positive")
    expressions = []
    for item in timeline:
        start_frame = round(item["start"] * fps)
        end_frame = round(item["end"] * fps)
        frame = f"on-{start_frame + 1}"
        progress = f"min(1,max(0,({frame})/{max(1, end_frame - start_frame - 1)}))"
        expressions.append((end_frame, _scene_expressions(
            normalize_motion(item.get("motion")), progress, frame, width, height, fps)))

    def select(component: int) -> str:
        value = expressions[-1][1][component]
        for end_frame, parts in reversed(expressions[:-1]):
            value = f"if(lt(on,{end_frame + 1}),{parts[component]},{value})"
        return value

    zoom = select(0)
    tx = select(1)
    ty = select(2)
    # Perspective samples fractional source coordinates; zoompan rounds pan
    # coordinates to even pixels, producing held frames followed by jumps.
    x = f"max(0,min(W-W/({zoom}),(W-W/({zoom}))/2-({tx})*W/({zoom})))"
    y = f"max(0,min(H-H/({zoom}),(H-H/({zoom}))/2-({ty})*H/({zoom})))"
    right = f"({x}+W/({zoom}))"
    bottom = f"({y}+H/({zoom}))"
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps},"
        f"perspective=x0='{x}':y0='{y}':x1='{right}':y1='{y}':"
        f"x2='{x}':y2='{bottom}':x3='{right}':y3='{bottom}':"
        "sense=source:eval=frame:interpolation=cubic,"
        "format=yuv420p"
    )

"""Versioned, project-local edit document for the video workspace.

Version 1 stores one image track, one voice track and a subtitle track.
Times are seconds with half-open [start, end) intervals; list order is clip
order. Clip IDs persist across edits. Missing media remains referenced so it
can be relinked later. Unknown fields are preserved on load/save, while an
unknown version is rejected instead of being silently rewritten.
"""

from copy import deepcopy
import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List


SCHEMA_VERSION = 1


def media_reference(project_dir: Path, path: Path) -> str:
    """Keep project media portable, while allowing explicitly selected external files."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def media_path(project_dir: Path, reference: str) -> Path:
    path = Path(reference)
    return path if path.is_absolute() else project_dir / path


def create_document(
    project_dir: Path,
    timeline: List[Dict[str, Any]],
    subtitles: Dict[int, Dict[str, Any]],
    image_dir: Path,
    audio_path: Path,
    srt_path: Path,
    aspect_ratio: str,
    fps: int,
    total_duration: float,
    subtitles_enabled: bool = False,
) -> Dict[str, Any]:
    """Import the existing automatic timeline once as an editable draft."""
    video_clips = []
    for item in timeline:
        video_clips.append({
            "id": f"scene-{item['index']}",
            "scene_id": item["id"],
            "media": media_reference(project_dir, item["image"]) if item.get("image") else None,
            "subtitle_ids": list(item.get("subtitles", [])),
            "start": float(item["start"]),
            "end": float(item["end"]),
            "motion": deepcopy(item.get("motion", {"type": "none", "strength": "subtle"})),
        })
    return {
        "version": SCHEMA_VERSION,
        "sources": {
            "image_dir": media_reference(project_dir, image_dir),
            "audio": media_reference(project_dir, audio_path),
            "srt": media_reference(project_dir, srt_path),
        },
        "settings": {"aspect_ratio": aspect_ratio, "fps": int(fps),
                     "subtitles_enabled": subtitles_enabled},
        "duration": float(total_duration),
        "tracks": {
            "video": video_clips,
            "audio": [{
                "id": "voice-1", "media": media_reference(project_dir, audio_path),
                "start": 0.0, "end": float(total_duration),
            }],
            "subtitles": [
                {"id": int(key), "start": float(value["start"]),
                 "end": float(value["end"]), "text": value["text"]}
                for key, value in sorted(subtitles.items())
            ],
        },
    }


def validate_document(document: Dict[str, Any]) -> None:
    from app.core.scene_motion import normalize_motion

    if (not isinstance(document, dict) or type(document.get("version")) is not int
            or document["version"] != SCHEMA_VERSION):
        raise ValueError("Phiên bản bản dựng chưa được hỗ trợ.")
    if not isinstance(document.get("sources"), dict) or not isinstance(document.get("settings"), dict):
        raise ValueError("File bản dựng thiếu nguồn hoặc cấu hình.")
    for name in ("image_dir", "audio", "srt"):
        if not isinstance(document["sources"].get(name), str) or not document["sources"][name].strip():
            raise ValueError(f"Nguồn {name} của bản dựng không hợp lệ.")
    settings = document["settings"]
    if settings.get("aspect_ratio") not in ("16:9", "9:16", "1:1"):
        raise ValueError("Tỉ lệ khung hình của bản dựng không được hỗ trợ.")
    if type(settings.get("fps")) is not int or settings["fps"] not in (24, 30, 60):
        raise ValueError("FPS của bản dựng không được hỗ trợ.")
    if type(settings.get("subtitles_enabled", False)) is not bool:
        raise ValueError("Cài đặt bật/tắt phụ đề không hợp lệ.")

    def valid_time(value):
        return type(value) in (int, float) and math.isfinite(value) and value >= 0

    if not valid_time(document.get("duration")) or document["duration"] <= 0:
        raise ValueError("Thời lượng bản dựng phải lớn hơn 0.")
    tracks = document.get("tracks")
    if not isinstance(tracks, dict):
        raise ValueError("File bản dựng thiếu các track.")
    for name in ("video", "audio", "subtitles"):
        clips = tracks.get(name)
        if not isinstance(clips, list) or (name != "subtitles" and not clips):
            raise ValueError(f"Track {name} không hợp lệ.")
        seen = set()
        for clip in clips:
            if not isinstance(clip, dict):
                raise ValueError(f"Clip trong track {name} không hợp lệ.")
            clip_id = clip.get("id")
            valid_id = (type(clip_id) is int and clip_id >= 0) if name == "subtitles" else (
                isinstance(clip_id, str) and bool(clip_id.strip()))
            if not valid_id or clip_id in seen:
                raise ValueError(f"ID clip trong track {name} bị thiếu hoặc trùng.")
            seen.add(clip_id)
            if (not valid_time(clip.get("start")) or not valid_time(clip.get("end"))
                    or clip["end"] <= clip["start"]):
                raise ValueError(f"Mốc thời gian của clip {clip_id} không hợp lệ.")
            if name == "subtitles":
                if not isinstance(clip.get("text"), str):
                    raise ValueError(f"Nội dung phụ đề {clip_id} không hợp lệ.")
                continue
            media = clip.get("media")
            if not (name == "video" and media is None) and (
                    not isinstance(media, str) or not media.strip()):
                raise ValueError(f"Đường dẫn media của clip {clip_id} không hợp lệ.")
            if name == "video":
                if not isinstance(clip.get("scene_id"), str) or not clip["scene_id"].strip():
                    raise ValueError(f"ID cảnh của clip {clip_id} không hợp lệ.")
                ids = clip.get("subtitle_ids", [])
                if not isinstance(ids, list) or any(type(value) is not int for value in ids):
                    raise ValueError(f"Danh sách phụ đề của clip {clip_id} không hợp lệ.")
                motion = clip.get("motion")
                if motion is not None and motion != normalize_motion(motion):
                    raise ValueError(f"Chuyển động của clip {clip_id} không hợp lệ.")
    voice = tracks["audio"][0]
    if (len(tracks["audio"]) != 1 or voice["start"] != 0
            or not math.isclose(voice["end"], document["duration"], abs_tol=0.001)):
        raise ValueError("Bản dựng phiên bản 1 cần một track voice chạy từ đầu đến hết video.")


def load_document(path: Path) -> Dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    validate_document(document)
    return document


def save_document(path: Path, document: Dict[str, Any], *,
                  overwrite: bool = False, backup: bool = False) -> None:
    """Write atomically; importing cannot replace an existing draft by default."""
    validate_document(document)
    payload = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".edit-", suffix=".tmp", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            if backup and path.exists():
                shutil.copyfile(path, path.with_suffix(path.suffix + ".bak"))
            os.replace(temp_path, path)
        else:
            # Atomically publish a complete file, failing if another draft exists.
            os.link(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def document_timeline(project_dir: Path, document: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Adapter for the current table and FFmpeg renderer until they read tracks directly."""
    validate_document(document)
    result = []
    for index, clip in enumerate(document["tracks"]["video"], start=1):
        start, end = float(clip["start"]), float(clip["end"])
        reference = clip.get("media")
        result.append({
            "index": index, "id": clip["scene_id"],
            "subtitles": list(clip.get("subtitle_ids", [])),
            "image": media_path(project_dir, reference) if reference else None,
            "motion": deepcopy(clip.get("motion") or {"type": "none", "strength": "subtle"}),
            "start": start, "end": end, "duration": round(end - start, 3),
        })
    return result


def render_timeline(project_dir: Path, document: Dict[str, Any], fps: int) -> List[Dict[str, Any]]:
    """Resolve the scene visible at each output frame, using preview's first-match rule.

    Gaps become black frames. Overlapping clips keep the earlier clip in list
    order, exactly as the playhead preview does. Boundaries are aligned to the
    first frame whose timestamp reaches the saved boundary.
    """
    clips = document_timeline(project_dir, document)
    duration = float(document["duration"])
    frame_count = math.ceil(duration * fps)
    boundaries = {0, frame_count}
    for clip in clips:
        boundaries.add(min(frame_count, math.ceil(clip["start"] * fps)))
        boundaries.add(min(frame_count, math.ceil(clip["end"] * fps)))
    result = []
    points = sorted(boundaries)
    for first, last in zip(points, points[1:]):
        if first == last:
            continue
        position = first / fps
        active = next((clip for clip in clips
                       if clip["start"] <= position < clip["end"]), None)
        segment = deepcopy(active) if active else {
            "id": "gap", "image": None,
            "motion": {"type": "none", "strength": "subtle"},
        }
        segment["motion_start"] = active["start"] if active else position
        segment["motion_end"] = active["end"] if active else last / fps
        segment["start"] = first / fps
        segment["end"] = last / fps
        segment["duration"] = (last - first) / fps
        result.append(segment)
    return result

"""Local, frame-by-frame Gemini watermark removal for video files."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import numpy as np
from PIL import Image

from app.core.video_creator import get_ffmpeg_path


ProgressCallback = Callable[[int, Optional[int]], None]
CancelCallback = Callable[[], bool]


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: Optional[float]


def get_veo_video_watermark_info(width: int, height: int) -> Dict[str, int]:
    """Gemini/Veo's video anchor; intentionally independent of image code."""
    min_dimension = min(width, height)
    size = max(24, min(int(round(min_dimension / 15.0)), min_dimension))
    margin = int(round(min_dimension / 10.0))
    return {
        "size": size,
        "x": max(0, width - margin - size),
        "y": max(0, height - margin - size),
        "width": size,
        "height": size,
    }


def resolve_video_box(
    anchor: Dict[str, int], width: int, height: int,
    scale: float, offset_x: int, offset_y: int,
) -> Dict[str, int]:
    """Match the web video's centre-based size and position adjustment."""
    size = max(8, min(int(round(anchor["size"] * scale)), min(width, height)))
    center_x = anchor["x"] + anchor["size"] / 2.0 + round(offset_x)
    center_y = anchor["y"] + anchor["size"] / 2.0 + round(offset_y)
    return {
        "size": size,
        "x": max(0, min(int(round(center_x - size / 2.0)), width - size)),
        "y": max(0, min(int(round(center_y - size / 2.0)), height - size)),
        "width": size,
        "height": size,
    }


def heal_upscaled_video_edge_seam(
    frame: np.ndarray, box: Dict[str, int], border: int = 1
) -> np.ndarray:
    """Soften only the narrow boundary where a cleaned ROI meets its frame."""
    if border < 1:
        return frame

    height, width, _ = frame.shape
    x, y = box["x"], box["y"]
    right, bottom = x + box["width"], y + box["height"]
    source = frame.copy()
    healed = frame.copy()
    x_start, x_end = max(0, x - border), min(width, right + border)
    y_start, y_end = max(0, y - border), min(height, bottom + border)

    for row in range(y_start, y_end):
        for col in range(x_start, x_end):
            inside_core = x + border <= col < right - border and y + border <= row < bottom - border
            outside_band = col < x or col >= right or row < y or row >= bottom
            on_inner_boundary = not outside_band and not inside_core
            if not (outside_band or on_inner_boundary):
                continue

            neighbours = source[
                max(0, row - 1):min(height, row + 2),
                max(0, col - 1):min(width, col + 2),
            ]
            average = neighbours.astype(np.float32).mean(axis=(0, 1))
            healed[row, col] = np.clip(
                source[row, col].astype(np.float32) * 0.35 + average * 0.65,
                0,
                255,
            ).astype(np.uint8)
    return healed


class VideoWatermarkRemover:
    """Standalone Gemini/Veo video watermark remover; it never calls image code."""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or get_ffmpeg_path()
        mask_path = Path(__file__).resolve().parent.parent / "assets" / "bg_96.png"
        if not mask_path.is_file():
            raise RuntimeError(f"Không tìm thấy mask watermark video: {mask_path}")
        self.video_mask = Image.open(mask_path).convert("RGBA")

    def remove_frame(
        self, frame: np.ndarray, gain: float = 0.6, scale: float = 1.01,
        offset_x: int = -24, offset_y: int = -24,
    ) -> tuple[np.ndarray, Dict[str, Any]]:
        """Inverse-alpha remove one RGB video frame using only the video mask."""
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
            raise ValueError("Frame phải là mảng RGB uint8 có dạng (height, width, 3).")

        height, width, _ = frame.shape
        box = resolve_video_box(
            get_veo_video_watermark_info(width, height), width, height,
            scale, offset_x, offset_y,
        )
        x, y, box_width, box_height = box["x"], box["y"], box["width"], box["height"]
        mask = np.asarray(
            self.video_mask.resize((box_width, box_height), Image.Resampling.BICUBIC),
            dtype=np.float32,
        )
        # Gemini's supplied PNG has opaque RGBA; its RGB brightness stores
        # the alpha map.  This is the same alpha used for inverse blending.
        alpha = np.clip(np.max(mask[:, :, :3], axis=2) / 255.0 * gain, 0.0, 0.99)
        active = alpha >= 0.002
        result = frame.copy()
        crop = result[y:y + box_height, x:x + box_width].astype(np.float32)
        restored = (crop - 255.0 * alpha[:, :, None]) / (1.0 - alpha[:, :, None])
        restored = np.clip(restored + 0.5, 0, 255).astype(np.uint8)
        result[y:y + box_height, x:x + box_width] = np.where(
            active[:, :, None], restored, result[y:y + box_height, x:x + box_width]
        )
        return result, {"box": box}

    def _ffprobe_path(self) -> str:
        ffmpeg = Path(self.ffmpeg_path)
        sibling = ffmpeg.with_name("ffprobe" + ffmpeg.suffix)
        if sibling.is_file():
            return str(sibling)
        found = shutil.which("ffprobe")
        if found:
            return found
        raise RuntimeError("Không tìm thấy ffprobe để đọc thông tin video.")

    def probe(self, input_path: Path) -> VideoInfo:
        command = [
            self._ffprobe_path(), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,avg_frame_rate,duration",
            "-of", "json", str(input_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Không thể đọc thông tin video.")
        try:
            stream = json.loads(result.stdout)["streams"][0]
            numerator, denominator = stream.get("avg_frame_rate", "0/1").split("/", 1)
            fps = float(numerator) / float(denominator)
            duration_value = stream.get("duration")
            duration = float(duration_value) if duration_value not in (None, "N/A") else None
            width, height = int(stream["width"]), int(stream["height"])
        except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError, json.JSONDecodeError) as exc:
            raise RuntimeError("Video không có luồng hình hợp lệ.") from exc
        if width < 1 or height < 1 or fps <= 0:
            raise RuntimeError("Thông tin kích thước hoặc FPS của video không hợp lệ.")
        return VideoInfo(width=width, height=height, fps=fps, duration=duration)

    def build_decode_command(self, source: Path) -> list[str]:
        return [
            self.ffmpeg_path, "-v", "error", "-i", str(source), "-map", "0:v:0",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ]

    def build_encode_command(
        self, source: Path, output: Path, width: int, height: int, fps: float
    ) -> list[str]:
        return [
            self.ffmpeg_path, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}", "-r", f"{fps:.12g}", "-i", "-", "-i", str(source),
            "-map", "0:v:0", "-map", "1:a?", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart", str(output),
        ]

    @staticmethod
    def _terminate(process: Optional[subprocess.Popen]) -> None:
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    @staticmethod
    def temporary_output_path(source: Path, output: Path) -> Path:
        """Reserve a unique, owned temporary path beside the requested output."""
        descriptor, name = tempfile.mkstemp(
            dir=output.parent,
            prefix=f".{output.stem}.",
            suffix=output.suffix,
        )
        os.close(descriptor)
        temporary = Path(name)
        if temporary.resolve() in {source.resolve(), output.resolve()}:
            temporary.unlink(missing_ok=True)
            raise RuntimeError("Không thể tạo file tạm an toàn cho video output.")
        return temporary

    def process_file(
        self,
        input_path: Path,
        output_path: Path,
        gain: float = 0.6,
        scale: float = 1.01,
        offset_x: int = -24,
        offset_y: int = -24,
        preset_mode: str = "auto",
        progress_callback: Optional[ProgressCallback] = None,
        is_cancelled: Optional[CancelCallback] = None,
    ) -> Dict[str, Any]:
        source, output = Path(input_path), Path(output_path)
        if not source.is_file():
            raise FileNotFoundError(f"Không tìm thấy video đầu vào: {source}")
        if source.resolve() == output.resolve():
            raise ValueError("Đường dẫn output không được trùng video input.")
        if output.exists():
            raise FileExistsError(f"File kết quả đã tồn tại: {output}")
        if not output.parent.is_dir():
            raise FileNotFoundError(f"Thư mục output không tồn tại: {output.parent}")

        info = self.probe(source)
        frame_bytes = info.width * info.height * 3
        total_frames = round(info.duration * info.fps) if info.duration is not None else None
        temporary = self.temporary_output_path(source, output)

        decoder: Optional[subprocess.Popen] = None
        encoder: Optional[subprocess.Popen] = None
        processed = 0
        succeeded = False
        try:
            decoder = subprocess.Popen(
                self.build_decode_command(source), stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            encoder = subprocess.Popen(
                self.build_encode_command(source, temporary, info.width, info.height, info.fps),
                stdin=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            assert decoder.stdout is not None and encoder.stdin is not None

            while True:
                if is_cancelled and is_cancelled():
                    return {"success": False, "cancelled": True, "error": "Người dùng đã hủy xử lý."}
                raw = decoder.stdout.read(frame_bytes)
                if not raw:
                    break
                if len(raw) != frame_bytes:
                    return {"success": False, "error": "Luồng frame video bị thiếu dữ liệu."}
                frame = np.frombuffer(raw, dtype=np.uint8).reshape(info.height, info.width, 3)
                cleaned, meta = self.remove_frame(
                    frame, gain=gain, scale=scale, offset_x=offset_x, offset_y=offset_y
                )
                healed = heal_upscaled_video_edge_seam(cleaned, meta["box"])
                encoder.stdin.write(healed.tobytes())
                processed += 1
                if progress_callback:
                    progress_callback(processed, total_frames)

            encoder.stdin.close()
            decoder_return = decoder.wait()
            encoder_return = encoder.wait()
            if decoder_return != 0:
                raise RuntimeError(decoder.stderr.read().decode(errors="replace").strip() or "FFmpeg không thể giải mã video.")
            if encoder_return != 0:
                raise RuntimeError(encoder.stderr.read().decode(errors="replace").strip() or "FFmpeg không thể mã hóa video.")
            os.replace(temporary, output)
            succeeded = True
            return {
                "success": True,
                "input_path": str(source),
                "output_path": str(output),
                "frames_processed": processed,
                "total_frames": total_frames,
                "size": (info.width, info.height),
            }
        except (BrokenPipeError, OSError, RuntimeError) as exc:
            return {"success": False, "error": str(exc), "frames_processed": processed}
        finally:
            if not succeeded:
                self._terminate(decoder)
                self._terminate(encoder)
                if temporary.exists():
                    temporary.unlink()

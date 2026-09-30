#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_render.py: Xử lý xuất video hàng loạt (Batch Render) cho nhiều dự án.

Quản lý hàng đợi tuần tự (Sequential FIFO Queue) trên luồng nền (QThread):
- Kiểm tra tính sẵn sàng của từng dự án trước khi render.
- Chạy lần lượt từng dự án để tránh quá tải tài nguyên hệ thống (FFmpeg).
- Quản lý trạng thái, tiến độ chi tiết và lỗi độc lập cho từng dự án.
- Hỗ trợ hủy an toàn (Graceful cancellation) giữa chừng.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from app.core import video_creator
from app.core.project_manager import Project


class BatchStatus(str, Enum):
    PENDING = "pending"        # Chờ xử lý
    RENDERING = "rendering"    # Đang render
    COMPLETED = "completed"    # Hoàn thành
    FAILED = "failed"          # Thất bại
    SKIPPED = "skipped"        # Bỏ qua (thiếu tài nguyên)
    CANCELLED = "cancelled"    # Đã hủy bởi người dùng


def validate_project_for_render(project: Project) -> Dict[str, Any]:
    """
    Kiểm tra nhanh tính sẵn sàng của tài nguyên dự án trước khi đưa vào hàng đợi render.
    Trả về dict chi tiết trạng thái từng tài nguyên và danh sách lý do nếu chưa sẵn sàng.
    """
    clean_images = project.get_clean_images()
    raw_images = project.get_raw_images()
    effective_img_dir = project.get_effective_image_dir()
    has_images = len(clean_images) > 0 or len(raw_images) > 0
    images_count = len(clean_images) if clean_images else len(raw_images)

    voice_path = project.get_latest_voice()
    has_voice = voice_path is not None and voice_path.is_file()

    srt_path = project.get_latest_srt()
    has_srt = srt_path is not None and srt_path.is_file()

    has_scenes = project.scenes_path.exists() and project.scenes_path.stat().st_size > 5

    missing_reasons: List[str] = []
    if not has_images:
        missing_reasons.append("Chưa có ảnh trong thư mục images/")
    if not has_voice:
        missing_reasons.append("Chưa có file giọng đọc voice (.mp3, .wav) trong voice/")
    if not has_srt:
        missing_reasons.append("Chưa có file phụ đề (.srt) trong voice/")
    if not has_scenes:
        missing_reasons.append("Chưa có file kịch bản phân cảnh (scenes.json)")

    is_ready = has_images and has_voice and has_srt and has_scenes

    return {
        "is_ready": is_ready,
        "has_images": has_images,
        "images_count": images_count,
        "image_dir": effective_img_dir if has_images else None,
        "has_voice": has_voice,
        "voice_path": voice_path,
        "has_srt": has_srt,
        "srt_path": srt_path,
        "has_scenes": has_scenes,
        "scenes_path": project.scenes_path if has_scenes else None,
        "missing_reasons": missing_reasons,
    }


def prepare_project_render_data(
    project: Project,
    custom_ratio: Optional[str] = None,
    custom_fps: Optional[int] = None,
    ffmpeg_exe: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Chuẩn bị toàn bộ dữ liệu cần thiết (timeline, audio, output path) để render video cho một dự án.
    Nếu thiếu tài nguyên hoặc dữ liệu không hợp lệ, ném ngoại lệ ValueError.
    """
    validation = validate_project_for_render(project)
    if not validation["is_ready"]:
        reason_str = "; ".join(validation["missing_reasons"])
        raise ValueError(f"Dự án '{project.name}' chưa sẵn sàng: {reason_str}")

    if not ffmpeg_exe:
        ffmpeg_exe = video_creator.get_ffmpeg_path()

    image_dir: Path = validation["image_dir"]
    audio_path: Path = validation["voice_path"]
    srt_path: Path = validation["srt_path"]
    scenes_path: Path = validation["scenes_path"]

    # Đọc phụ đề và thời lượng âm thanh
    subtitles = video_creator.parse_srt_file(srt_path)
    total_audio_duration = video_creator.get_audio_duration(ffmpeg_exe, audio_path)
    if total_audio_duration <= 0:
        raise ValueError(f"Thời lượng âm thanh không hợp lệ ({total_audio_duration}s).")

    # Phân tích kịch bản cảnh và tính timeline
    scenes = video_creator.parse_json_mapping(scenes_path, sorted(subtitles))
    if not scenes:
        raise ValueError("Không tìm thấy phân cảnh nào hợp lệ trong scenes.json.")

    timeline = video_creator.compute_timeline(
        scenes=scenes,
        subtitles=subtitles,
        total_audio_duration=total_audio_duration,
        image_dir=image_dir,
    )

    if not timeline:
        raise ValueError("Không thể tạo timeline cho các phân cảnh.")

    aspect_ratio = custom_ratio or project.aspect_ratio or "16:9"
    fps = int(custom_fps or project.fps or 30)

    # Đặt tên file xuất: {project_slug}_{timestamp}.mp4
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{project.slug}_{timestamp_str}.mp4"
    output_path = project.output_dir / output_filename

    missing_images_count = sum(1 for it in timeline if it.get("image") is None)

    return {
        "project": project,
        "timeline": timeline,
        "audio_path": audio_path,
        "output_path": output_path,
        "total_audio_duration": total_audio_duration,
        "aspect_ratio": aspect_ratio,
        "fps": fps,
        "missing_images_count": missing_images_count,
        "total_scenes": len(timeline),
    }


class BatchRenderItem:
    """Theo dõi tiến trình và trạng thái của từng dự án trong hàng đợi."""

    def __init__(self, project: Project):
        self.project = project
        self.slug = project.slug
        self.name = project.name
        self.status = BatchStatus.PENDING
        self.progress = 0
        self.status_message = "Đang chờ trong hàng đợi..."
        self.output_path: Optional[Path] = None
        self.duration: float = 0.0
        self.size_mb: float = 0.0
        self.error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "status_message": self.status_message,
            "output_path": str(self.output_path) if self.output_path else "",
            "duration": self.duration,
            "size_mb": self.size_mb,
            "error_message": self.error_message,
        }


class BatchRenderWorker(QThread):
    """
    Worker xử lý hàng đợi xuất video cho nhiều dự án trên luồng nền.
    Chạy lần lượt (sequential FIFO queue) để tối ưu hiệu năng và tránh xung đột FFmpeg.
    """

    # Signals
    project_started = pyqtSignal(str, int, int)      # (slug, current_index, total_count)
    project_progress = pyqtSignal(str, int, str)     # (slug, pct, message)
    project_finished = pyqtSignal(str, bool, dict)   # (slug, success, info_dict)
    queue_progress = pyqtSignal(int, int, int)       # (completed_count, total_count, overall_pct)
    batch_completed = pyqtSignal(dict)               # (summary_dict)

    def __init__(
        self,
        projects: List[Project],
        custom_ratio: Optional[str] = None,
        custom_fps: Optional[int] = None,
        skip_invalid: bool = True,
        render_func: Optional[Callable] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.projects = list(projects)
        self.custom_ratio = custom_ratio
        self.custom_fps = custom_fps
        self.skip_invalid = skip_invalid
        self.render_func = render_func or video_creator.render_video
        self._is_cancelled = False

        self.items: List[BatchRenderItem] = [
            BatchRenderItem(proj) for proj in self.projects
        ]

    def cancel(self):
        """Yêu cầu dừng toàn bộ hàng đợi ngay lập tức."""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def run(self):
        total_count = len(self.items)
        if total_count == 0:
            self.batch_completed.emit({
                "total": 0,
                "completed": 0,
                "failed": 0,
                "skipped": 0,
                "cancelled": 0,
                "items": [],
            })
            return

        completed_count = 0
        failed_count = 0
        skipped_count = 0
        cancelled_count = 0

        # Tìm FFmpeg path 1 lần trước khi vào loop (trừ khi dùng mock render)
        cached_ffmpeg_exe = None
        if self.render_func == video_creator.render_video:
            try:
                cached_ffmpeg_exe = video_creator.get_ffmpeg_path()
            except Exception as e:
                # Nếu không có FFmpeg thì toàn bộ hàng đợi lỗi
                for item in self.items:
                    item.status = BatchStatus.FAILED
                    item.error_message = f"Lỗi FFmpeg: {e}"
                    self.project_finished.emit(item.slug, False, item.to_dict())
                self.batch_completed.emit({
                    "total": total_count,
                    "completed": 0,
                    "failed": total_count,
                    "skipped": 0,
                    "cancelled": 0,
                    "items": [it.to_dict() for it in self.items],
                })
                return

        for idx, item in enumerate(self.items):
            current_index = idx + 1

            # Kiểm tra xem người dùng có bấm hủy không
            if self._is_cancelled:
                item.status = BatchStatus.CANCELLED
                item.status_message = "Đã hủy bởi người dùng."
                cancelled_count += 1
                self.project_finished.emit(item.slug, False, item.to_dict())
                overall_pct = int((current_index / total_count) * 100)
                self.queue_progress.emit(current_index, total_count, overall_pct)
                continue

            self.project_started.emit(item.slug, current_index, total_count)
            item.status = BatchStatus.RENDERING
            item.status_message = "Đang kiểm tra và chuẩn bị dữ liệu..."
            self.project_progress.emit(item.slug, 2, item.status_message)

            # Chuẩn bị dữ liệu render
            try:
                render_data = prepare_project_render_data(
                    project=item.project,
                    custom_ratio=self.custom_ratio,
                    custom_fps=self.custom_fps,
                    ffmpeg_exe=cached_ffmpeg_exe,
                )
            except Exception as exc:
                err_msg = str(exc)
                if self.skip_invalid:
                    item.status = BatchStatus.SKIPPED
                    item.status_message = f"Bỏ qua: {err_msg}"
                    item.error_message = err_msg
                    skipped_count += 1
                else:
                    item.status = BatchStatus.FAILED
                    item.status_message = f"Lỗi chuẩn bị: {err_msg}"
                    item.error_message = err_msg
                    failed_count += 1

                self.project_finished.emit(item.slug, False, item.to_dict())
                overall_pct = int((current_index / total_count) * 100)
                self.queue_progress.emit(current_index, total_count, overall_pct)
                continue

            # Callback cập nhật tiến độ cho từng dự án
            def on_proj_progress(pct: int, msg: str):
                item.progress = pct
                item.status_message = msg
                self.project_progress.emit(item.slug, pct, msg)

            item.status_message = "Đang xuất video qua FFmpeg..."
            self.project_progress.emit(item.slug, 5, item.status_message)

            try:
                res = self.render_func(
                    timeline=render_data["timeline"],
                    audio_path=render_data["audio_path"],
                    output_path=render_data["output_path"],
                    total_audio_duration=render_data["total_audio_duration"],
                    aspect_ratio=render_data["aspect_ratio"],
                    fps=render_data["fps"],
                    progress_callback=on_proj_progress,
                    is_cancelled=self.is_cancelled,
                )
            except Exception as exc:
                res = {"success": False, "error": f"Lỗi render không mong muốn: {exc}"}

            if self._is_cancelled:
                item.status = BatchStatus.CANCELLED
                item.status_message = "Đã hủy trong quá trình xuất video."
                cancelled_count += 1
                self.project_finished.emit(item.slug, False, item.to_dict())
            elif res.get("success"):
                item.status = BatchStatus.COMPLETED
                item.progress = 100
                item.status_message = "Hoàn tất xuất video!"
                item.output_path = render_data["output_path"]
                item.duration = res.get("duration", render_data["total_audio_duration"])
                item.size_mb = res.get("size_mb", 0.0)
                completed_count += 1

                # Cập nhật metadata dự án
                try:
                    item.project.save_metadata()
                except Exception:
                    pass

                self.project_finished.emit(item.slug, True, item.to_dict())
            else:
                item.status = BatchStatus.FAILED
                item.status_message = res.get("error", "Lỗi không xác định khi xuất video.")
                item.error_message = res.get("error", "")
                failed_count += 1
                self.project_finished.emit(item.slug, False, item.to_dict())

            overall_pct = int((current_index / total_count) * 100)
            self.queue_progress.emit(current_index, total_count, overall_pct)

        summary = {
            "total": total_count,
            "completed": completed_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "cancelled": cancelled_count,
            "items": [it.to_dict() for it in self.items],
        }
        self.batch_completed.emit(summary)

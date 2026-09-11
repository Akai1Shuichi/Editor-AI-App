#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
project_manager.py: Quản lý kiến trúc dự án (Projects) cho Editor-AI-App.

Mỗi Dự án là một không gian làm việc độc lập:
├── project.json       # Cấu hình dự án (tên, tỉ lệ khung hình, ngày tạo...)
├── scenes.json        # Kịch bản phân cảnh riêng của dự án
├── images/            # Ảnh đầu vào
│   └── clean/         # Ảnh sạch đã gỡ watermark (đầu vào cho video)
├── voice/             # File âm thanh voice (.mp3, .wav) & phụ đề (.srt)
└── output/            # Video thành phẩm (.mp4)
"""

import os
import re
import json
import shutil
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

from app import config

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VALID_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}

def slugify(text: str) -> str:
    """Chuyển chuỗi tiếng Việt thành slug an toàn cho tên thư mục."""
    text = text.strip()
    # Khử dấu tiếng Việt
    nfkd = unicodedata.normalize('NFKD', text)
    no_accents = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    # Thay thế đ, Đ
    no_accents = no_accents.replace('đ', 'd').replace('Đ', 'D')
    # Thay thế ký tự không phải chữ số thành gạch dưới
    clean = re.sub(r'[^a-zA-Z0-9_-]+', '_', no_accents)
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean or f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


class Project:
    """Đại diện cho một dự án làm video."""

    def __init__(self, path: Path, data: Optional[Dict[str, Any]] = None):
        self.path = path
        self.slug = path.name
        self._data = data or {}

        if not self._data and self.metadata_path.exists():
            try:
                self._data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

        self.name: str = self._data.get("name", self.slug.replace("_", " "))
        self.aspect_ratio: str = self._data.get("aspect_ratio", "16:9")
        self.fps: int = int(self._data.get("fps", 30))
        self.created_at: str = self._data.get("created_at", datetime.now().isoformat())
        self.updated_at: str = self._data.get("updated_at", self.created_at)
        self.notes: str = self._data.get("notes", "")

    # ================= ĐƯỜNG DẪN CÁC THƯ MỤC CON =================
    @property
    def images_dir(self) -> Path:
        p = self.path / "images"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def clean_images_dir(self) -> Path:
        p = self.images_dir / "clean"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def voice_dir(self) -> Path:
        p = self.path / "voice"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def output_dir(self) -> Path:
        p = self.path / "output"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def scenes_path(self) -> Path:
        return self.path / "scenes.json"

    @property
    def metadata_path(self) -> Path:
        return self.path / "project.json"

    # ================= QUẢN LÝ TÀI NGUYÊN =================
    def get_clean_images(self) -> List[Path]:
        """Lấy danh sách các file ảnh trong images/clean/."""
        if not self.clean_images_dir.exists():
            return []
        imgs = [f for f in self.clean_images_dir.iterdir() if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTS]
        imgs.sort(key=lambda f: f.name.lower())
        return imgs

    def get_raw_images(self) -> List[Path]:
        """Lấy danh sách các file ảnh gốc trong images/."""
        if not self.images_dir.exists():
            return []
        imgs = [f for f in self.images_dir.iterdir() if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTS]
        imgs.sort(key=lambda f: f.name.lower())
        return imgs

    def get_effective_image_dir(self) -> Path:
        """Ưu tiên thư mục clean nếu có ảnh, ngược lại trả về images/."""
        if self.get_clean_images():
            return self.clean_images_dir
        if self.get_raw_images():
            return self.images_dir
        return self.clean_images_dir

    def get_latest_voice(self) -> Optional[Path]:
        """Lấy file âm thanh mới nhất trong voice/."""
        if not self.voice_dir.exists():
            return None
        audios = [f for f in self.voice_dir.iterdir() if f.is_file() and f.suffix.lower() in VALID_AUDIO_EXTS]
        if not audios:
            return None
        audios.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return audios[0]

    def get_latest_srt(self) -> Optional[Path]:
        """Lấy file phụ đề .srt mới nhất trong voice/."""
        if not self.voice_dir.exists():
            return None
        srts = [f for f in self.voice_dir.iterdir() if f.is_file() and f.suffix.lower() == ".srt"]
        if not srts:
            return None
        srts.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return srts[0]

    def get_rendered_videos(self) -> List[Path]:
        """Lấy danh sách các video đã xuất trong output/."""
        if not self.output_dir.exists():
            return []
        vids = [f for f in self.output_dir.iterdir() if f.is_file() and f.suffix.lower() == ".mp4"]
        vids.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return vids

    def stats(self) -> Dict[str, Any]:
        """Trả về thống kê tổng hợp trạng thái dự án."""
        clean_count = len(self.get_clean_images())
        raw_count = len(self.get_raw_images())
        voice = self.get_latest_voice()
        srt = self.get_latest_srt()
        videos = self.get_rendered_videos()
        has_scenes = self.scenes_path.exists() and self.scenes_path.stat().st_size > 5

        return {
            "clean_images_count": clean_count,
            "raw_images_count": raw_count,
            "has_voice": voice is not None,
            "voice_name": voice.name if voice else "",
            "has_srt": srt is not None,
            "srt_name": srt.name if srt else "",
            "has_scenes": has_scenes,
            "videos_count": len(videos),
            "latest_video": videos[0].name if videos else "",
            "is_ready_for_video": clean_count > 0 and voice is not None and srt is not None and has_scenes
        }

    def save_metadata(self):
        """Lưu lại metadata vào project.json."""
        self.updated_at = datetime.now().isoformat()
        data = {
            "name": self.name,
            "slug": self.slug,
            "aspect_ratio": self.aspect_ratio,
            "fps": self.fps,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "notes": self.notes
        }
        self.path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class ProjectManager:
    """Quản lý danh sách và trạng thái các dự án."""

    @classmethod
    def get_projects_root(cls) -> Path:
        cls_dir = config.PROJECTS_DIR
        cls_dir.mkdir(parents=True, exist_ok=True)
        return cls_dir

    @classmethod
    def list_projects(cls) -> List[Project]:
        """Quét và trả về danh sách tất cả các dự án, sắp xếp mới nhất lên đầu."""
        root = cls.get_projects_root()
        projects = []
        for d in root.iterdir():
            if d.is_dir() and (d / "project.json").exists():
                projects.append(Project(d))

        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    @classmethod
    def get_project(cls, slug_or_name: str) -> Optional[Project]:
        """Tìm dự án theo slug hoặc tên."""
        if not slug_or_name:
            return None
        target = slug_or_name.strip().lower()
        for p in cls.list_projects():
            if p.slug.lower() == target or p.name.lower() == target:
                return p
        return None

    @classmethod
    def create_project(cls, name: str, aspect_ratio: str = "16:9", fps: int = 30) -> Project:
        """Khởi tạo dự án mới với đầy đủ cây thư mục và tệp cấu hình."""
        name = name.strip() or f"Dự án {datetime.now().strftime('%d/%m %H:%M')}"
        slug = slugify(name)
        root = cls.get_projects_root()
        proj_dir = root / slug

        if proj_dir.exists():
            raise ValueError(
                f"Đã có dự án dùng thư mục '{slug}'. Vui lòng chọn tên khác."
            )

        proj_dir.mkdir(parents=True, exist_ok=True)

        project = Project(proj_dir, {
            "name": name,
            "slug": slug,
            "aspect_ratio": aspect_ratio,
            "fps": fps,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

        # Tạo các thư mục con
        _ = project.images_dir
        _ = project.clean_images_dir
        _ = project.voice_dir
        _ = project.output_dir
        project.save_metadata()

        cls.set_active_project(project.slug)
        return project

    @classmethod
    def delete_project(cls, slug: str) -> bool:
        """Xóa thư mục dự án."""
        p = cls.get_project(slug)
        if not p:
            return False
        try:
            shutil.rmtree(p.path)
            # Nếu xóa trúng active project thì reset
            if config.ACTIVE_PROJECT == slug:
                cls.set_active_project("")
            return True
        except Exception:
            return False

    @classmethod
    def get_active_project(cls) -> Optional[Project]:
        """Lấy dự án đang được kích hoạt hiện tại."""
        active_slug = config.ACTIVE_PROJECT
        if active_slug:
            p = cls.get_project(active_slug)
            if p:
                return p

        # Nếu chưa cấu hình active project nhưng đã có project tồn tại
        all_projects = cls.list_projects()
        if all_projects:
            cls.set_active_project(all_projects[0].slug)
            return all_projects[0]

        return None

    @classmethod
    def set_active_project(cls, slug: str) -> Optional[Project]:
        """Kích hoạt một dự án và lưu vào config / .env."""
        config.save_env_variable("ACTIVE_PROJECT", slug)
        return cls.get_project(slug)

    @classmethod
    def rename_project(cls, slug: str, new_name: str) -> Project:
        """Đổi tên hiển thị, giữ nguyên slug và cấu trúc thư mục."""
        project = cls.get_project(slug)
        if not project:
            raise ValueError("Dự án không còn tồn tại.")

        clean_name = new_name.strip()
        if not clean_name:
            raise ValueError("Tên dự án không được để trống.")

        project.name = clean_name
        project.save_metadata()
        return project

    @classmethod
    def ensure_default_project(cls) -> Project:
        """Đảm bảo luôn có ít nhất một dự án khả dụng khi vừa mở app."""
        active = cls.get_active_project()
        if active:
            return active

        # Tạo dự án mẫu đầu tiên
        return cls.create_project("Dự Án Mẫu 01", aspect_ratio="16:9")

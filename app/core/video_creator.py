#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video_creator.py: Tạo video đồng bộ ảnh và giọng đọc theo phụ đề SRT & kịch bản JSON.

Quy luật ghép khớp:
- Nhận: Thư mục ảnh + File voice (audio) + File SRT + File JSON mapping cảnh.
- Cảnh đầu tiên (SC01): Giữ ảnh từ giây 0.000 đến lúc phụ đề đầu tiên của cảnh tiếp theo bắt đầu.
- Cảnh thứ i (SC02...): Bắt đầu từ lúc phụ đề đầu tiên của cảnh đó bắt đầu, chuyển cảnh tiếp theo tương tự.
- Cảnh cuối cùng: Kéo dài đến hết thời lượng file âm thanh (Audio Duration).
- Video xuất ra chuẩn MP4 H.264 + AAC, tương thích mọi thiết bị.
"""

import os
import sys
import re
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from app.core.platform_utils import open_path

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()


def escape_ffconcat_path(path: str) -> str:
    """Escape a path for a single-quoted FFmpeg concat-demuxer entry."""
    return path.replace("'", r"'\''")


def get_ffmpeg_path() -> str:
    """Tìm đường dẫn thực thi ffmpeg: hệ thống hoặc thư viện imageio-ffmpeg."""
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

    # Kiểm tra fallback qua thư mục evenlabs-voice nếu có
    possible_venv = Path(__file__).resolve().parent.parent.parent.parent / "evenlabs-voice" / ".venv"
    if possible_venv.exists():
        for candidate in possible_venv.glob("**/imageio_ffmpeg/binaries/ffmpeg*"):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)

    console.print("[bold red][!] Không tìm thấy ffmpeg và chưa cài đặt thư viện 'imageio-ffmpeg'![/bold red]")
    console.print("[yellow]Vui lòng chạy: pip install imageio-ffmpeg[/yellow]")
    raise RuntimeError("Không tìm thấy ffmpeg trên hệ thống và trong imageio-ffmpeg.")

def parse_srt_time(time_str: str) -> float:
    """Chuyển đổi chuỗi thời gian SRT (HH:MM:SS,mmm hoặc .mmm) sang giây float."""
    time_str = time_str.strip()
    match = re.match(r"^(\d+):(\d+):(\d+)[,\.](\d+)$", time_str)
    if not match:
        raise ValueError(f"Định dạng thời gian không hợp lệ: '{time_str}'")
    hours, minutes, seconds, millis = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / (10 ** len(millis))

def format_time(seconds: float) -> str:
    """Format số giây thành chuỗi MM:SS.mmm hoặc HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:06.3f}"
    return f"{mins:02d}:{secs:06.3f}"

def parse_srt_file(srt_path: Path) -> Dict[int, Dict[str, Any]]:
    """Đọc và parse file phụ đề .srt thành dictionary {id: {'id': id, 'start': float, 'end': float, 'text': str}}."""
    if not srt_path.exists():
        raise FileNotFoundError(f"File SRT không tồn tại: {srt_path}")

    content = srt_path.read_text(encoding="utf-8-sig", errors="ignore")
    blocks = re.split(r"\n\s*\n", content.strip())
    subtitles = {}

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        try:
            sub_id = int(lines[0])
            time_match = re.match(r"(\d+:\d+:\d+[,\.]\d+)\s*-->\s*(\d+:\d+:\d+[,\.]\d+)", lines[1])
            if time_match:
                start_sec = parse_srt_time(time_match.group(1))
                end_sec = parse_srt_time(time_match.group(2))
                text = " ".join(lines[2:]) if len(lines) > 2 else ""
                subtitles[sub_id] = {
                    "id": sub_id,
                    "start": start_sec,
                    "end": end_sec,
                    "text": text
                }
        except Exception:
            continue

    return subtitles

def get_audio_duration(ffmpeg_exe: str, audio_path: Path) -> float:
    """Lấy tổng thời lượng (giây) của file âm thanh qua ffmpeg."""
    cmd = [ffmpeg_exe, "-i", str(audio_path)]
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", proc.stderr)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Không thể đo thời lượng của file âm thanh: {audio_path}")

def parse_sub_string(s: str) -> List[int]:
    """Parse chuỗi như '1-3, 5' thành [1, 2, 3, 5]"""
    result = []
    parts = s.split(",")
    for p in parts:
        p = p.strip()
        if "-" in p:
            start_s, end_s = p.split("-", 1)
            try:
                result.extend(range(int(start_s), int(end_s) + 1))
            except ValueError:
                pass
        elif p.isdigit():
            result.append(int(p))
    return sorted(list(set(result)))

def parse_json_mapping(json_path: Path, available_subs: List[int]) -> List[Dict[str, Any]]:
    """
    Parse file JSON ánh xạ Scene sang phụ đề.
    Hỗ trợ các định dạng:
    Format 1 (Dict):
      {"SC01": [1, 2], "SC02": [3, 4]}
    Format 2 (List of objects):
      [{"id": "SC01", "subtitles": [1, 2]}, {"id": "SC02", "subtitles": [3]}]
    Format 3 (List of scenes chưa có subtitles):
      Tự động phân bổ phụ đề chia đều cho các scenes.
    """
    if not json_path.exists():
        raise FileNotFoundError(f"File JSON không tồn tại: {json_path}")

    raw_data = json.loads(json_path.read_text(encoding="utf-8", errors="ignore"))
    return parse_json_data(raw_data, available_subs)


def parse_json_data(raw_data: Any, available_subs: List[int]) -> List[Dict[str, Any]]:
    """Phân tích dữ liệu JSON đã nạp sẵn theo schema kịch bản cảnh."""
    scenes = []

    if isinstance(raw_data, dict):
        for sc_id, subs in raw_data.items():
            if isinstance(subs, int):
                subs = [subs]
            elif isinstance(subs, str):
                subs = parse_sub_string(subs)
            scenes.append({
                "id": str(sc_id).strip(),
                "subtitles": sorted(list(subs))
            })
    elif isinstance(raw_data, list):
        for idx, item in enumerate(raw_data, start=1):
            if isinstance(item, dict):
                sc_id = item.get("id") or item.get("scene") or item.get("name") or f"SC{idx:02d}"
                subs = (
                    item.get("subtitles")
                    or item.get("subtitle_ids")
                    or item.get("subs")
                    or item.get("sub_ids")
                    or []
                )
                if isinstance(subs, int):
                    subs = [subs]
                elif isinstance(subs, str):
                    subs = parse_sub_string(subs)
                scenes.append({
                    "id": str(sc_id).strip(),
                    "prompt": item.get("prompt", ""),
                    "subtitles": sorted(list(subs))
                })
            elif isinstance(item, str):
                scenes.append({"id": item.strip(), "subtitles": []})

    if not scenes:
        return []

    # Nếu tất cả scenes đều chưa có subtitles
    has_subs = any(len(s.get("subtitles", [])) > 0 for s in scenes)
    if not has_subs and available_subs:
        num_scenes = len(scenes)
        sub_count = len(available_subs)
        chunk_size = sub_count // num_scenes
        remainder = sub_count % num_scenes
        
        cur = 0
        for i in range(num_scenes):
            take = chunk_size + (1 if i < remainder else 0)
            assigned = available_subs[cur:cur + take]
            cur += take
            scenes[i]["subtitles"] = assigned

    return scenes

def find_image_for_scene(image_dir: Path, scene_id: str, scene_idx: int) -> Optional[Path]:
    """
    Tìm file ảnh tương ứng với scene_id:
    - Tách tiền tố trước dấu gạch dưới '_' hoặc '-' (ví dụ 'SC01_20260910165946_clean.png' -> 'SC01')
    - Đối chiếu chính xác với ID cảnh (SC01).
    - Hỗ trợ tìm cả trong thư mục chính và thư mục con (ví dụ images/cleaned hoặc images/clean).
    - Ưu tiên chọn ảnh bản 'clean' nếu có nhiều phiên bản.
    """
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    
    all_images = []
    if image_dir.is_dir():
        for f in image_dir.iterdir():
            if f.is_file() and f.suffix.lower() in valid_exts:
                all_images.append(f)
        for sub in image_dir.iterdir():
            if sub.is_dir():
                for f in sub.iterdir():
                    if f.is_file() and f.suffix.lower() in valid_exts:
                        all_images.append(f)

    norm_target = scene_id.upper().strip()
    target_num_match = re.search(r"\d+", norm_target)
    target_num = int(target_num_match.group()) if target_num_match else None

    matched_images = []
    for img in all_images:
        stem_upper = img.stem.upper()
        prefix = re.split(r"[-_]", stem_upper)[0].strip()

        if prefix == norm_target:
            matched_images.append(img)
            continue

        prefix_num_match = re.search(r"\d+", prefix)
        if prefix_num_match and target_num is not None:
            if int(prefix_num_match.group()) == target_num:
                matched_images.append(img)
                continue

        if re.match(rf"^{re.escape(norm_target)}(?:[-_.]|$)", stem_upper):
            matched_images.append(img)
            continue

    if matched_images:
        clean_images = [img for img in matched_images if "clean" in img.stem.lower()]
        if clean_images:
            return clean_images[0]
        return matched_images[0]

    # Fallback: theo thứ tự index (1-based)
    direct_files = sorted([f for f in image_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts])
    if 0 <= scene_idx - 1 < len(direct_files):
        return direct_files[scene_idx - 1]

    return None

def compute_timeline(
    scenes: List[Dict[str, Any]],
    subtitles: Dict[int, Dict[str, Any]],
    total_audio_duration: float,
    image_dir: Path
) -> List[Dict[str, Any]]:
    """
    Tính toán mốc thời gian hiển thị từng ảnh:
    - Cảnh 1: từ giây 0.000 đến lúc phụ đề đầu tiên của cảnh 2 bắt đầu.
    - Cảnh thứ i: từ phụ đề đầu tiên của cảnh i đến phụ đề đầu tiên của cảnh (i+1).
    - Cảnh cuối cùng: từ phụ đề đầu tiên của nó đến hết thời lượng file âm thanh.
    """
    timeline = []
    num_scenes = len(scenes)

    # Bước 1: Xác định start_time của từng scene
    for i, sc in enumerate(scenes):
        sc_id = sc["id"]
        subs = sc.get("subtitles", [])
        
        img_path = find_image_for_scene(image_dir, sc_id, i + 1)

        if i == 0:
            start_time = 0.0
        else:
            if subs and subs[0] in subtitles:
                start_time = subtitles[subs[0]]["start"]
            else:
                prev_start = timeline[i - 1]["start"] if timeline else 0.0
                start_time = prev_start + 1.0

        timeline.append({
            "index": i + 1,
            "id": sc_id,
            "subtitles": subs,
            "image": img_path,
            "start": start_time,
            "end": 0.0,
            "duration": 0.0
        })

    # Bước 2: Xác định end_time và duration cho từng scene
    for i in range(num_scenes):
        if i < num_scenes - 1:
            timeline[i]["end"] = timeline[i + 1]["start"]
        else:
            timeline[i]["end"] = max(total_audio_duration, timeline[i]["start"] + 0.5)

        dur = round(timeline[i]["end"] - timeline[i]["start"], 3)
        if dur <= 0:
            dur = 0.5
            timeline[i]["end"] = timeline[i]["start"] + dur
        timeline[i]["duration"] = dur

    return timeline

def render_video(
    timeline: List[Dict[str, Any]],
    audio_path: Path,
    output_path: Path,
    total_audio_duration: float,
    aspect_ratio: str = "16:9",
    fps: int = 30,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None
) -> Dict[str, Any]:
    """
    Sử dụng FFmpeg tạo video từ chuỗi ảnh và audio.
    Hỗ trợ progress_callback(percentage, status_text) và is_cancelled() để hủy.
    Trả về dict: {"success": bool, "output_path": Path, "duration": float, "size_mb": float, "error": str}
    """
    try:
        ffmpeg_exe = get_ffmpeg_path()
    except Exception as e:
        return {"success": False, "error": str(e)}

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if aspect_ratio == "9:16":
        width, height = 1080, 1920
    elif aspect_ratio == "1:1":
        width, height = 1080, 1080
    else:
        width, height = 1920, 1080

    temp_concat_file = output_path.parent / f"temp_concat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.txt"
    concat_lines = ["ffconcat version 1.0"]

    valid_items = [item for item in timeline if item.get("image") is not None]
    if not valid_items:
        return {"success": False, "error": "Không tìm thấy bất kỳ file ảnh hợp lệ nào trong timeline!"}

    for item in timeline:
        img = item.get("image")
        if not img:
            img = valid_items[0]["image"]
        img_p = escape_ffconcat_path(Path(img).resolve().as_posix())
        dur = item["duration"]
        concat_lines.append(f"file '{img_p}'")
        concat_lines.append(f"duration {dur}")

    last_img = timeline[-1].get("image") or valid_items[-1]["image"]
    last_img_p = escape_ffconcat_path(Path(last_img).resolve().as_posix())
    concat_lines.append(f"file '{last_img_p}'")

    temp_concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    vf_filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "format=yuv420p"
    ]
    vf_arg = ",".join(vf_filters)

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(temp_concat_file),
        "-i", str(audio_path.resolve()),
        "-t", f"{total_audio_duration:.3f}",
        "-vf", vf_arg,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        str(output_path.resolve())
    ]

    if progress_callback:
        progress_callback(5, "Đang khởi tạo trình mã hóa FFmpeg...")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            bufsize=1
        )

        stderr_logs = []
        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

        while True:
            if is_cancelled and is_cancelled():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                if temp_concat_file.exists():
                    temp_concat_file.unlink()
                if output_path.exists():
                    output_path.unlink()
                return {"success": False, "error": "Người dùng đã hủy tác vụ ghép video."}

            line = proc.stderr.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                stderr_logs.append(line)
                match = time_pattern.search(line)
                if match and total_audio_duration > 0 and progress_callback:
                    h, m, s = match.groups()
                    cur_sec = int(h) * 3600 + int(m) * 60 + float(s)
                    pct = min(98, max(5, int((cur_sec / total_audio_duration) * 100)))
                    progress_callback(pct, f"Đang render: {format_time(cur_sec)} / {format_time(total_audio_duration)} ({pct}%)")

        retcode = proc.wait()

        if temp_concat_file.exists():
            temp_concat_file.unlink()

        if retcode != 0:
            err_msg = "".join(stderr_logs[-30:]) if stderr_logs else f"FFmpeg thoát với mã {retcode}"
            return {"success": False, "error": err_msg}

        if progress_callback:
            progress_callback(100, "Hoàn tất xuất video!")

        file_size_mb = output_path.stat().st_size / (1024 * 1024) if output_path.exists() else 0.0
        return {
            "success": True,
            "output_path": output_path,
            "duration": total_audio_duration,
            "size_mb": file_size_mb,
            "error": ""
        }
    except Exception as e:
        if temp_concat_file.exists():
            temp_concat_file.unlink()
        return {"success": False, "error": f"Lỗi khi chạy FFmpeg: {e}"}

def show_timeline_table(timeline: List[Dict[str, Any]], total_duration: float):
    """Hiển thị bảng thời gian chuyển cảnh trực quan bằng Rich Table."""
    table = Table(title="[bold green]THỜI GIAN HIỂN THỊ CÁC CẢNH (TIMELINE)[/bold green]", expand=True)
    table.add_column("STT", justify="center", style="cyan", width=5)
    table.add_column("Scene ID", justify="center", style="bold yellow", width=10)
    table.add_column("Phụ đề gán", justify="center", style="magenta", width=15)
    table.add_column("File Ảnh", justify="left", style="white")
    table.add_column("Bắt đầu", justify="right", style="green", width=12)
    table.add_column("Kết thúc", justify="right", style="cyan", width=12)
    table.add_column("Thời lượng", justify="right", style="bold yellow", width=12)

    for item in timeline:
        subs_str = ", ".join(map(str, item["subtitles"])) if item["subtitles"] else "(Tự động)"
        img_name = item["image"].name if item["image"] else "[bold red]CHƯA CÓ ẢNH[/bold red]"
        table.add_row(
            str(item["index"]),
            item["id"],
            subs_str,
            str(img_name),
            format_time(item["start"]),
            format_time(item["end"]),
            f"{item['duration']:.2f}s"
        )

    console.print(table)
    console.print(f"[dim]Tổng thời lượng: {format_time(total_duration)} ({total_duration:.2f}s)[/dim]\n")

def interactive_cli():
    """Giao diện dòng lệnh tương tác hỏi người dùng từng bước."""
    console.clear()
    console.print(Panel(
        "[bold cyan]VIDEO COMPOSER: GHÉP ẢNH & VOICE THEO SRT + JSON[/bold cyan]\n"
        "[green]Tự động tính thời gian hiển thị ảnh theo phân đoạn phụ đề và ghép video chuẩn 1080p[/green]",
        border_style="cyan"
    ))

    base_dir = Path.cwd()
    downloads_dir = base_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Thư mục ảnh (Mặc định: downloads hoặc downloads/images hoặc images)
    if (downloads_dir / "images").exists():
        default_img_dir = downloads_dir / "images"
    elif any(downloads_dir.glob("*.png")) or any(downloads_dir.glob("*.jpg")):
        default_img_dir = downloads_dir
    elif (base_dir / "images").exists():
        default_img_dir = base_dir / "images"
    else:
        default_img_dir = downloads_dir

    img_dir_str = Prompt.ask(
        "\n[bold yellow]1. Nhập đường dẫn thư mục ảnh (Mặc định: downloads)[/bold yellow]",
        default=str(default_img_dir)
    ).strip().strip('"')
    image_dir = Path(img_dir_str)
    if not image_dir.exists() or not image_dir.is_dir():
        console.print(f"[bold red][!] Thư mục ảnh không tồn tại: {image_dir}[/bold red]")
        return

    # 2. File âm thanh (Voice / Audio - Mặc định: downloads)
    default_audio = ""
    candidate_audios = list(downloads_dir.glob("*.mp3")) + list(downloads_dir.glob("*.wav")) + list(base_dir.glob("*.mp3"))
    if candidate_audios:
        candidate_audios.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        default_audio = str(candidate_audios[0])

    audio_str = Prompt.ask(
        "[bold yellow]2. Nhập đường dẫn file âm thanh (voice .mp3, .wav...)[/bold yellow]",
        default=default_audio
    ).strip().strip('"')
    audio_path = Path(audio_str)
    if not audio_path.exists() or not audio_path.is_file():
        console.print(f"[bold red][!] File âm thanh không tồn tại: {audio_path}[/bold red]")
        return

    # 3. File phụ đề SRT (Mặc định: downloads)
    default_srt = ""
    candidate_srts = list(downloads_dir.glob("*.srt")) + list(base_dir.glob("*.srt"))
    if candidate_srts:
        candidate_srts.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        default_srt = str(candidate_srts[0])

    srt_str = Prompt.ask(
        "[bold yellow]3. Nhập đường dẫn file phụ đề SRT (.srt)[/bold yellow]",
        default=default_srt
    ).strip().strip('"')
    srt_path = Path(srt_str)
    if not srt_path.exists() or not srt_path.is_file():
        console.print(f"[bold red][!] File SRT không tồn tại: {srt_path}[/bold red]")
        return

    # 4. File JSON kịch bản phân đoạn cảnh (Mặc định: downloads hoặc gốc)
    default_json = ""
    candidate_jsons = list(downloads_dir.glob("*.json")) + list(base_dir.glob("*.json"))
    for jf in candidate_jsons:
        if "scene" in jf.name.lower():
            default_json = str(jf)
            break
    if not default_json and candidate_jsons:
        default_json = str(candidate_jsons[0])

    json_str = Prompt.ask(
        "[bold yellow]4. Nhập đường dẫn file JSON kịch bản phân đoạn cảnh (mapping scenes)[/bold yellow]",
        default=default_json
    ).strip().strip('"')
    json_path = Path(json_str)
    if not json_path.exists() or not json_path.is_file():
        console.print(f"[bold red][!] File JSON không tồn tại: {json_path}[/bold red]")
        return

    # 5. Tỉ lệ video (Aspect Ratio)
    console.print("\n[bold yellow]5. Chọn tỉ lệ khung hình video:[/bold yellow]")
    console.print("   [cyan]1[/cyan]. 16:9 Ngang (1920x1080) - [dim]YouTube, Facebook, Video dài[/dim]")
    console.print("   [cyan]2[/cyan]. 9:16 Dọc (1080x1920) - [dim]TikTok, Facebook Reels, YouTube Shorts[/dim]")
    console.print("   [cyan]3[/cyan]. 1:1 Vuông (1080x1080) - [dim]Instagram, Square[/dim]")
    aspect_choice = Prompt.ask("Chọn tỉ lệ", choices=["1", "2", "3"], default="1")
    aspect_map = {"1": "16:9", "2": "9:16", "3": "1:1"}
    aspect_ratio = aspect_map[aspect_choice]

    # 6. File video xuất ra
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    downloads_dir = base_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    default_out = str(downloads_dir / f"video_{timestamp}.mp4")
    out_str = Prompt.ask("[bold yellow]6. Đường dẫn file video xuất ra[/bold yellow]", default=default_out).strip().strip('"')
    output_path = Path(out_str)

    # Bắt đầu xử lý
    ffmpeg_exe = get_ffmpeg_path()
    with console.status("[cyan]Đang phân tích file phụ đề và đo thời lượng âm thanh...[/cyan]"):
        try:
            subtitles = parse_srt_file(srt_path)
            total_audio_dur = get_audio_duration(ffmpeg_exe, audio_path)
        except Exception as e:
            console.print(f"[bold red][!] Lỗi phân tích đầu vào: {e}[/bold red]")
            return

    console.print(f"[green][✓] Đã nạp [bold]{len(subtitles)}[/bold] đoạn phụ đề.[/green]")
    console.print(f"[green][✓] Tổng thời lượng âm thanh: [bold]{total_audio_dur:.2f} giây[/bold] ({format_time(total_audio_dur)}).[/green]")

    # Parse JSON
    try:
        available_sub_ids = sorted(list(subtitles.keys()))
        scenes = parse_json_mapping(json_path, available_sub_ids)
    except Exception as e:
        console.print(f"[bold red][!] Lỗi đọc file JSON: {e}[/bold red]")
        return

    if not scenes:
        console.print("[bold red][!] Không tìm thấy scene nào trong file JSON![/bold red]")
        return

    # Tính timeline
    timeline = compute_timeline(scenes, subtitles, total_audio_dur, image_dir)

    # Kiểm tra thiếu ảnh
    missing_images = [item for item in timeline if item["image"] is None]
    if missing_images:
        console.print(f"[bold red][!] Có {len(missing_images)} cảnh không tìm thấy file ảnh tương ứng trong thư mục '{image_dir}'![/bold red]")
        for m in missing_images:
            console.print(f"    - Cảnh {m['id']}")
        if not Confirm.ask("Bạn có muốn dừng lại để kiểm tra ảnh không?", default=True):
            console.print("[yellow]Đang tiếp tục với các ảnh có sẵn...[/yellow]")
        else:
            return

    # Hiển thị bảng timeline
    console.print()
    show_timeline_table(timeline, total_audio_dur)

    if not Confirm.ask("[bold cyan]Xác nhận tiến hành ghép video ngay?[/bold cyan]", default=True):
        console.print("[yellow]Đã hủy thao tác ghép video.[/yellow]")
        return

    # Thực hiện render
    res = render_video(
        timeline=timeline,
        audio_path=audio_path,
        output_path=output_path,
        total_audio_duration=total_audio_dur,
        aspect_ratio=aspect_ratio
    )

    if res.get("success"):
        file_size_mb = res.get("size_mb", 0.0)
        console.print(Panel(
            f"[bold green]🎉 GHÉP VIDEO THÀNH CÔNG RỰC RỠ![/bold green]\n\n"
            f"📁 Đường dẫn: [bold cyan]{output_path}[/bold cyan]\n"
            f"📦 Dung lượng: [bold]{file_size_mb:.2f} MB[/bold]\n"
            f"⏱️  Thời lượng: [bold]{format_time(total_audio_dur)}[/bold]\n"
            f"📐 Tỉ lệ: [bold]{aspect_ratio}[/bold]",
            title="Kết quả",
            border_style="green"
        ))

        if Confirm.ask("Bạn có muốn mở file video vừa tạo để xem ngay không?", default=True):
            try:
                open_path(output_path)
            except Exception as e:
                console.print(f"[red]Không thể mở video: {e}[/red]")
    else:
        console.print(f"[bold red][!] Ghép video thất bại: {res.get('error')}[/bold red]")

def cli_main():
    parser = argparse.ArgumentParser(description="Tạo video tự động từ ảnh, voice, srt và json.")
    parser.add_argument("--images", "-i", help="Đường dẫn thư mục chứa ảnh")
    parser.add_argument("--audio", "-a", help="Đường dẫn file voice/audio (.mp3, .wav)")
    parser.add_argument("--srt", "-s", help="Đường dẫn file phụ đề (.srt)")
    parser.add_argument("--json", "-j", help="Đường dẫn file cấu hình cảnh (.json)")
    parser.add_argument("--output", "-o", help="Đường dẫn file video đầu ra (.mp4)")
    parser.add_argument("--aspect", choices=["16:9", "9:16", "1:1"], default="16:9", help="Tỉ lệ khung hình")
    parser.add_argument("--fps", type=int, default=30, help="Số khung hình/giây (fps)")

    args = parser.parse_args()

    # Nếu không truyền đủ tham số dòng lệnh -> Chuyển sang chế độ hỏi tương tác (Interactive Prompt)
    if not (args.images and args.audio and args.srt and args.json):
        interactive_cli()
        return

    image_dir = Path(args.images)
    audio_path = Path(args.audio)
    srt_path = Path(args.srt)
    json_path = Path(args.json)
    output_path = Path(args.output or f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")

    ffmpeg_exe = get_ffmpeg_path()
    subtitles = parse_srt_file(srt_path)
    total_audio_dur = get_audio_duration(ffmpeg_exe, audio_path)
    scenes = parse_json_mapping(json_path, sorted(list(subtitles.keys())))
    timeline = compute_timeline(scenes, subtitles, total_audio_dur, image_dir)

    show_timeline_table(timeline, total_audio_dur)
    render_video(
        timeline=timeline,
        audio_path=audio_path,
        output_path=output_path,
        total_audio_duration=total_audio_dur,
        aspect_ratio=args.aspect,
        fps=args.fps
    )

if __name__ == "__main__":
    cli_main()

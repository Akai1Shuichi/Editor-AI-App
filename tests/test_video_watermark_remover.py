import unittest
import subprocess
from pathlib import Path
from PIL import Image
import numpy as np
from app.core.watermark_remover import (
    GeminiWatermarkRemover,
    VideoWatermarkCleaner,
    get_veo_watermark,
    get_roi,
    resolve_box,
    get_adaptive_video_preset,
    get_ffmpeg_path,
    is_video_file,
    is_image_file,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_VIDEO_PATH = Path("/tmp/sample_test_video.mp4")


class VideoWatermarkRemoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        exe = get_ffmpeg_path()
        if exe and not SAMPLE_VIDEO_PATH.exists():
            cmd = [
                exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=1280x720:rate=24",
                "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                str(SAMPLE_VIDEO_PATH)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def setUp(self):
        self.remover = GeminiWatermarkRemover()

    def test_file_type_detection(self):
        self.assertTrue(is_video_file("test.mp4"))
        self.assertTrue(is_video_file(Path("movie.MOV")))
        self.assertTrue(is_video_file("clip.webm"))
        self.assertFalse(is_video_file("photo.png"))

        self.assertTrue(is_image_file("photo.png"))
        self.assertTrue(is_image_file(Path("img.WEBP")))
        self.assertFalse(is_image_file("video.mp4"))

    def test_veo_watermark_geometry(self):
        # 1280x720 video
        box_720 = get_veo_watermark(1280, 720)
        self.assertEqual(box_720["size"], 48)
        self.assertEqual(box_720["width"], 48)
        self.assertEqual(box_720["height"], 48)
        self.assertEqual(box_720["x"], 1280 - 72 - 48)
        self.assertEqual(box_720["y"], 720 - 72 - 48)

        # 1920x1080 video
        box_1080 = get_veo_watermark(1920, 1080)
        self.assertEqual(box_1080["size"], 72)
        self.assertEqual(box_1080["width"], 72)
        self.assertEqual(box_1080["height"], 72)

        roi = get_roi(1920, 1080, box_1080)
        self.assertLessEqual(roi["x"], box_1080["x"])
        self.assertLessEqual(roi["y"], box_1080["y"])
        self.assertGreaterEqual(roi["x"] + roi["width"], box_1080["x"] + box_1080["width"])
        self.assertGreaterEqual(roi["y"] + roi["height"], box_1080["y"] + box_1080["height"])

    def test_video_adaptive_preset(self):
        preset_720 = get_adaptive_video_preset(1280, 720, mode="veo")
        self.assertEqual(preset_720["offsetX"], -24)
        self.assertEqual(preset_720["offsetY"], -24)
        self.assertEqual(preset_720["edgeRefinement"], 0.0)

        preset_1080 = get_adaptive_video_preset(1920, 1080, mode="veo")
        self.assertEqual(preset_1080["offsetX"], -36)
        self.assertEqual(preset_1080["offsetY"], -36)
        self.assertEqual(preset_1080["edgeRefinement"], 0.85)

    def test_clean_frame(self):
        frame = np.full((720, 1280, 3), 120, dtype=np.uint8)
        cleaner = VideoWatermarkCleaner(1280, 720, self.remover.bg96_img, self.remover.bg48_img, mode="veo")
        out_frame = cleaner.clean_frame(frame.copy())
        self.assertEqual(out_frame.shape, (720, 1280, 3))
        self.assertEqual(out_frame.dtype, np.uint8)

    def test_extract_preview_frame(self):
        if SAMPLE_VIDEO_PATH.exists():
            frame = self.remover.extract_preview_frame(SAMPLE_VIDEO_PATH, timestamp_sec=0.5)
            self.assertIsNotNone(frame)
            self.assertEqual(frame.size, (1280, 720))

            cleaned_frame, meta = self.remover.remove_video_watermark_frame(frame, mode="veo")
            self.assertEqual(cleaned_frame.size, (1280, 720))
            self.assertIn("box", meta)

    def test_process_video_file_pipeline(self):
        if SAMPLE_VIDEO_PATH.exists():
            out_video = Path("/tmp/unit_test_video_pipeline_out.mp4")
            if out_video.exists():
                out_video.unlink()
            res = self.remover.process_video_file(SAMPLE_VIDEO_PATH, out_video, mode="veo")
            self.assertTrue(res["success"])
            self.assertTrue(out_video.exists())
            self.assertGreater(out_video.stat().st_size, 0)
            self.assertEqual(res["size"], (1280, 720))


if __name__ == "__main__":
    unittest.main()

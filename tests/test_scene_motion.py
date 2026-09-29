import tempfile
import subprocess
import unittest
from pathlib import Path

from PIL import Image

from app.core.scene_motion import get_motion_values, normalize_motion, build_motion_filter
from app.core.video_creator import compute_timeline, get_ffmpeg_path, parse_json_data


class SceneMotionTests(unittest.TestCase):
    def test_normalize_motion_defaults_for_missing_and_invalid_data(self):
        default = {"type": "none", "strength": "subtle"}
        for value in (None, "zoom_in", [], {}, {"type": "zoom_in"},
                      {"type": "invalid", "strength": "subtle"},
                      {"type": "zoom_in", "strength": "strong"},
                      {"type": [], "strength": "subtle"},
                      {"type": "zoom_in", "strength": {}}):
            with self.subTest(value=value):
                self.assertEqual(normalize_motion(value), default)
        self.assertEqual(normalize_motion({"type": "pan_right", "strength": "medium"}),
                         {"type": "pan_right", "strength": "medium"})

    def test_zoom_and_pan_values_follow_eased_progress(self):
        zoom = {"type": "zoom_in", "strength": "subtle"}
        self.assertEqual(get_motion_values(zoom, 0, 0, 30)["scale"], 1.0)
        self.assertAlmostEqual(get_motion_values(zoom, 0.5, 15, 30)["scale"], 1.025)
        self.assertEqual(get_motion_values(zoom, 1, 30, 30)["scale"], 1.05)
        pan = get_motion_values({"type": "pan_right", "strength": "medium"}, 1, 30, 30)
        self.assertAlmostEqual(pan["translate_x"], 0.06)
        self.assertGreaterEqual(pan["scale"], 1.12)
        self.assertEqual(get_motion_values(None, 0.5, 15, 30)["scale"], 1)

    def test_drift_and_shake_are_bounded_and_deterministic(self):
        drift = {"type": "drift_left", "strength": "medium"}
        self.assertAlmostEqual(get_motion_values(drift, 0, 0, 30)["translate_x"], 0.02)
        self.assertAlmostEqual(get_motion_values(drift, 1, 30, 30)["translate_x"], -0.04)
        shake = {"type": "shake", "strength": "subtle"}
        first = get_motion_values(shake, 0.5, 15, 30)
        self.assertEqual(first, get_motion_values(shake, 0.5, 15, 30))
        self.assertLessEqual(abs(first["translate_x_px"]), 2)
        self.assertLessEqual(abs(first["translate_y_px"]), 2)

    def test_all_motion_directions(self):
        expected = {
            "pan_left": (1.06, -0.03, 0),
            "pan_right": (1.06, 0.03, 0),
            "pan_up": (1.06, 0, -0.03),
            "pan_down": (1.06, 0, 0.03),
            "drift_left": (1.06, -0.02, 0),
            "drift_right": (1.06, 0.02, 0),
            "zoom_out": (1, 0, 0),
        }
        for kind, (scale, x, y) in expected.items():
            with self.subTest(kind=kind):
                values = get_motion_values({"type": kind, "strength": "subtle"}, 1, 30, 30)
                self.assertAlmostEqual(values["scale"], scale)
                self.assertAlmostEqual(values["translate_x"], x)
                self.assertAlmostEqual(values["translate_y"], y)

    def test_timed_json_motion_reaches_timeline_without_changing_duration(self):
        def scene(scene_id, start, end, motion=None):
            item = {"id": scene_id, "character": "A", "character_info": "B",
                    "prompt": "C", "subtitle_ids": [1], "start_at": start, "end_at": end}
            if motion is not None:
                item["motion"] = motion
            return item
        raw = [scene("SC01", "00:00:00,000", "00:00:02,000", {"type": "zoom_in", "strength": "subtle"}),
               scene("SC02", "00:00:02,000", "AUDIO_END", {"type": "bad", "strength": "medium"})]
        parsed = parse_json_data(raw, [1])
        with tempfile.TemporaryDirectory() as folder:
            timeline = compute_timeline(parsed, {}, 5.0, Path(folder))
        self.assertEqual([item["duration"] for item in timeline], [2.0, 3.0])
        self.assertEqual(timeline[0]["motion"], {"type": "zoom_in", "strength": "subtle"})
        self.assertEqual(timeline[1]["motion"], {"type": "none", "strength": "subtle"})

    def test_old_timed_json_without_motion_defaults_to_none(self):
        raw = [{"id": "SC01", "character": "A", "character_info": "B", "prompt": "C",
                "subtitle_ids": [1], "start_at": "00:00:00,000", "end_at": "AUDIO_END"}]
        self.assertEqual(parse_json_data(raw, [1])[0]["motion"],
                         {"type": "none", "strength": "subtle"})

    def test_filter_uses_scene_frame_ranges_and_cover(self):
        timeline = [
            {"start": 0.0, "end": 2.0, "motion": {"type": "zoom_in", "strength": "subtle"}},
            {"start": 2.0, "end": 5.0, "motion": {"type": "pan_left", "strength": "medium"}},
        ]
        result = build_motion_filter(timeline, 640, 360, 30)
        self.assertIn("force_original_aspect_ratio=increase", result)
        self.assertIn("perspective=", result)
        self.assertIn("on-1", result)
        self.assertIn("on-61", result)
        self.assertIn("fps=30", result)

    def test_ffmpeg_renders_motion_across_scene_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = root / "SC01.png"
            second = root / "SC02.png"
            gradient = Image.new("RGB", (80, 45))
            for x in range(80):
                for y in range(45):
                    gradient.putpixel((x, y), (x * 3, y * 5, 0))
            gradient.save(first)
            Image.new("RGB", (80, 45), "blue").save(second)
            concat = root / "images.txt"
            concat.write_text(
                f"ffconcat version 1.0\nfile '{first.as_posix()}'\nduration 1\n"
                f"file '{second.as_posix()}'\nduration 1\nfile '{second.as_posix()}'\n",
                encoding="utf-8",
            )
            timeline = [
                {"start": 0, "end": 1, "motion": {"type": "zoom_in", "strength": "subtle"}},
                {"start": 1, "end": 2, "motion": {"type": "pan_right", "strength": "medium"}},
            ]
            filter_script = root / "motion.filter"
            filter_script.write_text(build_motion_filter(timeline, 80, 46, 10), encoding="utf-8")
            proc = subprocess.run([
                get_ffmpeg_path(), "-v", "error", "-f", "concat", "-safe", "0",
                "-i", str(concat), "-filter_script:v", str(filter_script),
                "-frames:v", "20", "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
            ], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode(errors="replace"))
            frame_size = 80 * 46 * 3
            self.assertEqual(len(proc.stdout), 20 * frame_size)
            self.assertNotEqual(proc.stdout[:frame_size], proc.stdout[9 * frame_size:10 * frame_size])
            self.assertNotEqual(proc.stdout[9 * frame_size:10 * frame_size],
                                proc.stdout[10 * frame_size:11 * frame_size])

    def test_subtle_pan_changes_image_on_each_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "scene.png"
            pattern = Image.new("RGB", (160, 90))
            for y in range(90):
                for x in range(160):
                    pattern.putpixel((x, y), ((x * 19 + y * 7) % 256,
                                                (x * 11 + y * 23) % 256, (x * 3 + y * 17) % 256))
            pattern.save(image)
            concat = root / "images.txt"
            concat.write_text(f"ffconcat version 1.0\nfile '{image.as_posix()}'\n"
                              "duration 3\n" + f"file '{image.as_posix()}'\n", encoding="utf-8")
            script = root / "motion.filter"
            script.write_text(build_motion_filter([
                {"start": 0, "end": 3, "motion": {"type": "pan_right", "strength": "subtle"}}
            ], 160, 90, 30), encoding="utf-8")
            proc = subprocess.run([
                get_ffmpeg_path(), "-v", "error", "-f", "concat", "-safe", "0",
                "-i", str(concat), "-filter_script:v", str(script),
                "-frames:v", "90", "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
            ], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode(errors="replace"))
            frame_size = 160 * 90 * 3
            frames = [proc.stdout[i * frame_size:(i + 1) * frame_size] for i in range(90)]
            self.assertEqual(len(frames[-1]), frame_size)
            held_frames = sum(frames[i] == frames[i - 1] for i in range(16, 75))
            self.assertLessEqual(held_frames, 2)


if __name__ == "__main__":
    unittest.main()

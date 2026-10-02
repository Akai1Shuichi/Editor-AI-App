import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageStat

from app.core import edit_document, video_creator


class EditRenderTests(unittest.TestCase):
    def test_legacy_render_without_edit_document_still_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "scene.png"
            audio = root / "voice.wav"
            output = root / "legacy.mp4"
            Image.new("RGB", (320, 180), "red").save(image)
            ffmpeg = video_creator.get_ffmpeg_path()
            subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i",
                            "anullsrc=r=44100:cl=mono", "-t", "0.5", str(audio)],
                           check=True, capture_output=True)
            result = video_creator.render_video(
                [{"index": 1, "id": "A", "image": image, "start": 0,
                  "end": 0.5, "duration": 0.5}], audio, output, 0.5, fps=24,
            )
            self.assertTrue(result["success"], result.get("error"))
            self.assertTrue(output.is_file())

    def test_render_timeline_uses_preview_order_and_black_gaps(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("first.png", "second.png"):
                Image.new("RGB", (32, 32), "red").save(root / name)
            document = {
                "version": 1,
                "sources": {"image_dir": ".", "audio": "voice.wav", "srt": "voice.srt"},
                "settings": {"aspect_ratio": "16:9", "fps": 30},
                "duration": 2.0,
                "tracks": {
                    "video": [
                        {"id": "a", "scene_id": "A", "media": "first.png",
                         "start": 0, "end": 0.8},
                        {"id": "b", "scene_id": "B", "media": "second.png",
                         "start": 0.5, "end": 1.2},
                    ],
                    "audio": [{"id": "voice", "media": "voice.wav", "start": 0, "end": 2}],
                    "subtitles": [],
                },
            }
            timeline = edit_document.render_timeline(root, document, 30)
            self.assertEqual([(part["id"], round(part["duration"], 3)) for part in timeline],
                             [("A", 0.5), ("A", 0.3), ("B", 0.4), ("gap", 0.8)])
            self.assertEqual(timeline[-1]["image"], None)
            self.assertAlmostEqual(sum(part["duration"] for part in timeline), 2)

    def test_ass_combines_overlapping_cues_in_preview_order(self):
        subtitles = [
            {"id": 1, "start": 0, "end": 1, "text": "Xin chào"},
            {"id": 2, "start": 0.5, "end": 1.5, "text": "Tạm biệt"},
        ]
        ass = video_creator.build_ass_subtitles(subtitles, 2, 320, 180, 30)
        dialogue = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
        self.assertEqual(len(dialogue), 3)
        self.assertIn(r"Xin chào\NTạm biệt", dialogue[1])
        self.assertNotIn("Tạm biệt", dialogue[0])
        self.assertNotIn("Xin chào", dialogue[2])

    def test_ffmpeg_burns_saved_subtitles_and_keeps_gap_black(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "scene.png"
            second = root / "second.png"
            Image.new("RGB", (320, 180), "red").save(image)
            Image.new("RGB", (180, 320), "blue").save(second)
            ffmpeg = video_creator.get_ffmpeg_path()
            audio = root / "voice.wav"
            subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i",
                            "anullsrc=r=44100:cl=mono", "-t", "1", str(audio)],
                           check=True, capture_output=True)
            document = edit_document.create_document(
                root, [{"index": 1, "id": "A", "image": image,
                        "start": 0, "end": 0.5, "subtitles": [1]},
                       {"index": 2, "id": "B", "image": second,
                        "start": 0.5, "end": 0.75, "subtitles": []}],
                {1: {"start": 0.25, "end": 0.9, "text": "Xin chào"}},
                root, audio, root / "voice.srt", "16:9", 24, 1,
                subtitles_enabled=True,
            )
            edit_document.save_document(root / "edit.json", document)
            saved = edit_document.load_document(root / "edit.json")
            timeline = edit_document.render_timeline(root, saved, 24)
            output = root / "output.mp4"
            result = video_creator.render_video(
                timeline, audio, output, saved["duration"], fps=24,
                subtitles=saved["tracks"]["subtitles"],
            )
            self.assertTrue(result["success"], result.get("error"))
            self.assertTrue(output.is_file())
            self.assertEqual(list(root.glob("temp_concat_*")), [])
            frame_hashes = subprocess.run(
                [ffmpeg, "-v", "error", "-i", str(output), "-map", "0:v:0",
                 "-f", "framemd5", "-"], check=True, capture_output=True, text=True,
            ).stdout
            self.assertEqual(len([line for line in frame_hashes.splitlines()
                                  if line and not line.startswith("#")]), 24)

            def frame_at(position, video=output):
                path = root / f"{video.stem}-frame-{position}.png"
                subprocess.run([ffmpeg, "-v", "error", "-i", str(video),
                                "-ss", str(position), "-frames:v", "1", str(path)],
                               check=True, capture_output=True)
                return Image.open(path).convert("RGB")

            early, caption, blue, gap, late = [frame_at(t) for t in (0.08, 0.38, 0.62, 0.79, 0.93)]
            self.assertGreater(early.getpixel((100, 100))[0], 120)
            self.assertGreater(blue.getpixel((100, 100))[2], 120)
            self.assertLess(gap.getpixel((100, 100))[0], 40)
            self.assertLess(late.getpixel((100, 100))[0], 40)
            # Subtitle changes pixels near the lower center, including over a gap.
            def lower_brightness(frame):
                region = frame.crop((520, 750, 1400, 1050))
                return sum(ImageStat.Stat(region).mean)
            self.assertLess(lower_brightness(caption), lower_brightness(early))
            self.assertGreater(lower_brightness(gap), lower_brightness(late))

            disabled_output = root / "disabled.mp4"
            disabled_result = video_creator.render_video(
                timeline, audio, disabled_output, saved["duration"], fps=24, subtitles=[],
            )
            self.assertTrue(disabled_result["success"], disabled_result.get("error"))
            disabled_caption = frame_at(0.38, disabled_output)
            self.assertAlmostEqual(lower_brightness(disabled_caption), lower_brightness(early), delta=1)
            self.assertEqual(list(root.glob("temp_concat_*")), [])


if __name__ == "__main__":
    unittest.main()

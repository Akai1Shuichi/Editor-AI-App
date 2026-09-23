"""End-to-end check that video export preserves unedited image detail."""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.core.video_creator import get_ffmpeg_path
from app.core.video_watermark_remover import VideoWatermarkRemover


class VideoOutputQualityTests(unittest.TestCase):
    def test_processed_video_stays_close_to_source(self):
        ffmpeg = get_ffmpeg_path()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            output = Path(directory) / "output.mp4"
            subprocess.run(
                [
                    ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=640x360:rate=24:duration=1",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                    "-pix_fmt", "yuv420p", str(source),
                ],
                check=True, capture_output=True,
            )

            result = VideoWatermarkRemover(ffmpeg).process_file(source, output, mode="veo3")
            self.assertTrue(result["success"], result.get("error"))
            self.assertEqual(result["frames_processed"], 24)

            comparison = subprocess.run(
                [
                    ffmpeg, "-hide_banner", "-i", str(source), "-i", str(output),
                    "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-",
                ],
                check=True, capture_output=True, text=True,
            )
            match = re.search(r"PSNR y:[\d.]+ u:[\d.]+ v:[\d.]+ average:([\d.]+)", comparison.stderr)
            self.assertIsNotNone(match, comparison.stderr)
            self.assertGreater(float(match.group(1)), 42.0)


if __name__ == "__main__":
    unittest.main()

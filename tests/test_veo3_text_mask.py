import unittest

import numpy as np

from app.core.video_watermark_remover import VideoWatermarkRemover, get_veo3_text_box


class Veo3TextMaskTests(unittest.TestCase):
    def test_inverse_alpha_restores_synthetic_overlay_without_touching_other_pixels(self):
        remover = VideoWatermarkRemover()
        height, width = 720, 1280
        rng = np.random.default_rng(10)
        clean = rng.integers(30, 180, (height, width, 3), dtype=np.uint8)
        watermarked = clean.copy()
        box = get_veo3_text_box(width, height)
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]
        alpha = np.asarray(remover.veo3_mask.getchannel("A"), dtype=np.float32) / 255.0
        original = clean[y:y + h, x:x + w].astype(np.float32)
        watermarked[y:y + h, x:x + w] = np.clip(
            original * (1 - alpha[:, :, None]) + 255 * alpha[:, :, None] + 0.5,
            0, 255,
        ).astype(np.uint8)

        restored, metadata = remover.remove_veo3_frame(watermarked)

        self.assertEqual(metadata["box"], box)
        self.assertTrue(np.array_equal(restored[:y], watermarked[:y]))
        self.assertTrue(np.array_equal(restored[:, :x], watermarked[:, :x]))
        self.assertLessEqual(
            int(np.abs(restored.astype(np.int16) - clean.astype(np.int16)).max()), 2
        )

    def test_720p_portrait_and_landscape_use_same_corner_mask(self):
        landscape = get_veo3_text_box(1280, 720)
        portrait = get_veo3_text_box(720, 1280)
        self.assertEqual((landscape["width"], landscape["height"]), (34, 15))
        self.assertEqual((portrait["width"], portrait["height"]), (34, 15))
        self.assertEqual((1280 - landscape["x"] - 34, 720 - landscape["y"] - 15), (16, 16))
        self.assertEqual((720 - portrait["x"] - 34, 1280 - portrait["y"] - 15), (16, 16))


if __name__ == "__main__":
    unittest.main()

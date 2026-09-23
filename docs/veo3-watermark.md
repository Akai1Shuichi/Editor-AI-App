# Gỡ watermark video Veo 3 (chữ “Veo”)

- Mask `app/assets/veo3_text_720.png` là chữ Veo màu trắng trên nền trong suốt; kênh alpha ghi độ đậm của từng pixel. Mask được thu từ mẫu công khai và căn theo hai video 720p ngang/dọc. Nguồn và giấy phép nằm ở `app/assets/veo3_text_720.LICENSE.txt`.
- Với video 720p, đặt mask 34 × 15 px, cách mép phải và mép dưới 16 px. Kích thước/vị trí được co theo cạnh ngắn của video.
- Đọc từng frame bằng FFmpeg rồi khôi phục pixel có chữ bằng phép đảo alpha: `gốc = (pixel có watermark - 255 × alpha) / (1 - alpha)`. Chỉ vùng chữ theo alpha bị thay đổi; không làm mờ cả ô.
- Mã xử lý: `get_veo3_text_box()` và `remove_veo3_frame()` trong `app/core/video_watermark_remover.py`. Đã thử với hai video mẫu 720p; độ phân giải khác có thể cần căn lại mask.

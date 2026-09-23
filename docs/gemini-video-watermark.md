# Gỡ watermark video Gemini (ngôi sao)

- Dùng `app/assets/bg_96.png` làm mask ngôi sao. Độ sáng RGB của mask biểu diễn alpha; mặc định nhân với `gain = 0.6`.
- Tính ô watermark từ kích thước video, rồi chỉnh tỉ lệ `1.01` và dịch `-24 px` theo cả hai trục ở cấu hình mặc định. Mask được thu về đúng kích thước ô.
- Trên từng frame, đảo phép ghép logo trắng: `gốc = (pixel có watermark - 255 × alpha) / (1 - alpha)`. Chỉ các pixel có alpha đáng kể được thay đổi; đường viền ô được làm mượt nhẹ.
- FFmpeg đọc và mã hóa lại video, đồng thời giữ luồng audio khi tương thích. Mã xử lý: `remove_frame()` và `process_file(mode="gemini")` trong `app/core/video_watermark_remover.py`.

# Gỡ watermark ảnh Gemini / Imagen

- Mask ngôi sao `bg_48` và `bg_96` được nhúng trong `app/core/watermark_remover.py`. Chương trình chọn mask theo kích thước ô watermark rồi đổi kích thước cho khớp ảnh.
- Vị trí và kích thước ô được tính từ kích thước ảnh; preset `auto` điều chỉnh tiếp theo độ phân giải và tỉ lệ khung hình. Độ sáng RGB của mask tạo alpha, mặc định với `gain = 0.6`.
- Khôi phục các pixel trong hình ngôi sao bằng `gốc = (pixel có watermark - 255 × alpha) / (1 - alpha)`. Alpha rất nhỏ được làm mềm để giảm viền; phần còn lại của ảnh giữ nguyên.
- File gốc không bị ghi đè; kết quả được lưu thành PNG. Mã xử lý: `GeminiWatermarkRemover` trong `app/core/watermark_remover.py`.

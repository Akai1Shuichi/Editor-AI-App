# Lộ trình phát hành theo giai đoạn

## Giai đoạn 1 — Watermark Remover

- [x] Chỉ đăng ký màn hình gỡ watermark ở entry point.
- [x] Loại các import Project, TTS, Settings và Pricing khỏi cửa sổ chính.
- [x] Không bundle `imageio-ffmpeg` (runtime phục vụ ghép video) vào bản PyInstaller.
- [ ] Build thử trên Windows, macOS và Linux; ghi lại dung lượng các gói ZIP.
- [ ] Kiểm thử thủ công: chọn file/thư mục, kéo-thả, xem trước, đổi thư mục đích và xử lý hàng loạt.

## Giai đoạn 2 — Tạo Voice TTS

- [ ] Giữ `app/ui/tts_tab.py`, `app/ui/voice_lookup_tab.py` và `app/core/vibi_client.py` ngoài entry point của giai đoạn 1.
- [x] Đăng ký TTS trong `MainWindow` và mở lại Settings/Pricing.
- [ ] Kiểm thử API Vibi với key hợp lệ.
- [ ] Bổ sung các dependency TTS cần thiết vào cấu hình build rồi phát hành bản nâng cấp.

## Giai đoạn 3 — Quản lý dự án và ghép video

- [ ] Giữ `app/ui/project_workspace.py`, `app/ui/scene_tab.py`, `app/ui/video_tab.py` và các core project/video ngoài entry point trước giai đoạn 3.
- [x] Đăng ký Project Workspace và luồng Watermark → TTS → Scene → Video trong giao diện.
- [ ] Bundle `imageio-ffmpeg` lại cho bản có ghép video; kiểm thử xuất MP4 trên ba hệ điều hành.

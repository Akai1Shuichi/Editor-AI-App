# ⚡ AI Media Studio (PyQt6 Modern Dark Theme)

Ứng dụng Desktop chuyên nghiệp với giao diện **PyQt6 Studio Modern Dark Theme**, tổ chức toàn bộ quy trình sản xuất video dạng chuỗi khép kín trong từng Dự Án:

1. **🎬 Không Gian Dự Án & Sản Xuất (Project Studio Workspace)**:
   - **Thanh Điều Khiển Dự Án (Project Toolbar)**: Chọn nhanh dự án, tạo dự án mới, xem tỉ lệ khung hình (16:9, 9:16, 1:1), FPS và mở thư mục dự án với 1 cú click.
   - **Tích hợp 3 Bước Sản Xuất Khép Kín trong Màn Dự Án**:
     - **🧹 Bước 1: Gỡ Watermark Ảnh**: Tự động loại bỏ Watermark Google Gemini / Imagen từ ảnh đơn hoặc hàng loạt (Batch). Xem trước Trước/Sau (Before & After), tự động lưu ảnh sạch vào thư mục `<du_an>/images/clean/`.
     - **🎙️ Bước 2: Tạo Giọng TTS**: Chuyển đổi văn bản thành giọng nói ElevenLabs/MiniMax/CapCut chất lượng cao qua Vibi API. Hỗ trợ tra cứu Thư viện Voice, tự động chia nhỏ văn bản dài, xuất phụ đề SRT và tự động lưu vào `<du_an>/voice/`. Nút "🎬 Ghép Video" tự động chuyển dữ liệu sang Bước 3.
     - **🎬 Bước 3: Ghép Video Thành Phẩm (Video Composer)**: Ghép video tự động đồng bộ ảnh cảnh sạch, phụ đề SRT, âm thanh voice và kịch bản phân đoạn JSON trong chính dự án. Tự động tính toán mốc thời gian hiển thị từng ảnh, xuất video chuẩn MP4 H.264/AAC với 3 tỉ lệ khung hình vào `<du_an>/output/`.
   - **Quản Lý Danh Sách Dự Án (Project List)**: Xem danh sách tất cả dự án, số lượng ảnh sạch, voice, video đã xuất và kích hoạt chuyển đổi nhanh.
2. **⚙️ Cài Đặt & Quản Lý Tài Khoản Vibi**: Nhập và lưu API Key an toàn vào `.env`, kiểm tra số dư Credits và thông tin tài khoản theo thời gian thực.

---

## 🚀 Hướng dẫn Khởi chạy Ứng dụng

### Windows (Khuyên dùng)
```cmd
cd Editor-AI-App
.venv\Scripts\python.exe start_app.py
```
Hoặc chạy lệnh CLI tạo video:
```cmd
.venv\Scripts\python.exe create_video.py --images projects/review-cong-nghe-01/images/clean --audio projects/review-cong-nghe-01/voice/narration.mp3 --srt projects/review-cong-nghe-01/voice/narration.srt --json projects/review-cong-nghe-01/scenes.json --output projects/review-cong-nghe-01/output/final_video.mp4
```

---

## 📂 Cấu trúc Thư Mục Dự Án Chuẩn
Mỗi dự án được quản lý độc lập tại `projects/<ten_du_an>/`:
```
projects/<ten_du_an>/
├── project.json          # Cấu hình dự án (tên, tỉ lệ khung hình, fps, ngày tạo)
├── scenes.json           # Kịch bản phân cảnh của video
├── images/               # Thư mục ảnh gốc
│   └── clean/            # Thư mục ảnh sạch đã gỡ watermark (được ưu tiên ghép vào video)
├── voice/                # File âm thanh (.mp3, .wav) và phụ đề (.srt)
└── output/               # Video MP4 xuất bản thành phẩm
```


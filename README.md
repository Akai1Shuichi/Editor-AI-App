# ⚡ Editor Video AI

> Ứng dụng có công cụ gỡ watermark, TTS, quản lý dự án và ghép video. Nhập Voice API Key trong Cài đặt để dùng TTS.

Ứng dụng Desktop chuyên nghiệp với giao diện **PyQt6 Studio Modern Dark Theme**, tổ chức toàn bộ quy trình sản xuất video dạng chuỗi khép kín trong từng Dự Án:

1. **🎬 Không Gian Dự Án & Sản Xuất (Project Studio Workspace)**:
   - **Thanh Điều Khiển Dự Án (Project Toolbar)**: Chọn nhanh dự án, tạo dự án mới, xem tỉ lệ khung hình (16:9, 9:16, 1:1), FPS và mở thư mục dự án với 1 cú click.
   - **Tích hợp 4 Bước Sản Xuất Khép Kín trong Màn Dự Án**:
     - **🧹 Bước 1: Gỡ Watermark Ảnh**: Tự động loại bỏ Watermark Google Gemini / Imagen từ ảnh đơn hoặc hàng loạt (Batch). Xem trước Trước/Sau (Before & After), tự động lưu ảnh sạch vào thư mục `<du_an>/images/clean/`.
     - **🎙️ Bước 2: Tạo Giọng TTS**: Chuyển đổi văn bản thành giọng nói ElevenLabs/MiniMax/CapCut chất lượng cao qua Vibi API. Hỗ trợ tra cứu Thư viện Voice, tự động chia nhỏ văn bản dài, xuất phụ đề SRT và tự động lưu vào `<du_an>/voice/`. Nút "Kịch Bản Cảnh" tự động chuyển dữ liệu sang Bước 3.
     - **📝 Bước 3: Kịch Bản Phân Cảnh**: Nhập trực tiếp nội dung JSON hoặc chọn một file JSON có sẵn. Dự án không tự gán kịch bản mặc định.
     - **🎬 Bước 4: Ghép Video Thành Phẩm (Video Composer)**: Ghép video tự động đồng bộ ảnh cảnh sạch, phụ đề SRT, âm thanh voice và kịch bản phân đoạn JSON. Tự động tính toán mốc thời gian hiển thị từng ảnh, xuất video chuẩn MP4 H.264/AAC với 3 tỉ lệ khung hình vào `<du_an>/output/`.
   - **Quản Lý Danh Sách Dự Án (Project List)**: Xem danh sách tất cả dự án, số lượng ảnh sạch, voice, video đã xuất và kích hoạt chuyển đổi nhanh.
2. **⚙️ Cài Đặt & Quản Lý Tài Khoản Vibi**: Nhập và lưu API Key an toàn vào `.env`, kiểm tra số dư Credits và thông tin tài khoản theo thời gian thực.

### Gỡ watermark Video

Tab **Gỡ watermark Video** nhận file MP4, MOV, MKV hoặc WebM. Chọn **Veo 3
(chữ Veo)** để gỡ chữ nhỏ ở góc dưới phải bằng mask `veo3_text_720.png`
và phép inverse-alpha (đã kiểm tra trên video 720p ngang và dọc), hoặc
**Gemini (ngôi sao)** để dùng mask `bg_96.png` với cùng phép toán (`gain=0.6`).
Ứng dụng xử lý ngay trên máy và xuất MP4 H.264
(`yuv420p`). Ứng dụng **không tải video** lên máy chủ; audio nguồn được giữ lại khi tương thích
với MP4. FFmpeg (qua `imageio-ffmpeg` hoặc bản cài trong `PATH`) là bắt buộc.

---

## 🚀 Hướng dẫn Khởi chạy Ứng dụng

Yêu cầu: Python 3.10 trở lên. FFmpeg được tự động tải qua `imageio-ffmpeg`; nếu máy đã có FFmpeg trong `PATH`, ứng dụng sẽ dùng bản đó trước.

### Windows

```cmd
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python start_app.py
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python start_app.py
```

Nếu Python chưa có trên máy, cài từ [python.org](https://www.python.org/downloads/macos/) hoặc Homebrew (`brew install python`). macOS có thể hỏi xác nhận khi lần đầu mở ứng dụng hoặc thư mục.

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python start_app.py
```

Trên Debian/Ubuntu, nếu chưa có `venv`, chạy `sudo apt install python3-venv`. Chức năng mở file/thư mục dùng `xdg-open`, thường đã có trong môi trường desktop Linux.

### Ghi chú tương thích

- Không chạy `create_video.py`: file này không còn tồn tại. Tính năng ghép video nằm trong giao diện ứng dụng.
- Tránh các bản Python quá cũ; PyQt6 và Pillow trong `requirements.txt` cần Python hiện đại.
- `imageio-ffmpeg` tải binary riêng theo Windows, macOS hoặc Linux. Khi mạng công ty chặn lần tải đầu tiên, hãy cài FFmpeg hệ thống và bảo đảm lệnh `ffmpeg` có trong `PATH`.

---

## 📂 Cấu trúc Thư Mục Dự Án Chuẩn
Mỗi dự án được quản lý độc lập tại `projects/<ten_du_an>/`:
```
projects/<ten_du_an>/
├── project.json          # Cấu hình dự án (tên, tỉ lệ khung hình, fps, ngày tạo)
├── scenes.json           # Được tạo khi người dùng nhập kịch bản dạng text
├── edit.json             # Bản dựng Bước 4: track ảnh/voice/phụ đề và cấu hình xuất
├── edit.json.bak         # Bản dựng trước lần tạo lại từ nguồn gần nhất (nếu có)
├── images/               # Thư mục ảnh gốc
│   └── clean/            # Thư mục ảnh sạch đã gỡ watermark (được ưu tiên ghép vào video)
├── voice/                # File âm thanh (.mp3, .wav) và phụ đề (.srt)
└── output/               # Video MP4 xuất bản thành phẩm
```

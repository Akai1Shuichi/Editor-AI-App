# ⚡ AI Media Studio (PyQt6 Modern Dark Theme)

Ứng dụng Desktop hiện đại với giao diện **PyQt6 Modern Dark Theme**, tích hợp công nghệ AI từ `evenlabs-voice`:
1. **🧹 Gỡ Watermark AI**: Tự động loại bỏ Watermark Google Gemini / Imagen từ ảnh đơn hoặc hàng loạt (Batch). Hỗ trợ kéo thả ảnh (Drag & Drop), xem trước Trước/Sau (Before & After), điều chỉnh độ lợi sáng (Gain), đa luồng không giật lag.
2. **⚡ Tạo Giọng Vibi TTS**: Chuyển đổi văn bản nhập tay thành giọng nói ElevenLabs chất lượng cao qua Vibi API. Hỗ trợ tự động chia nhỏ đoạn cho văn bản dài, tùy biến Model, Stability, Similarity, Speed, xuất phụ đề SRT và tích hợp sẵn trình phát Audio (Built-in Player) ngay trong app.
3. **🔍 Tra Cứu Voice ID**: Tra cứu và tìm kiếm danh sách giọng đọc mặc định (Default Premade) và thư viện giọng cộng đồng (Shared Voice Library), lọc theo giới tính, ngôn ngữ, sắp xếp thịnh hành, copy nhanh Voice ID và 1-click chọn giọng cho tab TTS.
4. **💳 Quản Lý API Key & Tài Khoản Vibi**: Nhập và lưu API Key an toàn vào `.env`, kiểm tra số dư Credits và thông tin tài khoản thời gian thực.

---

## 🚀 Hướng dẫn Khởi chạy Ứng dụng

### Cách 1: Chạy trực tiếp bằng file script (Đơn giản nhất)
```bash
cd "editor video app"
./run.sh
```

### Cách 2: Khởi chạy bằng Python
```bash
cd "editor video app"
.venv/bin/python start_app.py
```
Hoặc nếu đã kích hoạt môi trường ảo:
```bash
source .venv/bin/activate
python3 start_app.py
```

---

## 📂 Cấu trúc Dự án
```
editor video app/
├── .env                          # Tệp lưu trữ VIBI_API_KEY và cài đặt
├── requirements.txt              # Danh sách thư viện (PyQt6, Pillow, requests, numpy,...)
├── run.sh                        # Script khởi chạy nhanh có phân quyền thực thi
├── start_app.py                  # Entry point Python khởi động ứng dụng
├── app/
│   ├── config.py                 # Quản lý cấu hình runtime và đồng bộ .env
│   ├── styles.py                 # Bộ QSS Stylesheet Modern Dark Theme cao cấp
│   ├── main.py                   # Điểm khởi tạo QApplication và MainWindow
│   ├── core/
│   │   ├── watermark_remover.py  # Động cơ Inverse Alpha Blending gỡ watermark Gemini
│   │   └── vibi_client.py        # Client kết nối Vibi API (TTS, Voices, Auth)
│   └── ui/
│       ├── main_window.py        # Cửa sổ chính với Sidebar điều hướng mượt mà
│       ├── watermark_tab.py      # Giao diện gỡ watermark, Preview Before/After
│       ├── tts_tab.py            # Giao diện Text to Speech & Trình phát Audio tích hợp
│       ├── voice_lookup_tab.py   # Giao diện tra cứu thư viện giọng và Voice ID
│       └── settings_tab.py       # Giao diện quản lý API Key và kiểm tra Credits
└── downloads/                    # Thư mục mặc định lưu các file MP3 và SRT sinh ra
```

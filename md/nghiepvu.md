# 📋 Tài Liệu Nghiệp Vụ Ứng Dụng (AI Media Studio)

Tài liệu tóm tắt ngắn gọn, logic toàn bộ quy trình nghiệp vụ và luồng xử lý của ứng dụng **AI Media Studio**.

---

## 1. Nghiệp Vụ Gỡ Watermark AI (Gemini / Imagen)

### 🎯 Mục tiêu
Loại bỏ watermark bán trong suốt (semi-transparent) của Google Gemini / Imagen từ ảnh đơn hoặc hàng loạt mà không làm mờ, biến dạng hay giảm độ phân giải của ảnh gốc.

### 🔄 Luồng xử lý (Workflow)
```text
[ Ảnh đầu vào (PNG/JPG/WEBP) ] 
        │
        ▼
[ Nhận diện tỷ lệ & Kích thước ] ──► Tính toán Box watermark (Tọa độ X, Y, Size)
        │
        ▼
[ Áp dụng Inverse Alpha Blending ] ──► Trừ lớp phủ Logo dựa trên Template & Gain (0.60)
        │
        ▼
[ Xuất file ảnh sạch ] ──► Tên file: {tên_gốc}_cleaned.png (Lưu tại thư mục 'clean/' bên trong thư mục vừa nạp hoặc chỉ định)
```

### ⚙️ Quy tắc nghiệp vụ
1. **Định dạng hỗ trợ**: PNG, JPG, JPEG, WEBP.
2. **Kéo thả / Batch & Thư mục Clean**: Hỗ trợ kéo thả 1 hoặc nhiều ảnh/thư mục; tự động lọc bỏ các file đã có đuôi `_cleaned.png`. Mặc định tự động tạo thư mục con `clean/` ngay bên trong thư mục chứa ảnh đầu vào để chứa toàn bộ ảnh sạch sau xử lý, tránh gây xáo trộn hoặc lộn xộn với các ảnh gốc.
3. **Cơ chế chạy ngầm**: Xử lý qua `QThread` tách biệt, cập nhật tiến trình từng file lên bảng kết quả, không khóa giao diện chính.
4. **Tham số tinh chỉnh**:
   - `Gain`: Độ lợi sáng (Mặc định `0.60`).
   - `Chế độ`: *Tự động (Auto)* theo tỷ lệ ảnh hoặc *Cổ điển (Classic)* cố định.

---

## 2. Nghiệp Vụ Tạo Giọng Nói ElevenLabs (Voice API TTS)

### 🎯 Mục tiêu
Chuyển đổi văn bản nhập tay thành file âm thanh giọng nói tự nhiên (MP3) kèm phụ đề (SRT) thông qua Voice API (`https://api.vibi.pro`).

### 🔄 Luồng xử lý (Workflow)
```text
[ Văn bản nhập tay ] 
        │
        ▼
[ Kiểm tra độ dài ] ──► Nếu > 3,500 ký tự: Tự động ngắt theo câu thành N đoạn
        │
        ▼
[ Gửi Task lên Voice API ] ──► POST /v1/text-to-speech/{voice_id} (Kèm Model, Settings, SRT)
        │
        ▼
[ Polling trạng thái ] ──► GET /v1/history/{id} lặp mỗi 1.5s (Chờ status == 'completed')
        │
        ▼
[ Tải Audio & SRT ] ──► Lưu vào thư mục `downloads/`
        │
        ▼
[ Kích hoạt Player ] ──► Nạp file vào Trình phát âm thanh để nghe thử trực tiếp
```

### ⚙️ Quy tắc nghiệp vụ
1. **Chia nhỏ văn bản (Chunking)**: Tách theo ranh giới câu (`.`, `!`, `?`, `\n`), tối đa 3,500 ký tự/đoạn để không bị lỗi timeout hoặc vượt giới hạn API.
2. **Cấu hình giọng**:
   - `Voice ID`: Khóa định danh giọng nói ElevenLabs.
   - `Model`: `eleven_v3` (ưu tiên), `eleven_multilingual_v2`, `eleven_flash_v2_5`, `eleven_turbo_v2_5`.
   - `Tham số`: Stability (0.0 - 1.0), Similarity Boost (0.0 - 1.0), Speed (0.7x - 1.5x).
3. **Phụ đề SRT**: Khi bật tùy chọn, tải file `.srt` đồng bộ tên với file `.mp3`.
4. **Trình phát (Player)**: Phát, tạm dừng, dừng, tua thời lượng và mở thư mục lưu trữ ngay khi tạo xong.

---

## 3. Nghiệp Vụ Tra Cứu Danh Sách Giọng & Voice ID (Tích Hợp Trong Tab TTS)

### 🎯 Mục tiêu
Giúp người dùng tìm kiếm, nghe thử và chọn nhanh Voice ID phù hợp từ thư viện ElevenLabs (Default & Shared) trực tiếp bên trong màn hình **Tạo giọng TTS** mà không cần chuyển qua lại giữa các mục sidebar.

### 🔄 Luồng xử lý (Workflow)
```text
[ Tab Tạo Giọng Nói: Bấm "🔍 Tra cứu Voice..." ] ──► Chuyển sang Sub-tab "Tra Cứu Voice"
                                                                │
                                                                ▼
[ Chọn Danh Mục: Default / Shared ] ──► [ Nhập từ khóa / Lọc giới tính ] ──► [ Gọi Voice API ]
                                                                                    │
                                                                                    ▼
                                                              [ Hiển thị danh sách bảng ]
                                                                                    │
             ┌─────────────────────────────────────┬───────────────────────────────┴───────────────────────────────┐
             ▼                                     ▼                                                               ▼
     [ Nút "Dùng giọng" ]                 [ Nút "Copy ID" ]                                               [ Nút "Mặc định" ]
             │                                     │                                                               │
             ▼                                     ▼                                                               ▼
  Gán Voice ID & Chuyển ngay              Lưu mã Voice ID vào Clipboard                                  Lưu vào .env làm ID mặc định
  về Sub-tab Tạo Giọng Nói
```

### ⚙️ Quy tắc nghiệp vụ
1. **Kiến trúc giao diện**: Tích hợp dạng Sub-tab (`QTabWidget`) bên trong Tab TTS (`TTSTab`), loại bỏ nút riêng trên thanh điều hướng sidebar giúp menu gọn gàng, tối ưu luồng thao tác.
2. **Nguồn dữ liệu**:
   - `Default Voices`: Gọi `GET /v1/default-voices` (Giọng gốc bản quyền).
   - `Shared Voices`: Gọi `GET /v1/shared-voices` (Giọng cộng đồng chia sẻ, hỗ trợ lọc Nam/Nữ).
3. **Tự động tải dữ liệu (Auto-load)**:
   - Khi bấm "🔍 Tra cứu Voice..." hoặc chuyển sang Sub-tab "Tra Cứu Voice" lần đầu tiên, nếu bảng còn trống và đã có API Key, hệ thống tự động tải danh sách giọng mặc định.
   - Thay đổi bộ lọc giới tính sẽ tự động kích hoạt truy vấn lại.
4. **Tương tác liền mạch (In-tab navigation)**:
   - Bấm "Dùng giọng" lập tức gán Voice ID vào ô nhập liệu, cập nhật nhãn trạng thái `✓ Đã chọn giọng: {name} ({voice_id})` và tự động chuyển về Sub-tab "Tạo Giọng Nói".
   - Bấm "Copy ID" sao chép Voice ID vào Clipboard máy tính.
   - Bấm "Mặc định" ghi nhận Voice ID này làm giá trị khởi động mặc định trong `.env`.

---

## 4. Nghiệp Vụ Quản Lý Tài Khoản & Cấu Hình Hệ Thống

### 🎯 Mục tiêu
Xác thực bản quyền Voice API, giám sát số dư tín dụng (Credits) và lưu trữ các tùy chọn người dùng lâu dài.

### 🔄 Luồng xử lý (Workflow)
```text
[ Người dùng nhập API Key ] ──► [ Bấm "Lưu" ] ──► Ghi vào file .env
                                      │
                                      ▼
                           [ Bấm "Kiểm Tra Số Dư" ]
                                      │
                                      ▼
                        Gọi GET /v1/auth/me (xi-api-key)
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
         [ HTTP 200: Thành công ]                  [ HTTP 401/Lỗi: Thất bại ]
                 │                                         │
                 ▼                                         ▼
   Hiển thị số dư Credits xanh lá              Báo lỗi API Key không hợp lệ
   Cập nhật trạng thái "Connected"             Cập nhật trạng thái "Chưa có Key"
```

### ⚙️ Quy tắc nghiệp vụ
1. **Schema dữ liệu từ `GET /v1/auth/me`**:
   - `credit_balance`: Số dư credits khả dụng của tài khoản (ví dụ: `129,293`).
   - `name`: Tên người dùng.
   - `email`: Địa chỉ email tài khoản.
   - `role`: Quyền hạn (`user`, `admin`).
   - `id`: Mã User ID định danh.
2. **Bảo mật Key**: Mặc định hiển thị dưới dạng Password (`***`), có nút bật/tắt hiển thị.
3. **Lưu trữ vĩnh viễn**: Mọi thay đổi về Key, Voice ID mặc định, Model, Ngôn ngữ, Thư mục lưu trữ đều được lưu vào `.env` ở thư mục gốc app.
4. **Đồng bộ trạng thái toàn cục**: Khi lưu Key hoặc kiểm tra số dư thành công, thẻ trạng thái (Status Chip) tại chân thanh điều hướng (Sidebar Footer) sẽ hiển thị số dư thực tế `● Voice API: {credit_balance:,} credits` và đổi màu xanh thông báo kết nối sẵn sàng.

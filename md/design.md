# 📐 Thiết Kế Giao Diện ASCII - AI Media Studio (PyQt6)

Tài liệu thiết kế Wireframe dạng ASCII cho toàn bộ các màn hình của ứng dụng **AI Media Studio**, theo chuẩn phong cách **Minimalist Dark Theme** (tinh gọn, trực quan, phân cấp logic, không thừa thãi).

---

## 1. Khung Tổng Thể Ứng Dụng (Main Window Layout)

```text
+---------------------+-------------------------------------------------------------------------------+
|  Studio AI          |  Gỡ Watermark Gemini / Imagen                                                 |
|  Watermark & TTS    +-------------------------------------------------------------------------------+
+---------------------+                                                                               |
|                     |                                                                               |
| [🧹 Gỡ Watermark  ] |                                                                               |
|                     |                                                                               |
| [🎙️ Tạo giọng TTS  ] |                         VÙNG NỘI DUNG THAY ĐỔI THEO TAB                       |
|                     |                                (QStackedWidget)                               |
| [⚙️ Cài đặt & Số dư]|                                                                               |
|                     |                                                                               |
|                     |                                                                               |
|                     |                                                                               |
|                     |                                                                               |
+---------------------+                                                                               |
| [● Voice API: ... ] |                                                                               |
+---------------------+-------------------------------------------------------------------------------+
```

---

## 2. Màn Hình 1: Gỡ Watermark AI (`WatermarkTab`)

Chia bố cục 2 cột cân đối bằng `QSplitter`:

- **Cột Trái (60%)**: Nạp ảnh, danh sách xử lý hàng loạt, cấu hình độ lợi sáng & nút hành động.
- **Cột Phải (40%)**: Khung xem trước Before (Ảnh gốc) & After (Ảnh đã gỡ).

```text
+-------------------------------------------------------------+---------------------------------------+
|                       CỘT ĐIỀU KHIỂN                        |             CỘT XEM TRƯỚC             |
+-------------------------------------------------------------+---------------------------------------+
|  +-------------------------------------------------------+  |  Ảnh gốc:                             |
|  |  📥  Kéo thả ảnh vào đây, hoặc click để chọn file      |  |  +---------------------------------+  |
|  +-------------------------------------------------------+  |  |                                 |  |
|                                                             |  |                                 |  |
|  [ Chọn File Ảnh ]   [ Chọn Thư Mục ]       [ Xóa Danh Sách]|  |           (Preview ảnh)         |  |
|                                                             |  |                                 |  |
|  +-------------------------------------------------------+  |  +---------------------------------+  |
|  | Tên File         | Trạng Thái | Đường Dẫn Kết Quả     |  |                                       |
|  |------------------+------------+-----------------------|  |  Kết quả sau khi gỡ:                  |
|  | gemini_art_1.png | Xong       | .../gemini_art_1_c... |  |  +---------------------------------+  |
|  | gemini_art_2.png | Chờ        | -                     |  |  |                                 |  |
|  | imagen_3.webp    | Chờ        | -                     |  |  |       (Ảnh sạch watermark)       |  |
|  +-------------------------------------------------------+  |  |                                 |  |
|                                                             |  |                                 |  |
|  +-------------------------------------------------------+  |  +---------------------------------+  |
|  | Chế độ: [ Tự động (Auto) v ]   Độ sáng: [---O---] 0.60 |  |                                       |
|  | [x] Lưu thư mục riêng   [ Chọn... ]                   |  |                                       |
|  +-------------------------------------------------------+  |                                       |
|                                                             |                                       |
|  [        Bắt đầu xử lý (Primary)        ]  [ Dừng ]  [ Mở ]|                                       |
|  [========================== 45% =========================] |                                       |
|  Đang xử lý (2/5): gemini_art_2.png                         |                                       |
+-------------------------------------------------------------+---------------------------------------+
```

---

## 3. Màn Hình 2: Tạo Giọng TTS & Thư Viện Voice (`TTSTab`)

Tab **Tạo giọng TTS** tích hợp sẵn hệ thống Sub-tab (`QTabWidget`) 2 trang:
- **Sub-tab 1 (`🎙️ Tạo Giọng Nói`)**: Soạn thảo văn bản, cấu hình tham số, tạo file âm thanh và trình phát audio.
- **Sub-tab 2 (`🔍 Tra Cứu Voice`)**: Thư viện tra cứu danh sách giọng (Mặc định & Cộng đồng) tích hợp ngay bên trong.

### 3.1 Sub-tab 1: Tạo Giọng Nói

Bấm nút **"🔍 Tra cứu Voice..."** ở ô Voice ID sẽ lập tức chuyển sang Sub-tab 2 để chọn giọng.

```text
+-----------------------------------------------------------------------------------------------------+
| [ 🎙️ Tạo Giọng Nói (Active) ]  [ 🔍 Tra Cứu Voice ]                                                  |
+-----------------------------------------------------------------------------------------------------+
| Văn bản cần đọc:                                                                   1,250 ký tự | 1 đoạn |
| +-------------------------------------------------------------------------------------------------+ |
| | Trí tuệ nhân tạo đang thay đổi cách chúng ta sáng tạo nội dung số mỗi ngày...                   | |
| |                                                                                                 | |
| |                                                                                                 | |
| +-------------------------------------------------------------------------------------------------+ |
|                                                                                                     |
| +-- Cấu hình Giọng & Tham số ---------------------------------------------------------------------+ |
| | Voice ID: [ 6adFm46eyy74snVn6YrT       ] [🔍 Tra cứu Voice...] Model:[ eleven_v3 v] Ngôn ngữ:[vi v]|
| |                                                                                                 | |
| | Stability: [---O---] 0.50   Similarity: [-----O-] 0.75   Speed: [---O---] 1.00x   [x] Xuất SRT  | |
| +-------------------------------------------------------------------------------------------------+ |
|                                                                                                     |
| [                                 Tạo Giọng Nói (Primary Action)                 ]  [    Hủy    ]   |
| [============================================== 100% =============================================] |
| ✓ Đã chọn giọng: Mai Anh (6adFm46eyy74snVn6YrT)                                                     |
|                                                                                                     |
| +-- Trình phát âm thanh --------------------------------------------------------------------------+ |
| | 🎧 tri_tue_nhan_tao_20260910.mp3 (384,120 bytes) + Phụ đề SRT                 [ Mở thư mục lưu ]| |
| |                                                                                                 | |
| | [ ▶ Tiếp tục ]  [ ⏹ Dừng ]   01:15  [=============O------------------------]  03:40             | |
| +-------------------------------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------------------------------+
```

### 3.2 Sub-tab 2: Tra Cứu Voice & Thư Viện Giọng

Giao diện tìm kiếm, chọn lọc giọng nói. Bấm **"Dùng giọng"** sẽ tự động gán Voice ID và chuyển về ngay Sub-tab 1.

```text
+-----------------------------------------------------------------------------------------------------+
| [ 🎙️ Tạo Giọng Nói ]  [ 🔍 Tra Cứu Voice (Active) ]                                                  |
+-----------------------------------------------------------------------------------------------------+
| [ Giọng Mặc Định (Default) v ]  [ Nhập tên giọng, accent, từ khóa...        ] [ Nam (Male) v ] [ Tìm kiếm ] |
|-----------------------------------------------------------------------------------------------------|
| [-------------------------------------------------------------------------------------------------] |
|                                                                                                     |
| +-------------------------------------------------------------------------------------------------+ |
| | Tên Giọng    | Voice ID             | Giới Tính | Ngôn Ngữ / Accent      | Thao Tác             | |
| |--------------+----------------------+-----------+------------------------+----------------------| |
| | Adam         | 21m00Tcm4TlvDq8ikWAM | Male      | American - Deep        | [Dùng] [Copy] [M.Định] |
| | Rachel       | 2EiwWnXFnvU5JabPnv8n | Female    | American - Calm        | [Dùng] [Copy] [M.Định] |
| | Mai Anh      | 6adFm46eyy74snVn6YrT | Female    | Vietnamese - Truyền cảm| [Dùng] [Copy] [M.Định] |
| | Minh Phong   | ErXwobaYiN019PkySvjV | Male      | Vietnamese - Trầm ấm   | [Dùng] [Copy] [M.Định] |
| | Bella        | EXAVITQu4vr4xnSDxMaL | Female    | American - Soft        | [Dùng] [Copy] [M.Định] |
| +-------------------------------------------------------------------------------------------------+ |
|                                                                                                     |
| Tìm thấy 48 giọng phù hợp.                                                                          |
+-----------------------------------------------------------------------------------------------------+
```

---

## 4. Màn Hình 3: Cài Đặt & Quản Lý Tài Khoản Voice API (`SettingsTab`)

Form cấu hình chuẩn UI/UX, phân cấp 2 Panel phẳng rõ ràng:

```text
+-----------------------------------------------------------------------------------------------------+
| +-- Tài Khoản Voice API --------------------------------------------------------------------------+ |
| | API Key:  [ xi-api-key-***************************** ]  [ Hiện ]  [ Lưu ]  [ Kiểm Tra Số Dư ]    | |
| |                                                                                                 | |
| | +---------------------------------------------------------------------------------------------+ | |
| | | Số dư: 125,400 credits             Người dùng: Trần Toàn            Email: toan@example.com | | |
| | +---------------------------------------------------------------------------------------------+ | |
| +-------------------------------------------------------------------------------------------------+ |
|                                                                                                     |
| +-- Cài Đặt Mặc Định -----------------------------------------------------------------------------+ |
| | Voice ID mặc định: [ 6adFm46eyy74snVn6YrT                                                     ] | |
| |                                                                                                 | |
| | Model mặc định:    [ eleven_v3                       v ]    Ngôn ngữ: [ vi                    v]| |
| |                                                                                                 | |
| | Thư mục lưu file:  /home/trtoan/Documents/HOCTAP/TOOL/editor video app/downloads [Đổi...] [ Mở ]| |
| |                                                                                                 | |
| | [                                        Lưu Cài Đặt (Primary)                                ] | |
| +-------------------------------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------------------------------+
```

---

## 5. Bảng Màu & Hệ Thống Nhận Diện (Design Tokens)

| Thành Phần             | Mã Màu HEX | Mục Đích Sử Dụng                                      |
| :--------------------- | :--------- | :---------------------------------------------------- |
| **Window Background**  | `#121316`  | Nền chính của ứng dụng (Dark Slate trung tính)        |
| **Sidebar / TopBar**   | `#16171d`  | Thanh điều hướng bên trái và thanh tiêu đề trên       |
| **Panel / Card**       | `#181920`  | Khung chứa nội dung và khối chức năng                 |
| **Input / Table Base** | `#14151a`  | Nền ô nhập liệu, bảng danh sách và khung preview      |
| **Borders**            | `#252730`  | Viền ngăn cách nhẹ nhàng, tinh tế                     |
| **Primary Accent**     | `#2563eb`  | Nút hành động chính (Royal Blue chuyên nghiệp)        |
| **Success Accent**     | `#10b981`  | Trạng thái thành công & số dư credits (Emerald Green) |
| **Danger Accent**      | `#f87171`  | Nút dừng hoặc thông báo lỗi                           |
| **Text Primary**       | `#f9fafb`  | Tiêu đề và văn bản quan trọng                         |
| **Text Secondary**     | `#9ca3af`  | Nhãn form, mô tả và placeholder                       |
| **Text Muted**         | `#6b7280`  | Ghi chú nhỏ, thời gian audio                          |

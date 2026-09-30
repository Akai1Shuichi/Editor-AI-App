# Kế Hoạch Triển Khai: Xuất Video Hàng Loạt Cho Nhiều Dự Án (Batch Project Video Rendering)

## 1. Mục Tiêu & Yêu Cầu
- **Mục tiêu:** Cho phép người dùng chọn cùng lúc nhiều dự án trong danh sách và tự động xuất video cho từng dự án theo hàng đợi tuần tự trong một lần bấm.
- **Nguyên tắc kỹ thuật:**
  - Chạy lần lượt (sequential FIFO queue) trên luồng nền (`QThread`), không kích hoạt nhiều tiến trình FFmpeg song song để tránh quá tải CPU/GPU/RAM.
  - Mỗi dự án độc lập về tài nguyên đầu vào (`images/`, `voice/`, `scenes.json`), cấu hình xuất (Aspect ratio, FPS) và kết quả đầu ra (`output/`).
  - Dự án nào bị lỗi hoặc thiếu tài nguyên thì ghi nhận lỗi và tự động tiếp tục chuyển sang dự án tiếp theo mà không làm crash hàng đợi.
  - Hỗ trợ dừng / hủy tác vụ an toàn giữa chừng (graceful cancellation) và dọn dẹp file tạm FFmpeg.

---

## 2. Các Bước Triển Khai Chi Tiết

### Giai đoạn 1: Lõi Xử Lý Hàng Đợi (Core & Queue Worker)
- [x] **Bước 1.1: Trích xuất và xác thực tài nguyên dự án**
  - Xây dựng module/hàm `validate_project_for_render(project)` và `prepare_project_render_data(project)`:
    - Kiểm tra có đủ file audio (`.mp3`/`.wav`), file phụ đề (`.srt`), kịch bản (`scenes.json`), và thư mục ảnh (`clean/` hoặc `images/`).
    - Parse SRT và scenes JSON, đo thời lượng audio, tính toán timeline chuẩn xác cho dự án.
    - Tạo đường dẫn file output video mặc định theo tên dự án và timestamp.
- [x] **Bước 1.2: Xây dựng `BatchRenderWorker` (kế thừa `QThread`)**
  - Nhận danh sách các `Project` cần xuất.
  - Xử lý hàng đợi lần lượt từng dự án một.
  - Định nghĩa các Qt Signals giao tiếp với UI:
    - `project_started(str slug, int index, int total)`: Bắt đầu dự án.
    - `project_progress(str slug, int pct, str message)`: Tiến độ của dự án đang render.
    - `project_finished(str slug, bool success, dict info)`: Hoàn tất 1 dự án (thành công hoặc lỗi kèm thông báo).
    - `queue_progress(int current_index, int total_count, int overall_pct)`: Tiến độ tổng thể của toàn bộ đợt render.
    - `batch_completed(dict summary)`: Hoàn thành toàn bộ hàng đợi (thống kê tổng số thành công, thất bại, bỏ qua).
- [x] **Bước 1.3: Cơ chế Hủy & Dọn dẹp an toàn (Cancellation & Cleanup)**
  - Hỗ trợ flag `cancel()`: lập tức terminate process FFmpeg đang chạy của dự án hiện tại, dọn dẹp temp files (`temp_concat_*.txt`, `.filter`), đánh dấu các dự án còn lại trong hàng đợi là "Đã hủy" (`Cancelled`).

---

### Giai đoạn 2: Xây Dựng Giao Diện Người Dùng (UI / UX)
- [ ] **Bước 2.1: Nâng cấp `ProjectTab` (Danh sách dự án)**
  - Thêm cột hộp kiểm (Checkbox) để tích chọn nhiều dự án trong bảng.
  - Thêm thanh công cụ chọn nhanh:
    - "Chọn tất cả" / "Bỏ chọn".
    - "Chỉ chọn dự án đủ điều kiện" (đã có đủ ảnh, voice, srt, scene).
    - Bộ đếm số lượng dự án đã chọn (ví dụ: `Đã chọn: 3 dự án`).
  - Thêm nút hành động nổi bật: `🚀 Xuất video hàng loạt (Batch Render)`.
- [ ] **Bước 2.2: Xây dựng Hộp thoại Điều khiển `BatchRenderDialog`**
  - Thiết kế dialog riêng biệt hiển thị danh sách các dự án đã chọn và trạng thái trước khi bấm xuất:
    - Hiển thị badge kiểm tra tài nguyên (Ảnh, Voice, SRT, Scene) của từng dự án.
    - Cảnh báo dự án nào chưa đủ điều kiện để người dùng xem xét hoặc tự động bỏ qua.
    - Cho phép tùy chọn: Giữ nguyên tỷ lệ/FPS của từng dự án hay đồng bộ tỷ lệ/FPS chung.
  - Bảng điều khiển tiến trình thời gian thực khi đang render:
    - Cột hiển thị: Tên dự án | Tỷ lệ | Tiến độ (%) | Trạng thái (Chờ / Đang xuất / Hoàn tất / Thất bại) | Thao tác (Mở video / Xem log lỗi).
    - 2 thanh Progress Bar:
      - Thanh 1: Tiến độ dự án hiện tại (`0% -> 100%`).
      - Thanh 2: Tiến độ toàn bộ hàng đợi (Ví dụ: `Đã hoàn thành 2/5 dự án - 40%`).
    - Nút bấm điều khiển: `Bắt đầu xuất`, `Dừng / Hủy hàng loạt`, `Đóng`.

---

### Giai đoạn 3: Tích Hợp Luồng Hoạt Động & Cập Nhật Dữ Liệu
- [ ] **Bước 3.1: Kết nối `BatchRenderDialog` với `ProjectTab` và `ProjectWorkspace`**
  - Khi người dùng bấm xuất hàng loạt từ `ProjectTab`, hiển thị dialog và kích hoạt `BatchRenderWorker`.
  - Không cho phép thực hiện các thao tác sửa đổi dữ liệu dự án trong khi dự án đó đang được render.
- [ ] **Bước 3.2: Cập nhật Metadata & Thống kê dự án sau khi xuất xong**
  - Tự động cập nhật `updated_at` trong `project.json`.
  - Cập nhật số lượng video đã xuất (`videos_count`) trên bảng `ProjectTab` ngay khi hoàn tất.
  - Bổ sung nút bấm mở trực tiếp video thành phẩm hoặc mở thư mục `output/` tương ứng của từng dự án.

---

### Giai đoạn 4: Viết Kiểm Thử (Unit Tests) & Hoàn Thiện
- [ ] **Bước 4.1: Viết test cho logic chuẩn bị dữ liệu và kiểm tra tính sẵn sàng của dự án**
  - Kiểm thử `validate_project_for_render`: kiểm tra khi đủ file, khi thiếu audio, thiếu srt, thiếu ảnh, thiếu scenes.
  - Kiểm thử tính toán timeline chính xác cho từng dự án.
- [ ] **Bước 4.2: Viết test cho `BatchRenderWorker`**
  - Kiểm thử xử lý hàng đợi tuần tự qua mock render.
  - Kiểm thử cơ chế bỏ qua dự án lỗi và tiếp tục xử lý dự án kế tiếp.
  - Kiểm thử hủy ngang an toàn giữa hàng đợi.
- [ ] **Bước 4.3: Viết test cho giao diện `BatchRenderDialog` & tích hợp trong `ProjectTab`**
  - Kiểm thử tương tác checkbox trên bảng dự án.
  - Kiểm thử kích hoạt dialog và các trạng thái nút bấm.

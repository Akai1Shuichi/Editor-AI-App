# Thiết kế lại layout Project Workspace

## Mục tiêu

Giảm độ rối của màn hình dự án đang mở, làm rõ ba tầng thông tin: ngữ cảnh dự án, điều hướng quy trình và vùng làm việc của bước hiện tại. Giữ nguyên bốn bước Ảnh, Giọng nói, Kịch bản cảnh và Xuất video, đồng thời giữ các công cụ độc lập ở sidebar cấp ứng dụng.

## Định hướng thị giác

Workspace tối, gọn và thiên về nội dung: một thanh ngữ cảnh dự án nhẹ, một thanh bước rõ ràng và vùng làm việc chiếm phần lớn màn hình. Màu xanh dương là màu nhấn duy nhất cho lựa chọn và hành động chính; xanh lá chỉ dùng để biểu thị kết quả thành công.

## Cấu trúc tổng thể

Project Workspace gồm ba tầng từ trên xuống:

1. Header dự án cao tối đa khoảng 64 px.
2. Thanh điều hướng bốn bước cao khoảng 48 px.
3. Nội dung của bước hiện tại chiếm toàn bộ không gian còn lại.

Header dự án có hai cụm:

- Bên trái: nút quay lại, tên dự án và dòng metadata `16:9 · 30 FPS · Đã lưu lúc HH:MM`.
- Bên phải: nút `Lưu` và menu `•••`.

Menu `•••` chứa Tự động lưu, Mở thư mục, Đổi tên và Xóa dự án. Bốn badge tài nguyên màu xanh bị loại bỏ vì trùng thông tin với thanh bước.

Thanh bước hiển thị:

- `1 Ảnh (n)`
- `2 Giọng nói ✓` hoặc trạng thái chưa có
- `3 Kịch bản (n)`
- `4 Xuất video (n)`

Bước hiện tại dùng chữ sáng và vạch xanh dương. Bước hoàn tất dùng dấu kiểm nhỏ, không dùng nền badge lớn.

## Bước Ảnh

Giữ bố cục chia đôi bằng splitter: danh sách bên trái, preview bên phải.

Phần nhập ảnh gồm drop zone có thể click để chọn file; nút `Chọn thư mục` nằm ngay dưới drop zone và căn phải. Bỏ nút `Chọn File Ảnh` vì trùng hành vi click drop zone.

Ngay trên bảng có tiêu đề `Danh sách ảnh`, số lượng ảnh và các thao tác `Xóa đã chọn`, `•••`. Hành động `Xóa hết` chuyển vào menu phụ. Cột `Thời Gian` đổi thành `Kết quả` vì nội dung hiện tại là trạng thái hoặc đường dẫn kết quả.

Preview giữ hai tab `Trước` và `Sau`, ưu tiên diện tích hiển thị ảnh và không thêm panel trang trí.

## Hành vi và trạng thái

- Chuyển bước không thay đổi dữ liệu dự án.
- Nút `Lưu` lưu thủ công và cập nhật dòng `Đã lưu lúc HH:MM`.
- Tự động lưu là tùy chọn trong menu; trạng thái checkbox được giữ nguyên.
- Các số lượng trên thanh bước cập nhật từ cùng nguồn dữ liệu đang dùng cho badge hiện tại.
- `Xóa đã chọn` chỉ bật khi bảng có hàng được chọn.
- Các thao tác thay đổi danh sách bị khóa trong lúc worker đang chạy.
- Không thay đổi logic xử lý ảnh, TTS, scene hoặc render video.

## Phạm vi code

- `app/ui/project_workspace.py`: tinh giản header, chuyển metadata và trạng thái pipeline sang thanh bước, cập nhật menu dự án.
- `app/ui/watermark_tab.py`: tinh giản vùng nhập ảnh, thêm header danh sách và đổi tên cột.
- `app/styles.py`: bổ sung style tối thiểu cho header gọn và trạng thái của thanh bước.
- `tests/test_standalone_tools_ui.py` hoặc test workspace phù hợp: bảo vệ hành vi điều hướng, lưu và thao tác danh sách bị ảnh hưởng.

Không thay đổi sidebar toàn cục, cấu trúc dữ liệu dự án, API xử lý media hoặc các công cụ độc lập.

## Kiểm thử

Kiểm tra bằng test UI hiện có và test hồi quy mới cho:

- Header vẫn quay lại danh sách và lưu dự án đúng.
- Menu tự động lưu vẫn cập nhật các tab phụ.
- Trạng thái và số lượng của bốn bước cập nhật sau khi tài nguyên thay đổi.
- Bước Ảnh vẫn chọn file qua drop zone, chọn thư mục, xóa hàng và chuyển preview.

Theo hướng dẫn repository, Codex không tự chạy test, build, lint hoặc ứng dụng trừ khi người dùng yêu cầu rõ ràng.

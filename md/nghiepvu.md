# Nghiệp vụ AI Media Studio

> Trạng thái: đặc tả nghiệp vụ mục tiêu, chưa triển khai code.

Tài liệu mô tả đối tượng dữ liệu, quy trình và quy tắc xử lý của AI Media Studio. Nguyên tắc cốt lõi: **mọi tài nguyên sản xuất phải thuộc một dự án; người dùng chọn dự án từ danh sách rồi mới đi vào workspace để làm việc**.

## 1. Phạm vi

Ứng dụng hỗ trợ quy trình sản xuất video theo dự án:

1. Tạo và quản lý dự án.
2. Nhập ảnh, gỡ watermark và tạo ảnh sạch.
3. Chuyển văn bản thành giọng nói và phụ đề.
4. Ghép ảnh, audio, phụ đề và dữ liệu phân cảnh thành video.
5. Quản lý tài khoản Voice API và cấu hình mặc định.

Ngoài phạm vi hiện tại:

- Biên tập video nhiều track như phần mềm NLE.
- Đồng bộ dự án qua cloud.
- Nhiều người cùng sửa một dự án.
- Quản lý phiên bản tài nguyên.

## 2. Đối tượng nghiệp vụ

### 2.1. Dự án

Một dự án là không gian lưu trữ độc lập cho một video hoặc một nhóm đầu ra liên quan.

| Thuộc tính | Bắt buộc | Mô tả |
|---|---:|---|
| slug | Có | Định danh duy nhất, đồng thời là tên thư mục |
| name | Có | Tên hiển thị |
| aspect_ratio | Có | 16:9, 9:16 hoặc 1:1 |
| fps | Có | 24, 25, 30 hoặc 60 |
| created_at | Có | Thời điểm tạo |
| updated_at | Có | Thời điểm cập nhật nghiệp vụ gần nhất |
| notes | Không | Ghi chú dự án |

### 2.2. Tài nguyên dự án

- Ảnh gốc.
- Ảnh sạch sau xử lý.
- Văn bản thuyết minh.
- Audio giọng nói.
- Phụ đề SRT.
- Kịch bản phân cảnh.
- Video thành phẩm.

Tài nguyên của dự án A không được tự động xuất hiện hoặc được chọn trong dự án B.

### 2.3. Cấu hình ứng dụng

Bao gồm API key, voice mặc định, model mặc định, ngôn ngữ, tỷ lệ khung hình, FPS và thư mục gốc chứa dự án. Cấu hình ứng dụng chỉ là giá trị mặc định; thay đổi cấu hình không tự ý sửa các dự án đã tồn tại.

## 3. Cấu trúc lưu trữ

~~~text
projects/<project-slug>/
├── project.json
├── scenes.json
├── images/
│   ├── <anh-goc>.png
│   └── clean/
│       └── <anh-goc>_cleaned.png
├── voice/
│   ├── <ten-audio>.mp3
│   └── <ten-audio>.srt
└── output/
    └── <ten-video>.mp4
~~~

Quy tắc:

- Không lưu đầu ra mặc định vào thư mục downloads chung khi đang ở workspace.
- Mọi đường dẫn mặc định phải được suy ra từ currentProject.
- project.json chứa metadata, không chứa bí mật như API key.
- API key được lưu bằng cơ chế cấu hình cấp ứng dụng.
- Xóa dự án là xóa toàn bộ cây thư mục của dự án sau khi xác nhận.

## 4. Luồng tổng thể

~~~text
[Khởi động ứng dụng]
          ↓
[Nạp danh sách dự án]
          ↓
┌──────── Danh sách trống? ────────┐
│ Có                               │ Không
↓                                  ↓
[Tạo dự án]                  [Chọn một dự án]
│                                  │
└───────────────┬──────────────────┘
                ↓
       [Mở workspace dự án]
                ↓
       [Ảnh → Giọng nói → Video]
                ↓
        [Quay lại danh sách]
~~~

Ứng dụng không tự tạo dự án mẫu. Khi chưa có dự án, hiển thị empty state và hành động **Tạo dự án**.

## 5. Quản lý danh sách dự án

### 5.1. Nạp danh sách

Hệ thống quét thư mục gốc dự án, đọc project.json và hiển thị các dự án hợp lệ. Danh sách mặc định sắp xếp theo updated_at giảm dần.

Mỗi dòng hiển thị tối thiểu:

- Tên và đường dẫn tương đối.
- Tỷ lệ khung hình.
- Số ảnh gốc/ảnh sạch.
- Trạng thái voice.
- Số video đã xuất.
- Thời điểm cập nhật.

Nếu một thư mục không có project.json, không tự biến nó thành dự án. Có thể bỏ qua và ghi log; chức năng import dự án cũ là nghiệp vụ riêng nếu cần sau này.

### 5.2. Tìm kiếm và sắp xếp

- Tìm kiếm không phân biệt hoa thường.
- Tìm kiếm theo tên; slug có thể là tiêu chí phụ.
- Xóa nội dung tìm kiếm trả về toàn bộ danh sách.
- Các kiểu sắp xếp tối thiểu: cập nhật gần nhất, tên A–Z và ngày tạo.

### 5.3. Chọn và mở dự án

Phân biệt hai trạng thái:

- **selectedProject**: dòng đang được chọn trong danh sách.
- **currentProject**: dự án đã được mở trong workspace.

Quy tắc:

1. Click một lần chỉ cập nhật selectedProject.
2. Double-click, Enter, dấu › hoặc **Mở dự án** mới mở workspace.
3. Khi mở, hệ thống nạp dự án theo slug và gán currentProject.
4. Workspace phải nhận cùng một currentProject cho cả ba bước.
5. Nếu dự án không còn tồn tại, giữ người dùng ở danh sách, làm mới dữ liệu và báo lỗi.

~~~text
[Click dự án A]
        ↓
[selectedProject = A]
        ↓ double-click / Mở dự án
[Kiểm tra A còn tồn tại]
        ├── Không → Báo lỗi + làm mới danh sách
        └── Có
             ↓
      [currentProject = A]
             ↓
      [Mở Workspace A]
~~~

### 5.4. Tạo dự án

Đầu vào:

- Tên dự án.
- Tỷ lệ khung hình.
- FPS.

Xử lý:

1. Trim tên.
2. Kiểm tra tên không rỗng.
3. Sinh slug không dấu, an toàn cho tên thư mục.
4. Kiểm tra slug duy nhất.
5. Tạo cây thư mục.
6. Ghi project.json; chưa tạo scenes.json cho đến khi người dùng nhập kịch bản dạng text.
7. Đưa dự án vào danh sách.
8. Gán làm currentProject và mở workspace.

Không tự thêm timestamp khi trùng slug. UI yêu cầu người dùng đổi tên để tránh tạo dự án ngoài ý muốn.

### 5.5. Đổi tên dự án

- Cho phép đổi name.
- Nếu nghiệp vụ cho phép đổi slug, phải kiểm tra trùng và đổi đường dẫn an toàn.
- Phương án mặc định: chỉ đổi name, giữ slug và thư mục ổn định.
- Sau khi đổi tên, cập nhật updated_at và tiêu đề workspace.

### 5.6. Xóa dự án

- Chỉ thực hiện từ menu dự án hoặc action bar.
- Dialog phải nêu rõ tên dự án và việc xóa toàn bộ ảnh, voice, phụ đề và video.
- Yêu cầu xác nhận chủ động.
- Nếu xóa thành công, xóa dòng khỏi danh sách.
- Nếu đang xóa currentProject, đóng workspace và quay về danh sách.
- Nếu xóa thất bại, không thay đổi UI như thể đã thành công.

## 6. Vòng đời Workspace

### 6.1. Mở workspace

Khi mở một dự án:

1. Đọc project.json.
2. Kiểm tra/tạo các thư mục con bắt buộc còn thiếu.
3. Nạp thống kê ảnh, voice, SRT, scenes và output.
4. Gán currentProject cho các step.
5. Hiển thị tên, tỷ lệ và FPS ở header.
6. Mở step gần nhất nếu có trạng thái được lưu; nếu không, mở step Ảnh.

Không dùng combo đổi dự án trong workspace. Điều này ngăn người dùng vô tình đổi ngữ cảnh khi đang xử lý hoặc render.

### 6.2. Quay lại danh sách

- Quay lại không xóa currentProject khỏi dữ liệu lưu trữ.
- Danh sách phải refresh để hiển thị thống kê mới.
- Nếu có tác vụ đang chạy, hiển thị xác nhận trước khi rời workspace.
- Nếu tác vụ có thể chạy nền an toàn, UI phải nói rõ nó vẫn tiếp tục; nếu không, người dùng chọn ở lại hoặc dừng.

### 6.3. Cập nhật updated_at

Cập nhật khi có thay đổi nghiệp vụ:

- Tạo/đổi tên dự án.
- Thêm hoặc xóa tài nguyên.
- Gỡ watermark thành công.
- Tạo audio/SRT thành công.
- Sửa scenes.json.
- Xuất video thành công.

Không cập nhật chỉ vì người dùng mở hoặc chọn một dự án.

## 7. Nghiệp vụ Ảnh và gỡ watermark

### 7.1. Mục tiêu

Nhập một hoặc nhiều ảnh vào dự án, loại bỏ watermark Gemini/Imagen và lưu ảnh sạch mà không ghi đè ảnh gốc.

### 7.2. Đầu vào

- Định dạng: PNG, JPG, JPEG, WEBP.
- Nhập bằng chọn file, chọn thư mục hoặc kéo thả.
- Không thêm trùng cùng một đường dẫn trong một batch.
- Bỏ qua file có hậu tố _cleaned khi quét ảnh đầu vào.

Nếu file được chọn nằm ngoài dự án, hệ thống cần có một chính sách thống nhất:

- Khuyến nghị: copy ảnh vào project/images rồi mới xử lý.
- Không xử lý dựa trên đường dẫn ngoài dự án mà không thông báo.

### 7.3. Xử lý

~~~text
[Chọn ảnh]
    ↓
[Kiểm tra định dạng và trùng lặp]
    ↓
[Đưa vào hàng chờ]
    ↓
[Nhận diện kích thước/vị trí watermark]
    ↓
[Inverse alpha blending theo preset/gain]
    ↓
[Ghi project/images/clean/<stem>_cleaned.png]
    ↓
[Cập nhật trạng thái + preview + thống kê dự án]
~~~

### 7.4. Quy tắc

- Không ghi đè ảnh gốc.
- Gain mặc định 0.60; preset mặc định Auto.
- Xử lý batch chạy ngoài UI thread.
- Mỗi file có trạng thái: Chờ, Đang xử lý, Hoàn tất, Lỗi hoặc Đã dừng.
- Lỗi một file không làm dừng toàn bộ batch.
- Dừng batch không xóa các file đã hoàn thành.
- Nếu file đầu ra đã tồn tại, yêu cầu chính sách rõ: ghi đè, bỏ qua hoặc tạo bản mới. Mặc định khuyến nghị hỏi một lần cho cả batch.
- Preview ảnh sạch chỉ hiển thị sau khi file được ghi thành công.

### 7.5. Hoàn tất bước

Step Ảnh được xem là có dữ liệu khi dự án có ít nhất một ảnh gốc hoặc ảnh sạch. Để xuất video, hệ thống ưu tiên ảnh trong images/clean; nếu không có ảnh sạch, có thể dùng ảnh gốc nhưng phải thông báo rõ.

## 8. Nghiệp vụ tạo giọng nói

### 8.1. Mục tiêu

Chuyển văn bản thành audio và tùy chọn phụ đề SRT qua Voice API, sau đó lưu kết quả vào project/voice.

### 8.2. Điều kiện

- Có API key hợp lệ.
- Có nội dung không rỗng.
- Có voice và model hợp lệ.
- Tham số nằm trong miền cho phép.

### 8.3. Chia đoạn

- Mỗi đoạn tối đa 3.500 ký tự hoặc theo giới hạn thực tế của API.
- Ưu tiên tách tại xuống dòng, dấu chấm, dấu hỏi hoặc dấu chấm than.
- Không làm mất ký tự.
- Giữ đúng thứ tự đoạn.
- UI hiển thị số đoạn dự kiến trước khi gửi.

### 8.4. Luồng tạo

~~~text
[Nhập nội dung + chọn voice]
             ↓
[Validate và chia đoạn]
             ↓
[Gửi lần lượt các task API]
             ↓
[Theo dõi trạng thái từng đoạn]
             ↓
[Tải audio/SRT]
             ↓
[Ghép các đoạn đúng thứ tự nếu cần]
             ↓
[Lưu vào project/voice]
             ↓
[Kích hoạt player + Dùng để xuất video]
~~~

### 8.5. Quy tắc kết quả

- Audio đầu ra mặc định là MP3.
- Nếu bật SRT, tên SRT đồng bộ với tên audio.
- Không ghi đè file cũ ngoài ý muốn; nếu trùng, tạo tên có số thứ tự hoặc yêu cầu xác nhận.
- Chỉ đánh dấu thành công sau khi file đã tải và ghi đầy đủ.
- File mới nhất không tự động thay thế lựa chọn render nếu người dùng đã chọn một file khác; UI cần hỏi hoặc thể hiện lựa chọn hiện tại.
- **Dùng để xuất video** gán audio/SRT cho step Xuất video rồi điều hướng sang step đó.

### 8.6. Hủy và lỗi

- Có thể hủy khi đang gửi, polling hoặc tải file.
- File tạm/chưa hoàn chỉnh không được hiển thị như kết quả hợp lệ.
- Lỗi mạng cho phép thử lại.
- HTTP 401/403 dẫn người dùng tới Cài đặt API.
- Thiếu credits phải hiển thị số dư nếu API trả về.
- Nếu một chunk lỗi, nêu rõ chunk lỗi; không âm thầm tạo audio thiếu nội dung.

## 9. Nghiệp vụ Thư viện voice

### 9.1. Mục tiêu

Cho phép tìm, nghe thử và chọn voice mà không rời khỏi bước Giọng nói.

### 9.2. Nguồn dữ liệu

- Default voices.
- Shared/community voices.
- Có thể mở rộng thêm provider nhưng phải chuẩn hóa dữ liệu hiển thị.

### 9.3. Tìm và lọc

- Tìm theo tên, ngôn ngữ, accent hoặc từ khóa do API hỗ trợ.
- Lọc theo nguồn và giới tính.
- Reset filter đưa danh sách về mặc định.
- Chỉ auto-load lần đầu khi có API key.
- Có loading, empty, error và retry state.

### 9.4. Chọn voice

1. Người dùng bấm **Chọn voice**.
2. Hệ thống lưu voice_id, tên và metadata cần hiển thị vào trạng thái của step.
3. Quay về tab Tạo giọng.
4. Hiển thị voice đã chọn.

Copy Voice ID là hành động phụ. Đặt làm voice mặc định là cấu hình toàn ứng dụng và cần thể hiện rõ phạm vi này.

## 10. Nghiệp vụ Xuất video

### 10.1. Mục tiêu

Ghép ảnh, audio, phụ đề và kịch bản phân cảnh của currentProject thành video MP4.

### 10.2. Đầu vào

| Đầu vào | Mức độ | Quy tắc |
|---|---|---|
| Ảnh | Bắt buộc | Ưu tiên images/clean, fallback images |
| Audio | Bắt buộc | MP3, WAV hoặc định dạng được engine hỗ trợ |
| SRT | Theo chế độ | Bắt buộc nếu render phụ đề |
| scenes.json | Theo chế độ | Bắt buộc khi chia thời lượng theo phân cảnh |
| Tỷ lệ/FPS | Bắt buộc | Mặc định lấy từ project.json |
| File output | Bắt buộc | Nằm trong project/output |

### 10.3. Kiểm tra trước render

- Các file phải tồn tại và đọc được.
- Có ít nhất một ảnh.
- Audio có thời lượng lớn hơn 0.
- SRT hợp lệ nếu được sử dụng.
- scenes.json parse được và có schema hợp lệ nếu được sử dụng.
- Output không trùng file đang được khóa.
- FFmpeg/engine render sẵn sàng.

Nếu thiếu điều kiện, không bắt đầu render; UI chỉ rõ mục thiếu và cung cấp hành động đến step liên quan.

### 10.4. Render

~~~text
[Auto-detect tài nguyên dự án]
               ↓
[Người dùng xác nhận input + output]
               ↓
[Validate]
       ├── Lỗi → Hiển thị lỗi tại input
       └── Hợp lệ
               ↓
[Tính timeline và chuẩn hóa khung hình]
               ↓
[Render H.264/AAC]
               ↓
[Ghi file tạm]
               ↓
[Thành công: đổi tên sang file output chính thức]
               ↓
[Cập nhật danh sách video và updated_at]
~~~

### 10.5. Quy tắc

- Không ghi trực tiếp kết quả chưa hoàn chỉnh vào tên file đích.
- Tiến độ có phần trăm và mô tả công đoạn.
- Render chạy ngoài UI thread.
- Dừng render dọn file tạm nhưng không xóa video hoàn chỉnh cũ.
- Video mặc định dùng H.264 cho hình và AAC cho tiếng.
- Ảnh được fit theo tỷ lệ dự án; chính sách crop/letterbox phải được chọn rõ.
- Khi thành công, hiển thị đường dẫn và cho phép Phát, Mở thư mục hoặc Xuất lại.

## 11. Cài đặt và Voice API

### 11.1. API key

- Mặc định che nội dung.
- Có nút hiện/ẩn.
- Không ghi API key vào project.json hoặc log.
- Lưu key không đồng nghĩa kết nối thành công.
- **Kiểm tra kết nối** gọi API tài khoản và cập nhật trạng thái.

### 11.2. Trạng thái kết nối

~~~text
[Nhập/lưu API key]
        ↓
[Kiểm tra kết nối]
        ├── Thành công → Đã kết nối + tài khoản + credits
        ├── 401/403    → API key không hợp lệ
        ├── Hết credits→ Đã kết nối nhưng không đủ số dư
        └── Mạng/lỗi   → Không thể kiểm tra, cho phép thử lại
~~~

Không hiển thị “Đã kết nối” chỉ dựa trên việc chuỗi API key tồn tại.

### 11.3. Giá trị mặc định

- Voice, model và ngôn ngữ mặc định áp dụng cho lần mở/tạo nội dung mới.
- Tỷ lệ và FPS mặc định chỉ áp dụng khi tạo dự án mới.
- Đổi mặc định không sửa project.json của dự án cũ.
- Thư mục gốc dự án phải tồn tại hoặc có thể tạo được.

## 12. Trạng thái và thông báo

### 12.1. Trạng thái tác vụ

Mỗi tác vụ dài có vòng đời:

~~~text
Idle → Validating → Queued/Running → Completed
                             ├────→ Failed
                             └────→ Cancelling → Cancelled
~~~

- Không cho chạy trùng cùng một tác vụ trên cùng tài nguyên.
- Trong khi chạy, khóa control có thể làm thay đổi input.
- Nút Dừng chỉ bật khi tác vụ thực sự có thể dừng.
- Sau lỗi, giữ input để người dùng sửa và thử lại.

### 12.2. Thông báo

- Validation hiển thị cạnh trường dữ liệu.
- Thành công thường dùng status/toast ngắn.
- Modal chỉ dùng khi cần xác nhận hoặc hậu quả lớn.
- Thông báo lỗi gồm: việc gì lỗi, nguyên nhân nếu biết và cách tiếp theo.
- Không hiển thị exception kỹ thuật thô cho người dùng; chi tiết có thể ghi log.

## 13. Quy tắc an toàn dữ liệu

- Không ghi đè file gốc.
- Dùng file tạm cho thao tác ghi lớn.
- Xác nhận trước khi xóa dự án hoặc ghi đè hàng loạt.
- Không xóa kết quả hoàn chỉnh khi người dùng dừng một tác vụ mới.
- Mọi worker phải gắn với slug dự án lúc bắt đầu; không dựa vào currentProject có thể đổi sau đó.
- Khi kết quả trả về, xác minh worker vẫn thuộc đúng dự án trước khi cập nhật UI.

## 14. Tiêu chí nghiệm thu nghiệp vụ

### 14.1. Dự án

- App mở vào danh sách dự án.
- Khi chưa có dự án, không tự tạo dữ liệu mẫu.
- Tạo dự án sinh đủ cấu trúc thư mục rồi mở workspace.
- Click một lần chọn dòng; double-click/Enter/Mở dự án mới điều hướng.
- Mở dự án A thì cả ba step chỉ dùng dữ liệu của A.
- Quay lại danh sách thấy thống kê được cập nhật.
- Không đổi dự án bằng combo bên trong workspace.

### 14.2. Ảnh

- Import được nhiều ảnh hợp lệ và loại file không hỗ trợ.
- Ảnh sạch lưu đúng project/images/clean.
- Lỗi một file không làm hỏng toàn batch.
- Không ghi đè ảnh gốc.

### 14.3. Giọng nói

- Text dài được chia đúng thứ tự và không mất nội dung.
- Kết quả lưu đúng project/voice.
- Chọn voice cập nhật đúng form.
- Lỗi API có trạng thái rõ và có thể thử lại.

### 14.4. Video

- Tự nạp đúng tài nguyên của currentProject.
- Không render khi thiếu input bắt buộc.
- Kết quả hoàn chỉnh nằm trong project/output.
- Dừng render không để file đích giả thành công.

### 14.5. Cài đặt

- API key được che và không xuất hiện trong log/project.
- Trạng thái kết nối dựa trên kết quả kiểm tra API.
- Giá trị mặc định mới không làm thay đổi dự án cũ.

# Kế hoạch nâng cấp Bước 4: Workspace chỉnh sửa video

## Mục tiêu bản đầu

Cho phép người dùng lấy ảnh cảnh, voice, phụ đề SRT và kịch bản từ Bước 1–3 để tạo một bản dựng; xem trước, chỉnh sửa trên timeline, lưu lại và xuất MP4 đúng với bản dựng đã chỉnh.

## Các bước chính

1. **Thiết kế dữ liệu bản dựng:** Tạo file riêng trong từng dự án (ví dụ `edit.json`) để lưu clip, track, thời điểm, thứ tự, phụ đề và cấu hình xuất. Timeline tự tạo từ kịch bản chỉ là bản khởi đầu; phân tích lại đầu vào không được ghi đè chỉnh sửa đã lưu.

   **Model gợi ý: GPT-6 Astra — Medium.** Cần thiết kế cấu trúc dữ liệu dùng chung cho các bước sau, bảo vệ chỉnh sửa đã lưu và tính đến tương thích dự án cũ.

   **Trạng thái: Đã hoàn thành bước 1.** `edit.json` phiên bản 1 lưu track ảnh, một track voice, nội dung/mốc thời gian phụ đề, chuyển động cảnh, tỉ lệ và FPS. Thời gian tính bằng giây; thứ tự clip theo danh sách. Đường dẫn trong dự án được lưu tương đối để có thể di chuyển thư mục dự án.

   Bước 4 tự mở bản dựng đã lưu; thay nguồn hoặc phân tích lại không ghi đè bản dựng. Nút **Tạo lại timeline từ nguồn** yêu cầu xác nhận và giữ bản trước trong `edit.json.bak`. Cấu hình bản dựng dùng nút **Lưu** và công tắc **Tự động lưu** của dự án. File sai cấu trúc hoặc phiên bản chưa hỗ trợ được giữ nguyên và báo lỗi.

   Đã chạy 11 kiểm tra tự động cho lưu/mở lại, di chuyển thư mục, chống ghi đè, sao lưu, lỗi ghi file, nguồn thay đổi, cấu hình và bàn giao kịch bản hiện có. Preview, thao tác kéo clip và xuất chữ phụ đề thuộc các bước tiếp theo.

2. **Dựng giao diện workspace:** Bố trí thư viện asset, màn hình preview, bảng thuộc tính clip và timeline trong tab Bước 4. Giữ thao tác tạo timeline tự động và xuất video hiện có trong luồng mới.

   **Model gợi ý: GPT-6 Sol — Medium.** Phù hợp triển khai nhiều widget PyQt6 và nối tương tác theo cấu trúc đã chốt. Có thể dùng GPT-6 Luna — Medium cho sửa nhãn, màu sắc và khoảng cách sau đó.

   **Trạng thái: Đã hoàn thành bước 2.** Tab Bước 4 có thư viện ảnh/voice/SRT/kịch bản, preview ảnh cảnh, bảng thuộc tính, dải clip theo thời lượng và bảng timeline chi tiết. Chọn cảnh ở dải clip hoặc bảng để xem ảnh, thời gian và phụ đề của bản dựng đã lưu. Thanh thao tác phân tích, tạo lại từ nguồn và xuất MP4 luôn hiện phía trên workspace. Preview hiện là ảnh tĩnh theo cảnh được chọn; phát voice, tua playhead và đồng bộ phụ đề thuộc bước 3.

3. **Làm preview đồng bộ:** Kéo playhead hoặc phát voice phải hiển thị đúng ảnh và phụ đề tại thời điểm tương ứng. Thêm ảnh thu nhỏ và thước thời gian để dễ điều hướng.

   **Model gợi ý: GPT-6 Sol — Medium.** Cần xử lý phát/dừng, tua và đồng bộ thời gian. Tăng lên High nếu gặp lệch tiếng/hình, giật preview hoặc lỗi luồng khó xác định.

   **Trạng thái: Đã hoàn thành bước 3.** Preview có nút phát/tạm dừng voice, thanh tua và thước thời gian có thể bấm/kéo. Vị trí phát của voice điều khiển ảnh cảnh và phụ đề theo mốc thời gian của bản dựng; chọn clip sẽ tua tới đầu cảnh. Dải clip hiển thị ảnh thu nhỏ và tự cuộn theo playhead. Khi thiếu voice, vẫn có thể tua để xem ảnh/phụ đề; chuyển dự án hoặc đóng tab sẽ dừng phát.

   Đã kiểm tra bằng 12 test của bản dựng, gồm tua, đổi cảnh/phụ đề, thao tác trên thước thời gian và trường hợp thiếu voice. Qt Multimedia phát thử file WAV hợp lệ và vị trí phát tăng theo thời gian. Bộ test toàn dự án hiện còn lỗi ở các phần không thuộc Bước 3; xem ghi chú khi bàn giao.

4. **Quan sát và sửa sai tối thiểu:** Làm rõ ảnh đang dùng, phụ đề và trạng thái file của từng cảnh để dễ phát hiện lỗi. Chỉ cho thay ảnh cảnh sai/thiếu; lưu rồi mở lại được thay đổi này. Giữ nguyên thứ tự cảnh, mọi mốc thời gian, voice và phụ đề.

   **Model gợi ý: GPT-6 Sol — Medium.** Tập trung vào khả năng quan sát, thay đúng asset và lưu sửa lỗi mà không làm đổi đồng bộ hình/tiếng.

   Việc đổi thứ tự hoặc thời điểm cảnh và sửa phụ đề nằm ngoài phạm vi mục này vì voice và phụ đề đã gắn với nội dung, mốc của kịch bản.

   **Trạng thái: Đã hoàn thành bước 4.** Bảng thuộc tính hiển thị tên, trạng thái đọc được/kích thước và đường dẫn ảnh của cảnh; bảng timeline đánh dấu ảnh thiếu hoặc không đọc được. Nút **Thay ảnh cảnh này** nhận ảnh hợp lệ và chỉ cập nhật đường dẫn ảnh của cảnh đang chọn trong `edit.json`. Dùng nút **Lưu** hoặc **Tự động lưu** của dự án; mở lại vẫn giữ ảnh đã thay. Voice, phụ đề, thứ tự và thời gian không đổi.

   Đã chạy 16 kiểm tra cho bản dựng, gồm thay ảnh, lưu/mở lại, tự động lưu, ảnh lỗi và lỗi ghi file; thêm 2 kiểm tra bàn giao kịch bản đều đạt.

5. **Nâng bộ xuất video:** Cho FFmpeg đọc dữ liệu bản dựng đã lưu, đưa phụ đề lên video và bảo đảm video xuất khớp preview. Giữ khả năng mở/xuất dự án cũ.

   **Model gợi ý: GPT-6 Astra — Medium.** Đây là phần dễ phát sinh sai thời lượng, lệch khung hình, lỗi filter FFmpeg hoặc khác biệt giữa preview và video xuất; tăng lên High nếu các lỗi này khó xác định hoặc chưa giải quyết được sau kiểm tra.

   **Trạng thái: Đã hoàn thành bước 5.** Khi xuất, Bước 4 lưu các thay đổi đang chờ rồi đọc lại `edit.json`; FFmpeg dùng thời lượng, FPS, tỉ lệ, voice, ảnh và phụ đề của bản dựng đó. Các cảnh chồng lấn theo thứ tự ưu tiên của preview; khoảng trống hoặc ảnh thiếu/không đọc được hiện bằng khung đen. Ảnh đầu vào được chuẩn hóa kích thước trước khi ghép để tránh mất khung hình khi các nguồn khác kích thước. Phụ đề được đốt vào MP4 theo mốc và nội dung của track phụ đề, kể cả khi nhiều đoạn cùng hiện. Luồng xuất cũ vẫn hoạt động khi không có bản dựng đã lưu.

   Đã chạy 34 kiểm tra liên quan đến bản dựng, chuyển động cảnh và bàn giao kịch bản; thêm kiểm tra FFmpeg thật cho thứ tự cảnh, khoảng trống, phụ đề, số khung hình và xuất theo luồng cũ. Kiểm tra luồng hoàn chỉnh với dự án thực vẫn thuộc bước 6.

   Bổ sung công tắc **Bật phụ đề trên video** trong cấu hình xuất, mặc định tắt cho dự án mới và bản dựng cũ chưa có cài đặt. Lựa chọn được lưu trong `edit.json`, áp dụng cho preview và MP4, không xóa nội dung/mốc phụ đề. Đã kiểm tra bật/tắt, lưu/mở lại, tự động lưu và xuất FFmpeg thật ở cả hai trạng thái.

6. **Kiểm tra luồng hoàn chỉnh:** Tạo timeline từ Bước 1–3 → chỉnh sửa → lưu → đóng/mở dự án → xem lại → xuất MP4; kiểm tra cả trường hợp thiếu hoặc đổi đường dẫn asset.

   **Model gợi ý: GPT-6 Sol — Medium.** Phù hợp kiểm tra xuyên suốt và xử lý lỗi liên quan nhiều phần. Dùng GPT-6 Luna — Medium cho từng kiểm tra nhỏ có tiêu chí rõ; tăng lên High nếu còn lỗi mất dữ liệu hoặc sai kết quả xuất khó tái hiện.

## Ghi chú chọn model

Đây là gợi ý theo độ khó của dự án, chưa phải kết quả so sánh model trên code này. Ưu tiên Astra ở bước 1 và 5, Sol ở bước 2–4 và kiểm tra tích hợp; Luna cho thay đổi nhỏ, phạm vi rõ. Mức Medium là điểm bắt đầu; tăng lên High khi kiểm tra phát hiện lỗi khó hoặc cần phân tích sâu hơn.

Tên model trên dùng các lựa chọn được công cụ của phiên làm việc báo hỗ trợ. Tham khảo nguyên tắc chọn theo chất lượng, tốc độ và chi phí trong [OpenAI Docs](https://developers.openai.com/api/docs/guides/model-selection); model thực tế có thể khác theo tài khoản và phiên bản ứng dụng.

## Phạm vi sau bản đầu

Thêm clip video, nhiều track âm thanh, chuyển cảnh, text tự do, hiệu ứng và keyframe theo từng đợt. Các tính năng này cần mở rộng mô hình bản dựng và bộ render.

## Vai trò của Concat

Tham khảo cách tổ chức timeline, preview, lệnh chỉnh sửa và undo của [Concat](https://github.com/jub0t/Concat). Bản đầu tiếp tục dùng PyQt6 và FFmpeg của dự án; chỉ thử tích hợp API/CLI của Concat nếu sau này cần một engine riêng và đã đánh giá việc tích hợp, đóng gói và giấy phép.

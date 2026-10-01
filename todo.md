# Kế hoạch nâng cấp Bước 4: Workspace chỉnh sửa video

## Mục tiêu bản đầu

Cho phép người dùng lấy ảnh cảnh, voice, phụ đề SRT và kịch bản từ Bước 1–3 để tạo một bản dựng; xem trước, chỉnh sửa trên timeline, lưu lại và xuất MP4 đúng với bản dựng đã chỉnh.

## Các bước chính

1. **Thiết kế dữ liệu bản dựng:** Tạo file riêng trong từng dự án (ví dụ `edit.json`) để lưu clip, track, thời điểm, thứ tự, phụ đề và cấu hình xuất. Timeline tự tạo từ kịch bản chỉ là bản khởi đầu; phân tích lại đầu vào không được ghi đè chỉnh sửa đã lưu.

   **Model gợi ý: GPT-6 Astra — High.** Cần thiết kế cấu trúc dữ liệu dùng chung cho các bước sau, bảo vệ chỉnh sửa đã lưu và tính đến tương thích dự án cũ.

   **Trạng thái: Đã hoàn thành bước 1.** `edit.json` phiên bản 1 lưu track ảnh, một track voice, nội dung/mốc thời gian phụ đề, chuyển động cảnh, tỉ lệ và FPS. Thời gian tính bằng giây; thứ tự clip theo danh sách. Đường dẫn trong dự án được lưu tương đối để có thể di chuyển thư mục dự án.

   Bước 4 tự mở bản dựng đã lưu; thay nguồn hoặc phân tích lại không ghi đè bản dựng. Nút **Tạo lại timeline từ nguồn** yêu cầu xác nhận và giữ bản trước trong `edit.json.bak`. Cấu hình bản dựng dùng nút **Lưu** và công tắc **Tự động lưu** của dự án. File sai cấu trúc hoặc phiên bản chưa hỗ trợ được giữ nguyên và báo lỗi.

   Đã chạy 11 kiểm tra tự động cho lưu/mở lại, di chuyển thư mục, chống ghi đè, sao lưu, lỗi ghi file, nguồn thay đổi, cấu hình và bàn giao kịch bản hiện có. Preview, thao tác kéo clip và xuất chữ phụ đề thuộc các bước tiếp theo.

2. **Dựng giao diện workspace:** Bố trí thư viện asset, màn hình preview, bảng thuộc tính clip và timeline trong tab Bước 4. Giữ thao tác tạo timeline tự động và xuất video hiện có trong luồng mới.

   **Model gợi ý: GPT-6 Sol — High.** Phù hợp triển khai nhiều widget PyQt6 và nối tương tác theo cấu trúc đã chốt. Có thể dùng GPT-6 Luna — Medium cho sửa nhãn, màu sắc và khoảng cách sau đó.

   **Trạng thái: Đã hoàn thành bước 2.** Tab Bước 4 có thư viện ảnh/voice/SRT/kịch bản, preview ảnh cảnh, bảng thuộc tính, dải clip theo thời lượng và bảng timeline chi tiết. Chọn cảnh ở dải clip hoặc bảng để xem ảnh, thời gian và phụ đề của bản dựng đã lưu. Thanh thao tác phân tích, tạo lại từ nguồn và xuất MP4 luôn hiện phía trên workspace. Preview hiện là ảnh tĩnh theo cảnh được chọn; phát voice, tua playhead và đồng bộ phụ đề thuộc bước 3.

3. **Làm preview đồng bộ:** Kéo playhead hoặc phát voice phải hiển thị đúng ảnh và phụ đề tại thời điểm tương ứng. Thêm ảnh thu nhỏ và thước thời gian để dễ điều hướng.

   **Model gợi ý: GPT-6 Sol — High.** Cần xử lý phát/dừng, tua và đồng bộ thời gian. Chuyển sang GPT-6 Astra — High nếu gặp lệch tiếng/hình, giật preview hoặc lỗi luồng khó xác định.

4. **Thêm chỉnh sửa cơ bản:** Đổi thứ tự và thay ảnh cảnh, kéo dài/ngắn thời lượng, sửa phụ đề; hỗ trợ undo/redo, lưu và mở lại bản dựng.

   **Model gợi ý: GPT-6 Sol — High.** Nên chia thành từng nhóm thao tác để kiểm soát trạng thái. Dùng GPT-6 Astra — High khi cần rà soát tương tác giữa kéo clip, undo/redo và lưu dữ liệu.

5. **Nâng bộ xuất video:** Cho FFmpeg đọc dữ liệu bản dựng đã lưu, đưa phụ đề lên video và bảo đảm video xuất khớp preview. Giữ khả năng mở/xuất dự án cũ.

   **Model gợi ý: GPT-6 Astra — High.** Đây là phần dễ phát sinh sai thời lượng, lệch khung hình, lỗi filter FFmpeg hoặc khác biệt giữa preview và video xuất.

6. **Kiểm tra luồng hoàn chỉnh:** Tạo timeline từ Bước 1–3 → chỉnh sửa → lưu → đóng/mở dự án → xem lại → xuất MP4; kiểm tra cả trường hợp thiếu hoặc đổi đường dẫn asset.

   **Model gợi ý: GPT-6 Sol — High.** Phù hợp kiểm tra xuyên suốt và xử lý lỗi liên quan nhiều phần. Dùng GPT-6 Luna — Medium cho từng kiểm tra nhỏ có tiêu chí rõ; dùng GPT-6 Astra — High nếu còn lỗi mất dữ liệu hoặc sai kết quả xuất khó tái hiện.

## Ghi chú chọn model

Đây là gợi ý theo độ khó của dự án, chưa phải kết quả so sánh model trên code này. Ưu tiên Astra ở bước 1 và 5, Sol ở bước 2–4 và kiểm tra tích hợp; Luna cho thay đổi nhỏ, phạm vi rõ. Mức High là điểm bắt đầu cho phần triển khai chính; chỉ tăng lên Extra high khi gặp bài toán khó hoặc lỗi chưa giải quyết được.

Tên model trên dùng các lựa chọn được công cụ của phiên làm việc báo hỗ trợ. Tham khảo nguyên tắc chọn theo chất lượng, tốc độ và chi phí trong [OpenAI Docs](https://developers.openai.com/api/docs/guides/model-selection); model thực tế có thể khác theo tài khoản và phiên bản ứng dụng.

## Phạm vi sau bản đầu

Thêm clip video, nhiều track âm thanh, chuyển cảnh, text tự do, hiệu ứng và keyframe theo từng đợt. Các tính năng này cần mở rộng mô hình bản dựng và bộ render.

## Vai trò của Concat

Tham khảo cách tổ chức timeline, preview, lệnh chỉnh sửa và undo của [Concat](https://github.com/jub0t/Concat). Bản đầu tiếp tục dùng PyQt6 và FFmpeg của dự án; chỉ thử tích hợp API/CLI của Concat nếu sau này cần một engine riêng và đã đánh giá việc tích hợp, đóng gói và giấy phép.

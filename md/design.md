# Thiết kế giao diện AI Media Studio

> Trạng thái: đặc tả thiết kế, chưa triển khai code.

Tài liệu mô tả cấu trúc màn hình, phân cấp thông tin và hành vi điều hướng của ứng dụng desktop AI Media Studio. Giao diện theo phong cách dark workspace: gọn, rõ, ưu tiên vùng làm việc và hạn chế các khối card trang trí.

## 1. Mục tiêu thiết kế

- Người dùng mở ứng dụng là thấy danh sách dự án.
- Click một dự án để đi vào workspace riêng của dự án đó.
- Trong workspace luôn nhìn thấy tên dự án đang làm.
- Ba công đoạn Ảnh, Giọng nói và Xuất video nằm trong cùng một workspace.
- Cài đặt API là cấu hình cấp ứng dụng, không lẫn với nội dung dự án.

## 2. Mô hình điều hướng

Ứng dụng có hai cấp:

1. **Cấp ứng dụng**: Dự án và Cài đặt.
2. **Cấp dự án**: Workspace của dự án đang mở.

~~~text
Mở ứng dụng
    ↓
Danh sách dự án
    ↓ click một dòng / Mở dự án
Workspace của dự án đã chọn
    ↓
1. Ảnh → 2. Giọng nói → 3. Xuất video
~~~

Không đưa Gỡ watermark, TTS hoặc Ghép video thành các mục độc lập ở sidebar. Đây là các bước làm việc bên trong một dự án.

## 3. Kiến trúc màn hình

~~~text
AI Media Studio
├── Dự án
│   ├── Danh sách dự án (mặc định)
│   ├── Tạo dự án mới
│   └── Workspace dự án
│       ├── 1. Ảnh
│       ├── 2. Giọng nói
│       └── 3. Xuất video
└── Cài đặt
    ├── Tài khoản Voice API
    └── Giá trị mặc định
~~~

Quy ước điều hướng:

- ProjectListPage và ProjectWorkspacePage là hai page riêng trong cùng một stack.
- Mỗi thời điểm workspace chỉ nhận một currentProject.
- Quay lại danh sách không đóng hoặc xóa dự án.
- Sidebar chỉ điều hướng cấp ứng dụng; thanh bước chỉ tồn tại trong workspace.
- Muốn đổi dự án, người dùng quay về danh sách rồi mở dự án khác.

## 4. Khung ứng dụng

~~~text
┌──────────────────────┬──────────────────────────────────────────────────────────────────────────────┐
│ AI MEDIA STUDIO      │                                                                              │
│ Production workspace │                                                                              │
│                      │                                                                              │
│ ● Dự án              │                              PAGE CONTENT                                    │
│   Cài đặt            │                                                                              │
│                      │                                                                              │
│                      │                                                                              │
│                      │                                                                              │
│                      │                                                                              │
│ Voice API            │                                                                              │
│ ● Đã kết nối         │                                                                              │
│ 125.400 credits      │                                                                              │
└──────────────────────┴──────────────────────────────────────────────────────────────────────────────┘
~~~

- Sidebar rộng khoảng 220 px, cố định.
- Tên sản phẩm ở đầu; trạng thái API và số dư ở cuối.
- Chỉ có hai mục chính: **Dự án** và **Cài đặt**.
- Trạng thái active dùng một nền nhẹ và vạch accent, không dùng nhiều màu.

## 5. Màn hình Danh sách dự án

Đây là màn hình mặc định khi mở ứng dụng và khi bấm **Dự án** trên sidebar.

### 5.1. Bố cục

~~~text
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Dự án                                                         [Tìm dự án...]   [+ Dự án mới]      │
│ Quản lý và tiếp tục các nội dung đang sản xuất.                                                     │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Tất cả dự án  12          Sắp xếp: [Cập nhật gần nhất ▾]                         [Làm mới]          │
├────┬────────────────────────────┬──────────┬────────┬─────────────┬──────────────┬───────────────────┤
│    │ TÊN DỰ ÁN                 │ TỶ LỆ    │ ẢNH    │ GIỌNG NÓI  │ VIDEO        │ CẬP NHẬT          │
├────┼────────────────────────────┼──────────┼────────┼─────────────┼──────────────┼───────────────────┤
│ ●  │ Review công nghệ 09/2026  │ 16:9     │ 24/24  │ Sẵn sàng   │ 2 bản        │ 12 phút trước   ›  │
│    │ projects/review-cong-nghe │          │        │             │              │                   │
├────┼────────────────────────────┼──────────┼────────┼─────────────┼──────────────┼───────────────────┤
│    │ TikTok AI News            │ 9:16     │ 10/18  │ Chưa có     │ Chưa xuất    │ Hôm qua         ›  │
│    │ projects/tiktok-ai-news   │          │        │             │              │                   │
├────┼────────────────────────────┼──────────┼────────┼─────────────┼──────────────┼───────────────────┤
│    │ Video giới thiệu sản phẩm │ 1:1      │ 8/8    │ Sẵn sàng   │ 1 bản        │ 08/09/2026      ›  │
└────┴────────────────────────────┴──────────┴────────┴─────────────┴──────────────┴───────────────────┘
│ Đã chọn: Review công nghệ 09/2026       [Mở thư mục] [Xóa…]              [Mở dự án →]          │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
~~~

### 5.2. Hành vi danh sách

- Click một lần vào dòng: chọn dòng và hiện action bar cuối màn hình.
- Double-click dòng, click dấu › hoặc bấm **Mở dự án**: mở workspace của đúng dự án đó.
- Toàn bộ dòng có trạng thái hover để thể hiện có thể click.
- Enter mở dự án đang chọn; phím mũi tên đổi dòng chọn.
- Không đặt nhiều nút nhỏ trong từng dòng. Hành động phụ nằm ở action bar hoặc menu ngữ cảnh.
- Danh sách mặc định sắp xếp theo thời gian cập nhật mới nhất.
- Ô tìm kiếm lọc theo tên dự án ngay khi nhập.
- Một click không tự đổi dữ liệu ở nền; dự án chỉ trở thành currentProject khi được mở.

### 5.3. Trạng thái trống

~~~text
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Dự án                                                                            [+ Dự án mới]    │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                    │
│                                    Chưa có dự án                                                    │
│                     Tạo dự án đầu tiên để bắt đầu quy trình sản xuất.                               │
│                                    [+ Tạo dự án]                                                    │
│                                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
~~~

Không tự tạo “Dự án mẫu”. Người dùng chủ động tạo dự án đầu tiên.

## 6. Dialog Tạo dự án

~~~text
┌──────────────────────────── Tạo dự án mới ────────────────────────────┐
│ Tên dự án                                                            │
│ [Ví dụ: Review công nghệ tháng 9                                  ]  │
│                                                                       │
│ Tỷ lệ khung hình              Tốc độ khung hình                       │
│ [16:9 — Ngang ▾]              [30 FPS ▾]                              │
│                                                                       │
│ Thư mục sẽ được tạo:                                                  │
│ projects/review-cong-nghe-thang-9                                    │
│                                                                       │
│                                      [Hủy]  [Tạo và mở dự án]         │
└───────────────────────────────────────────────────────────────────────┘
~~~

Quy tắc:

- Tên dự án bắt buộc và được loại khoảng trắng thừa.
- Hiển thị trước slug/thư mục dự án.
- Nếu slug trùng, báo ngay dưới ô tên; không âm thầm thêm timestamp.
- Enter thực hiện **Tạo và mở dự án** khi dữ liệu hợp lệ.
- Tạo thành công thì đóng dialog và đi thẳng vào workspace mới.

## 7. Workspace dự án

### 7.1. Header và thanh bước

~~~text
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [← Danh sách dự án]  /  Review công nghệ 09/2026                         16:9   30 FPS   [•••]       │
│                         Cập nhật 12 phút trước                                                    │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  1  Ảnh                      2  Giọng nói                         3  Xuất video                    │
│  ━━━━━━━━━━━━━━━             ────────────────                    ────────────────                  │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                    │
│                                  STEP CONTENT                                                       │
│                                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
~~~

- Tên dự án là tiêu đề chính.
- Không dùng combo đổi dự án trong workspace.
- Nút **Danh sách dự án** luôn ở vị trí đầu header.
- Menu ••• gồm Đổi tên, Mở thư mục và Xóa dự án.
- Step có thể được mở trực tiếp. Nếu thiếu đầu vào, page giải thích dữ liệu còn thiếu và dẫn về bước phù hợp.
- Mọi đường dẫn, trạng thái và kết quả phải lấy từ currentProject.

## 8. Bước 1 — Ảnh

Mục tiêu: nhập ảnh gốc, gỡ watermark và quản lý ảnh sạch trong dự án.

~~~text
┌──────────────────────────────────────────────────────────────┬─────────────────────────────────────┐
│ Ảnh của dự án                                     12 ảnh     │ Xem trước                           │
│ [Thêm ảnh] [Nhập thư mục]                  [Xóa mục đã chọn] │                                     │
├──────────────────────────────────────────────────────────────┤  ┌───────────────────────────────┐  │
│ TÊN FILE                TRẠNG THÁI      KẾT QUẢ              │  │                               │  │
│ gemini-01.png           Đã xử lý        gemini-01_clean...   │  │          Ảnh đang chọn         │  │
│ gemini-02.png           Đang chờ        —                    │  │                               │  │
│ cover.webp              Lỗi             Không nhận diện...   │  └───────────────────────────────┘  │
│                                                              │                                     │
│                                                              │  [Ảnh gốc]  [Ảnh sạch]              │
├──────────────────────────────────────────────────────────────┤                                     │
│ Tự động nhận diện watermark                                  │  gemini-01.png · 1920 × 1080         │
│ Độ lợi sáng  0.60  [────────●────]                           │                                     │
│                                                              │                                     │
│ [Mở thư mục ảnh]                   [Gỡ watermark 2 ảnh]      │                                     │
│ [━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  2/3]       │                                     │
└──────────────────────────────────────────────────────────────┴─────────────────────────────────────┘
~~~

Quy tắc:

- Danh sách file là vùng chính; preview là inspector bên phải.
- Chỉ hiện tham số thường dùng; tham số ít dùng nằm trong **Nâng cao**.
- Kết quả mặc định lưu tại project/images/clean; không hỏi thư mục ở mỗi lần chạy.
- Nút chính phản ánh số ảnh hợp lệ đang chờ.
- Sau khi xong, cho phép kiểm tra kết quả và bấm **Tiếp tục: Giọng nói**.

## 9. Bước 2 — Giọng nói

Mục tiêu: soạn nội dung, chọn voice, tạo audio/SRT và nghe lại trong dự án.

### 9.1. Tạo giọng

~~~text
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [Tạo giọng]  [Thư viện voice]                                                                       │
├──────────────────────────────────────────────────────────────────────┬─────────────────────────────┤
│ Nội dung                                                   1.250 ký tự│ Cấu hình giọng              │
│ ┌──────────────────────────────────────────────────────────────────┐ │ Voice: Mai Anh              │
│ │ Trí tuệ nhân tạo đang thay đổi cách chúng ta sáng tạo...         │ │ [Đổi voice]                 │
│ │                                                                  │ │ Model   [eleven_v3 ▾]       │
│ │                                                                  │ │ Ngôn ngữ [Tiếng Việt ▾]     │
│ └──────────────────────────────────────────────────────────────────┘ │ Stability [────●──] 0.50    │
│ Dự kiến chia thành 1 đoạn                                            │ Similarity[─────●─] 0.75    │
│ File đầu ra: narration_20260911.mp3                                  │ Speed    [────●──] 1.00x    │
│ ☑ Tạo phụ đề SRT                                                     │ ☑ Xuất SRT                   │
├──────────────────────────────────────────────────────────────────────┴─────────────────────────────┤
│ [Tạo giọng nói]    Đang xử lý đoạn 1/1  [━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━]            │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ narration_20260911.mp3     [▶]  00:00 ━━━━━━━●━━━━━━━━ 03:40       [Mở thư mục] [Dùng để xuất video]│
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
~~~

### 9.2. Thư viện voice

~~~text
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [Tạo giọng]  [Thư viện voice]                                                                       │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Tìm theo tên, ngôn ngữ, accent...]  [Nguồn: Tất cả ▾] [Giới tính: Tất cả ▾]                       │
├────────────────────────┬─────────────────┬──────────────────────┬────────────────────────────────────┤
│ TÊN                    │ NGÔN NGỮ       │ ĐẶC ĐIỂM            │                                    │
│ Mai Anh                │ Việt Nam       │ Nữ · Truyền cảm      │ [▶ Nghe thử]       [Chọn voice]      │
│ Minh Phong             │ Việt Nam       │ Nam · Trầm ấm        │ [▶ Nghe thử]       [Chọn voice]      │
│ Rachel                 │ English (US)   │ Nữ · Calm            │ [▶ Nghe thử]       [Chọn voice]      │
└────────────────────────┴─────────────────┴──────────────────────┴────────────────────────────────────┘
~~~

- Không ưu tiên Voice ID trong cột chính; ID nằm trong menu phụ để xem/copy.
- **Chọn voice** cập nhật voice đang dùng và quay về tab Tạo giọng.
- Chỉ một audio preview phát tại một thời điểm.
- File tạo ra mặc định lưu tại project/voice.

## 10. Bước 3 — Xuất video

Mục tiêu: kiểm tra đầu vào, thiết lập render và xuất file thành phẩm.

~~~text
┌───────────────────────────────────────────────────────────────────┬────────────────────────────────┐
│ Dữ liệu đầu vào                                                   │ Thiết lập xuất                 │
├───────────────────────────────────────────────────────────────────┤                                │
│ ✓ 24 ảnh sạch                       [Xem thư mục]                  │ Tỷ lệ       [16:9 ▾]           │
│ ✓ narration_20260911.mp3  03:40     [Nghe]                        │ Độ phân giải[1920 × 1080 ▾]    │
│ ✓ narration_20260911.srt              [Xem]                        │ FPS         [30 ▾]             │
│ ✓ scenes.json · 24 phân cảnh          [Chỉnh sửa]                  │ Chất lượng  [Cao ▾]            │
│                                                                   │ Tên file    [final_video.mp4]  │
├───────────────────────────────────────────────────────────────────┤                                │
│ Timeline phân cảnh                                                │ Thư mục: project/output        │
│ 01  gemini-01_cleaned.png       00:00 → 00:08                     │                                │
│ 02  gemini-02_cleaned.png       00:08 → 00:17                     │ [Xuất video]                   │
│ 03  cover_cleaned.webp          00:17 → 00:25                     │                                │
└───────────────────────────────────────────────────────────────────┴────────────────────────────────┘
│ Đang render frame 1.248/6.600  [━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 19%]  [Dừng]                │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
~~~

- Nút **Xuất video** chỉ bật khi đầu vào bắt buộc hợp lệ.
- Nếu thiếu dữ liệu, hiển thị tại đúng dòng và có hành động đi tới bước bổ sung.
- Khi render xong, hiển thị file kết quả với **Phát**, **Mở thư mục** và **Xuất lại**.

## 11. Cài đặt

Cài đặt thuộc cấp ứng dụng, không thuộc dự án.

~~~text
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Cài đặt                                                                                            │
│ Thiết lập tài khoản và giá trị mặc định cho các dự án mới.                                         │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ TÀI KHOẢN VOICE API                                                                                │
│ API Key                                                                                            │
│ [••••••••••••••••••••••••••••••••••••••••] [Hiện] [Kiểm tra kết nối]                             │
│ ● Đã kết nối     Trần Toàn · toan@example.com                         125.400 credits              │
├────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ MẶC ĐỊNH CHO DỰ ÁN MỚI                                                                             │
│ Voice mặc định       [Mai Anh ▾]        Model              [eleven_v3 ▾]                           │
│ Ngôn ngữ             [Tiếng Việt ▾]     Tỷ lệ khung hình   [16:9 ▾]                               │
│ FPS                   [30 ▾]             Thư mục dự án      [.../projects] [Mở]                     │
│                                                                                                    │
│                                                                         [Lưu thay đổi]             │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
~~~

## 12. Trạng thái dùng chung

| Trạng thái | Cách hiển thị |
|---|---|
| Loading | Skeleton hoặc progress có mô tả tác vụ |
| Empty | Một câu giải thích và một hành động chính |
| Error | Thông báo gần vùng lỗi, có cách thử lại |
| Success | Xác nhận ngắn, không mở modal nếu không cần |
| Disabled | Nhãn vẫn rõ và có tooltip nêu điều kiện còn thiếu |
| Destructive | Dialog nêu rõ tên đối tượng và hậu quả |

## 13. Design tokens

### 13.1. Màu sắc

| Token | Giá trị | Mục đích |
|---|---:|---|
| bg.app | #0E1014 | Nền ứng dụng |
| bg.sidebar | #12151B | Sidebar |
| bg.surface | #151922 | Toolbar và panel |
| bg.input | #101319 | Input, table, preview |
| bg.hover | #1B2130 | Hover dòng |
| border.default | #262C38 | Divider và viền nhẹ |
| accent.primary | #4F7CFF | CTA, focus, tab active |
| status.success | #35C58A | Hoàn tất, kết nối |
| status.warning | #F2B84B | Cảnh báo, thiếu dữ liệu |
| status.danger | #F06A6A | Lỗi, xóa, dừng |
| text.primary | #F3F5F7 | Nội dung chính |
| text.secondary | #A7AFBE | Nhãn và metadata |
| text.muted | #70798A | Placeholder và thông tin phụ |

Chỉ dùng xanh lam làm accent tương tác chính. Xanh lá, vàng và đỏ chỉ dành cho trạng thái.

### 13.2. Chữ và khoảng cách

- Font: Inter hoặc font sans-serif hệ thống; tối đa hai font.
- Page title: 24 px / 32 px, semibold.
- Section title: 14 px / 20 px, semibold.
- Body: 13 px / 20 px.
- Metadata: 12 px / 18 px.
- Spacing theo lưới 4 px; dùng chủ yếu 8, 12, 16, 24 và 32 px.
- Control cao 36 px; primary action có thể cao 40 px.
- Border radius 6 px cho control, 8 px cho dialog/panel.

### 13.3. Component

- Dùng divider và khoảng trắng thay vì đóng khung mọi vùng thành card.
- Table/list là component chính của trang Dự án và danh sách tài nguyên.
- Mỗi vùng chỉ có một primary action.
- Icon không có text phải có tooltip.
- Focus ring phải rõ để hỗ trợ bàn phím.
- Vùng click tối thiểu 36 × 36 px.

## 14. Kích thước cửa sổ

- Kích thước khuyến nghị: 1440 × 900.
- Kích thước tối thiểu: 1100 × 700.
- Dưới 1200 px, inspector có thể thu hẹp nhưng không ẩn action chính.
- Sidebar giữ cố định; content và splitter co giãn.

## 15. Tiêu chí nghiệm thu thiết kế

- Mở app luôn thấy danh sách dự án trước.
- Click/double-click một dự án mở đúng workspace và đúng dữ liệu dự án đó.
- Workspace luôn có tên dự án và nút quay lại danh sách.
- Không thể nhầm dữ liệu/công cụ đang thuộc dự án nào.
- Ba bước nằm cùng một workspace theo thứ tự Ảnh → Giọng nói → Xuất video.
- Không dùng combo đổi dự án bên trong workspace.
- Cài đặt API chỉ xuất hiện ở cấp ứng dụng.
- Có thiết kế cho empty, loading, error, processing và completed.
- Không dùng dashboard card grid, quá nhiều badge hoặc nhiều màu accent cạnh tranh.

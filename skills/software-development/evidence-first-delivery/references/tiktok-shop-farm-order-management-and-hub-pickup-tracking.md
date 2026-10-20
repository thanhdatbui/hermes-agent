# TikTok Shop Farm Order Management & Hub Pickup Tracking

## 1. Bối Cảnh & Chống Quán Tính Ngữ Cảnh (Anti-Context Inertia)
- **Tình huống:** Khi farm đang chạy nhiều quy trình (nuôi acc, chuẩn hoá avatar, pin video), user gửi ảnh chụp màn hình đơn hàng TikTok Shop trên một thiết bị farm và yêu cầu:
  *"tạo cho tao 1 chỗ quản lí đơn hàng. Bao gồm hình ảnh này và các thông tin sau: Tên - SĐT - Địa chỉ, note thêm là máy X, acc row Y"*.
- **CẠM BẪY NGHIÊM TRỌNG:** Agent bị quán tính ngữ cảnh của các turn trước kéo về luồng chuẩn hoá tài khoản/video, phớt lờ yêu cầu quản lý đơn hàng của user, dẫn đến việc bị user phản ứng gay gắt.
- **QUY TẮC CỐT LÕI:**
  - Mệnh lệnh mới nhất của user luôn có thẩm quyền cao nhất, xóa bỏ quán tính các turn trước.
  - Phân tích kỹ ảnh đính kèm (dùng `browser_vision` hoặc WinRT OCR) để nhận diện chính xác màn hình đích (TikTok Shop Order Detail, trạng thái "Đã đặt hàng", shop, sản phẩm, phân loại, giá tiền, email liên kết `a***7@hotmail.com`).
  - Lập tức chuyển sang luồng Order Management, tuyệt đối không được tự ý lôi quy trình chuẩn hoá kênh ra làm thay thế.

## 2. Kỷ Luật Thực Thi: Chống "Nói Mõm" (Proactive Engineering Delivery)
- Khi user hỏi: *"có cách nào theo dõi đơn đó liên tục để biết lúc nào về kho ra lấy (không muốn qua shipper)?"*
- **HÀNH VI BỊ CẤM:** Trả lời trần thuật lý thuyết suông (nói về cơ chế tracking, các đơn vị vận chuyển...) mà không có code hay công cụ cụ thể ("nói mõm").
- **HÀNH VI BẮT BUỘC:**
  1. Xây dựng ngay script tracking tự động: `D:/Taadaa/orders/track_order.py`.
  2. Tạo kho lưu trữ Excel chuẩn: `D:/OneDrive/TaadaaData/kibe/QuanLyDonHang_TikTokShop.xlsx`.
  3. Tạo CSDL JSON đồng bộ: `D:/Taadaa/data/orders.json` và `D:/OneDrive/TaadaaData/kibe/orders/orders.json`.
  4. Cung cấp sẵn các lệnh CLI để tra cứu và gán mã vận đơn tức thì khi shop xuất hàng.

## 3. Kiến Trúc Theo Dõi Đơn Hàng & Cảnh Báo Ra Bưu Cục Lấy
- **Các đơn vị vận chuyển chính trên TikTok Shop VN:**
  - **SPX Express (Shopee/TikTok Express):** Mã bắt đầu bằng `SPXVN...` hoặc `VN...`. Tra cứu qua API `https://spx.vn/api/v2/fleet_order/tracking/search?sls_tracking_number={code}`.
  - **J&T Express:** Mã 10-15 chữ số. Tra cứu qua API `https://jtexpress.vn/api/tracker?billcode={code}`.
  - **Ninja Van:** Mã `NGVN...` hoặc `NIVN...`. Tra cứu qua `https://api.ninjavan.co/vn/dash/1.0/public/orders/id/{code}`.
- **Cơ chế bắt mốc "Đã về bưu cục phát / HUB địa phương":**
  - Quét từ khóa: `bưu cục phát`, `kho phát`, `hub đà nẵng`, `thanh khê`, `tam thuận`, `đã đến bưu cục`, `đến kho giao`.
  - **Mục tiêu lấy hàng trực tiếp:** Khi bưu kiện vừa đến kho phát (thường vào 6h-8h sáng hoặc đầu giờ chiều), bot phải bắn cảnh báo khẩn cấp ngay:
    > 🚨 **HÀNG ĐÃ VỀ KHO BƯU CỤC - ĐI LẤY NGAY!**
    > Cung cấp Mã vận đơn, Tên người nhận, SĐT và Địa chỉ bưu cục để user ra lấy tại quầy, chặn trước khi bưu tá xếp hàng vào giỏ mang đi giao ngoài đường.
  - Phân biệt với mốc `SHIPPER ĐANG ĐI GIAO` (`out for delivery`) để user kịp gọi điện thoại giữ hàng tại quầy nếu shipper đã bắt đầu di chuyển.

## 4. Kỷ Luật Điều Phối Worker Viết Script Khi Hết Ngân Sách T1
- **Cạm bẫy Coordinator Write Denied & Dispatch Gate:**
  * Khi Coordinator viết vượt ngân sách T1 (tối đa 10 files, <= 500 dòng), hook `guard_write_ownership` sẽ chặn ghi (`COORDINATOR WRITE DENIED`).
  * Gọi `delegate_task` cho việc sửa/tạo code sẽ bị chặn bởi Dispatch Gate (`BLOCKED_BY_DISPATCH_GATE`).
  * Chạy `dispatch_worker.py` ở chế độ foreground với timeout > 60s sẽ bị chặn bởi Foreground Guard (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
- **Quy trình chuẩn khi Coordinator hết budget:**
  * Khởi chạy worker bằng lệnh nền: `terminal(background=True, notify_on_complete=True, timeout=180)` gọi `python D:/Taadaa/tools/dispatch_worker.py "<contract>" --file "<target_file>" --workdir "<repo>" --timeout 150`.
  * Sau khi kích hoạt, kết thúc lượt trả lời để harness tự đánh thức khi worker xong (event-driven wakeup).
- **Kỷ luật soạn Contract chống Worker kẹt "BLOCKED: NEEDS_INPUT":**
  * Worker CLI chạy trong môi trường sandbox khóa chặt file (`tool_lock: locked`). Do đó CẤM giao task bắt tạo/sửa nhiều file nếu chỉ truyền 1 file qua `--file`.
  * BẮT BUỘC cung cấp sẵn cấu trúc JSON cụ thể (ví dụ: `order['customer']['name']`, `phone`, `address`, `tracking_code`).
  * BẮT BUỘC cung cấp URL endpoint API mẫu (ví dụ: `https://spx.vn/api/v2/fleet_order/tracking/search?sls_tracking_number={code}`).
  * Cung cấp tiêu chí nghiệm thu tự túc (self-contained verification): `python <script> --poll` trả về exit code 0. Thiếu các thông số này, worker sẽ từ chối suy đoán và dừng lại vì thiếu input.


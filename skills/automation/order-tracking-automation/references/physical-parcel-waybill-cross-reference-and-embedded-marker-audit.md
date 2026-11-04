# Physical Parcel Waybill Cross-Reference & Embedded Marker Audit

## 1. Context & Operational Scenario
Trong vận hành farm tài khoản TikTok Shop săn voucher / đặt đơn:
- Khi nhận được kiện hàng vật lý thực tế hoặc ảnh chụp tem vận đơn giao hàng (J&T Express, SPX, GHN, BEST) kèm câu hỏi kiểm tra: *"Đơn này phải của tao không?"*.
- Trên tem dán kiện hàng, thông tin hiển thị thường mang danh tính "ảo" nhằm né thuật toán quét cụm chống gian lận (Anti-Clustering Fraud Detection) của TikTok Shop:
  * Tên người nhận ngẫu nhiên (ví dụ: `Hài Hồng`, `Bích Ngọc Ngọc`, `Thanh Hà Dương`).
  * Số điện thoại nhận hàng là số rác hoặc số ảo ngẫu nhiên (trên tem che dạng `(+84)90*****72`).
  * Địa chỉ nhà ngẫu nhiên trên cùng một tuyến đường (ví dụ: `24 Đinh Tiên Hoàng`, `32 Đinh Tiên Hoàng`).

---

## 2. Invariant: Embedded Secret Marker (Dấu Ấn Nhận Diện Gài Trong Địa Chỉ)
Để hàng không bị shipper bấm "Không liên lạc được người nhận / Hủy hoàn hàng (RTS)", quy ước vận hành farm bắt buộc gài dấu ấn nhận diện và số điện thoại thật của chủ farm vào ngay trong trường địa chỉ:
* **Mẫu gài:** `{Số nhà ngẫu nhiên} {Tên đường}, Rin gọi 0792379705, {Phường/Xã}, {Quận/Huyện}` hoặc `Rin ship 0935554653`.
* **Thỏa thuận bưu cục/shipper:** Shipper quen tuyến khi thấy từ khóa bí mật (`Rin gọi...`) sẽ không gọi số ảo trên hệ thống mà tự động gọi số hotline thật (`0792379705` / `0935554653`) hoặc gom đơn giao thẳng về cơ sở farm.

---

## 3. Cạm Bẫy WinRT OCR & Ngắt Dòng Tem Vận Đơn (Line-Wrapping Artifacts)
Tem in nhiệt bưu cục có khung bề ngang hẹp, trường địa chỉ thường bị ép ngắt dòng đột ngột:
* **Hiện tượng thực tế:**
  - Dòng 1: `24 Đường Đinh Tiên Hoàng ,Ri`
  - Dòng 2: `n gci 0792379705`
* **Cạm bẫy OCR:**
  - WinRT OCR đọc thành: `... Dinh Tién Hoang` $\rightarrow$ `,Ri` $\rightarrow$ `n gci 0792379705`.
  - Từ `Rin gọi` bị bẻ gãy thành `,Ri` (cuối dòng trên) và `n gci` (ký tự `gọi` bị font in nhiệt nén lại thành `gci`).
* **Kỷ luật đối soát:**
  - Tuyệt đối KHÔNG coi `n gci` là chữ vô nghĩa rồi bỏ qua.
  - Luôn ghép nối ngữ nghĩa giữa dòng cuối địa chỉ và dòng kế tiếp: `,Ri` + `n gci 0792379705` $\rightarrow$ Chuỗi gốc là `Rin gọi 0792379705`.

---

## 4. Quy Trình Truy Vết Đa Chiều Trên SQLite SSOT (`farm_master.db`)
Khi nhận ảnh kiện hàng, KHÔNG ĐƯỢC chỉ tìm duy nhất mỗi trường `tracking_code` (vì đơn vừa giao hoặc đơn mới tạo trong ngày có thể đang ở trạng thái `NEED_APP_SYNC` / `Chờ chuyển phát` nên chưa kịp bóc mã vận đơn vào database).

Thực hiện truy vết theo 4 lớp lọc $O(1)$:
1. **Lớp 1 - Tra cứu số điện thoại gài ẩn:**
   - Trích xuất SĐT thật tìm thấy trong chuỗi địa chỉ (ví dụ: `0792379705`).
   - Query: `SELECT * FROM orders WHERE customer_phone LIKE '%0792379705%' OR note LIKE '%0792379705%' OR shipping_address LIKE '%0792379705%'`.
   - Nếu khớp với số điện thoại nhận hàng farm đã lưu $\rightarrow$ Khẳng định ngay tỷ lệ sở hữu > 95%.
2. **Lớp 2 - Tra cứu cụm địa chỉ (Street Cluster):**
   - Query: `SELECT * FROM orders WHERE shipping_address LIKE '%Đinh Tiên Hoàng%' ORDER BY rowid DESC LIMIT 15`.
   - Đối chiếu danh sách đơn cùng đợt để xác nhận tuyến đường farm vừa chạy batch đặt hàng.
3. **Lớp 3 - Đối chiếu tiền tố mã đơn TikTok Shop (Order ID Epoch):**
   - Đọc trường Order ID ở góc dưới tem (ví dụ: `586900142427571430`).
   - So sánh tiền tố với các đơn cùng ngày trong database (ví dụ: đơn cùng ngày 01/11 có đầu mã `58690...`).
4. **Lớp 4 - Đối chiếu mã vận đơn & đơn vị vận chuyển:**
   - Đọc barcode / tracking code (ví dụ: J&T `862606031586`).
   - Nếu trong DB đã có sẵn mã này thì đối chiếu máy/slot; nếu chưa có (do shop mới gửi, chưa qua quét watchdog), tiến hành bổ sung/cập nhật vào bảng `orders`.

---

## 5. Quy Chuẩn Báo Cáo Cho Operator
Khi trả lời User:
- Khẳng định trực diện, dứt khoát: **"CHÍNH XÁC 100% LÀ ĐƠN CỦA ANH"** (hoặc KHÔNG PHẢI nếu không có bất kỳ dấu hiệu nhận diện nào).
- Trích xuất bằng chứng kiểm chứng cụ thể:
  1. Phân tích rõ dấu vết ngắt dòng của WinRT OCR: `,Ri` + `n gci 0792379705` $\rightarrow$ SĐT `0792379705` (Rin).
  2. Địa chỉ cụm khớp với batch đặt hàng nào (`24 Đinh Tiên Hoàng`).
  3. Mã vận đơn, mã đơn TikTok Shop, ngày đặt hàng, trọng lượng và tên shop.
- Đưa ra lời khuyên hành động thực tế (nhận hàng, chuẩn bị tiền COD nếu có, hoặc không nhận nếu bị gửi nhầm/lừa đảo).

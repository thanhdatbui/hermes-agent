# Parallel Workers, Milestone Alerts, and Bundle Product Traps in Order Tracking

## 1. Cấm Tuần Tự (Cuốn Chiếu) — Bắt Buộc Song Song Đa Luồng (Max 15 Workers)
- **Bẫy cuốn chiếu tuần tự:** Vòng lặp tuần tự `for order in orders:` với giới hạn `max_app_syncs = 1` sẽ gây chết đói (starvation) nghiêm trọng. Nếu một máy đầu tiên bị kẹt (ví dụ kẹt popup nhạy cảm, bận ca nuôi, hoặc timeout), nó sẽ nuốt trọn slot duy nhất của mỗi chu kỳ và gọi `break`, khiến toàn bộ các máy phía sau không bao giờ được quét trong nhiều ngày.
- **Giải pháp cơ giới hóa:** Bắt buộc dùng `ThreadPoolExecutor(max_workers=min(15, len(pending_orders)))`.
  - Mỗi thread đảm nhiệm đúng 1 thiết bị/máy farm độc lập.
  - Xử lý timeout và `DeviceLockBusyError` độc lập: máy nào bận ca nuôi thì thread đó kết thúc nhanh, các máy khác vẫn song song bóc mã bình thường.
  - Toàn bộ farm hoàn tất quét chỉ trong 25–35 giây thay vì hàng chục phút.
- **Bắt buộc Thread-Safe Lock:** Vì nhiều worker trả về kết quả cùng lúc, mọi thao tác cập nhật `orders.json` và `QuanLyDonHang_TikTokShop.xlsx` BẮT BUỘC phải bọc trong `threading.Lock()`.

## 2. Quy Chuẩn 3 Mốc Báo Cáo Bắt Buộc (Milestone Alerts) Cho Hermes Cron
Với Hermes Cron chạy chế độ `no_agent: true`, stdout rỗng đồng nghĩa với im lặng (silent). Do đó, script BẮT BUỘC phải `print()` rõ ràng khi đạt các mốc sau để bot tự động gửi tin nhắn về Telegram:
1. **Mốc 1 — Bóc mã thành công sang Phase 2:**
   - Tiêu đề: `🎉 ĐÃ BÓC ĐƯỢC MÃ VẬN ĐƠN MỚI TỪ TIKTOK APP (MÁY N)`
   - Nội dung: Tên khách, sản phẩm, hãng vận chuyển, mã vận đơn, tiền mặt COD, thông báo chuyển sang Phase 2.
2. **Mốc 2 — Hàng cập bến Đà Nẵng:**
   - Tiêu đề: `🚨 HÀNG VỀ ĐÀ NẴNG: <MÃ ĐƠN> (<Tên khách> - <SĐT>)`
   - Bộ lọc địa phương: Quét tất cả các mốc `TTKT ĐÀ NẴNG`, `Đống Đa`, `Thanh Khê`, `Hải Châu`, `Liên Chiểu`, `Tam Thuận`.
3. **Mốc 3 — Shipper đi phát & Giao thành công:**
   - Tiêu đề: `🛵 SHIPPER ĐANG ĐI PHÁT` (kèm tên shipper + SĐT) và `✅ GIAO HÀNG THÀNH CÔNG` (kèm tên người ký nhận).

## 3. Khử Bẫy Silent Initialization & Chống Trùng Lặp Tin Báo
- **Bẫy Silent Init:** Trong các module watchdog (như `watch_jt_delivery.py`), khi một đơn mới được nạp lần đầu mà bưu cục đã có sẵn mốc đến kho phát hoặc shipper đang giao, CẤM thực hiện `continue` im lặng. Phải kiểm tra nếu đã ở kho phát hoặc đang đi phát thì BẮT BUỘC in cảnh báo ngay lập tức.
- **Chống trùng lặp tin báo:** Chỉ để duy nhất một module phát cảnh báo chính (`track_web_order`). CẤM gọi lồng thêm watchdog con in trùng sự kiện gây spam lặp tin nhắn trên Telegram.

## 4. Bẫy Thu Gọn Quà Tặng Kèm ("Thư Cảm Ơn") Khi Nạp Đơn
- **Hiện tượng:** Trên TikTok Shop, các đơn áp mã voucher thường gồm nhiều món hàng chính (dầu ăn, nước giặt, đồ gia dụng...) và kèm quà tặng 0đ (như thiệp cảm ơn, thư cảm ơn). TikTok tự động thu gọn và hiện nút `Xem thêm v`.
- **Hậu quả:** OCR chỉ đọc các dòng dưới cùng dẫn đến việc ghi nhận tên đơn là "Thư Cảm Ơn Quý Khách Hàng", làm người dùng không nhận diện được đơn khi hàng về.
- **Quy chuẩn:**
  - Khi chụp/đọc màn hình đơn hàng, phải kiểm tra nút `Xem thêm` để bung toàn bộ danh sách.
  - Ưu tiên bóc dòng sản phẩm đầu tiên (sản phẩm chính có giá trị cao nhất) thay vì lấy dòng cuối cùng mang tính chất quà tặng kèm.

## 5. Bẫy Popup Modal Che Chắn Màn Hình & Xóa Khoảng Trắng Kerning
- **Bẫy thiếu từ khóa Dismiss Modal:** Các dialog tài trợ hoặc banner popup (ví dụ: *"Trải nghiệm ngay"* kèm nút *"Đóng"* / *"D6ng"*) chặn toàn bộ touch input xuống bottom bar. Nếu `ORDER_POPUP_DISMISS_KEYWORDS` chỉ có *"Để sau"*, popup sẽ không bao giờ được tắt, gây kẹt màn hình vĩnh viễn. Bắt buộc mở rộng đầy đủ các biến thể: `"Đóng"`, `"Dong"`, `"D6ng"`, `"Bỏ qua"`, `"Bo qua"`, `"Hủy"`, `"Huy"`, `"Tắt"`, `"Tat"`.
- **Bộ lọc xóa khoảng trắng cho OCR Kerning trong `_find_center`:** WinRT OCR thường tách ký tự ngẫu nhiên (`H 6 sd`, `Hö s d`, `H6 sd`, `Hö sd`). So khớp nhãn tab/nút bắt buộc phải so sánh chuỗi đã loại bỏ khoảng trắng và chuẩn hóa `0` <-> `o`: `folded.replace(" ", "").replace("0", "o") == wanted.replace(" ", "").replace("0", "o")`.
- **Tự động lùi về từ Sub-activity:** Khi `dumpsys window windows` ghi nhận app đang nằm ở sub-activity như `I18nSettingManageMyAccountActivity` hoặc settings, runner phải gửi `KEYCODE_BACK` lùi về `SplashActivity` trước khi bắt đầu chu trình tìm tab đơn hàng.

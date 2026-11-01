---
name: farm-testbed-and-asset-governance
description: "Use when selecting testbed or auditing mailboxes."
---
# Farm Testbed Selection & Asset Inventory Governance

Kỷ luật vận hành cô lập rủi ro thiết bị và kiểm soát tồn kho tài nguyên (Mailboxes, TikTok Accounts) trên Taadaa Farm.

## 1. Farm Testbed Selection Invariant (Bảo vệ tuyệt đối máy chứa nick già)
- **CẤM TUYỆT ĐỐI đụng nick già cựu binh**: Khi thử nghiệm app mới (TikTok Lite, Dual App, Island), luồng reg mới, hoặc can thiệp kỹ thuật thử nghiệm:
  * CẤM chọn các máy mang dàn nick cựu binh (như Máy 1, dàn nick reg tháng 2–3/2026 đang gánh follow toàn farm). Mọi rủi ro văng nick, dính cờ checkpoint trên máy cựu binh đều gây tê liệt năng lực bơm follow của cả hệ thống.
- **Tiêu chuẩn chọn testbed an toàn**:
  * BẮT BUỘC query SQLite (`farm_account_info` / `snapshots`) lọc ra máy có **100% nick non / nick yếu** (các nick reg tháng 9–10/2026, `following = 0` hoặc `< 5`, ví dụ Máy 78, 79, 80 ở Kibe Local hoặc Máy 211, 249, 276, 279 ở Admin Remote).
  * Kiểm tra máy rảnh an toàn (màn hình Sleep/Dozing, Current Focus là Launcher) trước khi nạp thử nghiệm.

## 2. TikTok App Package & Geo Invariants
- **Phân định Package theo khu vực**:
  * **TikTok Chuẩn Đông Nam Á / VN**: `com.ss.android.ugc.trill` (toàn farm đang chạy).
  * **TikTok Lite trên Google Play VN**: Hiện ByteDance phân phối package **`com.zhiliaoapp.musically.go`** (bản `com.ss.android.ugc.trill.go` cũ v3.8.1 đã bị khai tử trên Play Store và trả về `Network Error` do ngắt server).
- **Cơ chế Instant-Ban khi Reg Lite trên máy đang nuôi**:
  * Khi máy đã kịch trần 8 nick trên TikTok chuẩn, nếu dùng TikTok Lite reg tiếp nick thứ 9 bằng cách gõ mail Hotmail thủ công trên proxy đã có lịch sử farm, ByteDance Security SDK đọc trùng hardware hash / Android ID và sẽ lập tức gắn cờ **`Tài khoản của bạn đã bị cấm`** ngay tại bước đặt nickname.
  * Email dính cờ cấm phải bị **PURGE XÓA SỔ NGAY** khỏi `mailboxes` trong `farm_master.db`, cấm tái sử dụng kẻo làm bẩn thiết bị khác.

## 3. Mailbox Inventory Accounting Discipline (Chống ảo giác số tổng)
- **CẤM báo số tổng thô**: Tuyệt đối không query `SELECT count(*) FROM mailboxes` (1.115 mail) rồi báo với User là "còn hàng trăm con". 
- **Công thức tính tồn kho thực tế khả dụng**:
  `Tồn kho khả dụng = Tổng mailboxes - Mail đã gán TikTok (1.058) - Mail reserve cứu Gmail DIE (26) - Mail rớt OAuth token`.
- **Phân tách luồng sử dụng**: Không nhầm lẫn giữa kho Hotmail dành cho TikTok Farm với kho Hotmail dùng cho luồng GPM -> ChatGPT -> Codex.
- **Xác thực tự động qua Graph API**: Dùng song song `ThreadPoolExecutor` gọi endpoint `https://login.live.com/oauth20_token.srf` để kiểm tra độ sống của refresh token và quét hòm thư tìm thư rác/mail TikTok trước khi cấp phát mail cho bất kỳ luồng nào. Nếu hòm thư đã có sẵn mail mã xác nhận từ TikTok (như trường hợp `estefanyjadencenn`), bắt buộc loại bỏ ngay khỏi danh sách reg mới.

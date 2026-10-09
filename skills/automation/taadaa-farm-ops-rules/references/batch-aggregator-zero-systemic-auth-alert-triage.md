# Triage Batch Alert: 0 Cụm Lỗi Hệ Thống Nhưng Vẫn Kích Hoạt Alert

## Hiện tượng
Hệ thống bắn Telegram Alert dạng:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG
• Quy trình / Script: Nuôi Acc / Lướt Feed
• Quy mô batch: 80 máy | Thành công: 63 | Thất bại: 17
• Tổng tỷ lệ thất bại toàn batch: 21.2% (17/80 máy)
• Số cụm lỗi hệ thống: 0

📋 CHI TIẾT LỖI VƯỢT NGƯỠNG KÉP (RATE & COUNT):

🎯 CHỈ DẪN CANARY POLICY & RECOVERY:
1. Khóa batch: Không can thiệp đồng loạt toàn bộ thiết bị.
2. Canary Test đại diện trên 1 máy: python D:/Taadaa/tools/inspect_machine.py N/A
...
⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện 1 máy dính lỗi login/xác minh:
   • Máy M52: login/account screen detected
```

Người vận hành nhìn vào thấy mục **"CHI TIẾT LỖI VƯỢT NGƯỠNG KÉP"** trống trơn và thắc mắc "là lỗi gì, đọc không thấy lỗi".

## Nguyên nhân cấu trúc (Code logic trong `batch_aggregator.py`)
1. **Ngưỡng kép Systemic (Dual-threshold):**
   Một lỗi chỉ được xếp vào `systemic_signatures` khi thỏa mãn đồng thời:
   - `count >= min_count` (thường là >= 3 máy)
   - `rate >= min_rate` (thường là >= 10% tổng số máy)
   Khi 17 máy fail vì các lỗi rải rác, không trùng lặp (app crash, adb timeout, proxy lag, selector miss lẻ tẻ 1-2 máy), toàn bộ 17 lỗi bị đưa vào `sporadic_signatures` (lỗi đơn lẻ). Do đó `len(systemic_signatures) == 0`, không có mục nào để render dưới tiêu đề chi tiết lỗi vượt ngưỡng kép, và máy canary candidate thành `N/A`.

2. **Trigger phát Alert khẩn P0:**
   Biến `should_alert` được kích hoạt bởi:
   ```python
   should_alert = len(systemic) > 0 or len(auth_failures) > 0
   ```
   Dù `systemic == 0`, nhưng có $\ge 1$ máy có keyword nhạy cảm về Auth (`login`, `account screen`, `verification`, `checkpoint`, `auth`, `văng`, `identity`), hệ thống BẮT BUỘC phát alert khẩn cấp để bảo vệ tài khoản khỏi nguy cơ văng/checkpoint lan rộng.

## Hướng dẫn giải thích & Triage nhanh cho Coordinator
1. **Giải thích trực tiếp cho User/Admin:**
   - Xác nhận ngay: **Toàn batch không có lỗi hệ thống sập nguồn hay bug script hàng loạt** (các máy fail là do lỗi mạng/thiết bị rải rác không vượt ngưỡng gom cụm).
   - Chỉ ra nguyên nhân alert nổ: **Chỉ do cảnh báo P0 ở máy đơn lẻ dính auth/login screen**.
2. **Hành động xử lý (Actionable):**
   - Không can thiệp vào 16 máy lỗi rải rác.
   - Chỉ định vị và xử lý đúng máy dính auth được nêu ở cuối alert:
     ```bash
     python D:/Taadaa/tools/inspect_machine.py <MÁY_BỊ_AUTH>
     ```
   - Chụp màn hình, kiểm tra session/tài khoản và login lại nếu cần.

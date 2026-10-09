# Batch Aggregator & Machine Alert Suppression Architecture

## 1. Bản Chất Kiến Trúc Cảnh Báo Lỗi Farm (Alert Governance)

Hệ thống Phone Farm vận hành theo cơ chế **Batch Error Aggregation** để triệt tiêu tình trạng Telegram bị spam hàng loạt tin nhắn alert máy lẻ khi chạy batch hàng chục / hàng trăm máy:

- **Chế độ Mặc định (Batch Mode):**
  - Mọi lỗi phát sinh trong lúc máy lẻ đang chạy batch (`multi-machine-feed-session`, v.v.) **BẮT BUỘC bị suppress** tại tầng `alerts.send_farm_machine_alert()`.
  - Mọi báo cáo sự cố được chuyển giao cho `batch_aggregator.py` tổng hợp sau khi batch kết thúc.
  - Cảnh báo chỉ được gửi về Telegram dưới dạng **`[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG`** khi thỏa mãn:
    1. **Ngưỡng kép (Dual-threshold):** Tỷ lệ lỗi $\ge 10\%$ toàn batch VÀ $\ge 3$ máy có cùng signature lỗi.
    2. **Lỗi P0 Login / Account / Session Lost / Checkpoint:** KHÔNG CẦN đạt % threshold, nhưng **BẮT BUỘC gửi dưới dạng Batch Alert gom cụm**, nêu danh sách máy dính lỗi login trong 1 tin nhắn duy nhất.

---

## 2. Anti-Pattern: Bypass Suppression Máy Lẻ

- **Hiện tượng (Sự cố sáng 21/09/2026 - Case 94):**
  Trong `send_farm_machine_alert`, nếu có logic bypass kiểu:
  ```python
  is_account_missing = any(k in str(error_reason).lower() for k in ("missing-expected", "account_missing", ...))
  if is_account_missing:
      # BYPASS suppression -> Bắn alert máy lẻ ngay lập tức!
  ```
  Khi một bug runtime (ví dụ NameError trong switcher) hoặc sự cố hàng loạt máy không tìm thấy nick mục tiêu, hàng chục tin nhắn Banner Đỏ `[MAY N]` kèm ảnh chụp màn hình sẽ nã liên tục vào Telegram của người dùng.

- **Quy tắc Bất Biến (Invariant):**
  1. **TUYỆT ĐỐI CẤM bypass suppression máy lẻ trong batch mode:** Bất kể lỗi là gì, trong batch mode toàn bộ máy lẻ đều phải im lặng.
  2. **Giao toàn quyền cho Batch Aggregator:** Lỗi mất nick, checkpoint, văng phiên đã có `SESSION_LOST_KEYWORDS` và `CHALLENGE_KEYWORDS` trong `batch_aggregator.py` quét và đưa vào `auth_failures` để kích hoạt Batch Alert tức thì.
  3. **Không tạo ngoại lệ nã lẻ:** Người dùng chỉ muốn nhận 1 tin nhắn tổng thể gom cụm, không bao giờ muốn nhận các tin lẻ tẻ từng máy làm ngập chat.

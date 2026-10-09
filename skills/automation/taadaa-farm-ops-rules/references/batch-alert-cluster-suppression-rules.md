# Quy Tắc Alert Báo Theo Cụm Lỗi & Triệt Tiêu Bypass Máy Lẻ

## 1. Nguyên Tắc Cốt Lõi (User Invariant)
- **Toàn bộ cảnh báo farm phải báo theo CỤM LỖI (Batch Alert) khi đạt % nhất định.**
- **Ngoại lệ P0 duy nhất:** Lỗi login / văng account / mất nick (`SESSION_LOST_KEYWORDS`). 
- **Quy cách phát cảnh báo ngoại lệ:** Dù không cần đạt % ngưỡng (ngay cả khi chỉ 1 máy dính), **BẮT BUỘC VẪN PHẢI BÁO THEO CỤM / DƯỚI DẠNG TIN NHẮN BATCH ALERT TỔNG THỂ**, tuyệt đối KHÔNG ĐƯỢC nã tin nhắn đỏ hay chụp ảnh banner lẻ tẻ từng máy (`[FARM ALERT: MÁY N]`).

---

## 2. Bài Học Từ Sự Cố (Case 94)
### Anti-Pattern:
- Trong `automation_core.alerts.send_farm_machine_alert`, trước đây có nhánh:
  ```python
  is_account_missing = any(k in str(error_reason).lower() for k in ("account-missing", "thiếu nick", ...))
  if is_account_missing:
      # BYPASS suppression -> Gửi alert Telegram máy lẻ ngay lập tức!
  ```
- **Hậu quả:** Khi switcher bị lỗi hoặc không tìm thấy nick (`ACCOUNT_MISSING`), hàng chục máy lần lượt vượt qua chốt chặn suppress và nã hàng loạt tin nhắn kèm ảnh đỏ riêng lẻ về Telegram, gây spam nghiêm trọng và phá vỡ cơ chế giám sát theo cụm của Farm.

### Giải pháp Chuẩn Hóa:
1. **Triệt tiêu toàn bộ bypass trong `alerts.py`:**
   - Khi `_should_suppress_immediate_machine_alert()` là `True` (mặc định trong batch run mode), toàn bộ machine alert lẻ đều bị suppress an toàn 100%.
   - Không tạo thêm bất kỳ nhánh bypass cục bộ nào trong `send_farm_machine_alert`.
2. **Ủy thác toàn quyền cho `batch_aggregator.py`:**
   - Đưa đầy đủ các từ khóa liên quan (`account-switcher-missing-expected`, `account_missing`, `account-missing`, `thiếu nick`, `mất nick`, `account missing`,...) vào `SESSION_LOST_KEYWORDS` trong `batch_aggregator.py`.
   - Khi batch kết thúc, `batch_aggregator.py` tự động phát hiện `session_lost_count > 0` và kích hoạt tin nhắn `[BATCH ALERT: LỖI HỆ THỐNG]` kèm mục `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]` tổng hợp danh sách máy lỗi trong 1 tin nhắn duy nhất.

---

## 3. Checklist Điều Phối Trước Khi Can Thiệp Alert
1. **Không thêm nhánh bypass machine alert lẻ** cho bất kỳ lỗi nào trừ khi có yêu cầu canary tường minh từ người dùng.
2. Mọi phân loại lỗi auth/account phải được ánh xạ vào `batch_aggregator.py` (`SESSION_LOST_KEYWORDS` hoặc `CHALLENGE_KEYWORDS`).
3. Khi debug cảnh báo lỗi farm: Kiểm tra `batch_aggregator.py` trước tiên để xem lỗi thuộc nhóm `systemic`, `sporadic`, hay `auth_failures`.

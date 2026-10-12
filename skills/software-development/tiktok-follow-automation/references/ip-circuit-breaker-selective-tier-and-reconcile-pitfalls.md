# IP Circuit Breaker Selective Tiering & Follow Reconcile Pitfalls

## 1. Cạm bẫy "Zero Tripped Proxies != Zero Follow Drops (Nhả Follow)"

### Hiện tượng & Sai lầm
Khi kiểm tra bảng `ip_circuit_breaker`, nếu thấy không có proxy nào bị `TRIPPED` mới trong ngày, Coordinator dễ kết luận ẩu: "Hôm nay sạch 100%, không có nick nào dính nhả".
Thực tế hiện trường có thể có hàng chục nick (ví dụ 48 nick Row 4) bị TikTok nhả follow ngay lượt đầu tiên (`FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session`).

### Cơ chế kỹ thuật (Selective Breaker Tier)
Trong `follow_state.py`:
```python
# IP Circuit Breaker: CHỈ ngắt cổng proxy khi nick CẤP KHỎE (was_graduated is True) bị nhả
if was_graduated:
    trip_ip_breaker(self.machine)
else:
    logger.info("Nick chua tot nghiep dinh nha -> chi phat account cooldown, KHONG ngat IP breaker")
```
- **Nick non / Probation / Row yếu (`is_graduated == False`):** Khi bị nhả, hệ thống coi nguyên nhân là do nick yếu (chưa đủ trust/video/tuổi), CHỈ phạt account cooldown (`fail_streak`, `cooldown_until_date`) và **KHÔNG ngắt IP Circuit Breaker**.
- **Nick tốt nghiệp (`is_graduated == True`):** Chỉ khi nick khỏe có lịch sử sạch mà vẫn bị nhả thì hệ thống mới coi là dải IP bị taint, lúc đó mới kích hoạt `trip_ip_breaker()`.
- **Hệ quả đối soát:** Tuyệt đối KHÔNG dùng số proxy TRIPPED để kết luận tình trạng dính nhả toàn farm. Bắt buộc phải quét các file `runs/state/follow_state_*_row_*.json` kiểm tra `last_failed_date == today` và `last_fail_reason`.

---

## 2. Đối soát số liệu Follow: State File vs Daily DB vs Session DB

Khi đối soát sản lượng follow trong ngày:
1. **Ground Truth thực tế:** Đếm các mục trong `followed` dict của từng file `runs/state/follow_state_*.json` có ISO timestamp bắt đầu bằng ngày `target_date`.
2. **`session_account_actions`:** Ghi nhận theo từng phiên (`caX_phienY`). Chú ý rằng một số bản ghi cập nhật lũy tiến giữa các phiên trong cùng một ca.
3. **`daily_account_actions`:** Có thể chênh lệch 4-5 lượt so với state file do ghi nhận lặp giữa các phiên hoặc retry không đồng bộ. Khi user thắc mắc số follow thực tế, luôn đối soát trực tiếp từ timestamp của state file trước khi giải thích.

---

## 3. Lý giải sản lượng Full Quota vs Probation Quota

### Cơ chế phân bổ hạn mức (`_determine_budget_tier`):
- **Full Quota (`mode: full`):** Cấp `random.randint(10, 20)` lượt **cho mỗi phiên**.
  - Nếu nick chạy đủ 2 phiên trong ca (Phiên 1 + Phiên 2) $\rightarrow$ Đạt tổng **20 - 30 follow/ngày**.
  - Nếu Phiên 1 bị skip do dải proxy đang ngâm 48h cách ly (chưa chạm mốc mở khóa), nick chỉ kịp chạy Phiên 2 $\rightarrow$ Tổng ngày chỉ đạt **10 - 15 follow** (ví dụ M17 đạt 12 fl, M23 đạt 14 fl). Đây là do thiếu phiên chứ không phải hệ thống bóp quota.
- **Probation Tier 1 (`mode: probation_tier1`):** Nick vừa hết cooldown hoặc có tiền sử nhả follow chỉ được cấp **1 - 2 lượt/ngày** (`random.randint(1, 2)`) để dò đường.
- **Progressive Cooldown Backoff:**
  - Streak 1: nghỉ 3 ngày (+3d).
  - Streak 2: nghỉ 5 ngày (+5d).
  - Streak 3: nghỉ 7 ngày (+7d).
  - Streak $\ge 4$: nghỉ 15 ngày (+15d).
  Khi dàn nick đã dính streak $\ge 2$, phần lớn tài khoản (ví dụ 57/78 nick Row 2) sẽ nằm im trong cooldown suốt chu kỳ.

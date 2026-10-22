# Burst Cadence Follow Probation Ladder & Config-Driven Thresholds

## 1. Bối cảnh: Thích ứng với Chu kỳ Xoay tua 4 Ngày (Burst & Hibernation)

Khi farm chuyển đổi sang chu kỳ vận hành 4 ngày (Parity 96h: N1 lẻ, N2 chẵn, N3 dưỡng, N4 slot động):
- **Khoảng nghỉ tự nhiên (Hibernation):** Các tài khoản có thời gian nghỉ 72h - 96h giữa các chu kỳ follow, tự động giải phóng một phần tín hiệu spam tích tụ ở backend TikTok.
- **Bất cập của nấc 4 ca sạch cũ:** Nếu giữ nguyên yêu cầu 4 ca sạch (mỗi ca cách nhau 4 ngày), tài khoản mất tới **16 - 17 ngày** để tốt nghiệp lên hạn mức bình thường (`clean_days >= 4`). Điều này làm nghẽn tiến độ nuôi dàn tài khoản mới (Rookie / Probation).
- **Rủi ro nếu bỏ hẳn Probation:** Nếu vừa hết cooldown mà nhảy thẳng lên Full Quota (10 - 15 follows/ca), hành động đột biến (action spike) sẽ kích hoạt cờ nghi vấn và làm giật cầu dao IP MikroTik 48h.

---

## 2. Chuẩn hóa Bậc thang Thử thách 2 Nấc Tối ưu (2-Clean-Days Ladder)

Lộ trình thử thách rút gọn từ 4 ca sạch xuống còn **2 ca sạch** (tổng 8 ngày):

| Giai đoạn | Điều kiện `clean_days` | Hạn mức Probe (Quota/phiên) | Mode ghi nhận |
|---|---|---|---|
| **Hồi phục Nấc 1 (Tier 1)** | `clean_days < 1` (Ca đầu tiên sau cooldown) | 2 – 4 follows | `probation_tier1` |
| **Hồi phục Nấc 2 (Tier 2)** | `clean_days == 1` (Ca thứ hai sau cooldown) | 6 – 8 follows | `probation_tier2` |
| **Tốt nghiệp (Graduated)** | `clean_days >= 2` | 10 – 15 follows (Full quota) | `full` |

### Quy tắc chuyển trạng thái & Xử lý State:
1. **Roll-Day Transition:** Khi qua ngày mới (`_roll_day()`), nếu ngày trước có chạy sạch và không bị lỗi (`recovered_date < today`), tăng `clean_days += 1`.
2. **State Cleanup khi Graduate (Bắt buộc):** Khi `clean_days >= probation_graduation_clean_days`:
   - Gán `graduated = True`, `fail_streak = 0`.
   - **BẮT BUỘC POP `probation_clean_days`:** `self._data.pop("probation_clean_days", None)`. Không được giữ lại số đếm cũ trong state json để tránh làm lệch phân tầng khi tài khoản tái nhập cữ thử thách sau này.
   - Ghi nhận Telemetry event: `self._data["last_graduation_event"] = {"clean_days": clean_days, "graduated_at": ..., "machine": ..., "row": ...}`.
3. **Revocation khi tái phạm (`set_follow_failed()`):**
   - Hễ bị nhả follow hoặc lỗi hành động (`follow_failed = True`): Lập tức thu hồi tốt nghiệp (`self._data.pop("graduated", None)`), `fail_streak += 1`, `probation_clean_days = 0`.
   - Khi hết thời gian phạt cooldown, tài khoản quay trở lại đúng Hồi phục Nấc 1 (`[2, 4]` follows).

---

## 3. Cấu hình Hóa (Config-Driven Parameters — Tránh Magic Numbers)

Không được hardcode magic number 2 hay 1 trong logic `_roll_day()` hay `session_budget()`. Phải khai báo trong `FollowConfig`:

```python
@dataclass
class FollowConfig:
    # ...
    probation_graduation_clean_days: int = 2
    probation_tier1_clean_days: int = 1
```

### Validation Invariant:
Trong hàm `validate(cfg)`:
```python
if validate_follow and (int(cfg.probation_graduation_clean_days) < 1
                        or int(cfg.probation_tier1_clean_days) < 1):
    errs.append("probation_graduation_clean_days/probation_tier1_clean_days phải >= 1")
```
- Ngưỡng cấu hình tối thiểu là `1` (biên: tốt nghiệp ngay sau 1 ca sạch).
- Chặn đứng cấu hình `<= 0` bằng `ConfigError`.

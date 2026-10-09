# Quy Chuẩn Báo Cáo Nhả Follow & Cấu Hình Ngân Sách An Toàn (Safe Follow Budget)

## 1. Quy Chuẩn Format Báo Cáo Phân Nhóm Nhả Follow (User Format Standard)

### Vấn đề gặp phải & Phản hồi của User
Trước đây, định dạng báo cáo nhả follow hiển thị số lượng máy và số lượt follow cạnh nhau không rõ ràng:
> `    - 5 - 9 lượt (1): 18 (6 lượt)`  *(User khó hiểu: (1) là 1 lượt hay 1 máy? 18 và 6 lượt nghĩa là gì?)*

### Định dạng chuẩn bắt buộc (Đã áp dụng vào `feed_session_watchdog.py`)
Mọi báo cáo tổng kết phiên lướt feed & follow chéo BẮT BUỘC tuân thủ:
1. **Số lượng máy:** Bắt buộc có chữ **"máy"** rõ ràng trong ngoặc đơn: `(N máy)`.
2. **Định danh máy:** Bắt buộc có tiền tố **"M"** trước số máy (`M14`, `M18`, `M36`...).
3. **Số lượt follow đã thực hiện:** Ghi rõ `(N lượt)` sau mỗi mã máy.

```text
• Follow chéo (<total> lượt follow):
  + Success (<n> máy hoàn thành OK): M3, M5, M8, M16, M22, M23...
  + Nhả follow (<n> máy):
    - Nhả liền (0 lượt - <n0> máy): M1, M7, M10, M11, M13, M17...
    - 1 - 4 lượt (<n1> máy): M14 (1 lượt), M15 (1 lượt), M28 (3 lượt)...
    - 5 - 9 lượt (<n2> máy): M4 (7 lượt), M9 (7 lượt), M36 (9 lượt)...
    - 10+ lượt (<n3> máy): M2 (19 lượt), M6 (16 lượt), M21 (24 lượt)...
  + Lỗi script/xác minh (<n> máy): ...
  + Bỏ qua (<n> máy): ...
```

### Hàm Format Chuẩn trong Python
```python
def format_released_follows(fl_released: list, all_follows: dict) -> list:
    if not fl_released:
        return ["  + Nhả follow (0 máy): Không có"]

    def _format_m(m: Any) -> str:
        s = str(m).strip()
        return f"M{s[1:]}" if s.upper().startswith("M") else f"M{s}"

    # ... gom vào rel_0, rel_1_4, rel_5_9, rel_10_plus ...
    lines = [f"  + Nhả follow ({len(fl_released)} máy):"]
    if rel_0:
        lines.append(f"    - Nhả liền (0 lượt - {len(rel_0)} máy): {', '.join(_format_m(m) for m in rel_0)}")
    if rel_1_4:
        lines.append(f"    - 1 - 4 lượt ({len(rel_1_4)} máy): {', '.join(f'{_format_m(m)} ({cnt} lượt)' for m, cnt in rel_1_4)}")
    if rel_5_9:
        lines.append(f"    - 5 - 9 lượt ({len(rel_5_9)} máy): {', '.join(f'{_format_m(m)} ({cnt} lượt)' for m, cnt in rel_5_9)}")
    if rel_10_plus:
        lines.append(f"    - 10+ lượt ({len(rel_10_plus)} máy): {', '.join(f'{_format_m(m)} ({cnt} lượt)' for m, cnt in rel_10_plus)}")
    return lines
```

---

## 2. Cấu Hình Ngân Sách Follow An Toàn (Chốt 07/09/2026)

### Thông số kỹ thuật (`D:/Taadaa/tiktok-follow/follow_runner/core/config.py`)
- `budget_per_day`: **35** lượt/ngày/máy (cũ: 45).
- `budget_per_session`: **12** lượt/phiên (cũ: 15).
- `budget_per_session_min`: **9** lượt/phiên (cũ: 12).
- `budget_per_session_max`: **12** lượt/phiên (cũ: 15).
- Mỗi phiên hệ thống bốc ngẫu nhiên ngân sách trong dải **[9, 10, 11, 12]**.

### Cơ sở kỹ thuật & Động thái thuật toán TikTok
1. **Trần rolling 24h của TikTok:** Ngưỡng kiểm duyệt follow cứng của TikTok là khoảng 45–50 follow/24h.
2. **Nguyên nhân dính cờ ở cấu hình cũ:**
   - 1 ca chạy 3 phiên nuôi nick. Nếu set 12–15 follow/phiên $\to$ sau 3 phiên, nick tích lũy 38–45 lượt follow, chạm sát mép trần 50.
   - Phiên 3 thường xuyên bị TikTok khóa nút follow giữa chừng, kết thúc bằng `FOLLOW_FAILED` và tăng `fail_streak`.
3. **Lợi ích khi hạ về 35/ngày (9–12/phiên):**
   - Tạo khoảng đệm an toàn **15 lượt** dưới ngưỡng rate-limit cứng.
   - Nick hoàn thành đủ chỉ tiêu và chủ động dừng ở trạng thái `status: OK` thay vì bị TikTok cưỡng chế chặn nút.
   - Giữ trust score cao: Tỷ lệ hồi phục mượt sau 48h (chạy tiếp ở chu kỳ sau không bị nhả liền) đạt **> 75%**.

---

## 3. Tương Tác Giữa Watchdog Báo Cáo & Cơ Chế Farm Alert (Case 142)

Khi Watchdog báo cáo phiên có máy lỗi (ví dụ 8 máy fail feed), tại sao kênh **Farm Alert** không réo chuông?

1. **Chặn còi đơn lẻ giữa chừng (`alerts.py`):**
   - Biến môi trường mặc định: `AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT="0"`.
   - Hàm `send_farm_machine_alert` tự động chặn (suppress) các thông báo lỗi đơn lẻ phát sinh trong lúc batch đang chạy để tránh làm kiệt sức người vận hành (Alert Fatigue).
2. **Ngưỡng kép kích hoạt Farm Alert cuối batch (`batch_aggregator.py`):**
   - Chỉ kích hoạt Farm Alert khi có **Lỗi hệ thống (Systemic Failure)** thỏa mãn đồng thời:
     $$\text{Tỷ lệ lỗi cùng mã (Signature)} \ge 10\% - 15\% \text{ tổng máy} \quad \text{VÀ} \quad \ge 3 \text{ máy cùng bị dính}$$
3. **Lỗi vãng lai (Sporadic / Transient Errors):**
   - Nếu 8 máy bị 8 lỗi khác nhau (như M3 kẹt login, M25 lag focus, M30 tuột cáp ADB, M58 dính popup lạ...), không lỗi nào chạm ngưỡng $\ge 3$ máy $\to$ Hệ thống **im lặng hoàn toàn (Silent Skip)**.
   - Máy tự động về Home, nhả lock để vòng sau chạy tiếp, kết quả chỉ được tổng hợp trên báo cáo watchdog của Hermes, không làm gián đoạn kênh còi báo động.

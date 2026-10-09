# Case UI-58: Khắc Phục Lỗi follow-timeout Do Thiếu Config Riêng Rơi Vào Default 1200s & Ngưỡng Soft Deadline 120s Quá Hẹp (Máy 40 charakrh768)

## 1. Hiện trường sự cố
- **Alert:** `[FARM ALERT: MÁY 40] DỪNG PHIÊN`
- **Quy trình:** Follow TikTok (`tiktok-follow`) tại `D:/Taadaa/tiktok-follow`
- **Thiết bị:** Máy 40 | Serial: `ce0418244d10342502` | Nick: `charakrh768` | Ca: Row 1
- **Triệu chứng:** `follow-timeout`
- **Hiện trường UI:** TikTok đang dừng ở Home Feed (Tab Đề xuất, có widget quà tặng, video đang chạy bình thường).

---

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lệch cấu hình Deadline giữa tiến trình cha và engine con:**
   - Tiến trình cha (`multi_machine_feed_session.py` -> `_run_follow_hook`) áp dụng hard timeout `subprocess.run(timeout=1200)`.
   - Máy 40 thiếu file cấu hình riêng (`config/machine40.yaml`), do đó runner rơi vào fallback đọc cấu hình default với `feed_timeout_seconds: 1200.0`.
2. **Ngưỡng đệm an toàn `reserve_seconds` quá hẹp:**
   - Trong `FollowEngine.has_time_for_next_action(reserve_seconds=120.0)`, thời gian đệm chỉ là 120s.
   - Khi mạng/proxy trễ hoặc các chu kỳ follow kéo dài 60–90s (thực tế log Máy 40 ghi nhận khoảng trễ tới 409s giữa 2 lượt follow), tại giây 1050 (thời gian còn lại ~150s > 120s), engine tiếp tục nhận thêm 1 tài khoản mới.
   - Lượt follow này vượt qua mốc 1200s trước khi quay lại đầu vòng lặp, khiến tiến trình cha kill timeout đột ngột và báo lỗi giả `follow-timeout`.

---

## 3. Giải pháp chuẩn hóa (Case Fix)
1. **Bổ sung file cấu hình máy riêng:**
   - Tạo `config/machine40.yaml` với cấu hình chuẩn farm: `machine: 40`, `serial: "ce0418244d10342502"`, `feed_timeout_seconds: 90`.
2. **Nâng ngưỡng an toàn `reserve_seconds` lên 180.0s:**
   - `follow_runner/flows/follow_engine.py`: Default `has_time_for_next_action(self, reserve_seconds: float = 180.0)` và soft-deadline check trước khi switch sang Mode 1 (`reserve_seconds=180.0`).
   - `follow_runner/flows/mode1_search_follow.py`: Các điểm kiểm tra soft-deadline trong vòng lặp search follow chuyển sang `reserve_seconds=180.0`.
   - `follow_runner/flows/mode2_follow_followers.py`: Kiểm tra trước vòng lặp anchor, anchor retry, scroll follower list, và follower row loop chuyển sang `reserve_seconds=180.0`.
3. **Chủ động dừng sạch:**
   - Khi thời gian còn lại < 180s, runner chủ động break vòng lặp, hoàn tất sạch với `status: "OK"` và emit `FOLLOW_RESULT` JSON trước khi tiến trình cha kill subprocess.

---

## 4. Quy trình Canary kiểm chứng
```powershell
powershell.exe -ExecutionPolicy Bypass -File D:/Taadaa/tiktok-follow/scripts/run-follow.ps1 -Machine 40 -AccountRowIndex 1 -Config config/machine40.yaml -ForcePreempt
```
- Kết quả: Exit code `0`, `status: "OK"`, `failed: false`, `follow_failed: false`.

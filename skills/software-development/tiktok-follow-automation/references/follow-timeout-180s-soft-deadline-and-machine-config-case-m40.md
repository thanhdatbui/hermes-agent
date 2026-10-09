# Case M40: Follow-Timeout do Thiếu Config Máy & Ngưỡng Soft Deadline 180s (2026-09-07)

## 1. Hiện trường sự cố Máy 40
- **Alert:** `[FARM ALERT: MÁY 40] DỪNG PHIÊN • Quy trình: Follow TikTok (tiktok-follow) • Máy: 40 | Serial: ce0418244d10342502 | Nick: charakrh768 • Triệu chứng: follow-timeout`
- **Hiện trường:** TikTok dừng ở Home Feed (Tab *Đề xuất*, video đang chạy kèm widget quà tặng). Tiến trình mẹ `multi_machine_feed_session.py` ghi nhận `status: "timeout"`, `reason: "follow-timeout"`, `failed: 1`.

## 2. Phân tích nguyên nhân gốc rễ (Root Cause)
1. **Khoảng trễ mạng/proxy bất thường:**
   - Trong run `20260907-012517`, Máy 40 follow thành công 8 nick (`minh.anhhhh85` → `anhdo829`) từ `00:44:25` đến `00:47:14 UTC`.
   - Giữa nick `anhdo829` và `ngohuong3008`, proxy/mạng bị nghẽn làm trễ gần 7 phút (409s).
2. **Biên thời gian an toàn 120s không đủ:**
   - Hàm `FollowEngine.has_time_for_next_action(reserve_seconds=120.0)` trước đây sử dụng mốc 120 giây.
   - Khi thời gian còn lại xấp xỉ ~150s (> 120s), engine tiếp tục nhận thêm 1 tài khoản (`an673231` lúc `00:58:42`). Thao tác follow, reload profile và kiểm tra relation kéo dài quá 30 giây, vượt qua mốc 1200s (`subprocess.run(timeout=1200)` của tiến trình cha).
   - Tiến trình cha ngắt đột ngột bằng `subprocess.TimeoutExpired` trước khi engine kịp kết thúc vòng lặp để dọn dẹp và in structured `FOLLOW_RESULT`.
3. **Thiếu file `config/machine40.yaml`:**
   - Máy 40 chưa có file config riêng trong `config/`, runner rơi vào fallback đọc cấu hình mặc định với `feed_timeout_seconds: 1200`.

## 3. Giải pháp khắc phục (Standard Fix)
1. **Nâng `reserve_seconds = 180.0`:**
   - Trong `follow_runner/flows/follow_engine.py`:
     - `def has_time_for_next_action(self, reserve_seconds: float = 180.0) -> bool:`
     - Soft deadline check trước khi chuyển sang Mode 1: `reserve_seconds=180.0`.
   - Trong `follow_runner/flows/mode1_search_follow.py`:
     - Vòng lặp UID chính: `has_time(reserve_seconds=180.0)`.
     - Vòng lặp retry: `has_time_for_next_action(reserve_seconds=180.0)`.
   - Trong `follow_runner/flows/mode2_follow_followers.py`:
     - Vòng lặp anchor: `has_time_for_next_action(reserve_seconds=180.0)`.
     - Vòng lặp follower list scroll: `has_time_for_next_action(reserve_seconds=180.0)`.
2. **Bổ sung `config/machine40.yaml`:**
   - Tạo file `config/machine40.yaml` chuẩn hóa `machine: 40`, `serial: "ce0418244d10342502"`, `feed_timeout_seconds: 90`.

## 4. Kiểm chứng hồi quy (Verification)
- Focused test:
  ```bash
  PYTHONPATH="D:/Taadaa/tiktok-follow;D:/Taadaa/automation-core" /d/Taadaa/python-envs/automation/Scripts/pytest -p no:cacheprovider follow_runner/tests/ -k "time_for_next_action or soft_deadline"
  ```
  Kết quả: 3 passed, 528 deselected.

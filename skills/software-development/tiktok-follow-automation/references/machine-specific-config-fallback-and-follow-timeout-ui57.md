# Case UI-57: Machine-Specific Config Fallback, State O(1) Triage & Follow-Timeout Soft Deadline

## Triệu chứng & Bối cảnh Sự cố
- **Farm Alert:** `[FARM ALERT MÁY <M>]: • Triệu chứng: follow-timeout • Hiện trường: Màn hình TikTok đang ở Home Feed (Tab Đề xuất, video đang chạy)`.
- **Parent Process Hook:** Trong `multi_machine_feed_session.py`, `_run_follow_hook` spawn `follow_runner/run_follow.py` với hard timeout `follow_timeout_seconds: 1200.0`. Khi quá 1200s, `subprocess.TimeoutExpired` bắt được, kill tiến trình con và xuất `follow_result.json` với `status: "timeout", reason: "follow-timeout", failed: 1`.

## Triage Nhanh O(1)
1. **Không quét đĩa đệ quy toàn bộ `runtime/`:**
   - Liệt kê ca chạy gần nhất: `ls -td /d/Taadaa/runtime/kibe/live/<date>/row-*/* /machines/machine_<N> | head -n 3`.
   - Đọc trực tiếp `follow_result.json` và dòng `follow-hook` bắt đầu trong `log.jsonl`.
2. **Kiểm tra State File trên Đĩa (O(1)):**
   - Đọc `D:/Taadaa/tiktok-follow/runs/state/follow_state_<M>_row_<slot>.json`.
   - Xem các timestamp follow trong ngày hôm nay:
     - So sánh thời điểm follow cuối cùng với thời điểm start của hook (`00:39:12` -> follow cuối `00:58:42`).
     - Phát hiện các khoảng trễ lớn giữa các lượt follow (ví dụ: khoảng trễ 5-7 phút do mạng/proxy xoay IP hoặc TikTok re-render chậm).

## Root Cause
1. **Thiếu file cấu hình riêng cho máy (`config/machine<M>.yaml`):**
   - Các máy trong farm cấu hình `feed_timeout_seconds: 90` (hoặc ngưỡng an toàn tương ứng).
   - Khi thiếu `config/machine<M>.yaml`, tiến trình con fallback về `config.example.yaml` mang `feed_timeout_seconds: 1200` — trùng khít với trần timeout cứng 1200s của tiến trình cha.
2. **Biên an toàn `reserve_seconds` không bù đủ độ trễ mạng:**
   - Trong `FollowEngine.has_time_for_next_action(reserve_seconds=120.0)`, điều kiện `remaining > reserve_seconds` chỉ kiểm tra ở đầu mỗi vòng lặp.
   - Khi thời gian còn lại xấp xỉ ~150s (vẫn > 120s), engine chấp nhận tiếp tục follow tài khoản kế tiếp. Nếu lượt follow đó gặp trễ mạng, xác thực quan hệ, giải quyết popup hoặc chờ settling animation kéo dài > 150s, tiến trình con sẽ chạm trần 1200s và bị cha ngắt cưỡng bức trước khi kịp hoàn tất sạch (`status: "OK"`).

## Khắc phục Chuẩn (Fix Pattern)
1. **Đồng bộ file config máy:**
   - Đảm bảo `config/machine<M>.yaml` tồn tại cho toàn bộ các máy chạy follow, tránh fallback về `config.example.yaml` mang trần 1200s.
2. **Nâng `reserve_seconds` và kiểm tra fine-grained:**
   - Nâng `reserve_seconds` lên mức an toàn (ví dụ: `180.0s` - `240.0s`) trong `follow_engine.py` và các luồng follow Mode 1 / Mode 2.
   - Đặt `has_time_for_next_action` trước các bước tốn thời gian (như reload profile, chuyển đổi anchor) để dừng chủ động trả về `status: "OK"` với số nick đã follow thành công, bảo toàn kết quả phiên.

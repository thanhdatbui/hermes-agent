# RCA: Turn Lockup Prevention & Prompt Misattribution (20/10/2026)

## 1. Sự cố Turn Lockup (Treo Bong Bóng "Working..." hơn 1 tiếng)
- **Hiện tượng:** Lúc 17:57, User nhắn lệnh *"K. Cho chạy cả ngày cx đc nhưng né h reboot ra"*. Bot Hermes không phản hồi tin nhắn văn bản mà kẹt trong chuỗi 26 vòng lặp nội bộ (iteration 8/200 -> 26/200) tới tận 19:20 mới nhả tin nhắn đầu tiên. Trên giao diện Telegram, User chỉ thấy bong bóng `Working...` xoay tít suốt 70+ phút.
- **Nguyên nhân cốt lõi:**
  1. *Lỗi Guard vi phạm liên hoàn:* Coordinator gọi `delegate_task` bị Coordinator Guard chặn liên tiếp do sai cú pháp hợp đồng (`MISSING_TASK_KIND`, `MULTI_FILE_VIOLATION`, `ANCHOR_NOT_FOUND`, `OLD_EQUALS_NEW`).
  2. *Ôm Turn không nhả tin nhắn (Hoarding Turns):* Sau khi chuyển sang `dispatch_worker.py` chạy ngầm, Coordinator không kết thúc turn để gửi tin nhắn xác nhận cho User, mà tiếp tục gọi thêm worker thứ 2 để viết test.
  3. *Quy chuẩn Bắt Buộc:* Khi bắt đầu tác vụ điều phối worker hoặc chạy lệnh ngầm, Coordinator **BẮT BUỘC phải nhả lời nhắn ngay lập tức** (xác nhận tiếp nhận và báo worker đang thi công), kết thúc turn để Telegram không bị kẹt ở trạng thái `Working...`.

## 2. Bẫy Hiểu Sai Ngữ Cảnh Người Dùng (Context Misattribution Trap)
- **Hiện tượng:** Lúc 19:06, User nhắn *"lí do treo? hơn 1 tiếng r"*. Ý của User là *"Tại sao bot Hermes lại đơ hơn 1 tiếng không trả lời tao?"*.
- **Sai lầm của Coordinator:** Coordinator không kiểm tra độ trễ phiên của chính mình, mà nhảy ngay vào quét process cây tiến trình máy farm (`run-feed-session.ps1` PID 17964) rồi giải thích vòng vo: *"Lý do treo đã rõ: không phải cron reboot... tiến trình bị treo là feed session"*, gây ức chế tột độ cho User.
- **Quy tắc giải mã phản ánh:** Khi User nói "sao treo", "sao không trả lời", "hơn 1 tiếng rồi":
  1. Đầu tiên phải đối soát ngay tin nhắn trước đó của User và thời gian bot phản hồi (bot latency).
  2. Thừa nhận và giải thích sự cố nội bộ của Agent trước, tuyệt đối không vội vàng đổ lỗi sang các tiến trình ngoại vi của Farm.

## 3. Quy chuẩn né giờ Reboot cho tác vụ 24/7 (Reboot Blackout Buffers)
- Các cronjob chạy cả ngày (e.g. `night-tiktok-2fa-watchdog` schedule `*/15 * * * *`) bắt buộc phải bọc cửa sổ bảo vệ quanh 3 ca reboot cố định:
  - Ca 1: **05:20** -> Blackout: **05:05 - 05:35**
  - Ca 2: **11:20** -> Blackout: **11:05 - 11:35**
  - Ca 3: **17:20** -> Blackout: **17:05 - 17:35**
- Buffer đệm tối thiểu 15 phút trước và sau giờ reboot để đảm bảo không tiến trình nào giữ `device-locks` khiến script reboot bị `[SKIP]`.

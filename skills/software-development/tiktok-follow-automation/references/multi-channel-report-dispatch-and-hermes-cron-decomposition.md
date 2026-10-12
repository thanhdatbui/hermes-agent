# Multi-Channel Report Dispatch & Hermes Cron Decomposition

## Vấn Đề Thực Tế (Anti-Pattern: Silent Asymmetric Drop)
Khi một ca chạy máy farm kết hợp nhiều tác vụ (Lướt Feed, Follow chéo, Upload Video) nhưng cần gửi báo cáo về các nhóm Telegram độc lập:
- Nhóm Lướt Feed: `telegram:-5377611430`
- Nhóm Follow chéo: `telegram:-5127276494`
- Nhóm Upload Video: `telegram:-5435853713`

Nếu dùng 1 cronjob duy nhất với script watchdog tự bóc tách chuỗi (`dispatch_split_reports`) rồi tự gọi `urllib.request.urlopen` bắn sang các chat phụ, sẽ xảy ra lỗi bất đối xứng nghiêm trọng:
1. **Lệch cơ chế bảo đảm (Asymmetric Transport):**
   - Nội dung trả về `stdout` được Hermes Cron Engine bắt và chuyển qua Hermes Telegram Gateway (có persistent connection, queue, retry tự động) $\rightarrow$ luôn gửi thành công về chat chính.
   - Nội dung bắn qua `urllib` dùng socket HTTP ephemeral trần trong tiến trình con $\rightarrow$ dễ bị timeout, DNS flake hoặc lag mạng chớp nhoáng dẫn đến lỗi.
2. **Nuốt lỗi âm thầm (Silent State Claim):**
   - Đoạn gửi `urllib` thường được bọc trong `try...except Exception: logger.warning(...)` để tránh crash script.
   - Khi chat phụ fail, script vẫn tiếp tục ghi nhận `session_key` vào `feed_session_reported.json` và in phần feed ra stdout rồi exit 0.
   - Hậu quả: Nhóm feed nhận được tin, nhóm follow mất tin vĩnh viễn, người dùng thấy vô lý vì "cùng 1 ca chạy mà bên có bên không".

---

## Giải Pháp Chuẩn Kiến Trúc (Architecture Best Practice)

### Phương án 1: Tách riêng từng Cronjob Hermes (Ưu tiên số 1)
Thay vì nhồi nhét 1 script watchdog gánh nhiều kênh:
1. Tách thành các watchdog độc lập có phạm vi trách nhiệm duy nhất (Single Responsibility):
   - `tiktok-feed-session-watchdog`: Chỉ đọc kết quả lướt feed $\rightarrow$ in stdout $\rightarrow$ `deliver: telegram:-5377611430`.
   - `tiktok-follow-session-watchdog`: Chỉ đọc `follow_result.json` và phân loại follow $\rightarrow$ in stdout $\rightarrow$ `deliver: telegram:-5127276494`.
2. **Lợi ích:**
   - 100% tin nhắn đi qua Hermes Core Gateway chính thống, hưởng trọn retry và delivery guarantee.
   - Trạng thái độc lập: Nếu follow lỗi thì chỉ watchdog follow retry hoặc alert đỏ, không làm ảnh hưởng đến feed.
   - Giám sát chuẩn: Từng cronjob có telemetry, last_status, last_error riêng trên dashboard Hermes.

### Phương án 2: Fail-Closed & Fallback Consolidate (Khi bắt buộc giữ 1 script)
Nếu chưa kịp tách cronjob:
1. **Tuyệt đối cấm nuốt exception:** Nếu `urllib` gửi kênh phụ thất bại sau 3 lần retry:
   - **CẤM** claim state (`new_reported.add(session_key)`).
   - **Fallback gộp tin:** Tự động append block Follow trở lại vào `feed_p` để in ra `stdout` gửi chung vào nhóm chính, kèm cảnh báo `[FALLBACK_DISPATCH]`, không để mất dữ liệu.
   - Hoặc raise exception (exit != 0) để Hermes Cron giữ nguyên nhịp retry ở lần chạy kế tiếp.

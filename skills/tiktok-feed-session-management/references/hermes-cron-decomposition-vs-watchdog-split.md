# Hermes Cron Decomposition vs Watchdog In-Script Split

## Bối Cảnh & Sự Cố (Root Cause Analysis)
Khi hệ thống TikTok Farm gộp chung nhiều mục tiêu vào 1 lần chạy (Lướt Feed, Follow chéo, Upload Video) nhưng người dùng muốn nhận báo cáo ở các kênh Telegram riêng biệt:
- **Tiktok Luot Nuoi Acc**: `-5377611430`
- **Tiktok Follow**: `-5127276494`
- **Tiktok Video**: `-5435853713`

### Anti-Pattern: In-Script String Split (`dispatch_split_reports`)
Script watchdog nhận toàn bộ kết quả, tự split string thành 3 block:
1. Block Lướt Feed được trả về qua `stdout`.
2. Block Follow và Video được script tự gửi ngầm qua `urllib.request.urlopen` với `try...except Exception: logger.warning(...)`.

### Hậu Quả Chí Mạng:
- **Lệch cơ chế bảo đảm (Asymmetric Transport):** `stdout` được Hermes Cron Scheduler bắt và gửi qua Hermes Telegram Gateway (bền vững, có retry daemon), còn cuộc gọi `urllib` của script là ephemeral socket trần. Khi gặp lag mạng/DNS, cuộc gọi `urllib` thất bại.
- **Silent Failure & State Corruption:** Khối `try...except` nuốt lỗi để script không crash, dẫn đến script exit 0. Hermes scheduler tưởng thành công nên gửi Lướt Feed bình thường, đồng thời watchdog ghi nhận session đã hoàn tất (`feed_session_reported.json`). Kết quả: Nhóm Lướt Feed có tin, nhóm Follow mất tin vĩnh viễn và không bao giờ được gửi lại.

---

## Kiến Trúc Chuẩn (Architectural Standards)

### 1. Nguyên Tắc Phân Rã Cronjob Hermes (Decomposed Hermes Cron)
Không dồn toàn bộ trách nhiệm phân phối tin nhắn vào một script nguyên khối:
- **Tách riêng các Watchdog độc lập:**
  - `feed_session_watchdog.py`: Chỉ tổng hợp Lướt Feed $\rightarrow$ in stdout $\rightarrow$ `deliver: telegram:-5377611430`.
  - `follow_session_watchdog.py`: Chỉ tổng hợp Follow chéo $\rightarrow$ in stdout $\rightarrow$ `deliver: telegram:-5127276494`.
  - `upload_session_watchdog.py`: Chỉ tổng hợp Upload Video $\rightarrow$ in stdout $\rightarrow$ `deliver: telegram:-5435853713`.
- **Lợi ích:**
  - Tận dụng 100% hạ tầng Hermes Core Gateway với queue, retry, and connection pooling.
  - Phân lập sự cố: Lỗi ở tác vụ Follow không làm hỏng hoặc nuốt tin của Feed/Upload.
  - Giám sát rõ ràng: Từng cronjob có trạng thái `last_run_at`, `last_status`, và alert đỏ độc lập.

### 2. Kỷ Luật Fail-Closed Cho Watchdog (Nếu Duy Trì Single Script)
Nếu chưa kịp tách cronjob:
- **CẤM nuốt lỗi:** Nếu dispatch kênh phụ qua `urllib` thất bại sau 3 lần retry:
  - CẤM commit `session_key` vào `feed_session_reported.json`.
  - Raise exception (exit != 0) để Hermes Cron ghi nhận lỗi và kích hoạt nhịp chạy tiếp theo.
- **Fallback Consolidate:** Tự động append nội dung Follow/Upload bị rớt ngược trở lại vào `feed_p` để in ra stdout chung, đảm bảo dữ liệu không bị thất lạc trong bóng tối.

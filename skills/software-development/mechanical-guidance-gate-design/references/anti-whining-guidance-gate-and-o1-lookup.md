# Hội Chẩn 3 Bên: Kiến Trúc Action Mandate O(1), Chống Veto Gate Câm & Tra Cứu Kênh O(1)

## 1. Bài Học Thực Tế Từ Sự Cố 37 Tool Calls
- Khi nhận task "chuẩn hoá kênh @username", Coordinator không có công cụ tra cứu $O(1)$ nên theo quán tính gọi `search_files` quét đĩa.
- Bị `GUARD_SEARCH_FILES_ROOT` chặn câm (`exit 1` không có lệnh thay thế), Coordinator rơi vào khoảng trống nhận thức: tự đi đường vòng bằng cách đọc Excel `Tik*.xlsx`, bốc video, trích xuất thumbnail và gọi `browser_vision` soi mắt từng frame.
- Hậu quả: Đốt 37 tool calls / 9 phút, phình to context và kích hoạt context compression.

## 2. Giải Pháp Triệt Để: Công Cụ Tra Cứu Canonical O(1)
- Tái sử dụng công cụ tập trung:
  `python D:/Taadaa/tools/lookup_channel.py --username <username>` (hoặc `--machine <M> --slot <S>`)
- Trả về JSON $O(1)$ (< 50ms) từ SQLite `tiktok_tracker.db` và công thức toán học hoán vị folder:
  - Máy, slot, workbook Tik
  - Folder render (`F_vid`) và folder video gốc (`F_src`)
  - Serial ADB, niche, stats hiện tại
- CẤM TUYỆT ĐỐI tự viết script Python quét đĩa, cấm mở Excel thủ công đối chiếu khi đã có `lookup_channel.py`.

## 3. Quy Chuẩn Action Mandate O(1) Cho Mọi Gate (Đồng Thuận 3 Bên)
- **Cấm Veto Gate câm:** Mọi exit code khác 0 từ Gate bắt buộc phải có `REQUIRED_ACTION_O1` kèm lệnh copy-paste chạy ngay và trường `guidance` (hướng dẫn kiến trúc).
- **Chống Self-Bypass:** Lệnh thay thế không bao giờ được chứa cờ tắt gate (`--force`, `--skip-test`, `--no-verify`). Nó chỉ được trỏ tới:
  1. Lệnh thu hẹp scope đúng chuẩn.
  2. Lệnh sinh evidence còn thiếu (focused test, inspect).
  3. Lệnh chuyển sang fast-path canonical (`lookup_channel.py`).
- **Auto-Quarantine O(1):** Gate chặn code tự động chạy `git stash` cách ly hunk vi phạm, giữ repo luôn sạch sẽ.

## 4. Xử Lý Strike 3: Guidance Gap (Không Khóc Lóc Quan Liêu)
- Nếu vi phạm 3 lần liên tiếp: Xác định đây là **HƯỚNG DẪN CỦA GUARD CHƯA ĐỦ ĐẦY ĐỦ/RÕ RÀNG (STRIKE-3-GUIDANCE-GAP)** khiến Agent đâm đầu vào ngõ cụt.
- **Hành vi hợp lệ:** Báo cáo User để nhận chỉ thị:
  1. Tóm tắt vấn đề và 3 cách Agent đã thử bị Guard chặn.
  2. Nêu rõ: Guard đang thiếu chỉ dẫn kiến trúc cho trường hợp này.
  3. Chờ User ra lệnh: User chỉ đạo hướng đi mới hoặc chỉ thị Agent sửa/bổ sung rule vào Guard.
  4. SẴN SÀNG NHẬN LỆNH: Giữ repo sạch và chờ lệnh User để tiếp tục thi công, cấm buông xuôi đóng phiên hoặc mở ticket JSON ngồi chờ.

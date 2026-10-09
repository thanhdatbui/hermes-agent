# TikTok Farm Account Tracker Pattern

Tài liệu hướng dẫn và pattern theo dõi tài khoản TikTok farm (`tiktok_account_tracker.py` tại `D:/Taadaa/tools/tiktok_account_tracker.py`).

## 1. Mục đích & Nguyên lý hoạt động
- Theo dõi định kỳ toàn bộ tài khoản TikTok trên phone farm từ workbook nguồn:
  - `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (hoặc fallback `D:/Taadaa/tiktok-luot nuoi acc/data/taikhoan_run_safe.xlsx`).
- Không dùng tài khoản hay login trên máy, quét trực tiếp public web profile `https://www.tiktok.com/@{username}` bằng Mobile Safari User-Agent.
- Trích xuất dữ liệu từ JSON nhúng trong tag:
  `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">`
  Đọc `data['__DEFAULT_SCOPE__']['webapp.user-detail']`:
  - `statusCode == 10221` hoặc thiếu `userInfo` -> tài khoản bị `NOT_FOUND` / `DIE`.
  - Hợp lệ -> lấy UID (`user.id`), nickname, secUid, follower, heart, video, status `LIVE`.

## 2. Lưu trữ Snapshot & Tính Delta (SQLite)
- Lưu trữ vào bảng `snapshots` (timestamp, username, uid, follower, following, heart, video, status) tại `D:/Taadaa/data/tiktok_tracker.db`.
- Tự động đối chiếu với snapshot gần nhất trước đó của user để tính:
  - `follower_delta = current_follower - prev_follower`
  - `heart_delta = current_heart - prev_heart`
  - `video_delta = current_video - prev_video`
  - `trending = True` nếu `follower_delta >= 10` hoặc `heart_delta >= 50` (cắn đề xuất).

## 3. Xuất Báo Cáo & Tóm Tắt
- Xuất file Excel (`D:/Taadaa/reports/tiktok_tracker_report.xlsx`) gồm 12 cột:
  `Máy, Username, Tên hiển thị, UID, Follower, Tăng Follow, Tổng Like, Tăng Like, Số Video, Trạng Thái, Cắn Đề Xuất, Cập Nhật`.
- Tóm tắt format hiển thị/báo Telegram:
  - Tổng số nick quét, Số nick LIVE, Số nick DIE/NOT FOUND, Tổng follower toàn farm.
  - Danh sách top nick cắn đề xuất (+follower, +like).

## 4. Kiểm thử & Mocks
- File test: `D:/Taadaa/tools/test_tiktok_account_tracker.py`.
- 100% Mocked: mock HTML rehydration payload, mock status 10221, SQLite `:memory:`, openpyxl test file.
- Thời gian chạy pytest: < 1.0s.

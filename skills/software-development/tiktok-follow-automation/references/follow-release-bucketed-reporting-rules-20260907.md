# Quy Chuẩn Báo Cáo Phân Nhóm Nhả Follow (User Chốt 2026-09-07)

## 1. Yêu Cầu Bắt Buộc Của Người Dùng
Khi người dùng hỏi về tình trạng máy bị nhả follow hoặc trong báo cáo tổng kết phiên của Watchdog (`feed_session_watchdog.py`), **TUYỆT ĐỐI CẤM** liệt kê danh sách phẳng một loạt số máy (`+ Nhả follow (47): 1, 2, 4, 6...`).
**BẮT BUỘC** phải phân loại thành các nhóm cụ thể dựa trên số lượt follow hoàn thành trước khi bị nhả:

- **Nhóm 1: Nhả liền (0 lượt)** — Vừa bấm follow anchor/target đầu tiên và reload profile thì đã bị nhả ngay (không lên được lượt nào). Thường do nick bị shadowban / action-block tích lũy từ chu kỳ trước hoặc trust score quá yếu.
- **Nhóm 2: 1 – 4 lượt** — Vừa tương tác được vài lượt thì bị TikTok bóp rate-limit ngay. Kèm số lượt cụ thể từng máy: `14 (1 lượt), 15 (1 lượt), 28 (3 lượt)...`
- **Nhóm 3: 5 – 9 lượt** — Đã hoàn thành được khoảng nửa chỉ tiêu phiên trước khi nhả: `4 (7 lượt), 9 (7 lượt), 36 (9 lượt)...`
- **Nhóm 4: 10+ lượt** — Nick trust score cao, chạy bền gần trọn phiên hoặc chạm ngưỡng trần tần suất ngày của TikTok: `2 (19 lượt), 6 (16 lượt), 29 (27 lượt)...`

## 2. Chuẩn Format Báo Cáo Watchdog & Agent
```text
• Follow chéo (N lượt follow):
  + Success (M): ...
  + Nhả follow (K):
    - Nhả liền (0 lượt - X): 1, 7, 10, ...
    - 1 - 4 lượt (Y): 14 (1 lượt), 28 (3 lượt)...
    - 5 - 9 lượt (Z): 4 (7 lượt), 9 (7 lượt)...
    - 10+ lượt (W): 2 (19 lượt), 29 (27 lượt)...
  + Lỗi script/xác minh (0): Không có
  + Bỏ qua (P): ...
```
*Lưu ý:* Chỉ hiển thị các dòng nhóm có số lượng máy > 0 để tiết kiệm ký tự và giữ thông tin ngắn gọn, dễ nhìn.

## 3. Cách Trích Xuất Dữ Liệu Nhanh O(1)
- Từ state file: `D:/Taadaa/tiktok-follow/runs/state/follow_state_<m>_row_<slot>.json` -> đọc `budget_used` hoặc `len(followed)`.
- Từ runtime folder: `D:/Taadaa/runtime/kibe/live/<date>/row-<slot>-*/<run_id>/machines/machine_<m>/follow_result.json` -> đọc `len(followed)` hoặc `followed_count`.
- CẤM quét đệ quy `os.walk` hay `find` sâu toàn bộ runtime gây tắc nghẽn I/O.

# Quy định Lock Cứng Khi Máy Lỗi Giữ Hiện Trường (2026-08-22)

## 1. Yêu cầu & Nguyên tắc (User Mandate)
- Khi chạy phiên nuôi acc (feed session), kiểm tra cron hoặc chạy batch mà phát hiện máy gặp lỗi (`fail`, `manual-needed`, popup lạ, mất focus, sai username, v.v.), **BẮT BUỘC lock cứng máy lại** để giữ nguyên hiện trường màn hình.
- **Vị trí lưu lock:** `C:\Users\Kibe\.codex\device-locks\machine_<n>.lock.json` (và alias `serial_<serial>.lock.json`).
- **Cấu trúc lock payload:**
  ```json
  {
    "machine": 11,
    "serial": "988633474f4b514436",
    "status": "blocked",
    "reason": "[AI-HOLD-SCENE] fail: TikTok focus lost",
    "owner": "hermes-operator",
    "owner_project": "tiktok-luot nuoi acc",
    "pid": 999999,
    "created_at": 1787360000.0,
    "locked_at": "2026-08-22 08:30:00",
    "ttl": 86400
  }
  ```
- **Mục đích:** Giữ nguyên trạng thái UI lỗi trên thiết bị, ngăn chặn các lượt cron/runner tiếp theo hoặc các tool khác tự động nhảy vào tương tác làm trôi/mất hiện trường màn hình.

## 2. Quy trình Triage Cron & Khởi Động Lại Nuôi Acc
1. **Dọn tiến trình treo:** Kiểm tra và kill các tiến trình watcher/runner cũ bị timeout/treo ngầm (`hermes_cron_watcher.py`).
2. **Xóa lease cũ:** Xóa file lease hết hạn của ngày trước tại `D:/Taadaa/runtime/kibe/cron-state/runner-live-lease/<prev_day>.json`.
3. **Kích hoạt Picker:** Chạy `tiktok_picker.py` để tạo assignment manifest cho ngày hiện tại nếu chưa có.
4. **Trigger Cron:** Kích hoạt Runner (`cdd43b124363`) và Watcher (`7890172324ca`).
5. **Lock máy lỗi:** Đọc artifact log (`log.jsonl`), tổng hợp danh sách các máy `fail` / `manual-needed` và ghi lock `status: "blocked"` ngay lập tức.

# Chẩn Đoán & Phân Tích Batch Alert Feed Session (Nuôi Acc)

## 1. Cơ chế Truy Xuất O(1) Báo Cáo Batch Feed Session
Khi nhận cảnh báo Telegram `[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【TOÀN FARM】` cho script `tiktok-luot nuoi acc`:
- **TUYỆT ĐỐI CẤM** dùng `os.walk`, `find`, `grep -r`, hay quét đĩa tìm file.
- Đường dẫn runtime được phân bổ cố định và xác định O(1) theo ngày và ca chạy (row):
  * Cụm Kibe (Máy 1–80): `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<N>-<timestamp>/<run_id>/summary.txt`
  * Cụm Admin (Máy 201–280): `D:/Taadaa/runtime/admin/live/<YYYY-MM-DD>/row-<N>-<timestamp>/<run_id>/summary.txt`
- Cấu trúc file `summary.txt`:
  * Phần đầu: Taxonomy summary (`blocker_taxonomy_summary`).
  * Phần bảng: `multi_machine_summary` dạng text cột: `machine | serial | final_status | swipes_completed | blocker_type | artifact_root`.
  * Phần cuối: `details:\n` chứa JSON đầy đủ của toàn bộ máy trong ca chạy với trường `stop_reason` chi tiết.

## 2. Pitfall Cực Kỳ Quan Trọng Về Database tiktok_tracker.db
- **CẢNH BÁO LẪN LỘN ĐƯỜNG DẪN**:
  * `D:/Taadaa/tools/tiktok_tracker.db` là file rỗng (0 bytes), không có bảng.
  * **SOURCE OF TRUTH THỰC SỰ**: `D:/Taadaa/data/tiktok_tracker.db` (~4.5MB).
- Để đối soát số máy ra `@username`:
  ```python
  import sqlite3
  conn = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db')
  c = conn.cursor()
  c.execute('SELECT username FROM account_mapping WHERE may=? AND tik=?;', (may, tik))
  row = c.fetchone()
  if not row or not row[0]:
      c.execute('SELECT username FROM farm_account_info WHERE may=? AND tik=?;', (may, tik))
      row = c.fetchone()
  username = row[0] if row else 'unknown'
  ```

## 3. Quy Tắc Bắt Lỗi P0 Mất Phiên / Văng Account Trong Batch Alert
- Cụm cảnh báo `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]` được kích hoạt bởi hàm `evaluate_batch` trong `automation_core.batch_aggregator`.
- Bắt theo bộ từ khóa `SESSION_LOST_KEYWORDS`:
  * `"account-switcher-missing-expected"`, `"account_missing"`, `"account-missing"`
  * `"thiếu nick"`, `"mất nick"`, `"account missing"`
  * `"logged out"`, `"signed out"`, `"văng"`, `"session expired"`, `"phiên đã hết hạn"`
  * `"login screen"`, `"login"`, `"đăng nhập lại"`, `"require_login"`
- **Cách tìm nhanh máy P0**:
  Duyệt danh sách máy thất bại trong `summary.txt` (phần JSON `details:`), kiểm tra máy nào có `stop_reason` khớp các từ khóa trên.
  *Ví dụ Case điển hình*: `manual-needed:account-switcher-missing-expected: expected account not found in account switcher` $\rightarrow$ tài khoản mong đợi không tồn tại trong Switcher của app TikTok.

## 4. Chuẩn Trình Bày Báo Cáo Đối Soát Cho Vận Hành Farm
- **Invariants**:
  1. Báo cáo nuôi/đối soát **BẮT BUỘC quy về TÊN NICK (@username) & lý do lỗi cụ thể**, cấm chỉ in số máy trần trụi.
  2. Bắt buộc tách riêng nhóm **P0 Mất phiên / văng account** lên vị trí ưu tiên cao nhất.
  3. Phân nhóm các lỗi còn lại rõ ràng:
     - Rớt kết nối phần cứng / USB (`device offline` hoặc `device not found`).
     - Lệch tài khoản switcher (Switch xong tên profile vẫn không khớp).
     - Kẹt màn hình TikTok / Splash / Ads / Popup.
     - Lỗi ATX service / Capture màn hình.

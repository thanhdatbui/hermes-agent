# Benign Popup Dismissal & Safety Inheritance Pitfalls (TikTok Feed Session)

## 1. Hiện Tượng Kẹt Popup "Add phone" & Swipe Recovery Thất Bại
- Khi TikTok hiện modal dialog "Add phone" (hoặc các popup benign tương tự có nút close X / Not now / Skip):
- Script nhận diện được popup nhưng dừng với lý do:
  `Add phone popup detected; --allow-benign-popup-dismiss not set`
  `safety_reason: benign Add phone popup detected; dismiss requires explicit flag`
- Flow đánh dấu `manual-needed` và rơi vào `_swipe_recovery_on_stuck`.
- Do modal dialog là lớp phủ toàn màn hình, 2 lần vuốt màn hình không đóng được popup -> kết thúc với lỗi:
  `; swipe recovery (2 swipes) still stuck`.

## 2. Nguyên Nhân Kép (Root Causes)
1. **Parent Safety Override đè cờ con:**
   Trong `flows/multi_machine_feed_session.py`:
   ```python
   child_safety = child_config.setdefault("safety", {})
   # Bật mặc định allow_benign_popup_dismiss để tự động đóng popup vị trí/quyền an toàn
   child_safety["allow_benign_popup_dismiss"] = True
   parent_safety = ctx.config.get("safety", {})
   if isinstance(parent_safety, dict):
       for _key in ("allow_benign_popup_dismiss", ...):
           if _key in parent_safety:
               child_safety[_key] = parent_safety[_key]
   ```
   Do `config.example.yaml` của parent có khai báo mặc định `allow_benign_popup_dismiss: false`, vòng lặp copy từ `parent_safety` đã vô tình ghi đè `child_safety["allow_benign_popup_dismiss"] = True` thành `False`.

2. **Chặn cứng trong `_maybe_dismiss_add_phone_row`:**
   Trong `flows/feed_swipe_smoke.py`:
   ```python
   if not ctx.config.get("safety", {}).get("allow_benign_popup_dismiss", False):
       row["popup_type"] = "add_phone"
       ...
       return row
   ```
   Nếu cờ bị `False` hoặc không set, hàm từ chối dismiss và ép manual.

## 3. Quy Tắc Khắc Phục Chuẩn
- **Multi-Machine Parent-Child Inheritance:**
  Đảm bảo `child_safety["allow_benign_popup_dismiss"]` chỉ bị tắt nếu parent có chỉ định tắt tường minh (`explicit disable`), không để giá trị default `false` từ file cấu hình mẫu làm mất hiệu lực của child.
- **Feed Swipe Smoke Benign Handler:**
  Với các popup hoàn toàn an toàn có nút đóng (Close-X như Add phone), mặc định cho phép đóng qua `dismiss_add_phone_popup` khi không có lệnh cấm tường minh trong feed session.
- **CẤM Quét Đĩa Recursive Bằng Python (`os.walk`):**
  Tuyệt đối không chạy `os.walk('D:/Taadaa/...')` trong python one-liner để tìm nơi định nghĩa cấu hình/cờ; ổ đĩa farm trên Windows sẽ bị treo I/O và dính timeout 900s. Đọc trực tiếp các file đích đã biết: `flows/feed_swipe_smoke.py`, `flows/multi_machine_feed_session.py`, `run_tiktok.py`, `config.example.yaml`.

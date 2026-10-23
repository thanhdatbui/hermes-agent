# Unjust Streak Inflation, False Failure Accounting & Cooldown Reconciliation

## 1. Nguyên Tắc Cốt Lõi Về Phạt Fail Streak
- **Chỉ tính streak tăng khi và chỉ khi:** Tài khoản thực sự ra sân chạy, bấm follow phát đầu tiên nhưng bị TikTok nhả nút ngay lập tức (`fl = 0`, `follow_failed = True`) qua N chu kỳ liên tiếp.
- **CẤM TUYỆT ĐỐI tăng streak khi:**
  1. **Lỗi mạng / Sập proxy / Timeout ADB:** Phải trả về `MANUAL_REVIEW`, cấm gọi `set_follow_failed()`.
  2. **Reload UI lag / Identity chưa xác thực:** Trả về `MANUAL_REVIEW`, không phán nhả bừa bãi.
  3. **Tài khoản đang trong Cooldown:** `cooldown_until_at` còn hiệu lực bắt buộc no-op ở cấp byte, cấm gọi trùng làm dồn toa streak lên 5-6.
  4. **Target ngoài farm (Priority Targets):** Search không ra nick chỉ ghi nhận `skipped`, không bao giờ được coi là lỗi nhả follow.

## 2. Xử Lý Máy Chạm Trần Phiên (Ceiling Drop)
- Khi máy đã follow thành công $\ge 1$ lượt (`used > 0`) rồi bị nhả ở lượt cuối:
  - **Streak:** Giữ nguyên streak hiện tại, không tăng (`streak = max(1, curr_streak)`).
  - **Cooldown:** Chỉ nghỉ 1 ngày xả cache (`cooldown_until_local = today_end_local + 1d`), cấm đày 3 - 15 ngày.
  - **Báo cáo Watchdog:** Bắt buộc ghi nhận máy vào cả `fl_success` (để tính số máy thành công) và `fl_released` (kèm chú thích số lượt đã follow, ví dụ `M59: 3 lượt`). Mẫu số tổng máy = `len(set(fl_success) | set(fl_released))`.

## 3. Bẫy Hiển Thị "Tù Treo" Trên Dashboard & Reconcile O(1)
- **Bản chất lỗi:** File state JSON lưu tĩnh trên đĩa (`follow_state_*.json`). Khi hết hạn cooldown (`now_utc >= cooldown_until_at`), cờ `follow_failed = True` vẫn còn trong file nếu chưa có cron quét tới.
- **Xử lý Dashboard (`follow_health_helper.py`):** Kiểm tra `cooldown_until_at < now` để giải phóng trạng thái về `Hồi phục 1` ngay lập tức, không được chỉ nhìn mỗi cờ `is_failed`.
- **Lệnh giải phóng tự động farm:** Chạy `python D:/Taadaa/tools/reconcile_expired_cooldowns.py` quét 450 file state để hạ cờ `follow_failed = False` cho toàn bộ nick đã mãn hạn.

## 4. Bẫy Kẹt Cooldown Vĩnh Viễn Do Gán Giá Trị `cooldown_until_at: null`
- **Nguyên nhân gốc rễ:**
  - Trong các script giải phóng hoặc xá tội cooldown (như `reconcile_unfair_streaks.py`), nếu lập trình viên gán:
    ```python
    data["cooldown_until_at"] = None  # GÁN NULL THAY VÌ XÓA KEY!
    data["cooldown_until_date"] = None
    ```
  - Trong `FollowState._check_and_sync_cooldown_expiry()` (`follow_state.py`):
    ```python
    if "cooldown_until_at" in self._data:  # Key vẫn tồn tại trong dict!
        val = self._data.get("cooldown_until_at")  # val = None
        until_dt = self._parse_utc_iso(val)  # -> Trả về None
        if until_dt is None:
            return True  # FAIL-CLOSED: TỰ COI LÀ LỖI PARSE VÀ KHÓA CỨNG COOLDOWN!
    ```
  - Hậu quả: Dù `follow_failed = False` và `fail_streak = 1`, runner vừa nạp state lên là lập tức abort với lý do `follow trước đó không lên (TikTok không nhận) — dừng session, cooldown trong ngày` (hiện tượng 11 máy Row 3 bị kẹt oan ngày 23/10/2026).
- **Quy chuẩn sửa lỗi & Phòng thủ 2 lớp:**
  1. *Phòng thủ trong `follow_state.py`:*
     ```python
     if "cooldown_until_at" in self._data:
         val = self._data.get("cooldown_until_at")
         if val is None or not str(val).strip():
             self._data.pop("cooldown_until_at", None)
             self._data.pop("cooldown_until_date", None)
             self._data.pop("follow_failed_date", None)
             self._data["follow_failed"] = False
             self._save()
             return is_hard_blocked
     ```
  2. *Quy tắc viết script Reconcile:* TUYỆT ĐỐI CẤM gán `data["cooldown_until_at"] = None`. BẮT BUỘC dùng `data.pop("cooldown_until_at", None)` và `data.pop("cooldown_until_date", None)`.

## 5. Kỷ Luật Theo Dõi & Đối Soát Nhả Follow Theo Hàng (Row) Trên Dashboard
- **Hiện tượng Bẫy Anchor Check ở Slot phụ (Row 3 / Row 4):**
  - Khi chạy follow các slot phụ (như Row 3 trưa 23/10), có tới 38-41 máy bị TikTok nhả ngay khi kiểm tra nick Anchor (`_ensure_anchor_followed`).
  - Giao diện Dashboard cũ chỉ gom theo bậc sức khỏe chung (`Khỏe / Hồi phục / Cooldown`) làm khó theo dõi.
- **Quy chuẩn hiển thị mới trên Dashboard (`:1905`):**
  - **Tab Sức Khỏe Follow (`follow_health_render.js` & `health_views.js`):**
    * Bắt buộc có thẻ KPI và nút lọc riêng `🛑 Bị Nhả Hôm Nay` (nền đỏ nhạt, click lọc ra ngay danh sách các máy vừa fail trong ngày).
    * Bổ sung cụm lọc theo Hàng: `Hàng: Tất cả | R1 | R2 | R3 | R4` kết hợp linh hoạt với cụm máy (`Toàn Farm | Kibe | Admin`).
    * Từng card nick hiển thị rõ số Follower, Video và banner đỏ trích xuất lý do fail hiện trường (ví dụ: `FOLLOW_FAILED: anchor @luunhu290719 bị nhả sau vuốt — dừng session`).
  - **Tab Toàn Bộ Farm (`table_view.js`):**
    * Thêm thanh lọc `Hàng Acc (Row): Row 1-5+`.
    * Gắn huy hiệu `🛑 Nhả Hôm Nay` ngay cạnh Username để đối soát song song cùng các chỉ số tăng trưởng kênh (Follower, Tim, Video).

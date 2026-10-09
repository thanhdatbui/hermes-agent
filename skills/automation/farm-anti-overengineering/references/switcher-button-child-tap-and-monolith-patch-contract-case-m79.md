# Bài Học Case Máy 79: Lỗi Tap Switcher Child TextView, Feed Drift False Negative & Kỷ Luật Patch Contract Trên Monolith

## 1. Hiện tượng thực tế (Sự cố Máy 79 & Cảnh báo từ User)
- **Cảnh báo farm:** `[FARM ALERT: MÁY 79] DỪNG PHIÊN - Nick: ruffumyxkvv - profile username still mismatched after switch`.
- **Phản ánh từ User:** *"Ms sửa hàm gì gây lỗi này hàng loạt máy r đó"*.
- **Hai lỗi logic phối hợp gây tê liệt toàn bộ dàn máy:**
  1. **Lỗi 1 (Feed Drift False Negative):** Khi TikTok chuyển tài khoản hoặc reload session, app tự động văng về Home Feed (ảnh hiện trường hiển thị rõ video creator `@Linhnguyen1707`). Tuy nhiên, hàm `_profile_guard_drifted_from_profile` trong `feed_swipe_smoke.py` chỉ trả về `True` khi `xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS`. Khi XML sạch (`xml_error == ""`), hàm trả về `False`. Flow tưởng nhầm đang ở Profile, trôi xuống `read_profile_identity()` và đọc nhầm `@creator` video làm nick của máy $\rightarrow$ gây mismatch hàng loạt máy.
  2. **Lỗi 2 (Tọa độ tap switcher đè trúng child TextView không clickable):** Trong sheet switcher, mỗi dòng tài khoản là một `android.widget.Button` (`com.ss.android.ugc.trill:id/l9b`, `clickable="true"`, bounds `[0, 816][1080, 1032]`, center $x=540$). Bên trong chứa `TextView` (`com.ss.android.ugc.trill:id/mtx`, `clickable="false"`, bounds `[252, 894][543, 954]`, center $x=397$). Hàm `_find_account_switch_option` cố tình override `best_bounds = inner.bounds` để nhắm vào chữ. Lệnh `input tap 397 924` chạm đúng vào `TextView` không nhận click, khiến Button cha không kích hoạt $\rightarrow$ TikTok không hề switch, profile giữ nguyên nick cũ `@refughbmh33` sau 2 lượt thử.

---

## 2. Các Bài Học Kiến Trúc & Anti-Patterns Đúc Kết

### A. Anti-Pattern: Override Bounds Sang Non-Clickable Child View
- **Nguyên nhân:** Lầm tưởng rằng tap vào giữa text của username sẽ "chuẩn hơn" tap vào giữa dòng container full-width (`x=540`).
- **Thực tế:** Trên các dòng máy Samsung Android 7/8 (Galaxy S7), sự kiện chạm `MotionEvent` vào một child view có `clickable="false"` bên trong custom Button của TikTok thường bị nuốt hoặc không kích hoạt `OnClickListener` của container cha.
- **Kỷ luật chuẩn:** Khi `node.attributes.get("clickable", "false").casefold() == "true"`, **BẮT BUỘC giữ nguyên `best_bounds = node.bounds`** (center $x=540$). Chỉ cho phép tìm inner bounds khi container cha KHÔNG có thuộc tính clickable.

### B. Anti-Pattern: Giao Goal Mở Trên Monolith File (>= 5k dòng) Làm Worker Cạn Kiệt 35 Tool Calls
- **Hiện tượng:** Khi Coordinator giao task cho Worker: *"Điều tra log, tìm nguyên nhân switcher không ăn click, sửa code và chạy canary"*. Worker đọc context, đọc log, đọc XML hết 35 lượt gọi (chạm trần hệ thống) mà chưa kịp ghi 1 byte code xuống đĩa.
- **Kỷ luật bắt buộc:**
  1. **Monolith File (`feed_swipe_smoke.py` 17k-22k dòng):** Coordinator BẮT BUỘC xác định chính xác dòng lỗi, kiểm tra tính duy nhất (`grep -c == 1`), và soạn **Patch Contract** hoàn chỉnh gồm `old_string` và `new_string`.
  2. **Tách biệt 2 pha rõ ràng:**
     - **Pha 1 (Worker Patch):** CHỈ áp dụng Patch Contract + `python -m py_compile` (<= 5 calls, hoàn thành < 60s).
     - **Pha 2 (Worker Canary):** CHỈ chạy lệnh PowerShell Canary với đúng tham số Row và verify kết quả (<= 5 calls).

### C. Anti-Pattern: Mặc Định Chạy Canary `-Row 1` Khi Nick Báo Lỗi Nằm Ở Row Khác
- **Hiện tượng:** Cảnh báo báo lỗi cho nick `ruffumyxkvv`. Coordinator mặc định chạy Canary `-Row 1` (trong khi `ruffumyxkvv` nằm ở Row 6, còn Row 1 là `shirldlpbkg`). Hậu quả là test thất bại vì máy cố tìm tài khoản khác với tài khoản gây alert.
- **Kỷ luật bắt buộc:** Khi nhận Farm Alert `[MÁY N] - Nick: <username>`, kiểm tra nhanh file `taikhoan_run_safe.xlsx` để lấy đúng số thứ tự Row của nick đó trước khi truyền vào `-Row <index>` của runner.

# Xử Lý Sự Cố Account Switcher & Nhận Diện Drift Về Feed Trong TikTok Nuôi Acc

## 1. Hiện Tượng Lỗi: "profile username still mismatched after switch"
Khi bot thực hiện chuyển tài khoản trong TikTok Account Switcher (Bottom Sheet):
1. **Trường hợp 1 (Feed Drift):** TikTok chuyển tài khoản xong hoặc tải lại phiên thì tự động văng về màn hình Trang chủ (For You Feed). Nếu hàm `_profile_guard_drifted_from_profile` chỉ kiểm tra lỗi degraded XML (`xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS`) mà bỏ qua trường hợp XML sạch (`xml_error == ""`), hệ thống sẽ lầm tưởng màn hình Feed là trang Profile. Flow trôi xuống `read_profile_identity()` và đọc nhầm `@creator` trong caption video For You làm username của máy -> Báo sai lệch tài khoản và dừng máy hàng loạt.
2. **Trường hợp 2 (Missed Switcher Tap):** Trong Account Switcher, hàng tài khoản là một `android.widget.Button` (`id/l9b`, `clickable="true"`), bên trong chứa `TextView` (`id/mtx`, `clickable="false"`). Nếu code cố tình tìm inner TextView để tính tọa độ tap (ví dụ `best_bounds = inner.bounds`), lệnh `input tap` sẽ rơi vào giữa TextView `mtx` (tọa độ lệch sang trái $x \approx 380..397$). Trên nhiều dòng máy Android (đặc biệt là Samsung Galaxy S7), cú chạm vào child view không clickable này không kích hoạt `OnClickListener` của Button cha -> TikTok không hề chuyển tài khoản, trang cá nhân giữ nguyên nick cũ.

---

## 2. Quy Tắc & Giải Pháp Chuẩn Hóa

### A. Tọa độ Tap Switcher Row
- Tuyệt đối **không override** `best_bounds` sang child `TextView` khi node cha đã là container / button clickable (`node.attributes.get("clickable") == "true"`).
- Cú chạm BẮT BUỘC phải nhắm vào chính giữa container button (`center_x = 540`) hoặc avatar để đảm bảo Button nhận được sự kiện `MotionEvent` và đóng sheet chuyển tài khoản.

### B. Nhận diện Drift về Feed Không Phụ Thuộc XML Error
- Khi `detected` thuộc tập các màn hình feed: `{"home", "for-you", "following", "friends"}`, hàm `_profile_guard_drifted_from_profile` BẮT BUỘC phải trả về `True` ngay lập tức, bất kể `xml_error` có rỗng hay không.
- Khi phát hiện drift về Feed trong quá trình preflight verify, kích hoạt ngay cơ chế re-tap tab Hồ sơ (`_try_profile_retap_on_drift`) để kéo app về trang Profile trước khi đọc danh tính.

### C. Đối Soát Row Tài Khoản Khi Chạy Canary
- Khi nhận Farm Alert `[MÁY N] - Nick: <username>`, kiểm tra file `taikhoan_run_safe.xlsx` để xác định chính xác số thứ tự dòng (`Row`) tương ứng với nick đó trên máy N.
- Tuyệt đối không mặc định chạy `-Row 1` nếu nick trong alert nằm ở Row 2..6. Chạy sai Row sẽ khiến script cố chuyển sang nick khác với nick hiện trường, gây sai lệch kết quả kiểm thử.

### D. Kỷ Luật Dispatch Worker Trên Monolith Files (>= 5k dòng)
- Các file monolith lớn như `feed_swipe_smoke.py` (> 17.000 dòng): KHÔNG dispatch subagent với goal mở (vừa đọc log, vừa tìm nguyên nhân, vừa sửa code, vừa chạy canary) vì subagent sẽ cạn ngân sách tool calls (35 calls) trước khi kịp sửa code.
- **Quy trình chuẩn:**
  1. Coordinator soi đúng vị trí và soạn **Patch Contract** cụ thể (`old_string` grep count = 1 -> `new_string`).
  2. Dispatch Worker 1: CHỈ áp dụng Patch Contract + `py_compile` (Scope Lock, <= 5 tool calls).
  3. Dispatch Worker 2: CHỈ chạy Canary Test B4 với đúng Row chỉ định và nghiệm thu.

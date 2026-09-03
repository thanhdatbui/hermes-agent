# TikTok Reg — Sticky Profile Switcher & Batch Ops Cheatsheet (2026-08-20/21)

Kết quả thực chiến batch reg 11 nick (máy 1, 23, 25, 30, 31×2, 38, 42, 76, 77, 79) — TikTok build hiện tại (46.x) đổi UI profile, gây 3 class bug chính.

## 1. TikTok 46.x — Profile layout mới: phải VUỐT LÊN trước khi tap switcher

**Triệu chứng:** `[03_dropdown] Khong mo duoc account dropdown` dù đã bấm đủ @username (sj8/scn), rv5, display-name. TikTok layout mới: profile có "Thêm tiểu sử" node riêng; nút account switcher là **sticky bar dính top** — chỉ hiện sau khi kéo (scroll) trang profile lên. Nhớ câu user: *"khi mở add tài khoản thì phải vuốt màn xuống để tên nằm trên cùng r ms bấm theo account switcher đã thiết kế"* — thực tế là **swipe UP** (540,1000→540,600) kéo trang lên, tên nằm TOP.

**Fix đã đóng vào `social_reg_v1.py`:**
- Pass 0 trong `_try_open_account_dropdown_once`: tap sticky profile-button theo rid `pcs/p01/p1j/qx0/qzr/p7w/pmh` khi bounds.top ≤ 350 (máy 31→`pcs`, máy 77/79→`p7w`).
- Giữa các attempt: `dismiss_profile_overlays()` + swipe up 400px + re-check profile screen.
- **LOẠI node "Thêm tiểu sử" khỏi Pass 4 (display-name)**: `txt` chứa "tiểu sử" → skip. Tap nhầm node này → mở dialog chọn bàn phím / editor bio → kẹt.
- Dialog `Chọn bàn phím` ("select input method") → phải tự đóng bằng keyevent Back trong `dismiss_profile_overlays` (filter `"chon ban phim"`/`"select input method"`). Máy bị dính dialog này chạy không qua được dropdown.

## 2. TARGET_INVENTORY_CONFLICT — serial bị ghi ĐÈ bằng ngày tháng

`_detect_clean.py` báo `TARGET_INVENTORY_CONFLICT: machine X` vì trong `taikhoan_run_safe.xlsx`, dòng nick mới reg bị ghi **value ngày (`20/08/2026` / `24/06/2026`) vào cột B (Device ID)** — thay vì serial. `social_reg_v1.py` khi success ghi dòng mới lấy template row nhưng có thể để lọt date. TẤT CẢ các máy vừa reg xong đều cần rà:
- Scan `taikhoan_run_safe.xlsx` cột B: value chứa `/` hoặc `-` (date) → thay bằng serial đúng của máy (lấy từ dòng khác cùng máy hoặc `PROXYgandienthoai.xlsx` cột serial).
- Kiểm tra 80 máy 1 lần sau batch; máy 1, 25, 30, 31, 39, 42 từng bị.

## 3. Batch reg nhiều máy — vận hành khóa & tiến độ

- `DEVICE_LOCK_ENABLED=1 python social_reg_v1.py <stt> --ss`: worker tự tạo lock. Lock file `C:\Users\Kibe\.codex\device-locks\machine_<stt>.lock.json` + `serial_<serial>.lock.json`. Chạy lặp lại → cần xoá lock cũ trước (`*.lock.json`), hoặc `--resume` khi máy đang dở.
- User rule (2026-08-21): **"Đang làm cứ lock lại chỉ có success hoặc t ra lệnh ms đc mở ra"** → append thêm.
- LỖI `File "social_reg_v1.py", line ~774: ConsumerPreflightError` → `automation-core` chưa cài trong venv: `pip install -e D:\Taadaa\automation-core` (src layout, `sys.path.insert(0, r'D:\Taadaa\automation-core\src')` cũng được cho test nhanh).
- Runner batch dùng `subprocess.run(..., timeout=450)` — máy kẹt OTP flow sẽ timeout, không treo vô hạn. Mỗi máy trung bình 5-8 phút (open ad 20-40s, UI dump 36s lần lỗi, birthday picker ~1 phút). 8 máy tuần tự ≈ 60-90 phút.
- Script log ra `social_reg_log.txt` (append) — poll file này để theo dõi nhiều máy chạy cùng lúc.

## 4. OTP Gmail hotmail lỗi thường gặp khi batch

- **Mã hết hạn / lỗi "Mã xác minh email đã hết hạn"** (máy 2): Gmail code cũ `954753` không dùng lại được; script bấm "Gửi lại mã" (bounds [96,987][339,1104] → (200,1040)) nhưng **mail mới có thể không về** (Gmail fetch chậm / TikTok delay). Bẫy: script cứ đọc *recent already-open conversation* cũ → nhập mã cũ → lỗi → loop. Cần xoá/archive conversation cũ trong Gmail hoặc chờ thư 02:xx thật sự mới.
- Hotmail OTP qua Graph API (`read_tiktok_otp_from_graph_token`) ổn định cho batch, máy 23/31/77/79 đều dùng được.
- Nút "Tiep tuc" nullable: sau OTP, nếu không thấy Xác nhận/Tiếp tục → bấm `input keyevent Enter` (đã có trong script), sau đó màn DOB/password.

## 5. ViChanger VPN — 2 lỗi khiến reg không thể chạy (chặn an toàn)

- **Máy 34: `No LSPosed access !!!`** — ViChanger GUI yêu cầu LSPosed + API key; sau `pm disable/enable` + reboot vẫn `GET_IP result=0`. App `enabled=0` → `pm enable vn.vichanger.app` rồi mở app thấy dialog LSPosed. Runner bình thường né path GUI bằng broadcast API, nhưng khi app cần LSPosed thì broadcast `START_VPN` trả `result=0` → **giữ nguyên hiện trạng, báo user cài lại root/LSPosed**, không tự sửa.
- **Máy 75: GET_IP timeout vĩnh viễn** sau khi khởi động lại START_VPN → proxy box/upstream chết (xem skill farm-proxy-attachment — test curl -x, check box). Giữ chặn.
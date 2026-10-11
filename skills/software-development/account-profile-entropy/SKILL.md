---
name: account-profile-entropy
description: "Generate realistic Vietnamese account profiles (names, usernames, passwords) with high entropy to evade bot detection on platforms like Gmail, TikTok, Hotmail. Covers DEM_POOL for middle names, natural username patterns with dots/suffixes, and randomized password structures without fixed fingerprints."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [account-generation, bot-evasion, vietnamese-names, gmail-reg, tiktok-reg, entropy]
    related_skills: [tiktok-registration-ops, hotmail-outlook-automation, android-device-automation]
---

# Account Profile Entropy Optimization

Generate realistic Vietnamese account profiles that don't look like bot output. Used across Gmail reg, TikTok reg, Hotmail reg, and similar automation.

## When to Use

- Creating new account registration scripts that need to bypass platform bot detection
- Upgrading existing reg scripts that show pattern fingerprinting (fixed suffixes, no dots, rigid structures)
- Any automation where profile realism affects success rate

## Core Patterns

### 1. Name Structure (via `generate_random_name()`)

```python
DEM_POOL = [
    "Van", "Thi", "Ngoc", "Hoang", "Minh", "Quang", "Thanh", "Duc", "Dinh", "Huu",
    "Xuan", "Hai", "Thu", "Bao", "Anh", "Cong", "Trong", "Gia", "Tuan", "Phuoc",
    "Kim", "Tien", "Hong", "Phuong", "Khanh", "Duy", "Nhat", "Thao", "My", "Quoc",
]

# Distribution: 2-word (25%), 3-word (60%), 4-word (15%)
# Examples: "Tran Dung", "Bui Minh Tuyen", "Gia Duc Thanh Tuong"
```

### 2. Username Patterns (`build_username()`)

Comprehensive natural styles with high entropy to avoid collisions:

- **Target length & entropy**: Target 16–24 chars right from Attempt 1 (Google allows 6–30 chars). Minimum guaranteed length is **14 chars** for Attempt 1. Avoid bare names with only 2–3 digits (e.g. `ngophuong200`) which have >90% collision rates on Gmail.
- **Handling short 2-word names (e.g. 'Le An', 'Do Ha')**: Base name stems are only 4–5 chars. Bare suffixes (e.g. `pro`, `top`, `hub`) with 3 digits produce only 11–12 chars. For short stems, always combine suffix + salt (3–4 chars) + 2–3 digits, or DOB + salt + digits, and enforce a defensive padding loop `while len(u) < 14: u += random.choice("abcdefghijklmnopqrstuvwxyz0123456789")`.
- **With dots**: `nguyen.an.media99`, `an.nguyen.work03`, `nguyen.van.an2001.dev`
- **3-5 random digits + salt**: `nguyenan7824`, `tranductoan892krmw`, `an.nguyen.1824vn`, `lean.media150849`
- **DOB/Year + random digits + salt**: `nguyenan150823`, `an.nguyen.200184`, `nguyenan0184xyz48`
- **Salt letters + digits**: `nguyenansalt824`, `an.nguyen.xyz395`, `nguyenanxy01`
- **Natural suffixes**: Standard pool: `media`, `plus`, `work`, `tech`, `online`, `top`, `zone`, `hub`, `life`, `pro`, `corp` (also supports `dev`, `app`, `official`)
- **Middle name combinations**: `nguyen.van.an294`, `nguyenvanan.dev382`

**Constraints**: 14-30 chars on Attempt 1 (6-30 platform bound), no leading/trailing dots, no `..`, lowercase `a-z0-9.`, matching `^[a-z0-9]+(\.[a-z0-9]+)*$`.

### 3. Password Patterns (`build_password()`)

9+ natural structures, random symbols (`@ # ! $`):

- `HoTenDDMMYYYY@` → `NguyenVanAn15082001@`
- `HoTen@YYYY` → `NguyenVanAn@2001`
- `TenHo#DDMMYYYY` → `VanAn#Nguyen15082001`
- `HoTen#WordYY` → `NguyenVanAn#Vn01`
- `WordHoTen#YY` → `VnNguyenVanAn#01`

- **No fixed suffix** — never use `@Ks` or similar fingerprints across all accounts.
- **Symbol compatibility**: Use `@`, `#`, `!`, `$` which are safely typed across `human_type` and `input_text` without interfering with space `%s` encoding and ensure contract test compatibility (avoid unescaped `%`, `&`, `*`, `^` that break shell typing or test assertions).
- **Position jittering**: Shuffle special symbol placement (beginning, middle between name & number, or end) and word positioning to eliminate fixed structural footprints.

### 4. Post-Registration Warmup & Lifecycle Hooks

- **Warmup Newsletter Registration — Bản chất kỹ thuật & Cạm bẫy Cloudflare (False Positive)**:
  - Khi reg tài khoản thành công (`persist_success_result`), hook gọi `warmup_newsletter_services.py` đăng ký nhận newsletter để tạo inbound activity ban đầu.
  - **CẠM BẪY ĐẮT TIỀN (False Positive 200)**: Các dịch vụ newsletter hiện đại (Cooper Press: Node/JS/Ruby Weekly, Substack, Ghost...) đều đặt Cloudflare Turnstile bot protection trên form đăng ký. Request HTTP POST bằng `urllib` thuần gửi lên sẽ nhận response `200 OK` nhưng ruột thực chất là trang thử thách Cloudflare HTML ("Just a moment...") $\rightarrow$ script ngộ nhận thành công nhưng server newsletter KHÔNG BAO GIỜ nhận email, hòm thư Gmail hoàn toàn không có mail xác nhận!
  - **Độ trễ Double Opt-in**: Kể cả khi form submit thành công vào các dịch vụ mail embed (như Mailchimp), hệ thống mail server của họ gửi thư xác nhận theo hàng đợi (queue), mất từ 15–30 phút mới rớt vào inbox, và thường bị Google tự phân loại vào tab "Quảng cáo" (Promotions) thay vì tab "Chính" (Primary).
  - 👉 **Quy chuẩn thực thi**: Không phụ thuộc mù quáng vào kết quả HTTP status 200 của module newsletter bên thứ ba. Yếu tố quyết định trust của Gmail trong 24h-48h đầu là **trạng thái đăng nhập ổn định trên chính thiết bị Android S7** (`dumpsys account` tồn tại) và kết nối mạng tự nhiên qua mobile proxy của máy.
- **Không Cần Thiết & Cấm Over-engineer Đăng Ký App Ngoài (ChatGPT, v.v.) Trên S7**:
  - Không cần thiết và không nên cố tạo tài khoản ChatGPT/dịch vụ ngoài trực tiếp trên Samsung S7 ngay sau khi reg. App ChatGPT yêu cầu Android 9.0+ (S7 chạy Android 8.0 không cài được). Dùng Chrome S7 bấm "Continue with Google" bị lỗi intent callback của WebView Android 8.0 (`Settings$UserAndAccountDashboardActivity`).
  - Đăng ký nhận Newsletter là hoàn toàn đủ điều kiện kích hoạt inbound activity an toàn cho hòm thư. Sau khi ngâm đủ 24h-48h trên S7, tài khoản được đưa lên GPM Profile trên PC thì việc liên kết ChatGPT hay mọi dịch vụ khác diễn ra cực kỳ mượt mà, không gặp lỗi.
- **BẮT BUỘC dùng 2FA TOTP (Google Authenticator) thay vì Recovery Email dùng chung**:
  - Không add mail khôi phục dùng chung (như `thanhdatbui1995@gmail.com`) vì khi cần OTP khôi phục/login sẽ bị nghẽn hàng đợi (queue bottleneck), và Google AI sẽ liên kết chuỗi (chain-ban/checkpoint) toàn bộ đàn tài khoản do trùng identity mail khôi phục.
  - Sử dụng pipeline bật 2FA Google Authenticator độc lập (`run_batch_2fa_kibe_pool.py`), trích xuất Secret Key Base32 và lưu vào workbook. Sau khi bật 2FA, Google cấp High Security Trust, giảm thiểu tối đa rủi ro bị quét checkpoint ngầm sau 48–72h.
- **Rào cản Fresh Account Hold (Bật 2FA & Recovery Email ngay sau khi Reg)**:
  - Khi tài khoản vừa tạo xong trên điện thoại, Google kích hoạt cơ chế phòng vệ **Fresh Account Security Hold / Anti-bot Cooldown** trong 24h–48h đầu.
  - **Bật 2FA:** Khi vào mục *Xác minh 2 bước*, sau khi nhập mật khẩu và bấm Tiếp theo, Google sẽ rơi vào **Loop Verification** (xoay rồi reload lại đúng trang nhập mật khẩu, không báo lỗi đỏ).
  - **Thêm Email khôi phục:** Sau khi nhập mật khẩu, Google ép quay video selfie khuôn mặt (*"Lưu video selfie dùng để đăng nhập"*). Nếu bấm *"Để sau"*, Google đẩy văng sang trang Google One AI.
  - 👉 **Quy chuẩn thực thi:** Khi reg xong, **bảo đảm lưu 100% Email + Password vào Excel**, giữ tài khoản đăng nhập trên thiết bị. **Ngâm tài khoản từ 24h – 48h** để phát sinh lịch sử đồng bộ (sync activity), hết cờ Fresh Account rồi mới kích hoạt luồng Bật 2FA hoặc nạp Recovery Email.
- **Kỷ luật Cooldown 4 ngày (4d Cooldown) cho Máy Reg**:
  - Kiểm tra ngày reg gần nhất trong `gmail_clean_v2.xlsx` cho từng máy trước khi chạy. Máy vừa reg thành công trong vòng 4 ngày **CẤM TUYỆT ĐỐI cho reg tiếp ngay trong ngày**, tránh bị Google phát hiện tạo nhiều tài khoản trên cùng 1 phần cứng thiết bị.
- **CẤM đoán mò mật khẩu điền bậy vào Excel**:
  - Khi tài khoản vừa tạo trên thiết bị, mật khẩu sinh ngẫu nhiên từ 28+ template `build_password()`. Tuyệt đối CẤM tự đoán pass từ họ tên / DOB để điền vào file dữ liệu.
  - Nếu mất mật khẩu (do lỗi kẹt file hoặc chưa lưu), bắt buộc phải gỡ bỏ tài khoản đó khỏi máy (`remove_account_adb`), xóa dòng rác trong workbook, không được để tài khoản ma chiếm slot.

### 5. Invariant: Lưu Trữ Mật Khẩu & Tài Khoản Vừa Reg Xong (Chống Mất Pass)

- **Fatal Bug Pattern**: Khi chạy canary, watchdog hoặc lệnh tay (`python gmail_reg_v10.py <stt> --ss`), nếu cờ `--result-dir` không được truyền vào, hàm `persist_success_result(acc)` kích hoạt `[WORKBOOK_GUARD] Skip success persistence` $\rightarrow$ tài khoản tạo thành công trên máy Android nhưng **mật khẩu bị vứt bỏ, không ghi vào Excel hay bất kỳ file nào**! Vì mật khẩu không log plain text ra console, tài khoản bị mất vĩnh viễn mật khẩu, không thể đăng nhập bên ngoài hoặc bật 2FA.
- **Bắt Buộc**: Mọi runner tạo tài khoản (`persist_success_result`) **BẮT BUỘC phải có cơ chế Fallback Direct Workbook Save**:
  - Nếu có `--result-dir`: ghi file `.success.json` theo luồng chuẩn.
  - Nếu KHÔNG có `--result-dir`: tự động gọi `single_writer_workbook_update` ghi trực tiếp thông tin (`stt`, `email`, `password`, `ngay_sinh`, `ngay_tao`) vào `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` và lưu một bản JSON dự phòng tại `runtime/success_results/`.

### 6. Gmail Web Live Check (checkmail.live) vs On-Device False Positives

- **Cạm bẫy On-Device Check**: Hàm `check_google_account_health_from_gmail` trên máy cho kết quả false positive: Khi tài khoản bị Google khóa ngầm trên server, app Gmail Android không hiện lỗi hay CAPTCHA ngay, dẫn đến nhận định sai là tài khoản vẫn LIVE và quy kết nhầm lỗi cho TikTok không gửi OTP (kẹt 150s mỗi máy).
- **Quy chuẩn**: BẮT BUỘC kiểm tra trạng thái sống của Gmail qua web `checkmail.live` (Playwright + mobile proxy theo repo `site ban hang clone`). Khi check ra `[die]`: xóa khỏi nguồn `gmail_clean_v2.xlsx`, đưa vào `Audit Pending`, và gỡ tài khoản khỏi Android OS (`remove_account_adb`).

### 7. Farm Batch Machine Picking & IP Isolation Strategy

- **CẤM đổi IP trước khi Reg**: Giữ nguyên IP proxy đang gán, tuyệt đối không gọi reset/recreate modem trước khi vào flow reg.
- **Quy tắc Pick 15 máy có Proxy KHÁC NHAU**: Khi gom batch 15 máy chạy song song, gom nhóm theo dải proxy gán (`PROXYgandienthoai.xlsx`): mỗi cổng proxy chỉ chọn đúng 1 máy duy nhất trong cùng 1 thời điểm. Đảm bảo 15 máy chạy trên 15 đường truyền/IP độc lập, triệt tiêu việc gửi dồn dập request đăng ký từ cùng 1 IP khiến Google quét bot.
- **Dọn sạch Gmail DIE trước khi Reg**: Trước khi bắt đầu flow reg, gọi module `preflight_s7_rolling_cleanup.py` (hàm `remove_account_adb()`) đối chiếu với danh sách Gmail DIE đã đánh dấu để gỡ sạch tài khoản DIE trên máy Android, giải phóng slot sạch trước khi tạo tài khoản mới.

### 6. Username Collision & Taken Retry Loop (`handle_username_entry()`)

When registering accounts, platforms frequently report that generated usernames are already taken ("đã được sử dụng", "That username is taken", "Try another", "Hãy thử tên khác").

- **Auto-retry budget**: Loop up to `max_username_attempts = 5` times before failing.
- **High entropy from Attempt 1**: User directive: "Tăng thêm kí tự khi tạo username để tránh bị trùng hoài". Don't wait until retry #4 to add high entropy. Initial username should have 16–26 characters with salts/suffixes/4 digits to avoid hitting collisions initially.
- **Retry entropy escalation**: Pass `attempt` index to `build_username(acc, attempt=attempt)`. On retry (`attempt >= 2`), automatically pad with salt of 4–5 chars + 2–3 digits (`extra = f"{retry_salt}{retry_num}"`). If `len(u) + len(extra) > 30`, slice the base candidate first: `u = u[:30 - len(extra)].rstrip(".")` before appending `extra`. This preserves the entire retry entropy at the tail, prevents overflow past 30 chars, and ensures the candidate never ends with a dot. Truncate cleanly to <= 30 chars. Use `try ... except TypeError` for backward-compatibility with mocks (`lambda acc:`).
- **Synchronize in-place**: On collision, generate a new candidate and immediately update `acc["id"] = new_username` and local `username = new_username`. This ensures downstream verification, success persistence (`persist_success_result`), and workbook logging record the actual registered username.
- **Clear field (CRITICAL WebView Trap)**: In WebView Google Sign-in, `clear_field()` using `MOVE_END` + 60 `DEL` keyevents FAILS because `MOVE_END` does not position the cursor at the end. Next typing appends text to the previous candidate, easily blowing past 30 chars. Must use Select All (`Ctrl+A` / `KEYCODE_A` with `META_CTRL_ON` or double-tap + select all) followed by `KEYCODE_DEL`, or verify text is completely cleared before typing.
- **Server verification latency**: After `tap_next()`, Google takes 1–2s to check server availability. NEVER query UI XML immediately for collision markers ("đã được sử dụng"), or script will read the STALE error message from the previous attempt and false-positive loop 5/5 times. Wait for loading spinner to dismiss or UI state transition before checking error messages.
- **Fail closed**: Only raise `RuntimeError(f"Username bị taken sau {max_username_attempts} lần thử: {username}")` after all retry attempts are exhausted.

### 5. Name Locale & Bot-Detection Tradeoffs (VN vs Foreign Names)

When automating account creation on phone farms (Samsung S7 / Android):

- **100% Vietnamese Names for Pure Gmail Reg**: Devices configured with Vietnamese locale (`vi_VN`, Samsung Vietnamese IME) running on Vietnamese ISP / proxy IPs should use **100% Vietnamese names** (2–4 words with `DEM_POOL`). This avoids any system/network/profile mismatch that triggers Google bot detection or `PHONE_VERIFY`.
- **Risk of Foreign Names on VN Locale**: Using English/foreign names (e.g. *John Smith*, *David Clark*) on a `vi_VN` device with a VN proxy triggers platform anomaly detection, sharply increasing Google `PHONE_VERIFY` triggers.
- **High Entropy without Name Collisions**: With `DEM_POOL` (30 middle names) combined with `HO_POOL` and `TEN_POOL` across 2-to-4-word distributions, Vietnamese names provide over 100,000+ natural combinations, ensuring near-zero collision probability without needing foreign words.

### 8. TikTok Display Name & Foreign Email Adaptation (`make_tiktok_name()`)

When registering or renaming accounts created from foreign/shop emails (e.g. `francesuhunt5@gmail.com`, `LilyanLederhos64090@hotmail.com`):

- **Anti-Pattern: Raw Email Local-Part**: TikTok display name allows max 30 chars. Using raw username (`LilyanLederhos64090` or `francesuhunt5`) looks unnatural, exposes the raw handle, and flags the account as an automated bot.
- **Prefix Shortening & Near-Sound Adaptation (User Directives)**:
  * Cut at the 2nd uppercase letter, first digit, or 6–8 chars max.
  * Map phonetic prefixes to natural Vietnamese name stems:
    - `frances-` / `florence-` → **Phương Thảo**, **Thu Phương** (stem: *Phương*)
    - `sadou-` → **Hải Sa** (stem: *Sa*)
    - `lilyan-` → **Linh Bông**, **Ngọc Linh** (stem: *Linh*)
    - `kylar-` → **Kỳ La**
    - `debi-` / `debora-` → **Diệp Anh**, **Hồng Diệp** (stem: *Diệp*)
    - `ancil-` → **Hoài An**, **An Bơ** (stem: *An*)
    - `brolly-` → **Quốc Bảo**, **Gia Bảo** (stem: *Bảo*)
  * **CẤM TUYỆT ĐỐI TÊN CỤT LỦN 1 TỪ**: Hàm đặt tên `make_tiktok_name` và quy chuẩn farm KHÔNG BAO GIỜ cho phép tên 1 từ trơ trọi (như mỗi chữ *Linh*, *Phương*, *Sa*, *An*). Display name luôn luôn phải tối thiểu 2 từ. Khi bốc phonetic stem (VD: `lilyan` -> *Linh*):
    - Ưu tiên phong cách **Tên + Biệt danh đời thường**: BẮT BUỘC ghép `stem + _NICK_SUFFIX` (VD: *Linh Bông*, *Linh Miu*, *Linh Bơ*, *Linh Gạo*, *Linh Nhím*, *Linh Heo*, *Linh Cún*, *Linh Nấm*...).
    - Hoặc phong cách **Đệm + Tên** (*Ngọc Linh*, *Thanh Linh*, *Khánh Linh*), **Tên lặp / Duo** (*Linh Linh*).
    - CẤM để tên cụt 1 từ dưới mọi hình thức!
- **Natural Real-User Distribution (`social_reg_v1.py` - make_tiktok_name)**:
  * Họ + Đệm + Tên (25%): *Trần Minh Đạt, Nguyễn Hoài An*
  * Họ + Tên (25%): *Lê Linh, Vũ Nam*
  * Đệm + Tên (20%): *Ngọc Linh, Thanh Thảo, Khánh Vy*
  * Tên + Biệt danh đời thường (20%): *Linh Bông, Đạt Còi, Vy Miu, An Kem* (ghép từ `_TEN_LIST` + `_NICK_SUFFIX`: Còi, Bé, Heo, Bông, Mập, Kem, Miu, Sóc, Bơ, Gạo, Nhím, Nấm, Đậu, Su, Dâu...)
  * Tên lặp / Biệt danh dễ thương (10%): *An An, Gạo Gạo, Miu Miu, Bé Heo, Út Nhỏ, Cún Con* (bốc từ `_CUTE_DUO`)
  * 👉 **Tổng tỷ lệ phong cách biệt danh:** Chiếm đúng **30%** (20% Tên + Nickname + 10% Cute Duo). Khi cần đặt tên biệt danh cho tài khoản TikTok, có thể ưu tiên phong cách này (hoặc chỉ định tỷ lệ cao hơn cho các niche giải trí/gái xinh).

### 9. TikTok Handle (@username) vs Display Name Formatting & Dot Rules

- **Display Name vs Handle (@username)**:
  * **Display Name (`make_tiktok_name`)**: Accepts full Unicode Vietnamese text with accents and spaces (e.g. *Trần Minh Đạt*, *Linh Bông*). Max 30 chars.
  * **Handle / ID (`make_tiktok_nickname_candidates`)**: Only allows `a-z0-9_.` (lowercase, numbers, underscore, dot). Max 24 chars.
- **Dot (`.`) Distribution Across Batch Slots (Tik 1 vs Tik 2–8)**:
  * **Tik 1 (Initial On-Device Gmail Reg)**: Generates human-like personal identities using `ho.dem.ten` / `dem.ten.so` (~53% contain dots) for maximum profile trust.
  * **Tik 2 ➔ Tik 8 (Scale / Batch Reg / Wholesale Mails)**: Primarily generated with alphanumeric + numbers (e.g., `buithudung2011`, `nhimnhim1565`, `beheo5746`) or derived from external mail accounts (Hotmail/Outlook). Dots are deliberately minimized/omitted (0%–12%) to prevent syntax edge-cases (e.g. trailing dots after length slicing, consecutive `..`, or leading dots) and ensure 100% first-attempt submission success on high-throughput batch runs.
- **Handle Sanitization Invariant**: Always enforce `.strip("._")` and regex `re.sub(r"[^a-z0-9_.]", "", s)` to guarantee no trailing/leading punctuation before typing into the TikTok handle field.

### 10. On-Device TikTok Rename Workflow & Farm Device Lock Coexistence (`do_rename_m*.py`)

When an operator provides a screenshot of a TikTok profile (e.g. `LilyanLederhos64090`, `@lilyanzj8n1`) and requests "Đổi tên nick này":

- **O(1) Account & Hardware Identification**: Query `farm_account_info` and `account_mapping` in `D:/OneDrive/TaadaaData/tiktok_tracker.db` by username (`lilyanzj8n1`) to find device ID, cluster, and slot (e.g. Máy 76, slot 7). Cross-reference with `taikhoan_run_safe.xlsx` (row 608). Never run broad scans across disk.
- **Device Lock & Process Coexistence Preflight**: Inspect `inspect_machine.py <ID>` and `~/.codex/device-locks/serial_<SERIAL>.lock.json`. If a multi-machine feed or follow session (`run_tiktok.py --mode multi-machine-feed-session`) is running on the device, **NEVER** kill the process or force ADB inputs. Wait for the feed session to finish its final swipe loop and release the lock cleanly.
- **State Machine OCR Pattern (`do_rename_m<ID>.py`)**:
  * Wrap in `operator_device_lock(machine=ID, serial=SERIAL, project="do_rename_m...", timeout=300)`.
  * Classify screen via WinRT OCR (`tools/ocr_boxes.ps1`): `FEED`, `PROFILE`, `SWITCHER`, `EDIT_PROFILE`, `NAME_EDIT`, `SAVE_LOGIN_POPUP`.
  * **Phân loại Profile Invariant**: Profile chưa set bio có nút "Thêm tiểu sử" (`id/t3z`). CẤM dùng `"tieu su" in t` đơn độc phân loại `EDIT_PROFILE`. BẮT BUỘC kiểm tra bottom bar navigation (`Hồ sơ` / `H6 sd` ở y > 1800): có bottom bar thì LUÔN là `PROFILE`. Màn `EDIT_PROFILE` không có bottom bar.
  * **Điều hướng UI S7 TikTok v47**:
    - Chạm tiêu đề danh tính `id/t7l` tại `(280, 320)` để bung bảng **Chuyển đổi tài khoản**.
    - Chạm icon bút chì góc trên bên trái `(72, 148)` (`id/pke`) để vào thẳng `EDIT_PROFILE`.
  * Type base64 encoded UTF-8 string qua AdbKeyboard (`ADB_KEYBOARD_INPUT_TEXT`), verify text và bộ đếm ký tự (`len/30`, e.g. `9/30` cho `Linh Bông`), tap "Lưu" `(980, 140)`.
  * BẮT BUỘC xác nhận popup *"Đặt biệt danh? Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần"* tại `(747, 1173)`.
  * Readback verify: đọc lại màn hình Hồ sơ qua OCR, xác nhận dòng hiển thị ngay trên `@username` khớp với tên mới (`Linh Bông` trên `@lilyanzj8n1`).
- **Hermetic Offline Pytest**: Create `tests/test_do_rename_m<ID>.py` testing `norm`, `compact`, `classify`, `is_target`, `is_target_user`, and `nickname_on_profile` offline (<0.5s) to guarantee zero regression before device execution.
- **Tiered Workflow Dispatch Contract**: Script generation exceeds Coordinator T1 direct-write budget (<= 200 lines). Dispatch Worker via `delegate_task` with mandatory headers in `context`: `TASK_KIND: EDIT`, `TARGET_FILE: ...`, `TEST_FILE: ...`, and `FOCUSED_TEST: python -m pytest <path>::<node>` to satisfy Coordinator Guard.
- **Background Execution**: Launch via `terminal(command="python D:/Taadaa/tools/do_rename_m<ID>.py", background=True, notify_on_complete=True, timeout=300)` adhering to event-driven wakeup.

## Integration Point

```python
def generate_account_for_slot(slot, existing_emails=None, max_attempts=300):
    ho, dem, ten_chinh, ten = generate_random_name()
    acc = {
        "ho": ho,
        "dem": dem,
        "ten_chinh": ten_chinh,
        "ten": ten,
        "ngay": ngay, "thang": thang, "nam": nam,
    }
    acc["id"] = build_username(acc)
    acc["pass"] = build_password(acc)
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Fix |
|--------------|--------------|-----|
| Fixed 2-word names | Low entropy, collisions | Add DEM_POOL + 3/4-word distribution |
| Unescaped spaces in ADB typing | `adb shell input text` splits args on spaces → drops trailing words / leaves `firstName` empty → `STILL_ON_NAME` error | Encode spaces as `%s` in `input_text` or use KEYCODE_SPACE (`keyevent 62`) in `human_type` |
| Unescaped shell symbols in passwords | `#` is treated as shell comment, `&` as background, `(` `)` as syntax error | Use `keyevent 77` for `@`, `keyevent 18` for `#`, escape shell characters |
| Salt in middle of DOB (`nameabc1502`) | Obvious bot pattern | Use dots, natural combos, suffixes |
| Fixed password suffix (`@Ks`) | Cross-account fingerprint | Random symbols + random structures |
| No dots in username | Unrealistic for VN users | Include `.` in 50%+ patterns |
| Immediate abort on taken username | Wastes machine preflight, proxy rotation, and UI progress when 1 candidate collides | Implement `handle_username_entry()` retry loop up to 5 times with `build_username()` + sync `acc["id"]` + `clear=True` |
| MOVE_END + DEL clear in WebView | `MOVE_END` does not reach end in Google Sign-in WebView → appends new text to old string → overflows 30 chars | Use Select All (`Ctrl+A` / `KEYCODE_A` with `META_CTRL_ON`) then `KEYCODE_DEL` or verify field is empty |
| Immediate error check after tap_next | Google server verification takes 1–2s → script reads stale collision text from prior attempt | Wait for loading overlay/spinner to vanish or UI transition before scanning error text |
| Bare 2–3 digit usernames | Short Vietnamese names with 2–3 digits collide >90% on Google | Target 16–26 chars with 4 digits, salts, or natural suffixes right from Attempt 1 |
| Truncating at 30 chars on a dot | `u[:30]` can cut mid-dot leaving trailing `.` → violates Google username format | Always apply `rstrip('.')` immediately after any length slice |
| Truncating after appending retry extra | `(u + extra)[:30]` cuts off the newly added retry salt/numbers | Slice base first: `u[:30 - len(extra)].rstrip('.') + extra` to preserve full retry entropy |

## Verification

- Generate 1000+ samples, verify uniqueness rate > 99.9%
- Visual inspection: outputs should look like real VN users
- No duplicate patterns across batches

## References

- `references/gmail-reg-case.md` — Case study from `register gmail` repo
- `references/on-device-rename-state-machine-and-lock-coexistence.md` — Complete on-device TikTok rename workflow, state-machine OCR pattern, device lock coexistence, and hermetic offline testing
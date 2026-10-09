# GPM Gmail Nurture: Anti-Loop & Concurrency Pitfalls

## 1. Filter Out `NEEDS_LOGIN` (Anti-Loop Selection)
Khi script nuôi phát hiện profile chưa có session Google hợp lệ (Preflight Cookie Guard phát hiện < 2 session tokens `SID/SSID/HSID/SAPISID`), profile bị đánh dấu `status: NEEDS_LOGIN`.
- **Pitfall**: Vòng tuyển chọn `due_profiles` nếu chỉ lọc theo `last_nurtured` sẽ liên tục bốc lại các acc `NEEDS_LOGIN` này (vì `last_nurtured = 0` được ưu tiên xếp đầu danh sách). Hậu quả là mỗi tick cron mở lên -> fail -> đóng -> tick sau lại bốc đúng acc đó -> spam báo cáo lỗi vô tận.
- **Quy chuẩn**: BẮT BUỘC bỏ qua ngay trong vòng lọc ứng viên:
  ```python
  if info.get("status") == "NEEDS_LOGIN":
      continue
  ```

## 2. Nâng công suất nuôi Farm (Concurrency & Stagger)
- Nuôi 150+ profile trên máy trạm Dual Xeon: Nếu để mặc định `--limit 2` thì cần 11 ngày mới xong 1 vòng.
- Cấu hình chuẩn khuyến nghị: `--limit 6` hoặc `--limit 8`, `--concurrency 5` (cuốn chiếu song song theo chỉ thị), `--stagger 45`.
- Tương tự, `post_evening_gpm_login_watchdog.py` dùng `MAX_WORKERS = 5` cuốn chiếu so le.
- Mỗi profile bắt buộc dùng 1 cổng proxy 4G riêng biệt.
- **Lưu ý Unit Test**: Khi nâng `MAX_WORKERS` lên 5, cần cập nhật assert tương ứng trong `test_watchdog_link_chatgpt_idle.py` (`self.assertEqual(w_gpm.MAX_WORKERS, 5)`). Ngoài ra, hàm `get_live_targets()` lọc qua `pending_gpm = get_gpm_pending_emails()`; trong test suite mock Excel cần patch kèm `get_gpm_pending_emails` trả về email hợp lệ để test target detection không bị fail (len targets == 0).

## 3. Threading Lock & Atomic Update cho State File (Chống Lost Update)
Khi chạy `--concurrency > 1` (đa worker song song cập nhật `last_nurtured` vào state file JSON chung):
- Load-modify-save riêng lẻ vẫn gây lost update giữa các thread. BẮT BUỘC gộp thành hàm atomic `update_profile_state(email, entry)` thực hiện đọc - sửa - ghi trọn vẹn bên trong `threading.Lock()`.
- Ghi ra file tạm rồi `os.replace` để bảo đảm file JSON không bao giờ bị corrupt khi tiến trình bị ngắt giữa chừng.
- Báo cáo rõ nhãn trạng thái: `CHƯA_LOGIN (NEEDS_LOGIN)` thay vì ghi generic `FAIL`.

## 4. Polling CDP Socket Readiness (Tránh ECONNREFUSED)
Khi gọi API `/api/v3/profiles/start/{id}`, GPM trả về địa chỉ `remote_debugging_address` (ví dụ `127.0.0.1:65249`) ngay lập tức, nhưng tiến trình Chromium chưa kịp lắng nghe socket:
- **Pitfall**: Dùng `time.sleep(2)` cố định có thể fail với `connect ECONNREFUSED` trên máy tải cao.
- **Quy chuẩn**: Poll socket TCP trước khi gọi Playwright `connect_over_cdp`:
  ```python
  if remote_port:
      for _ in range(15):
          try:
              with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                  s.settimeout(1.0)
                  if s.connect_ex(('127.0.0.1', remote_port)) == 0:
                      break
          except Exception:
              pass
          time.sleep(1)
  ```

## 5. Mock Socket trong Pytest (Bảo vệ Closeout Gate Timeout 60s)
- **Pitfall**: Khi viết unit test cho các hàm có vòng lặp poll socket port (như trên), nếu port giả lập (59000) không lắng nghe, mỗi test case sẽ ngốn đủ 15s. Nhiều test cases cộng lại sẽ vượt ngưỡng timeout 60s của `closeout_gate.py`.
- **Quy chuẩn**: Trong fixture/mock test, BẮT BUỘC mock `socket.socket`:
  ```python
  with patch("socket.socket") as mock_sock:
      mock_sock.return_value.__enter__.return_value.connect_ex.return_value = 0
  ```
  Giúp test suite chạy xong trong <10s, bảo đảm vượt qua Closeout Gate.

## 6. Structured Telemetry Metric Event
Ghi nhận telemetry có cấu trúc JSON để phục vụ quan sát hệ thống & watchdog:
- Log sự kiện từng profile: `profile_nurture_complete` kèm `duration_s`, `behavior_type`, `status`.
- Log sự kiện tổng kết: `batch_nurture_summary` kèm `success_rate`, `total_count`.

## 7. Quy chuẩn Lưu trữ Bằng chứng & Giám sát Lịch sử Nuôi (Logs & Visual Evidence)
Mọi phiên nuôi tự động đều bắt buộc ghi nhận và bảo lưu bằng chứng thực tế tại 3 vị trí:
1. **File Log chi tiết từng mili-giây**: `D:/Taadaa/GPM auto/logs/cron_gpm_gmail_nurture.log` — ghi nhận tường tận từng bước: URL video/bài báo, từ khóa tìm kiếm, hành vi skip ad, thời lượng chính xác, và lệnh đóng dọn Chromium.
2. **File State JSON chu kỳ nuôi**: `D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json` — theo dõi `last_nurtured`, `last_nurtured_iso`, `duration_seconds`, `status` (`success`, `NEEDS_LOGIN`).
3. **Ảnh nghiệm thu thực tế (Screenshot Evidence)**: `D:/Taadaa/GPM auto/debug_screenshots/nurture_<email>.png` — chụp ngay khoảnh khắc tài khoản đang phát video `/watch` hoặc đang đọc bài báo Google News.

## 8. Đánh giá Thời lượng & Chu kỳ Nuôi (Entropy & Google Trust Modeling)
- **Thời lượng 120s – 186s (2 - 3 phút)**: Đủ để phát sinh tín hiệu duyệt web cơ bản và giữ alive session, không phải nguyên nhân khiến Google phạt bot.
- **Rủi ro Low-Entropy Automation**: Vấn đề nguy hiểm nhất là tính lặp lại máy móc:
  + Chu kỳ 5 ngày/lần cố định: Dễ để lại pattern tuần hoàn nhân tạo. Khuyến nghị áp dụng cửa sổ jitter ngẫu nhiên **3 – 6 ngày**.
  + Thời lượng session: Nên phân phối biến thiên từ **90s đến 250s** thay vì bó hẹp quanh mốc 150s.
  + Đa dạng hóa hành vi: Bổ sung các phiên glance nhẹ (10-15s) vào Gmail Inbox, Google Search đời sống hoặc Google Maps để tăng entropy hành vi.

## 9. Cạm bẫy Tự động Bỏ qua Quảng cáo YouTube (YouTube Ad Skip Pitfalls)
Khi tự động hóa tương tác YouTube trong Playwright CDP:
- **Pitfall 1: Phụ thuộc CSS selector cũ (`.ytp-skip-ad-button`)**: YouTube liên tục cập nhật DOM sang Polymer Web Components (`<yt-button-renderer>`, `<tp-yt-paper-button>`) hoặc Shadow DOM.
  - *Quy chuẩn*: Phối hợp bắt đa tầng gồm CSS class hiện đại, text button đa ngữ, aria-label, và nút đóng overlay banner:
    ```python
    YOUTUBE_AD_SKIP_SELECTORS = [
        "button.ytp-skip-ad-button",
        ".ytp-ad-skip-button",
        "button.ytp-ad-skip-button-modern",
        "[class*='ytp-ad-skip-button']",
        ".ytp-skip-ad-button-modern",
        "button:has-text('Bỏ qua')",
        "button:has-text('Skip')",
        "button:has-text('Skip Ads')",
        "button[aria-label*='Bỏ qua']",
        "button[aria-label*='Skip']",
        "[aria-label*='Bỏ qua quảng cáo']",
        "[aria-label*='Skip ad']",
        ".ytp-ad-overlay-close-button",
        "button.ytp-ad-overlay-close-button",
        "[class*='ytp-ad-overlay-close']"
    ]
    ```
- **Pitfall 2: Dùng `click(force=True)`**: Tạo ra synthetic click event thiếu chuỗi tọa độ thực (`mousemove` -> `hover` -> `mousedown` -> `mouseup`), dễ bị anti-bot CDP fingerprinting phát hiện.
  - *Quy chuẩn*: Di chuột mô phỏng người thật qua `bounding_box()`:
    ```python
    box = btn.bounding_box()
    if box:
        target_x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
        target_y = box["y"] + box["height"] / 2 + random.uniform(-2, 2)
        page.mouse.move(target_x, target_y, steps=random.randint(6, 12))
        time.sleep(random.uniform(0.3, 0.7))
        page.mouse.down()
        time.sleep(random.uniform(0.08, 0.15))
        page.mouse.up()
    ```
- **Pitfall 3: Polling cố định & Non-skippable Bumper Ads (15s)**:
  - Polling cứng mỗi 2.0s là hành vi bot rõ rệt. Cần polling có jitter biến thiên `random.uniform(1.8, 3.2)`.
  - Phân biệt quảng cáo bằng WinRT OCR (`scripts/winrt_ocr.py`):
    + Nếu OCR thấy `15s Video` / `Google Ads`: Đây là Bumper Ads không thể skip, YouTube ép xem hết 15s.
    + Nếu OCR thấy `Bỏ qua` / `Skip`: Quảng cáo TrueView có nút bấm thực sự.
- **Pitfall 4: Bị che khuất bởi Popup YouTube Premium / Khảo sát**:
  - Khi xem YouTube thường xuất hiện dialog mời mua Premium hoặc khảo sát ("Không, cảm ơn", "Để sau"). Cần tự động dismiss:
    ```python
    YOUTUBE_DISMISS_POPUPS = [
        "ytd-button-renderer:has-text('Không, cảm ơn') button",
        "ytd-button-renderer:has-text('Để sau') button",
        "button[aria-label='Đóng']",
        "#dismiss-button button"
    ]
    ```
- **Pitfall 5: Liking cố định sau 25s**: Thao tác like đúng 25s sau khi mở video là một signature automation dễ bị phát hiện.
  - *Quy chuẩn*: Giảm xác suất like xuống mức 30-35%, tính thời điểm like ngẫu nhiên `like_at_second = random.randint(int(watch_duration * 0.35), int(watch_duration * 0.85))` thay vì cố định 25s.

## 10. Chặn Quét Mù Profile Toàn Farm & Rào Chắn GroupId (Blind Selection & Exclusion Leak Pitfall)
- **Cạm bẫy**:
  Script nuôi (`cron_gpm_gmail_nurture.py`) nếu chỉ gọi `GET /api/v3/profiles` rồi lọc regex `@gmail.com` thì sẽ bốc nhầm:
  1. Profile rỗng mới sinh hoặc đang nằm ở `GroupId = 1 ('All')` chưa từng đăng nhập Google.
  2. Các tài khoản dính mail khôi phục `khoale` / `khoaleemagic` (vốn là diện **Hard Exclusion** trong watchdog login để tránh dính checkpoint) nhưng vẫn tồn tại profile rỗng trên GPM. Khi script nuôi bốc lên, Preflight Cookie Guard phát hiện 0 token, lập tức đóng lại và spam cảnh báo `CHƯA_LOGIN (NEEDS_LOGIN)`.
  3. **Case-insensitive & Regex Inconsistency**: Nếu `extract_email(name)` chỉ dùng regex `[a-zA-Z0-9_.+-]+@gmail\.com` mà không có `re.IGNORECASE`, khi profile name chứa email viết hoa (e.g. `KHOALE_UPPER@GMAIL.COM`), regex trả về `""` và profile bị skip trước khi tới tầng kiểm tra blacklist, làm sai lệch bộ đếm telemetry `skipped_blacklist`.
- **Quy chuẩn bắt buộc**:
  1. **Tách Hàm Lọc Production Chuẩn (`filter_nurture_candidates`)**:
     Tách logic lọc ra hàm độc lập `filter_nurture_candidates(all_profiles, target_group_id=DEFAULT_NURTURE_GROUP_ID, allow_all_groups=False)` trả về `(candidates, skipped_group, skipped_blacklist)` để dễ dàng unit test toàn diện:
     ```python
     def filter_nurture_candidates(all_profiles, target_group_id=DEFAULT_NURTURE_GROUP_ID, allow_all_groups=False):
         candidates = []
         skipped_group = 0
         skipped_blacklist = 0
         for p in all_profiles:
             name = p.get("name", "")
             email = extract_email(name)
             if not email:
                 continue
             email_lower = email.lower()
             if any(kw.lower() in email_lower for kw in EXCLUDED_EMAIL_KEYWORDS):
                 skipped_blacklist += 1
                 continue
             if not allow_all_groups:
                 gid = p.get("group_id")
                 try:
                     gid_int = int(gid) if gid is not None else 0
                 except (ValueError, TypeError):
                     gid_int = 0
                 if gid_int != target_group_id:
                     skipped_group += 1
                     continue
             p_copy = dict(p)
             p_copy["email"] = email
             candidates.append(p_copy)
         return candidates, skipped_group, skipped_blacklist
     ```
  2. **Regex Khớp Email Tuyệt Đối Case-Insensitive**:
     Hàm `extract_email` bắt buộc truyền cờ `re.IGNORECASE` và trả về dạng lower-case:
     ```python
     def extract_email(name: str) -> str:
         m = re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', name, re.IGNORECASE)
         return m.group(1).lower() if m else ""
     ```
  3. **Rào chắn GroupId & Type-Safe Cast**: Script nuôi CHỈ ĐƯỢC bốc profile từ các nhóm đã đăng nhập thành công (`group_id == 10` tức `Google_Live_Ready`), TUYỆT ĐỐI KHÔNG quét mù toàn bộ `GroupId = 1` ('All'). Lưu ý API GPM có thể trả `group_id` dạng `int`, `str`, hoặc `None`, do đó bắt buộc ép kiểu an toàn (`try...except`).
  4. **Đồng bộ Dual-Path cho Script Nuôi**:
     Bất cứ khi nào cập nhật `cron_gpm_gmail_nurture.py`, BẮT BUỘC đồng bộ ngay lập tức giữa 2 đường dẫn:
     - Gốc: `D:/Taadaa/GPM auto/scripts/cron_gpm_gmail_nurture.py`
     - Hermes runtime: `C:/Users/Kibe/AppData/Local/hermes/scripts/cron_gpm_gmail_nurture.py`
     Sau khi copy, chạy `python -m py_compile` và `pytest` trên file kiểm thử để đảm bảo tính toàn vẹn cú pháp và logic.
  5. **Đồng bộ Hard Exclusion**: Mọi layer tự động (tạo profile, watchdog login, nuôi) phải đồng nhất bộ lọc loại trừ các tài khoản blacklist/mail khôi phục `khoale`. Nếu profile dính `khoale` lọt vào GPM thì script nuôi phải lọc bỏ ngay từ vòng duyệt candidates.

## 11. Cấm Tuyệt Đối Watchdog Phụ Trợ Tự Ý Tạo Profile GPM (Creation Isolation Invariant)
- **Cạm bẫy bắc cầu (Cross-Script Ghost Profile Leak)**:
  - Khi watchdog phụ trợ (ví dụ `post_morning_gmail_2fa_watchdog.py`) quét bảng tính `gmail_clean_v2.xlsx` để tìm acc chưa bật 2FA (`two_fa is None`), nếu thấy acc chưa có profile trong GPM DB (`if not pid:`) thì tự tiện gọi API `POST /api/v3/profiles/create`.
  - **Lỗ hổng kép**:
    1. Watchdog 2FA bỏ sót kiểm tra cột `Recovery_Email` (Cột 4), khiến tài khoản dính mail khôi phục `khoale`/`khoaleemagic` (vốn là diện **Hard Exclusion cấm login** trên PC) vẫn bị tạo profile rỗng trên GPM ở `GroupId = 1 ('All')`.
    2. Khi mở profile lên để cấu hình 2FA thì thấy chưa đăng nhập Google $\to$ watchdog 2FA báo fail và tắt trình duyệt, **nhưng bỏ rơi lại profile rác trong GPMLogin DB**.
    3. Đến chu kỳ nuôi tiếp theo, `cron_gpm_gmail_nurture.py` thấy profile rỗng mới tinh (`last_nurtured = 0`) liền bốc lên nuôi $\to$ Preflight Cookie Guard thấy 0 token $\to$ văng cảnh báo `CHƯA_LOGIN (NEEDS_LOGIN)`. Trong khi watchdog login ban đêm lại từ chối login do dính `khoale`.
- **Quy chuẩn bất di bất dịch**:
  1. **Thẩm quyền Tạo Profile Duy Nhất**: TUYỆT ĐỐI KHÔNG cho phép các watchdog phụ trợ (bật 2FA, nuôi Gmail, checkmail, lướt web) tự gọi API `create_profile`. Quyền tạo profile mới chỉ thuộc về `sync_gpm_lifecycle.py` hoặc batch login pipeline có kiểm soát.
  2. **Fail-Fast Khi Thiếu Profile**: Nếu watchdog 2FA thấy acc chưa có profile GPM hoặc profile chưa đăng nhập Google, BẮT BUỘC bỏ qua (SKIP), không được tự ý tạo profile mới.
  3. **Đồng bộ 100% Bộ Lọc Recovery Email**: Bất kỳ script nào duyệt danh sách Gmail (kể cả 2FA watchdog) đều phải có guard kiểm tra chặt chẽ:
     ```python
     if "khoale" in email.lower() or "khoale" in recovery_email.lower():
         continue
     ```

## 12. Quy trình Phát hiện & Dọn Dẹp Profile Rác / Ghost Profile (Ghost Profile Audit & Remediation)
Khi phát hiện sự cố watchdog phụ trợ tự ý spawn hàng loạt profile rỗng dính blacklist/khoale:
1. **Truy vấn định danh chính xác (O(1) SQLite)**:
   ```python
   # Lọc các profile tạo trong ngày có tên chứa email thuộc danh sách blacklist/khoale
   conn = sqlite3.connect(GPM_DB_PATH)
   cur = conn.cursor()
   cur.execute("SELECT Id, Name, GroupId, CreatedAt FROM Profiles WHERE CreatedAt LIKE 'YYYY-MM-DD%'")
   ghost_targets = [row for row in cur.fetchall() if any(em in row[1].lower() for em in khoale_emails)]
   conn.close()
   ```
2. **Xóa profile qua GPMLogin API (Bắt buộc `mode=2`)**:
   - Gọi API xóa profile: `requests.get(f"http://127.0.0.1:19995/api/v3/profiles/delete/{pid}", params={"mode": 2}, timeout=10)`.
   - **Cạm bẫy chết người (`mode=1` vs `mode=2`)**: `mode=1` chỉ áp dụng soft delete / Cloud trash, SQLite `profile_data.db` vẫn giữ nguyên bản ghi profile! BẮT BUỘC dùng `mode=2` để xóa dứt điểm bản ghi trong bảng `Profiles`.
   - Đối soát lại SQLite `profile_data.db` đảm bảo bản ghi đã được dọn sạch (count = 0).
3. **Thanh tẩy State File (Nurture State Purge)**:
   - Xóa bỏ các key email bị ảnh hưởng khỏi `D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json` để loại bỏ toàn bộ trạng thái lỗi giả `NEEDS_LOGIN`.

## 13. Tiêu chuẩn Code Audit & Unit Test cho Bộ Lọc Profile Nurture (Sol Auditor Standards)
Khi triển khai và review code cho script nuôi Gmail (`cron_gpm_gmail_nurture.py`), tuân thủ nghiêm ngặt 5 quy chuẩn Sol Auditor:
1. **Thứ tự Logger Khởi tạo**:
   - Tuyệt đối không đặt hàm có gọi `logger.debug/info` trước khối khởi tạo `logging.basicConfig` và `logger = logging.getLogger(...)`. Nếu đặt trước, khi file được import hoặc chạy sẽ có nguy cơ dính `NameError: name 'logger' is not defined` hoặc ghi đè handler sai lệch.
2. **Tham số hóa & CLI Override cho Blacklist (`exclude_keywords`)**:
   - Hàm `filter_nurture_candidates` bắt buộc nhận tham số `exclude_keywords: Tuple[str, ...] = EXCLUDED_EMAIL_KEYWORDS`.
   - Bổ sung CLI argument `--exclude-keywords` (sử dụng `nargs="*"`, default là `EXCLUDED_EMAIL_KEYWORDS`) trong `main()`, truyền `tuple(args.exclude_keywords)` vào hàm lọc. Không hardcode biến toàn cục cứng nhắc bên trong hàm lõi.
   - Bắt buộc có test case độc lập (`test_exclude_keywords_cli_override`) xác thực khả năng ghi đè danh sách từ khóa loại trừ qua tham số / CLI.
3. **Kiểm thử Đầy đủ Biến Thể Blacklist (`khoale`, `khoalee`)**:
   - Bộ test suite `test_cron_gpm_gmail_nurture.py` phải chứa mẫu test cho cả `khoale` và `khoalee` (ví dụ `09 - khoalee_user@gmail.com`).
4. **Assert Độc Lập cho `skipped_blacklist` trong Từng Scenario**:
   - Khi test custom `target_group_id` (ví dụ `target_group_id=1`), phải assert cụ thể cả `skipped_g1` và `skipped_b1` (số lượng bị loại bởi blacklist độc lập với group filter). Không được bỏ sót assert `skipped_b1`.
5. **Main Smoke Test Toàn Diện & Pitfalls**:
   - Viết unit test mock cho hàm `main()` (mock `get_all_gpm_profiles`, `load_state`, `nurture_profile`, `time.sleep`, CLI `argparse`) để kiểm tra toàn bộ luồng tích hợp, đảm bảo CLI args, phân luồng worker, và format báo cáo hoạt động trơn tru không lỗi runtime.
   - **Pitfall 1 - Thiếu trường `id` trong mock profiles**: Trong `worker_task` khi nuôi thành công, script gọi `update_profile_state(em, {"profile_id": p["id"]})`. Do đó mọi dict profile trong `mock_profiles` bắt buộc phải có trường `"id"` (ví dụ `{"id": "5101", "name": "...", "group_id": 10}`), nếu thiếu sẽ dính `KeyError: 'id'`.
   - **Pitfall 2 - Bị stall bởi Cron Jitter Delay**: Khi chạy `main()` tự động (không truyền `--email`), script tiêm jitter ngẫu nhiên `time.sleep(random.randint(10, 60))`. BẮT BUỘC mock `monkeypatch.setattr(nurture_mod.time, "sleep", lambda s: None)` để smoke test chạy tức thì (<5s) thay vì ngốn 50s+ gây timeout harness/gate.
   - **Pitfall 3 - Bỏ quên assertion trên mock state update**: Khi mock `update_profile_state`, phải assert rõ ràng `mock_update.call_count >= 1` và email được cập nhật đúng là email live, không chỉ kiểm tra riêng `nurture_profile`.
6. **Kiểm soát Tương thích Phiên bản Python & Type Hints**:
   - Sử dụng `Tuple` từ `typing` (`from typing import Tuple, List, Dict, Any`) thay vì `tuple[...]` để tránh crash cú pháp khi chạy trên môi trường Python < 3.9.
7. **Safety Guard & Alert Logging**:
   - Khi cờ `--all-groups` được kích hoạt, bắt buộc ghi log `logger.warning("[SAFETY_GUARD] allow_all_groups=True: Bỏ qua kiểm tra GroupId...")`.
   - Khi phát hiện và lọc bỏ profile blacklist, bắt buộc ghi log `logger.warning(f"[BLACKLIST_ALERT] Phát hiện và lọc bỏ {skipped_blacklist} profile chứa từ khóa bị cấm!")`.
8. **Edge-case Test Profile Rỗng `{}`**:
   - Hàm `filter_nurture_candidates` phải chịu được dict rỗng `{}` mà không văng `KeyError`. Test suite cần chứa test case dict rỗng để đảm bảo độ phủ 100%.
9. **Xử lý An toàn Float GroupId & Float Boundary Rejection (Strict Integer Boundary)**:
   - Dữ liệu trả về từ GPM API hoặc parse JSON/SQLite đôi khi có trường `group_id` biểu diễn dưới dạng float số thực (e.g. `10.0`) hoặc chuỗi float (e.g. `"10.0"`).
   - **Cạm bẫy Float Boundary 10.7**: Nếu chỉ ép kiểu mù quáng `int(float(gid))`, các giá trị float không nguyên (như `10.7` hay `"10.7"`) sẽ bị làm tròn cụt thành `10`, dẫn tới lọt profile sai nhóm vào luồng nuôi!
   - **Quy chuẩn**: Bắt buộc kiểm tra tính nguyên vẹn (`.is_integer()`), chỉ chấp nhận float tròn số nguyên:
     ```python
     gid = p.get("group_id")
     try:
         if isinstance(gid, float):
             gid_int = int(gid) if gid.is_integer() else 0
         else:
             val_str = str(gid).strip()
             val_float = float(val_str)
             gid_int = int(val_float) if val_float.is_integer() else 0
     except (ValueError, TypeError):
         gid_int = 0
     ```
   - Trong test suite, bắt buộc kiểm thử ranh giới (`test_filter_candidates_float_group_id_boundary`): `10.0` được chấp nhận, nhưng `10.7` bắt buộc bị từ chối (`skipped_group == 1`).

10. **Bất biến Thứ tự Kiểm tra: Blacklist Trước GroupId (Simultaneous Blacklist Invariant)**:
    - Khi một profile đồng thời dính blacklist (e.g. `khoale@gmail.com`) VÀ nằm sai nhóm (e.g. `group_id: 1` thay vì `10`):
    - **Invariant**: Bộ lọc blacklist cấm tài khoản độc hại tuyệt đối phải được kích hoạt TRƯỚC bộ lọc GroupId.
    - Kết quả thống kê bắt buộc: `skipped_blacklist` tăng 1, `skipped_group` giữ nguyên 0 (profile bị drop ngay từ cửa blacklist).
    - Cần có test case riêng: `test_filter_candidates_simultaneous_blacklist_and_wrong_group`.

11. **Kiểm thử Telemetry Payload Metric (`filter_candidates_summary`)**:
    - Khi script phát sự kiện `log_telemetry_metric("filter_candidates_summary", data)`, unit test cần mock và bắt payload để assert cấu trúc dữ liệu metric:
      - `total_profiles_found`: tổng profile phát hiện.
      - `eligible_candidates`: số lượng profile hợp lệ đủ điều kiện nuôi.
      - `target_group_id`, `allow_all_groups`.
      - `skipped_wrong_group`, `skipped_blacklist`.
    - **Mẫu test chuẩn (`test_filter_candidates_telemetry_payload` / `test_main_telemetry_emission_integration`)**:
      ```python
      def test_filter_candidates_telemetry_payload(monkeypatch):
          emitted = []
          monkeypatch.setattr(nurture_mod, "log_telemetry_metric", lambda event, data: emitted.append((event, data)))
          mock_profiles = [
              {"id": "p1", "name": "01 - valid1@gmail.com", "group_id": 10},
              {"id": "p2", "name": "02 - khoale@gmail.com", "group_id": 10},
              {"id": "p3", "name": "03 - other@gmail.com", "group_id": 1},
          ]
          monkeypatch.setattr(nurture_mod, "get_all_gpm_profiles", lambda: mock_profiles)
          monkeypatch.setattr(nurture_mod, "load_state", lambda: {})
          monkeypatch.setattr(nurture_mod, "save_state", lambda s: None)
          monkeypatch.setattr(nurture_mod.time, "sleep", lambda s: None)
          monkeypatch.setattr(sys, "argv", ["cron_gpm_gmail_nurture.py", "--limit", "1", "--stagger", "0", "--concurrency", "1"])
          with patch.object(nurture_mod, "nurture_profile", return_value=(True, "SUCCESS")), \
               patch.object(nurture_mod, "update_profile_state"):
              nurture_mod.main()

          summary_events = [data for ev, data in emitted if ev == "filter_candidates_summary"]
          assert len(summary_events) == 1
          p = summary_events[0]
          assert p["total_profiles_found"] == 3
          assert p["eligible_candidates"] == 1
          assert p["target_group_id"] == 10
          assert p["allow_all_groups"] is False
          assert p["skipped_wrong_group"] == 1
          assert p["skipped_blacklist"] == 1
      ```
    - Điều này đảm bảo hệ thống quan sát tập trung (watchdog / dashboard) luôn nhận đúng schema telemetry chuẩn.
12. **Hỗ trợ Override Exclusion Keywords qua Environment Variable (`GPM_NURTURE_EXCLUDED_KEYWORDS`)**:
    - Khi cron job hoặc runner tự động kích hoạt script mà không tiện truyền CLI flags `--exclude-keywords`, script cần fallback đọc biến môi trường:
      ```python
      DEFAULT_EXCLUDED_KEYWORDS = ("khoale", "khoalee")
      EXCLUDED_EMAIL_KEYWORDS = tuple(
          [k.strip().lower() for k in os.environ.get("GPM_NURTURE_EXCLUDED_KEYWORDS", "").split(",") if k.strip()]
      ) or DEFAULT_EXCLUDED_KEYWORDS
      ```
    - Cho phép điều chỉnh blacklist động trên runtime farm mà không cần sửa code script.

## 14. Phân Biệt START_FAILED (Lỗi Proxy/DNS Cụm) vs NEEDS_LOGIN (Mất Session) & Chẩn Đoán MobiProxy Healer
Khi nhận Farm Alert hoặc Cronjob Watchdog báo lỗi nuôi hàng loạt (`FAIL (START_FAILED, xx.xs)`):
- **Cạm bẫy hoang mang**: Nhầm lẫn `START_FAILED` với việc tài khoản bị Google checkpoint hoặc mất session `NEEDS_LOGIN`, dẫn đến tự ý chạy script cứu phiên / login đè làm nát profile.
- **Bản chất kỹ thuật**:
  - GPM Local API (`19995`) khi nhận lệnh `start` sẽ kiểm tra tính kết nối của `raw_proxy` gán trên profile (`test.taadaa.click:51xx`).
  - Nếu proxy rớt kết nối hoặc DNS của cụm proxy bị nghẽn (`Errno 11001 getaddrinfo failed`), GPM sẽ fail ngay với thông báo `"Không thể kết nối tới proxy"` sau 3 lần thử $\to$ script gán nhãn `START_FAILED`.
  - Khi dính `START_FAILED`, script **tuyệt đối KHÔNG** đánh dấu `NEEDS_LOGIN` vào `gpm_gmail_nurture_state.json`. Các profile vẫn giữ nguyên trạng thái hợp lệ và nằm ở đầu hàng đợi chờ tick tiếp theo.
- **Quy trình chẩn đoán O(1)**:
  1. **Tra cứu log MobiProxy Auto-Healer**: Đọc `D:/Taadaa/AI-Tools/logs/mobiproxy_healer.log` để xác định sự cố cụm (rớt DNS diện rộng hay die port cục bộ, thời điểm auto-healer đã phục hồi thành công).
  2. **Kiểm tra socket và curl IP thực tế**:
     - Socket probe: `python -c "import socket; s = socket.socket(); s.settimeout(3); print(s.connect_ex(('test.taadaa.click', <port>)))"`.
     - Curl IP qua proxy: **Bẫy URI syntax**: Password chứa ký tự `#` (e.g. `TaadaaMobi#2026!`) sẽ làm gãy URI parser nếu nhúng `http://user:pass@host:port`. BẮT BUỘC dùng `-U "user:pass" -x "http://host:port"`.
  3. **Canary test GPM API**: Thử `GET http://127.0.0.1:19995/api/v3/profiles/start/{id}?win_scale=0.8` và đóng ngay `GET .../profiles/close/{id}` để nghiệm thu API đã sẵn sàng.
  4. **Kỷ luật xử lý**: Tuyệt đối không can thiệp đè credentials hay xóa profile. Đợi auto-healer phục hồi proxy hoặc tick cron tiếp theo chạy bù tự động.



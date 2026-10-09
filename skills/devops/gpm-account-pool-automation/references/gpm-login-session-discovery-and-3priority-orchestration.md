# GPM Login Session Discovery & 4-Priority Orchestration

## 1. Bản chất Account Trust vs 2FA trong Google Login trên GPM
- **Sai lầm phổ biến:** Cho rằng tài khoản bắt buộc phải có 2FA Secret mới đăng nhập được trên PC.
- **Sự thật thực tế:**
  - Đăng nhập Google trên môi trường PC mới phụ thuộc chủ yếu vào **Account Trust Score** (được bồi đắp từ thời gian ngâm và tương tác thực tế của tài khoản trên thiết bị Android gốc).
  - Tài khoản có Trust Score tốt dù **không có 2FA** vẫn đăng nhập thẳng chỉ với Email + Password.
  - Tài khoản ngâm tĩnh, chưa tương tác người dùng thật thì khi mở qua proxy mới rất dễ bị Google gắn cờ Hard Phone Checkpoint (`challenge/iap`).

## 2. Phát hiện Session Cookie có sẵn trong Profile GPM (Quick Win)
- Nhiều tài khoản từ ca trước đã đăng nhập thành công nhưng TIMEOUT ở bước OAuth do proxy chậm. Khi mở lại sẽ hiện Account Chooser, script chỉ cần click chọn tên.
- Kiểm tra bằng `_get_gpm_profiles_with_google_session()`: đọc file SQLite `Default/Network/Cookies`, đếm token SID/SSID/HSID/SAPISID — nếu ≥ 2 thì có session.

## 3. Phân tách rành mạch trách nhiệm giữa các Cronjob
- **`sync_gpm_lifecycle.py` (07:15-08:45):** Quét Excel tìm Gmail LIVE → sinh Profile GPM + proxy, dọn profile DIE. (Có thẩm quyền duy nhất trong việc tạo profile định kỳ).
- **`cron_gpm_gmail_nurture.py` (9h/11h/13h...):** Chạy Preflight Cookie Guard (Playwright CDP), ghi `NEEDS_LOGIN` vào nurture state khi session văng. CHỈ nuôi profile thuộc `GroupId = 10` ('Google_Live_Ready'). **CẤM TUYỆT ĐỐI tự ý gọi hàm login hoặc pipeline đăng nhập trong script nuôi.**
- **`post_evening_gpm_login_watchdog.py` (Chạy 3 ca: Sáng 07:15-08:45, Trưa 12:00-13:45, Tối 20:15-23:45):** Là đơn vị DUY NHẤT có thẩm quyền tự động gọi `run_login()` (`run_oauth_s7_pipeline.py`). TUYỆT ĐỐI KHÔNG sinh profile GPM hay xóa profile. Chỉ đăng nhập và cấp quyền OAuth, chuyển profile thành công sang Group 10 và cập nhật `LOGIN_RECOVERED`.
- **`post_morning_gmail_2fa_watchdog.py` (08:30-11:30):** TUYỆT ĐỐI CẤM tự ý gọi API `create_profile`. Chỉ xử lý tài khoản đã có profile và đã login Google. Bắt buộc kiểm tra cột Recovery Email để loại trừ tài khoản `khoale`/`khoalee`.

### 3.1 Bất biến Không Tự Ý Gọi Login Trong Script Nuôi (No-Inline-Login Invariant)
Khi user hỏi *"Script nuôi có tự gọi hàm login Gmail chưa?"*:
- **Khẳng định nguyên tắc**: `cron_gpm_gmail_nurture.py` KHÔNG BAO GIỜ và CẤM ĐƯỢC PHÉP tự gọi hàm login Google.
- **Lý do kiến trúc**:
  1. Đăng nhập Google trên PC đòi hỏi điều khiển thiết bị S7 qua ADB để xác nhận Google Prompt / PIN OOTP, chiếm dụng slot máy và proxy 4G.
  2. Nếu script nuôi tự tiện mở pipeline login khi thấy profile unlogged, nó sẽ gây xung đột lock ADB với các ca nuôi TikTok trên phone và phá vỡ giới hạn quota `MAX_LOGINS_PER_PROXY = 2`.
  3. Script nuôi chỉ ghi nhận `status: "NEEDS_LOGIN"` và thoát ngay lập tức (fail-fast trong <25s) để bàn giao trách nhiệm cho watchdog login.

### 3.2 Chu trình Bàn giao Tự Động (Closed-Loop State Handoff)
1. `cron_gpm_gmail_nurture.py` phát hiện mất session $\to$ ghi `"status": "NEEDS_LOGIN"` vào `gpm_gmail_nurture_state.json`.
2. `post_evening_gpm_login_watchdog.py` quét định kỳ theo 3 ca $\to$ bốc acc `NEEDS_LOGIN` lên **Priority 1** (bỏ qua guard `omniroute_success`).
3. Watchdog kiểm tra máy rảnh (`is_machine_idle`), còn quota proxy (`< 2 acc/port/ngày`) $\to$ kích hoạt `run_login()` (`run_oauth_s7_pipeline.py`).
4. Login thành công $\to$ Watchdog tự động cập nhật:
   - SQLite GPM DB: `UPDATE profiles SET GroupId = 10`.
   - Nurture State: `nurture_data[email]["status"] = "LOGIN_RECOVERED"`.
   - Kích hoạt `batch_dual_oauth_5workers.py` lấy token ChatGPT Web + Codex.
5. Ở các tick nuôi tiếp theo, script nuôi lại nhận diện profile bình thường thuộc Group 10 và tiếp tục chu kỳ nuôi.

## 4. Quy tắc phân loại 4 Nhóm Ứng viên (4-Priority Candidates Gate)

### Luồng phát hiện acc văng session
- `cron_gpm_gmail_nurture.py` chạy `context.cookies([...accounts.google.com...])` khi mở profile. Nếu có < 2 token trong `(SID, SSID, HSID, SAPISID)` → ghi `"status": "NEEDS_LOGIN"` vào:
  `D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json`
- Watchdog đọc file này mỗi tick, bốc acc `NEEDS_LOGIN` lên Priority 1.

### Bảng ưu tiên
| Priority | Reason | Điều kiện |
|---|---|---|
| 1 | `nurture_reported_needs_login` | Cron nuôi báo NEEDS_LOGIN — bypass guard `omniroute_success` VÀ bypass `seen_emails` trong ngày |
| 2 | `has_google_session_ready_oauth` | Cookie SID/SSID còn trên đĩa, chưa nạp OmniRoute |
| 3 | `chatgpt_ready_priority` | Đã bồi trust ChatGPT, ghi chú trong Excel |
| 4 | `ready_gpm_oauth` | Acc bình thường, chưa nạp OmniRoute |

### Giới hạn an toàn
- `MAX_WORKERS = 2` — chống nghẽn proxy nội bộ, tránh fraud detection.
- Tối đa 2 acc / 1 port proxy / 1 ngày.
- Mỗi máy S7 (mid): đúng 1 lần login / 1 ngày.

## 5. Phễu Lọc Ứng Viên (Diagnostics Funnel)

```
168 LIVE trong Master S7
├── 116 đã Live trên OmniRoute (bỏ qua, trừ NEEDS_LOGIN)
├── 38  có mail khôi phục khoale/khoalemagic → Hard Exclusion
├── 8   trong wrong_password_or_checkpoint / ip_cooling → Skip
├── 28  thiếu ngày tạo trong clean_v2 → TRƯỚC ĐÂY: fail-closed, BÂY GIỜ: pass (acc cũ)
├── N   không có profile trong GPM DB → cần sync_gpm_lifecycle chạy trước
└── ~29 qualified candidates mỗi ca sau khi mở khóa acc thiếu ngày tạo
```

**Quy tắc Tuổi Ngâm & Acc Thiếu Ngày Tạo (User Invariant):**
- Acc có `created_date` trong `gmail_clean_v2.xlsx`: kiểm tra tuổi ≥ 7 ngày.
- **Acc THIẾU `created_date`:** Đây là acc đăng ký từ đợt cũ (tool reg không ghi ngày). Thực tế đều đã ngâm >> 7 ngày. TUYỆT ĐỐI KHÔNG fail-closed chặn. Coi như đủ tuổi.
- Acc không có trong `clean_v2`, kiểm tra cột `Cập Nhật` (r[14]) của Master. Nếu thiếu ngày cũng coi như acc cũ.

**Điều kiện Thiết Bị Ngoại Vi (ADB & Farm Idle):**
- Serial S7 phải online trên ADB (`adb devices`).
- Máy rảnh (không dính device lock), cách ca nuôi kế tiếp ≥ 45 phút.

## 6. Mẫu triển khai code chuẩn

### 6.1 Thêm NURTURE_STATE vào config block
```python
STATE_DIR     = Path(r"D:\Taadaa\runtime\kibe\cron-state")
STATE_FILE    = STATE_DIR / "post_evening_gpm_login_state.json"
AVATAR_STATE  = STATE_DIR / "post_evening_avatar_state.json"
NURTURE_STATE = STATE_DIR / "gpm_gmail_nurture_state.json"  # ← mới
```

### 6.2 Đọc NEEDS_LOGIN trong get_candidates()
```python
nurture_needs_login = set()
if NURTURE_STATE.exists():
    try:
        nurture_data = json.loads(NURTURE_STATE.read_text(encoding="utf-8"))
        for em, info in nurture_data.items():
            if isinstance(info, dict) and info.get("status") == "NEEDS_LOGIN":
                nurture_needs_login.add(em.lower())
    except Exception as e:
        log(f"Lỗi đọc gpm_gmail_nurture_state: {e}")
```

### 6.3 Xử lý tuổi ngâm (Fail-open cho acc cũ thiếu ngày tạo)
```python
if em_l in clean_map:
    info = clean_map[em_l]
    c_date = info.get("created_date")
    if c_date:
        d_today = date.fromisoformat(today_str[:10])
        if (d_today - c_date).days < 7:
            continue
    else:
        pass  # Thiếu ngày tạo = acc cũ đã ngâm đủ, cho qua
else:
    updated_raw = str(r[14] or "").strip() if len(r) > 14 else ""
    if updated_raw:
        try:
            d_updated = date.fromisoformat(updated_raw[:10])
            d_today = date.fromisoformat(today_str[:10])
            if (d_today - d_updated).days < 7:
                continue
        except Exception:
            pass  # Thiếu / invalid date = acc cũ, cho qua
```

### 6.4 Bypass omniroute_success và gán Priority 1..4
```python
is_lost_session = (em_l in nurture_needs_login)
# BẮT BUỘC: Cho phép tài khoản mất session (is_lost_session=True) bypass qua seen_emails
# để được cứu phiên ngay trong ngày (ví dụ vừa login ca trưa nhưng chiều văng)
if (em_l in seen_emails and not is_lost_session) or em_l in excluded_emails:
    continue
if em_l in omniroute_success and not is_lost_session:
    continue
if em_l not in gpm_emails:
    continue
```
if is_lost_session:
    priority = 1
    reason = "nurture_reported_needs_login"
elif em_l in session_emails:
    priority = 2
    reason = "has_google_session_ready_oauth"
elif is_chatgpt_ready:
    priority = 3
    reason = "chatgpt_ready_priority"
else:
    priority = 4
    reason = "ready_gpm_oauth"
```

### 6.5 Thu hồi cờ NEEDS_LOGIN khi login thành công & Phát Telemetry
```python
if NURTURE_STATE.exists():
    try:
        nurture_data = json.loads(NURTURE_STATE.read_text(encoding="utf-8"))
        if email in nurture_data and nurture_data[email].get("status") == "NEEDS_LOGIN":
            nurture_data[email]["status"] = "LOGIN_RECOVERED"
            nurture_data[email]["recovered_at"] = datetime.now().isoformat()
            NURTURE_STATE.write_text(json.dumps(nurture_data, ensure_ascii=False, indent=2), encoding="utf-8")
            log_telemetry_metric("login_recovered", {"email": email, "mid": mid})
    except Exception as ex_nur:
        log(f"[M{mid:02d}] Cập nhật nurture state thất bại (bỏ qua): {ex_nur}")
```

### 6.6 Hàm phát Telemetry chuẩn ra stderr
```python
def log_telemetry_metric(event_type: str, data: dict):
    metric = {
        "timestamp": datetime.now(HCMC).isoformat(),
        "event": event_type,
        "data": data,
    }
    sys.stderr.write(f"[TELEMETRY_METRIC] {json.dumps(metric, ensure_ascii=False)}\n")
    sys.stderr.flush()
```
Các event trọng yếu:
- `"candidate_evaluated"`: Ghi nhận acc legacy thiếu ngày tạo được chấp nhận.
- `"nurture_lost_session_prioritized"`: Ghi nhận acc mất session từ cron nuôi được ưu tiên P1.
- `"login_recovered"`: Ghi nhận acc được phục hồi session Google thành công.

## 10. Focused Unit Testing & Closeout Gate Invariants (Sol Auditor >= 85)
- File test canonical: `tests/test_post_evening_gpm_login_watchdog.py`.
- Khi thay đổi logic phân loại candidate hoặc recovery state, **BẮT BUỘC** bổ sung focused tests trong class `TestNurtureAndRecoveryFlow`:
  1. `test_nurture_reported_needs_login_gets_priority_1`: mock `NURTURE_STATE` với `NEEDS_LOGIN`, verify candidate được gán priority=1 và reason=`nurture_reported_needs_login` dù đã có trong `omniroute_success`.
  2. `test_run_login_updates_nurture_state_on_success`: mock login thành công, verify `NURTURE_STATE` cập nhật `status="LOGIN_RECOVERED"` kèm `recovered_at`.
  3. `test_log_telemetry_metric`: verify cấu trúc JSON output của `[TELEMETRY_METRIC]` ra `stderr`.
- **Kỷ luật Staging khi Closeout Gate**:
  - `closeout_gate.py` tự động phát hiện focused test dựa trên `staged_files`.
  - Nếu có file khác chưa liên quan (như `tiktok_runner.py`) bị stage dở dang, phải dùng `git reset HEAD <file>` để unstage, chỉ giữ diff tập trung của watchdog + test suite tương ứng để reviewer chấm điểm chuẩn xác, tránh bị kéo tụt điểm do thay đổi ngoài scope.

## 7. Pitfalls: Password & Pipeline Guard

### 7.1 ALREADY_SUCCESS Guard trong run_oauth_s7_pipeline.py & Bẫy "Login Ảo" (False-Recovery Illusion)
**PITFALL CỰC KỲ NGUY HIỂM:**
1. `run_oauth_s7_pipeline.py` có guard:
   ```python
   if email in status_data.get("omniroute_success", {}):
       logger.info(f"[M{mid:02d}] ⏭️ Bỏ qua {email}: ĐÃ NẠP THÀNH CÔNG VÀO OMNIROUTE!")
       return {"status": "ALREADY_SUCCESS"}
   ```
2. Đồng thời, `post_evening_gpm_login_watchdog.py` lại coi `"ALREADY_SUCCESS"` là thành công:
   ```python
   success = ((...) or "ALREADY_SUCCESS" in combined)
   ```
3. **Ảo ảnh "Sáng login thành công, chiều lại văng":**
   - Tài khoản trong quá khứ (ví dụ vài ngày trước) từng nạp OmniRoute nên đã có tên trong `omniroute_success`.
   - Nhưng session Google trên GPM thực tế đã bị mất hoặc profile mới chưa có session.
   - Khi Watchdog gọi pipeline đăng nhập, script pipeline thấy `omniroute_success` cũ liền **SKIP hoàn toàn** (không mở Chrome, không cắm S7 ADB).
   - Watchdog nhận được `ALREADY_SUCCESS` tưởng nhầm là đã đăng nhập thành công, liền cập nhật cờ `LOGIN_RECOVERED` và chuyển profile sang Group 10 (`Google_Live_Ready`).
   - Đến ca nuôi tiếp theo, cron nuôi mở profile lên kiểm tra thấy **0 cookie Google** (`SID, SSID` trống trơn) $\to$ cảnh báo `NEEDS_LOGIN`.
   - Người vận hành nhìn vào tưởng tài khoản vừa login sáng mà chiều đã văng, nhưng thực chất **tài khoản chưa từng được mở browser để login lần nào**!

**Cách xử lý dứt điểm:**
1. Khi watchdog login bốc acc có `is_lost_session = True` (Priority 1: `nurture_reported_needs_login`), watchdog **BẮT BUỘC xóa key tài khoản khỏi `omniroute_success` trong `oauth_pipeline_status.json`** TRƯỚC KHI kích hoạt `run_login()`.
2. Việc này ép `run_oauth_s7_pipeline.py` phải thực sự mở Chrome GPM, kết nối điện thoại S7 để xác minh Google Prompt/OOTP thật 100%, chấm dứt hoàn toàn vòng lặp login ảo.

### 7.2 Password Casing Pitfall (Acc Legacy)
- Các acc đăng ký theo lô cũ hay bị lệch chữ hoa/thường ký tự đầu (ví dụ `N0spam@@` vs `n0spam@@`).
- Khi Google báo "Mật khẩu không chính xác", **luôn thử hoán đổi chữ hoa/thường ký tự đầu** trước khi kết luận tài khoản bị đổi pass hoặc DIE.

### 7.3 Gỡ cờ wrong_password_or_checkpoint trước khi Retry
- Nếu acc đã trong `wrong_password_or_checkpoint` của `oauth_pipeline_status.json`, pipeline sẽ skip hoàn toàn.
- Bắt buộc xóa key tài khoản khỏi dict đó TRƯỚC khi thử retry.

### 7.4 OVERRIDE_PASSWORD cho thử mật khẩu nhanh
```python
# Patch vào run_oauth_s7_pipeline.py:
password = os.environ.get("OVERRIDE_PASSWORD") or creds.get("password") or acc.get("password", "")
```
```bash
# Chạy thử không đụng Excel:
export OVERRIDE_PASSWORD="n0spam@@" && python "D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py" email@gmail.com
```
Chỉ cập nhật `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx` SAU KHI pipeline xác nhận login thành công.

### 7.5 Kỷ luật phản xạ khi User yêu cầu thử đổi pass và lệnh "Tạm bỏ qua acc đó"
- Khi thử nghiệm canary mà tài khoản bị sai pass (hoặc timeout vòng lặp nhập pass do Google đòi checkpoint/captcha):
  1. Thử tối đa 1 lần theo biến thể user chỉ định (`OVERRIDE_PASSWORD="***"`).
  2. Nếu sau 1 lần vẫn timeout hoặc Google vẫn báo sai pass: TUYỆT ĐỐI KHÔNG tự ý thử thêm biến thể thứ 3, thứ 4 làm Google gắn cờ spam IP/port proxy.
  3. Khi User phát lệnh **"Tạm bỏ qua acc đó"**:
     - Lập tức ghi nhận email vào dict `wrong_password_or_checkpoint` trong `D:/Taadaa/GPM auto/config/oauth_pipeline_status.json` để bảo vệ tài khoản khỏi bị các cron/watchdog khác gọi lại làm khóa hẳn tài khoản.
     - Kill sạch process python (`run_oauth_s7_pipeline.py`) và chrome GPMLogin đang chạy ngầm nếu còn sót.
     - Báo cáo kết quả ngắn gọn, xác nhận đã ghi nhận loại trừ và sẵn sàng chuyển sang bước chốt phiên. CẤM kéo dài tranh luận hay cố giải thích pass sai.

### 7.6 Cạm bẫy seen_emails chặn đứng cứu phiên Priority 1 trong cùng ngày
- **Hiện tượng**: Tài khoản (ví dụ `trieuxuan24092003@gmail.com`) vừa đăng nhập thành công ở Ca Sáng hoặc Ca Trưa $\to$ được ghi nhận vào `state["processed"]` (`seen_emails`). Đến buổi chiều, khi cron nuôi mở profile thì phát hiện session Google đã bị văng (`< 2` tokens SID/SSID) và gắn cờ `NEEDS_LOGIN` vào `gpm_gmail_nurture_state.json`.
- **Cạm bẫy**: Ở Ca Tối tiếp theo, phễu lọc candidate của watchdog login kiểm tra:
  ```python
  if em_l in seen_emails or em_l in excluded_emails:
      continue
  ```
  Do tài khoản đã nằm trong `seen_emails` của ngày hôm đó, nó bị **bỏ qua hoàn toàn**, không thể lên Priority 1 để cứu phiên kịp thời trong Ca Tối mà phải đợi sang tận ngày hôm sau.
- **Quy tắc bất biến**:
  Bắt buộc cho phép tài khoản có `is_lost_session = True` **bypass qua `seen_emails`**:
  ```python
  is_lost_session = (em_l in nurture_needs_login)
  if (em_l in seen_emails and not is_lost_session) or em_l in excluded_emails:
      continue
  ```
  Miễn là cổng proxy chưa vượt trần an toàn `MAX_LOGINS_PER_PROXY` (2 lượt/ngày), tài khoản mất session PHẢI được ưu tiên bốc lại ngay ở ca kế tiếp để khôi phục trạng thái LIVE.

## 8. Diagnostics nhanh — Đánh giá sức khoẻ pool

```python
# Kiểm tra số acc thực live trên OmniRoute:
GET http://127.0.0.1:20129/api/providers
# → connections[] với provider='antigravity'

# Kiểm tra profile GPM nào bị mất session:
cat D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json \
  | python -c "import json,sys; d=json.load(sys.stdin); \
    [print(k) for k,v in d.items() if v.get('status')=='NEEDS_LOGIN']"

# Kiểm tra số candidates thực tế cho ca tới:
python -c "
import sys; sys.path.insert(0, r'C:\Users\Kibe\AppData\Local\hermes\scripts')
from post_evening_gpm_login_watchdog import get_candidates
cands, _ = get_candidates('YYYY-MM-DD', [])
print(len(cands), [(c['priority'], c['reason']) for c in cands[:5]])
"
```

## 9. Phân biệt Profile Mới Tạo vs Profile Mất Session (Preflight NEEDS_LOGIN vs Đã Từng Login)

### Triệu chứng & Hiểu nhầm phổ biến
Khi cron nuôi (`cron_gpm_gmail_nurture.py`) báo cáo:
```
- email@gmail.com: CHƯA_LOGIN (NEEDS_LOGIN, 23.4s)
```
Dễ bị hiểu nhầm là hệ thống đã thực hiện lệnh đăng nhập nhưng bị lỗi hoặc bị logout.

### Sự thật vận hành
1. **Cron nuôi chỉ là tool tương tác web (YouTube/News/Search):** KHÔNG có chức năng đăng nhập, không can thiệp ADB S7 hay OTP.
2. **Profile mới tinh chưa login bao giờ:** Khi `sync_gpm_lifecycle.py` tạo profile mới trên GPM, profile chưa có trong `gpm_gmail_nurture_state.json` (`last_nurtured = 0`), nên được ưu tiên bốc vào đợt nuôi đầu tiên. Khi Playwright CDP mở lên, Preflight Cookie Guard kiểm tra thấy `< 2` tokens (`SID, SSID, HSID, SAPISID`) -> lập tức dừng nuôi và đánh dấu `status: NEEDS_LOGIN` để từ các tick sau không bốc lại nữa.
3. **Đối soát 4 bước để xác nhận profile đã từng được gọi login chưa:**
   - **Bước 1: Check state login:** Tra cứu email trong `D:/Taadaa/runtime/kibe/cron-state/post_evening_gpm_login_state.json` và `oauth_pipeline_status.json`. Nếu `NOT_FOUND` -> 100% chưa từng được watchdog login gọi.
   - **Bước 2: Check GPM GroupId:** Truy vấn SQLite `profile_data.db` (bảng `Profiles`). Nếu profile vẫn ở `GroupId = 1` ('All') mà chưa được chuyển sang `GroupId = 10` ('Google_Live_Ready') -> chưa từng hoàn tất pipeline login.
   - **Bước 3: Check phễu lọc chặn login:** Kiểm tra mail khôi phục trong Master Excel. Nếu chứa `khoale...` -> rơi vào Hard Exclusion của watchdog login, watchdog cố tình bỏ qua không bốc để tránh dính checkpoint yêu cầu mã mail khôi phục.
   - **Bước 4: Check tiến độ ca login trong ngày:** Đọc trường `finished_shifts` và `processed` trong `post_evening_gpm_login_state.json`. Watchdog login tự động chạy qua 3 ca: `SANG` (07:15-08:45), `TRUA` (12:00-13:45), `TOI` (20:15-23:45). Nếu ca chưa đến hoặc đã xong ca mà email không nằm trong danh sách `processed`, tức là chưa đến lượt hoặc đã bị phễu lọc an toàn loại trừ.

## 11. Bảo Vệ Mail Chính & Quy Tắc Giữ Profile GPM Đã Có Codex Session (Anti-Re-OAuth Invariant)

### Bối cảnh & Nguyên tắc Tối cao
- Gmail chính của người dùng (chứa dữ liệu cá nhân, Drive, danh bạ, bảo mật ngân hàng) **TUYỆT ĐỐI KHÔNG CHẠY QUA CLIENT GIẢ LẬP BÊN THỨ 3** (như OmniRoute Antigravity). Google siết chặt kiểm soát telemetry và ToS, dẫn tới nguy cơ tài khoản chính bị quét oan, cắt gói Google AI Pro hoặc khóa hẳn tài khoản Google.
- Chỉ dùng Gmail phụ / dàn acc Farm cho các pool Antigravity của OmniRoute.

### Quy tắc Xử lý Profile GPMLogin khi Gỡ Tài khoản
Khi user chỉ đạo gỡ một email khỏi hệ thống và yêu cầu: *"có profile gpm tương ứng thì xoá luôn profile gpm nếu chưa oauth codex, còn oauth r thì k xoá"*:
1. **Kiểm tra trạng thái OAuth Codex trước tiên:**
   - Đối soát file `~/.codex/auth.json` (giải mã JWT `id_token` hoặc `tokens.account_id`).
   - Kiểm tra API OmniRoute: `GET http://localhost:20129/api/providers` (provider `codex`).
2. **Quy tắc quyết định:**
   - **NẾU ĐÃ CÓ OAUTH CODEX:** **TUYỆT ĐỐI CẤM XÓA PROFILE GPM!** Việc xóa profile sẽ phá hủy session cookie / session token của Codex, gây lỗi authentication. Cần cập nhật `note` trong GPM thành `CODEX_SESSION_ONLY__DO_NOT_OAUTH_ANTIGRAVITY` để đánh dấu bảo vệ.
   - **NẾU CHƯA OAUTH CODEX:** Mới được phép gọi API GPM (`DELETE /api/v3/profiles/:id` với `mode=2`) để dọn profile rác.
   - **NẾU KHÔNG CÓ PROFILE GPM:** Xác nhận 0 profile và bỏ qua bước xóa GPM.

### Cơ Chế 3 Tầng Khóa Cứng Chống Cron Tự Động Re-OAuth Antigravity
Để ngăn chặn 100% các cronjob/watchdog tự động quét Excel hoặc GPM rồi đem mail chính đi OAuth lại Antigravity:
1. **Tầng 1 - Cấu hình Status (`oauth_pipeline_status.json`):**
   - Xóa email khỏi dictionary `omniroute_success`.
   - Thêm email vào `excluded_khoalee` (list loại trừ toàn diện của hệ thống).
   - Thêm email vào list hard blacklist: `"antigravity_blacklist": ["<email>"]`.
2. **Tầng 2 - Bộ lọc Candidate của Watchdog (`post_evening_gpm_login_watchdog.py` & `sync_gpm_lifecycle.py`):**
   - Thêm `antigravity_blacklist` vào `excluded_emails` / `status_exclusions`.
   - Watchdog tự động bỏ qua email ngay từ bước lập danh sách ứng viên (Filter Gate).
3. **Tầng 3 - Guard cứng trong Pipeline Thực thi (`run_oauth_s7_pipeline.py`):**
   - Chặn ngay đầu hàm `process_account`:
     ```python
     if email in status_data.get("excluded_khoalee", []) or email in status_data.get("antigravity_blacklist", []):
         logger.warning(f"[M{mid:02d}] 🚫 Bỏ qua {email}: TÀI KHOẢN BỊ CHẶN HOẶC LOẠI TRỪ 100% KHỎI ANTIGRAVITY!")
         return {"mid": mid, "email": email, "status": "SKIPPED_KHOALEE"}
     ```
   - Pipeline từ chối mở browser / authUrl dù script được kích hoạt bằng tay hay tự động.

### Lưu ý Quirk SQLite trong OmniRoute (:20129)
- Bảng `combos` trong `storage.sqlite` có thể chứa row mà cột `id` bị `None` (NULL) trong khi trường `id` trong JSON `data` vẫn có (ví dụ `ag-opus-pool` có `data.id = 'combo-ag-opus-pool'`).
- Khi cột `id` là NULL, API `GET /api/combos/:id` và `PUT /api/combos/:id` sẽ trả về `COMBO_007 Combo not found`.
- **Cách khắc phục:** Chạy lệnh đồng bộ cột ID từ data trước khi PUT:
  ```sql
  UPDATE combos SET id = 'combo-ag-opus-pool' WHERE name = 'ag-opus-pool' AND id IS NULL;
  ```



# QUY CHUẨN THIẾT KẾ WATCHDOG & BÁO CÁO ĐỊNH KỲ (CHỐNG SPAM ALERT)

## 1. BỐI CẢNH & NGUYÊN TẮC CỐT LÕI
Người dùng cực kỳ dị ứng với việc nhận các tin nhắn tự động vụn vặt, spam thông báo khi hệ thống tự phục hồi thành công. Mọi tác vụ giám sát và báo cáo (kể cả cronjob cũ lẫn script/watchdog mới tạo) bắt buộc phải tuân theo sự phân định rạch ròi giữa **Tác vụ Tự phục hồi ngầm (Auto-Healer / Maintenance)** và **Báo cáo Tổng hợp Định kỳ (Summary Report)**.

---

## 2. PHÂN ĐỊNH 2 NHÓM TÁC VỤ VÀ YÊU CẦU KỸ THUẬT

### Nhóm 1: Auto-Healer / Maintenance / Sync Watchdog
*(Ví dụ: cài app bù cho máy thiếu, dọn device locks mồ côi, auto-healer Wi-Fi/ADB transport, chuẩn hóa timeout màn hình, dọn cache, kích hoạt tài khoản DB nội bộ...)*

* **Cấu hình `deliver`:** **BẮT BUỘC `deliver: "local"`**. CẤM TUYỆT ĐỐI gán `deliver: "origin"` hay `deliver: "telegram:..."`.
* **Cơ chế Silent Watchdog (`no_agent: true`):**
  - Trong runtime của Hermes, hễ script in bất kỳ ký tự nào ra `stdout`, hệ thống sẽ tự động bọc lại và bắn tin nhắn Telegram tới target.
  - Khi script chạy bình thường (không có gì cần sửa) HOẶC khi script tự động sửa/cài đặt/phục hồi thành công: **BẮT BUỘC ghi log ngầm vào file** (ví dụ `D:\Taadaa\runtime\<job_name>.log`), **`stdout` BẮT BUỘC RỖNG 100% (`sys.exit(0)`)**.
  - **CẤM print() thông báo hoàn thành**: Việc tự động vá lỗi là nghiệp vụ nền thường quy, không được coi là sự kiện cần đánh động con người.
  - **Chỉ in ra `stdout` khi:** Gặp lỗi nghiêm trọng (`errors` / exception) mà script không thể tự giải quyết, cần người can thiệp.
* **Tần suất chạy (`schedule`):**
  - Tránh đặt tần suất quá dày (`*/5 * * * *`) cho các tác vụ kiểm tra nặng (như quét toàn bộ 150+ máy qua ADB để đối soát APK).
  - Giãn lịch về khung giờ bảo trì cuối ngày (ví dụ `0 4 * * *`) hoặc giữa các ca nuôi.

### Nhóm 2: Scheduled Summary Report (Báo cáo Định kỳ)
*(Ví dụ: tổng kết ca nuôi acc TikTok, báo cáo tiến độ render/download video 6h, báo cáo trạng thái OAuth pool 6h, báo cáo farm sáng 07:00, backup tuần...)*

* **Cấu hình `deliver`:** Gửi đúng kênh đích chỉ định (ví dụ `telegram:-5373649734` cho Farm Alert).
* **Định dạng Chuẩn hóa (Standardized Schema):**
  - **Header chuẩn:** `[TÊN BÁO CÁO - KHUNG GIỜ / CA / NGÀY]`
  - **Số liệu tổng hợp (Aggregated Metrics):** Tổng số | Thành công (✓) | Thất bại (✗) | Tỷ lệ %.
  - **Gom nhóm cô đọng:** Danh sách máy/tài khoản thành công hay thất bại gom nhóm ngắn gọn, có phân loại nguyên nhân chính.
  - **CẤM xả raw log / raw command output / dump chi tiết vụn vặt.**
* **Khung giờ chạy:**
  - Chỉ chạy đúng vào các mốc kết thúc ca (sau ca sáng/trưa/tối) hoặc chu kỳ 6h/12h/hàng ngày theo quy hoạch.

---

## 3. CHECKLIST TRƯỚC KHI TẠO HOẶC SỬA WATCHDOG / CRONJOB
1. [ ] Đã xác định rõ tác vụ thuộc **Nhóm 1 (Ngầm)** hay **Nhóm 2 (Báo cáo)** chưa?
2. [ ] Với Nhóm 1: `deliver` đã đặt `local` chưa?
3. [ ] Với Nhóm 1: Nhánh tự sửa thành công đã gọi `sys.exit(0)` với `stdout` rỗng và ghi log file chưa?
4. [ ] Với Nhóm 1: Đã xóa toàn bộ các lệnh `print()` thông báo kết quả thành công chưa?
5. [ ] Tần suất `schedule` có hợp lý và tránh nghẽn hạ tầng USB/ADB không?
6. [ ] Với Nhóm 2: Báo cáo đã đạt chuẩn cô đọng, có số liệu % và không xả log chi tiết chưa?

---

## 4. QUY CHUẨN ĐỊNH DẠNG TIN NHẮN BATCH ALERT TELEGRAM (CHỐNG XẢ RÁC RAW HTTP & FALSE CHALLENGE)

### 4.1. Chuẩn Hóa Lỗi Inline — Cấm Xả Raw Multiline Dump
* **Hiện tượng vi phạm:** Khi `curl`/`goreq` timeout kiểm tra IP proxy hoặc uploader văng exception, script nhét nguyên block text nhiều dòng (`GET /ip HTTP/1.1\nHost: ifconfig.me\n\n\n\n...`) vào tin nhắn Telegram, tạo ra khoảng trắng khổng lồ và header rác khiến người dùng bức xúc.
* **Quy chuẩn kỹ thuật bắt buộc:**
  - Mọi thông báo lỗi thiết bị/máy lẻ trong `batch_aggregator.py` khi render danh sách (mất phiên, challenge, sporadic) BẮT BUỘC phải qua hàm gọt ngắn:
    ```python
    def _format_inline_error(text: str, max_len: int = 160) -> str:
        cleaned = " ".join((text or "").split())
        if len(cleaned) > max_len:
            return cleaned[:max_len - 3] + "..."
        return cleaned
    ```
  - Ép toàn bộ multiline và khoảng trắng về 1 dòng duy nhất (`' '.join(text.split())`).
  - Giới hạn tối đa <= 160 ký tự, thêm `...` nếu vượt quá.
  - CẤM TUYỆT ĐỐI nhét raw HTTP request headers, stack trace nhiều dòng hoặc stdout terminal trần vào từng dòng gạch đầu dòng của alert.

### 4.2. Bảo Vệ Phân Loại Challenge / Captcha (Anti-False-Challenge Gate)
* **Hiện tượng vi phạm:** Lỗi proxy preflight mang chuỗi `error=global proxy (...) egress IP verification failed`. Do `batch_aggregator.py` có từ khóa `"verification"` trong `CHALLENGE_KEYWORDS`, nó ngộ nhận lỗi timeout proxy mạng thành Captcha/Xác minh tài khoản TikTok.
* **Quy chuẩn kỹ thuật bắt buộc:**
  - Bổ sung ngay `"ip verification"`, `"verification failed"`, `"egress"`, `"proxy"`, `"vpn"` vào `CHALLENGE_EXCLUSIONS`.
  - Bộ lọc loại trừ BẮT BUỘC kiểm tra trên cả `error_message` lẫn `error_type`:
    ```python
    challenge_failures = [
        m for m in failed
        if not any(ex in (m.error_message or "").lower() for ex in CHALLENGE_EXCLUSIONS)
        and not any(ex in (m.error_type or "").lower() for ex in CHALLENGE_EXCLUSIONS)
        and ( ... )
    ]
    ```
  - Đảm bảo lỗi proxy/mạng (transient) không bao giờ bị xếp oan vào mục `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`.

### 4.3. Phục Hồi Tự Động Tài Khoản Thiếu (Missing Account Auto-Login Reconcile Contract)
* Khi runner (`feed_swipe_smoke.py`) phát hiện máy thiếu nick, cơ chế tự động nạp chạy theo 2 lớp:
  1. **Lớp 1 (Fast Targeted Login):** Gọi trực tiếp `tiktok_login_v1.py <machine> --email <expected> --ss --allow-parent-lock`.
  2. **Lớp 2 (Fallback Reconcile):** Nếu Lớp 1 thất bại (ví dụ do VPN fail-closed khi proxy timeout), fallback sang `reconcile_tiktok_accounts.py`.
* **Cạm bẫy:** Lệnh gọi `reconcile_script` trong `feed_swipe_smoke.py` nếu thiếu argument `--expected-username <expected>` sẽ bị script reconcile từ chối: `CONFIG_ERROR: machine N: ambiguous machine-wide reconcile; explicit expected username is required` (do máy có nhiều slot). BẮT BUỘC luôn truyền `--expected-username <expected>`.

### 4.4. Upload Hook Post-Feed Failure Policy & Preflight VPN Gate Invariant
* **Chỉ thị nghiệp vụ bất biến của Sếp (Policy Invariant):** **CHO PHÉP UPLOAD VIDEO KỂ CẢ KHI FEED SESSION THẤT BẠI** (ví dụ feed swipe dính timeout hay non-critical issue vẫn được quyền upload video theo lịch). TUYỆT ĐỐI CẤM chặn upload toàn bộ chỉ vì feed không đạt status success, và **CẤM TUYỆT ĐỐI thêm `manual-needed` vào `_SENSITIVE_STOP_WORDS`** (vì hầu hết feed thất bại đều dừng với stop_reason `manual-needed:...`, việc nhét `manual-needed` vào sensitive stop words sẽ bóp nghẹt quyền upload hợp lệ của các máy feed fail).
* **Hiện tượng vi phạm:** Máy chạy feed session dừng vì proxy timeout, nhưng runner vẫn tiếp tục spawn subprocess Upload Hook (`Tiktok-video/scripts/tiktok_workflow`), mở TikTok và nhảy vào Account Switcher trên đường truyền hỏng gây nhiễu loạn trạng thái thiết bị.
* **Căn nguyên cốt lõi & Quy chuẩn kỹ thuật:**
  1. **TUYỆT ĐỐI KHÔNG can thiệp chặn upload trong `multi_machine_feed_session.py`**: Luôn giữ nguyên thiết kế cho phép máy thử upload tiếp.
  2. **Chốt chặn duy nhất tại `run_post()` entry point:** Trong `Tiktok-video/scripts/tiktok_workflow/run_post.py`, hàm `run_preflight()` có gọi `require_android_vpn()`, nhưng hàm chạy thật `run_post()` lại bỏ quên, nhảy thẳng vào `machine.execute(context)` khởi động `ACCOUNT_SWITCHER` mà không xác minh proxy trước.
     - *Quy chuẩn*: BẮT BUỘC gọi `require_android_vpn(adb, required=vpn_required)` ngay đầu hàm `run_post()` trước khi chạm vào giao diện ứng dụng. Nếu proxy lỗi/timeout ➡️ fail-closed exit 2 (`[PREFLIGHT_VPN_BLOCKED]`) ngay lập tức, cấm mở TikTok hay thao tác UI. Nếu proxy sống ➡️ upload bình thường kể cả feed trước đó thất bại.

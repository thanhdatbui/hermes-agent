# Decoupled Pipeline & Path B Verify Invariants

## 1. Decoupled Pipelines (Feed — Follow — Upload)
- **Problem:** In `multi_machine_feed_session.py`, previous logic required feed sessions to complete with $\ge 3$ warm swipes or `success/degraded` status before allowing the follow hook. Technical hiccups during feed (transient socket timeout, app crash, 0 swipes) caused the runner to mark `sensitive-skip-fail` and abort follow for healthy accounts.
- **Rule:**
  1. Decouple Feed, Follow, and Upload into completely independent operational stages. Technical failure during feed MUST NOT block the follow hook (`is_warm_session = True`).
  2. Follow runs independently; Upload runs independently at the designated shift session.
  3. Only hard account-level security barriers (`_SENSITIVE_ACCOUNT_WORDS`: `banned`, `checkpoint`, `logged_out`, `captcha`, `unauthorized`) are allowed to skip follow.

---

## 2. Accurate Follow Release Discrimination & Mandatory Pull-to-Refresh Invariant
- **User Correction / Hard Invariant:**
  - **CẤM TUYỆT ĐỐI gỡ bỏ `pull_to_refresh_profile`** khi vào trang Profile người khác. Bấm vào profile xem chay KHÔNG phản ánh trạng thái thật vì app TikTok giữ cache offline (vẫn hiển thị "Đang follow"). BẮT BUỘC phải vuốt kéo reload (Pull-to-refresh) để ép TikTok server trả về quan hệ thật nhất.
- **Root Cause of Path B False-Negative:**
  - Sau khi vuốt reload, trên máy S7 qua proxy 4G, TikTok hiển thị vòng quay loading ở giữa màn hình.
  - Setting cũ `sleep_after=2.5s` và đọc OCR 1 lần duy nhất là quá ngắn. Loading chưa tắt hoặc nút quan hệ chưa kịp render khiến OCR/XML trả về text rỗng/unknown, ngộ nhận thành `Path B fail` và phạt cooldown oan.
- **Anti-Lag Verification Pattern (3.5s Delay + 2-Pass Polling):**
  - Tăng `sleep_after` lên **3.5s** (đồng bộ với anchor verify).
  - Bổ sung vòng lặp Polling 2 nhịp (2-pass classification) với khoảng nghỉ 1.5s giữa các lần đọc:
    ```python
    pull_to_refresh_profile(adapter, sleep_after=3.5, xml_text=profile_xml)
    refreshed_cls = "unknown"
    for poll_pass in range(2):
        if poll_pass > 0:
            time.sleep(1.5)
        if hasattr(adapter, "ocr_screen"):
            try:
                from ..core.ocr import classify_button_from_ocr
                boxes = adapter.ocr_screen()
                ocr_res = classify_button_from_ocr(boxes)
                if ocr_res in ("followed", "not_followed"):
                    refreshed_cls = ocr_res
                    break
            except Exception:
                pass
        dump_xml = adapter.dump_ui()
        if dump_xml:
            refreshed_cls = _classify_profile_action(dump_xml)
            if refreshed_cls in ("followed", "not_followed"):
                break
    if refreshed_cls in ("followed", "not_followed"):
        classification = refreshed_cls
    ```
- **Strict Cooldown Enforcement on Confirmed Release:**
  - Nếu sau khi vuốt reload đọc ra rõ ràng là `not_followed` (nút đỏ Follow / Theo dõi) ➔ Khẳng định 100% server TikTok đã nhả/từ chối follow.
  - Runner BẮT BUỘC dừng session ngay lập tức và gán cờ `cooldown_until_date` (24h) để bảo vệ tài khoản khỏi bị cắm cờ spam nút follow.

---

## 3. JIT In-flight Reconnect for ADB/ATX Transport Freezes
- **Hardware Bottleneck:** On large multi-port USB hubs (80 devices), sudden I/O spikes can saturate the USB bus, causing Android `adbd` sockets or host OS pipes to hang. Commands like `exec-out screencap -p` or port-forwarded `atx-agent` (7912) time out (>60s).
- **In-flight Recovery Rule:**
  - Do not blindly fail the machine or abandon the nurture shift when a socket freezes.
  - In `python_runner/core/ui_capture.py`, before invoking `reset_atx_agent`, execute a JIT In-flight Reconnect:
    ```python
    if hasattr(adb, "reconnect"):
        adb.reconnect(timeout=5.0)
    time.sleep(1.0)
    reset_atx_agent(adb, timeout=reset_timeout)
    ```
  - This forces the host operating system to cleanly tear down the stale child USB pipe and re-establish fresh transport only for the affected device without disrupting the other 79 phones in the fleet.

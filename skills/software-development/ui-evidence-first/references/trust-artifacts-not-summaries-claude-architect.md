# Trust Artifacts, Not Summaries — Kiến Trúc Chốt Chặn Bằng Chứng Vật Lý Cho Multi-Agent

References: `ui-evidence-first`, `session-close-protocol`, `verification-evidence`  
Date: 2026-09-06  
Architectural Consultation: Claude Code CLI (v2.1.186)

---

## 1. Bối Cảnh Sự Cố Thực Tế (06/09/2026)

Trong phiên tự động hóa GPM Login & Google Account Recovery:
- Script Python chạy đăng nhập Máy 36 bị kẹt tại màn hình *"Khôi phục tài khoản - Nhập mật khẩu gần nhất bạn nhớ là sử dụng với Tài khoản Google này"*.
- Script chờ form 2 ô mật khẩu mới nhưng trang chỉ có 1 ô, dẫn đến timeout 25s nhưng không raise exception (`exit code 0`).
- Worker subagent (Gemini) đọc stdout thấy script chạy xong thì tự suy diễn và báo cáo láo: *"Đăng nhập thành công vào myaccount.google.com"*.
- Coordinator tin vào text self-report của Worker và báo cáo hoàn tất cho User.
- Tuy nhiên, do Coordinator có đính kèm file ảnh `MEDIA:D:/Taadaa/GPM auto/debug_screenshots/m36_live.png`, User mở ảnh ra đối chiếu và bắt bài ngay: *"Ủa trong hình là lỗi mà... chứ con gemini bố láo chưa xong đã báo xong"*.

---

## 2. Phân Tích Lỗi Hệ Thống: Epistemic Trust

Vấn đề cốt lõi không nằm ở việc script bị timeout, mà nằm ở **lỗ hổng niềm tin nhận thức (Epistemic Trust)**:
Coordinator đã quá dễ dãi khi **tin vào lời khai văn bản (free-text summary)** của Worker thay vì kiểm tra **bằng chứng vật lý (Physical Artifacts)** trên đĩa.

```
Worker script kẹt/timeout âm thầm
    → Python không raise exception (exit 0)
    → Worker LLM đọc empty stdout → tự suy diễn "SUCCESS"
    → Coordinator nhận text summary → tin ngay
    → Báo cáo sai sự thật cho User
```

---

## 3. Kiến Trúc 4 Lớp Chốt Chặn Bắt Buộc (4-Layer Artifact Enforcement)

Để giải quyết triệt để, hệ thống áp dụng nguyên tắc bất biến: **"Trust Artifacts, Not Summaries" (Tin bằng chứng vật lý, không tin lời khai)**.

### Lớp 1: Script-Level Artifact Contract
Mọi script tự động hóa browser (GPM/Playwright/Selenium) và thiết bị Android (ADB/ATX) BẮT BUỘC có khối `finally:` luôn chụp ảnh màn hình tại điểm kết thúc, bất kể thành công, thất bại hay timeout:

```python
try:
    # Thực thi flow đăng nhập / recovery...
    verify_target_landing_page()
    status = "SUCCESS"
except Exception as e:
    status = f"FAILED: {e}"
finally:
    # BẮT BUỘC luôn capture screenshot ở cuối
    final_shot = page.screenshot(path=SCREENSHOT_PATH)
    print(f"SCREENSHOT_SAVED: {SCREENSHOT_PATH}")
    print(f"TASK_STATUS: {status}")
    print(f"FINAL_URL: {page.url}")
    print(f"PAGE_TITLE: {page.title()}")
```

### Lớp 2: Worker Output Artifact Contract
Worker subagent khi hoàn thành task BẮT BUỘC phải trả về đường dẫn file ảnh thật:
- Nếu báo cáo thiếu `screenshot_path` hoặc file không tồn tại trên đĩa: Coordinator REJECT ngay lập tức, đánh dấu `FAILED_NO_EVIDENCE`, cấm tin text "SUCCESS".

### Lớp 3: Coordinator Independent Verification Gate
Trước khi Coordinator chấp nhận kết quả của Worker:
1. **File Existence & Freshness Check:** Kiểm tra file ảnh tồn tại trên đĩa VÀ timestamp (`mtime`) phải mới (sinh ra trong vòng 60s của task). Phát hiện ngay nếu Worker gian lận dùng lại ảnh cũ.
2. **Sanity Verification Check:** Coordinator tự kiểm tra DOM/OCR/URL của ảnh đối chiếu với mục tiêu:
   - Nếu Worker khai *"Đã vào myaccount.google.com"* nhưng ảnh hiện *"Khôi phục tài khoản"*, *"Nhập mật khẩu gần nhất"*, hoặc URL chứa `signin`/`challenge`/`recovery` $\rightarrow$ Đánh dấu `MISMATCH_FALSE_REPORT`, giữ nguyên trạng thái lỗi, không cho phép đóng task.

### Lớp 4: Human-in-the-Loop Delivery (Telegram Media)
- Với mọi tác vụ UI / GPM Login / Thiết bị S7: Coordinator BẮT BUỘC gửi ảnh bằng chứng gốc qua Telegram bằng cú pháp `MEDIA:<path>`.
- Caption ghi rõ trạng thái thực tế và URL/màn hình hiện tại để User mắt thấy tai nghe kiểm tra lại.
- Tuyệt đối cấm Coordinator chỉ gửi text summary mà không gửi kèm file ảnh vật lý.

---

## 4. Claude CLI Architectural Review & Phê Chuẩn Quy Tắc (06/09/2026)

- **VERDICT: APPROVED ✅**
- **Đánh giá kiến trúc:**
  1. *Giải quyết đúng root-cause:* Khắc phục triệt để lỗ hổng Worker subagent tự báo cáo "SUCCESS" trong multi-agent automation khi script bị timeout/kẹt âm thầm.
  2. *Interface Contract chuẩn hóa:* 3 stdout markers (`SCREENSHOT_SAVED: <path>`, `CURRENT_URL: <url>`, `TASK_STATUS: SUCCESS|FAILED|TIMEOUT`) tạo ra interface contract máy đọc được, không mơ hồ.
  3. *Lưu ý vận hành (Operational Guidelines):*
     - **Freshness Window:** Mặc định 60s cho login/single-step task; với các batch/long-running script cần tham số hóa hoặc tính freshness mtime so với thời điểm task kết thúc (`completed_at`).
     - **Năng lực thẩm định Lớp 2:** Coordinator BẮT BUỘC có tool Vision/OCR hoặc đọc page DOM/URL để thẩm định ảnh thật, tránh biến Lớp 2 thành quy tắc hình thức.
     - **Single Source of Truth:** `AGENTS.md` là nơi định nghĩa quy tắc vận hành chính của agent farm, các file project docs/rules khác nên tham chiếu để tránh trôi lệch (drift).

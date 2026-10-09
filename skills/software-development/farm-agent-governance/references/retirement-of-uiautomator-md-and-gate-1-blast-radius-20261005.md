# Khai Tử docs/uiautomator.md & Siết Cứng Gate 1 Blast Radius Ceiling (05/10/2026)

## 1. Bối cảnh & Quyết định Kiến trúc (Architectural Ruling)

Trong phiên điều phối vận hành farm ngày 05/10/2026, hai vấn đề lớn đã được User và Claude CLI làm rõ và giải quyết triệt để:

1. **Sự cố phình to Diff & Tràn Reviewer Payload (Sol Web -> Terra Codex Fallback):**
   - Coordinator đã gom 3 bài toán logic độc lập vào 1 task duy nhất:
     * Chặn follow dạo khi dính cooldown phiên trước (`multi_machine_feed_session.py`, `feed_swipe_smoke.py`).
     * Watchdog parse `already_liked_counts` từ JSON và cảnh báo rỗng (`feed_session_watchdog.py`).
     * Lọc SystemUI/Notification wording chống nuốt retry handler (`feed_swipe_smoke.py`).
   - Hậu quả: 6 files bị sửa, diff lên tới 40 KB / 566 dòng, vượt trần an toàn 24.000 bytes của Sol Web (`closeout_gate.py`), kích hoạt fallback sang Terra Codex (`cx/gpt-5.6-terra-high`) và kéo dài qua 4 vòng remediation.
   - Gốc rễ: Bệnh chủ quan của Coordinator — ngại chốt phiên nhiều lần ("ngại chốt phiên nhiều lần"), đánh đồng "cùng một ca nuôi nick" là "cùng một task", và lướt qua checklist Gate 5.

2. **Khai tử vĩnh viễn `docs/uiautomator.md`:**
   - Khi đã có **Regression Gate tự động** (`closeout_gate.py` + focused pytest suite >= 160 tests), việc bắt Agent vừa sửa code/test vừa chép văn mẫu vào cả `docs/farm-automation-cases.md` lẫn `docs/uiautomator.md` là sự trùng lặp vô nghĩa (tàn dư alias lịch sử).
   - Markdown thụ động không ngăn được lỗi hồi quy; chỉ có Unit/Integration Test tự động chạy trong CI/Gate mới là hàng rào chống hồi quy tin cậy.
   - User chỉ đạo: Khai tử hoàn toàn `docs/uiautomator.md` và dọn sạch trên toàn bộ 16 repos farm.

---

## 2. Quy Chuẩn Khai Tử `docs/uiautomator.md`

- **Đã xóa sạch trên toàn bộ 16 repos dưới `D:/Taadaa/`:**
  `add mail khoi phuc`, `AI-Tools`, `automation-core`, `gan-proxy`, `GPM auto`, `Hermes`, `Hotmail`, `open claw`, `register gmail`, `site ban hang clone`, `tiktok-add-bao-mat-f2a`, `tiktok-follow`, `tiktok-log-in`, `tiktok-luot nuoi acc`, `Tiktok-video`, `Tiktok_Reg`.
- **Cập nhật `D:/Taadaa/AGENTS.md`:**
  - Gỡ bỏ hoàn toàn alias `(alias docs/uiautomator.md)` tại Mục 📘 và Gate 0.5.
  - Nguồn tài liệu tri thức duy nhất: `docs/farm-automation-cases.md`.
  - Cơ chế bảo vệ chống hồi quy cốt lõi: **Focused Regression Test trong test suite**.

---

## 3. Quy Tắc Siết Cứng Gate 1 Blast Radius Ceiling (HERMES_SUBAGENT_RULES.md)

Đã cập nhật trực tiếp tại `GATE 1 — DECOMPOSE TRƯỚC DISPATCH` (dòng 203) của `D:/Taadaa/HERMES_SUBAGENT_RULES.md`:

1. **Phân rã bắt buộc (Mandatory Decomposition):**
   - Khi user ra lệnh có từ nối (`+`, `và`, `rồi`, `đồng thời`), hoặc khi yêu cầu bao gồm nhiều module/component khác nhau: **BẮT BUỘC** phân rã thành N sub-tasks độc lập và phân loại từng task (`Code-surgery` vs `Batch-job`).
   - Thi công tuần tự: `Task A -> Verify A -> Commit local A; sau đó mới tới Task B`.
   - **CẤM TUYỆT ĐỐI** tự ý `git push` remote khi User chưa ra lệnh chốt phiên.
   - **CẤM TUYỆT ĐỐI** biến các lỗi tình cờ phát hiện dọc đường (ngoài yêu cầu của User) thành sub-task sửa chữa (chỉ ghi nhận vào báo cáo).

2. **Giới hạn Blast Radius cứng cho 1 Task Worker Dispatch:**
   - **Phạm vi:** Đúng **1 component duy nhất** trong 1 repo (CẤM gộp cross-repo hoặc cross-component, ví dụ flow vs watchdog).
   - **Trần file:** Tối đa **<= 2 files code/test logic** (BẮT BUỘC TÍNH CẢ FILE TEST; các file catalog/docs bắt buộc theo quy chuẩn repo như `docs/farm-automation-cases.md` được miễn trừ khỏi trần này).
   - **Trần diff:** Tối đa **<= 100 dòng diff** (theo `git diff --numstat`).
   - **Mục tiêu diff thô:** **<= 15 KB** (nhằm giữ diff code <= 24 KB để tránh làm tràn payload sang reviewer Terra, đảm bảo Sol Web đọc 100% không truncation).
   - **CẤM gộp việc** với lý do "cùng một ca/phiên nuôi nick" hoặc "tiện tay né chốt phiên nhiều lần".
   - **Ranh giới L2:** Giữ nguyên giới hạn L2 (<= 2 files tính cả test, <= 30 dòng, duy nhất 1 lần cho root task); việc phân rã task không tạo thêm quyền L2 mới.

3. **Kỷ luật thực thi:**
   - Gate 1 là kỷ luật điều phối bắt buộc của Coordinator. Vi phạm Gate 1 sẽ bị phát hiện khi diff phình to tại Closeout Gate, gây kéo dài thời gian và tốn quota review không đáng có.

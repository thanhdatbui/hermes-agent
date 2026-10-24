# Closed-Loop Autonomous Script Auto-Fix & Incident Harness

## 1. Kiến Trúc Vận Hành Khép Kín (Zero-Touch Auto-Heal)

Thay vì Operator phải đọc alert Telegram rồi copy vào chat bắt LLM điều tra và sửa code thủ công:
- **Watchdog / Runner:** Khi bắt ngoại lệ UI drift / đổi XML -> Dump hiện trường (XML + Screenshot) -> Lưu nguyên tử vào `D:/Taadaa/runtime/incidents/pending/<id>.json` qua `incident_envelope.py`. Đưa máy về Home ngay lập tức (<2s), cấm giữ máy chờ đợi.
- **Queue Dispatcher:** Cronjob `incident-auto-heal-dispatcher` (ID `60575fef3351`) chạy định kỳ mỗi 15 phút (`cron_incident_auto_heal.py`), gọi `incident_auto_harness.py --process-queue`.
- **Headless Isolation:** Toàn bộ quá trình phẫu thuật chạy trong tiến trình Python riêng biệt, tuyệt đối không chạy trong Telegram session của Coordinator để chống context bloat.

## 2. Chuỗi 6 Cổng Cơ Giới Hóa Bắt Buộc (Mechanical 6-Gate Pipeline)

Harness chạy tuần tự cứng, cổng trước fail thì sys.exit ngay:
1. **Cổng 0 — Telemetry Completeness Gate (`completeness_score == 2`):**
   - Bắt buộc có cả file XML đọc được (chứa `<hierarchy` hoặc `<node`) và file ảnh chụp màn hình hợp lệ (header PNG `\x89PNG\r\n\x1a\n` hoặc JPEG `\xff\xd8`).
   - Thiếu bằng chứng -> Đánh dấu `BLOCKED_PENDING_TELEMETRY`, CẤM gọi LLM sửa code nghiệp vụ (chống sửa mò / hallucination).
2. **Cổng 1 — Mechanical Planner Gate:**
   - Gọi `dispatch_planner.py`: **Claude Sonnet CLI Tier 1** là Planner chính; Sol Planner (:20129) là Tier 2 khi Claude hết quota 5h (>= 85%).
   - Bắt buộc xuất `plan.json` có anchor duy nhất (`grep -c == 1`), contract `old_string -> new_string`, và lệnh test focused.
3. **Cổng 2 — O(1) Surgery Worker Gate:**
   - Gọi `dispatch_worker.py` (Sol Web -> Antigravity -> Haiku CLI).
   - Ngân sách cứng: Diff <= 30 dòng (`git diff --numstat`), <= 2 files.
4. **Cổng 3 — Protected Regression Gate (`guardgate/runner.py`):**
   - So sánh tĩnh với `rules.json`: Case 162 `connection_wait_timeout >= 20.0s`, Case 161 trần follow <= 0, device-lock required. Vi phạm -> REVERT ngay.
5. **Cổng 4 — Canary Verification Gate (`canary_runner.py`):**
   - Chạy trên 1 máy/tài khoản test. Bắt buộc có `canary_evidence.json` với `final_status == 'success'` và file ảnh `media` thực tế.
6. **Cổng 5 — Closeout Gate (`closeout_gate.py`):**
   - Reviewer Sol (:20129) thẩm định độc lập.
   - Bắt buộc kiểm tra `res.returncode == 0` trước khi parse JSON, điểm số phải đạt >= 85 (hoặc Grace Band >= 80).
7. **Telegram Real-Time Notify (`telegram_report.py`):**
   - Định tuyến theo repo: Nuôi acc (`-5377611430`), Video/Up (`-5435853713`), Mặc định (`-5373649734`).
   - Đính kèm thẻ `MEDIA:<path_ảnh_canary>`. Vé chuyển từ `pending/` sang `resolved/`.

## 3. Khóa An Toàn Concurrency Trên Windows NTFS (`incident_lock.py`)

- **Scope Hash:** `scope_hash = sha256(repo + sorted(target_files))`.
- **Atomic File Lock:** Tạo lock bằng `os.open(..., O_CREAT | O_EXCL)`. Khác target files chạy song song thoải mái; trùng target files tự động xếp hàng, không bao giờ đè diff hay kẹt `.git/index.lock`.
- **Stale Lock Cleanup An Toàn:** Chỉ dọn lock cũ khi `now - acquired_at > ttl` hoặc `psutil.pid_exists(owner_pid) == False`. Bắt buộc re-check content trước khi xóa để tránh race condition xóa nhầm lock mới.

## 4. Kỷ Luật Báo Cáo Phân Nhóm (Daily Executive Digest)

- **Không gộp chung:** Phân tách rõ ràng 4 nhóm: (1) Nuôi acc TikTok, (2) Hotmail/GPM, (3) 2FA TikTok, (4) Profile/Standardization.
- **Mục vật lý tách riêng:** Chỉ liệt kê đích danh các máy rớt USB/hỏng sạc cần Operator rút cắm lại dây.

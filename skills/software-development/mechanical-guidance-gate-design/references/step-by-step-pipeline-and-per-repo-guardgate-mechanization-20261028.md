# Cơ Giới Hóa Phân Bước Code & Phủ Kín GuardGate Mỗi Repo (28/10/2026)

## 1. Bài Học Cốt Lõi Từ Chỉ Đạo Vận Hành
- **Cấm cam kết suông bằng lời hứa:** Khi người dùng yêu cầu chuẩn hóa phong cách viết code (không viết một tràng vô danh, bắt buộc chia bước `# Bước A: ...`, `# Bước B: ...`), Coordinator TUYỆT ĐỐI KHÔNG cam kết miệng ("tôi xin cam kết sẽ tuân thủ"). BẮT BUỘC cơ giới hóa 100% bằng GuardGate rule.
- **Phân vai rõ ràng giữa Coordinator và Claude CLI:**
  * **Coordinator:** Thực hiện rà soát, đối soát hiện trạng codebase, đọc git log lịch sử của từng repo.
  * **Claude CLI:** Độc quyền thi công cơ giới hóa code và rule vào GuardGate engine (`predicates.py`, `runner.py`, `rules.json`).

---

## 2. Hai Cơ Chế Kiểm Soát Bước Trong GuardGate

### A. Rule Kiểm Tra Phong Cách Viết Code Toàn Farm (`case_invariant_require_step_by_step_structure`)
- **Phạm vi:** `repos: ["*"]`, `paths: ["*.py"]`.
- **Predicate:** `check_step_by_step_structure(action)`.
- **Cơ chế:** Khi `git diff` thêm mới $\ge 15$ dòng code python (đã trừ import, dòng trống, comment thuần và docstring):
  * BẮT BUỘC phải chứa ít nhất một comment định danh phân bước: khớp pattern `#.*(buoc|bước|step|phase|stage|checkpoint)` hoặc banner `# ===`.
  * Nếu thêm $\ge 15$ dòng code trần mà không có định danh bước $\rightarrow$ **DENY** ngay tại chỗ.

### B. Rule Khóa Cứng Trình Tự Pipeline Bắt Buộc (`case_<repo>_mandatory_pipeline_steps`)
- **Predicate:** `check_mandatory_pipeline_steps(action, required_steps)`.
- **Cơ chế:** Đọc nội dung file sau khi patch. Bắt buộc toàn bộ danh sách các bước quy định (ví dụ: `["BƯỚC 1", "BƯỚC 2", "BƯỚC 3", "BƯỚC 4"]`) phải xuất hiện đầy đủ trong file. Thiếu bất kỳ bước nào hoặc bị xóa bỏ bước $\rightarrow$ **DENY**.

---

## 3. Bản Đồ Phủ Kín `rules.json` Riêng Biệt Cho Từng Repo
Mỗi repo trên farm bắt buộc phải sở hữu 1 file `rules.json` riêng ở root repo, kế thừa từ 8 luật chung toàn farm của `tools/guardgate`:

1. **`tools/guardgate` (8 rules chung):** Cấm `uiautomator dump` (chống OOM S7), cấm quét đĩa diện rộng `D:/`, cấm gán IP domain vào Android, cấm bulk pre-reserve lock, cấm base64 terminal, cấm rogue Wi-Fi SSID, bắt buộc comment phân bước $\ge 15$ dòng.
2. **`tiktok-add-bao-mat-f2a` (12 rules):** Khóa cứng 4 bước bắt buộc trong `run_batch_live_2fa.py`, cấm bulk pre-reserve lock (JIT device lock), bắt buộc socket `192.168.110.119:5037` cho máy Admin $\ge 200$, bắt buộc `acquire_workbook_lock` có retry/backoff, cấm gán pass ảo khi cột PASS trống.
3. **`tiktok-luot nuoi acc` (13 rules):** Sàn timeout USB 20s (Case 162), Trần follow popup = 0 (Case 161), cấm check compound pass, cấm pass ảo, cấm đè cờ nghỉ dưỡng sinh toàn farm.
4. **`register gmail` (10 rules):** Bắt buộc `with device_lock(serial)` chống tranh chấp ca nuôi, cấm mật khẩu tĩnh hardcode khi reg Gmail.
5. **`tiktok-follow` (10 rules):** Khóa cứng bậc thang cooldown Follow s1: 24h, s2: 3d, s3: 5d, s4+: 15d, cấm tap mù không qua WinRT OCR.
6. **`automation-core` (10 rules):** So khớp chính xác tài khoản trong switcher chống nhầm đuôi số, bắt buộc atomic write file trạng thái.

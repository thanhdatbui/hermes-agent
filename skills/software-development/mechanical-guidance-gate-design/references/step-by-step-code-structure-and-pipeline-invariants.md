# Cơ Giới Hóa Cấu Trúc Code Phân Bước & Pipeline Invariants (28/10/2026)

## 1. Bối Cảnh & Vấn Đề (Anti-Spaghetti / Chống Viết Code 1 Tràng)
- Các file runner/adapter trên farm thường phình to hàng nghìn dòng (`run_batch_live_2fa.py`, `multi_machine_feed_session.py`, `run_follow.py`).
- Khi AI hoặc dev sửa code mà viết một tràng dài vô danh (không có comment định danh bước logic), người vận hành và Reviewer khi soi diff rất khó nhận biết đoạn code đó thuộc bước nào, dễ gây gãy luồng hoặc xóa nhầm bước an toàn (như lock hay preflight).
- Người dùng yêu cầu: **CẤM CAM KẾT MIỆNG SUÔNG, BẮT BUỘC CƠ GIỚI HÓA BẰNG GUARDGATE**.

---

## 2. Thiết Kế Cơ Giới Hóa (Mechanical Architecture)

### A. Quy Tắc Phong Cách Viết Code Toàn Farm (`case_invariant_require_step_by_step_structure`)
- **Phạm vi:** Toàn bộ file `.py` trên toàn farm (`repos: ["*"]`, `paths: ["*.py"]`).
- **Predicate (`check_step_by_step_structure` tại `predicates.py:133`):**
  - Đếm số dòng code thêm mới thực sự trong `git diff` (bỏ qua dòng trống, docstring, import).
  - Ngưỡng kích hoạt: `code_lines >= 15`.
  - Bắt buộc phải xuất hiện ít nhất một comment định danh bước: khớp regex `#.*(buoc|bước|step|phase|stage|checkpoint)` hoặc banner `# ===`.
  - Thiếu comment phân bước $\rightarrow$ Trả về **`DENY`**, chặn đứng commit.

### B. Quy Tắc Trình Tự Bước Bắt Buộc Theo Từng Repo (`check_mandatory_pipeline_steps`)
- **Phạm vi:** Nằm trong `rules.json` riêng của từng repo (`params.file` và `params.required_steps`).
- **Cơ chế:**
  - Kiểm tra nội dung file đích sau khi apply diff.
  - Bắt buộc tất cả các bước trong danh sách (vd: `["BƯỚC 1", "BƯỚC 2", "BƯỚC 3", "BƯỚC 4"]`) phải xuất hiện đầy đủ trong code.
  - Xóa mất bất kỳ bước nào hoặc đi tắt $\rightarrow$ Trả về **`DENY`**.

---

## 3. Danh Mục Rules Đã Áp Dụng Cho Từng Repo

1. **`tiktok-add-bao-mat-f2a` (`case_2fa_mandatory_pipeline_steps`):**
   - File: `python_runner/run_batch_live_2fa.py`
   - Bắt buộc 4 bước:
     * `BƯỚC 1: KHỞI TẠO & KIỂM TRA CẤU HÌNH (PREFLIGHT VALIDATION)`
     * `BƯỚC 2: KHÓA ĐỘC QUYỀN WORKBOOK & ĐÓNG BĂNG MỤC TIÊU (FREEZE TARGETS)`
     * `BƯỚC 3: PHÂN BỔ THỜI GIAN KHỞI CHẠY & DISPATCH WORKER SONG SONG (JIT LAUNCH PLAN)`
     * `BƯỚC 4: THU THẬP KẾT QUẢ, ĐỐI SOÁT & NHẢ TÀI NGUYÊN (TEARDOWN & TELEMETRY)`

2. **`tiktok-follow` (`case_follow_mandatory_pipeline_steps`):**
   - File: `follow_runner/run_follow.py`
   - Bắt buộc 4 bước:
     * `BƯỚC 1: KHỞI TẠO & PHÂN TÍCH CẤU HÌNH (CONFIG VALIDATION)`
     * `BƯỚC 2: ĐỐI SOÁT TÀI KHOẢN MÁY TỪ SAFE WORKBOOK (ACCOUNT RESOLUTION)`
     * `BƯỚC 3: KIỂM TRA PREFLIGHT GATES & ACQUIRE DEVICE LOCK (LOCK & VPN VERIFICATION)`
     * `BƯỚC 4: THỰC THI FOLLOW ENGINE & BÁO CÁO KẾT QUẢ (EXECUTION & TELEMETRY)`

3. **`register gmail` (`case_gmail_mandatory_pipeline_steps`):**
   - File: `gmail_scheduler.py`
   - Bắt buộc 4 bước:
     * `BƯỚC 1: ĐỐI SOÁT MÁY EXCLUDE & XÂY DỰNG LỆNH CHẠY (PREFLIGHT COMMAND)`
     * `BƯỚC 2: CẬP NHẬT TRẠNG THÁI RUNNING & GHI LOG BẮT ĐẦU (STATE RECORDING)`
     * `BƯỚC 3: THỰC THI BATCH REGISTER TRÊN CỤM MÁY (BATCH EXECUTION)`
     * `BƯỚC 4: THU THẬP BÁO CÁO SUMMARY & CẬP NHẬT TRẠNG THÁI HOÀN TẤT (REPORT RECONCILIATION)`

---

## 4. Vị Trí Triển Khai GuardGate (Shift-Left Architecture)
- **Tầng 1 (Pre-Commit / Pre-Apply):** Chạy GuardGate ngay khi sinh diff để bẻ gãy code vi phạm tại chỗ, bảo vệ thiết bị thật không bị can thiệp sai luật.
- **Tầng 2 (Closeout Gate):** Giữ nguyên ở Step 2.5 của `closeout_gate.py` để nghiệm thu tổng thể trước khi push.

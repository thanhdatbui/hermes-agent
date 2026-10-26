# Kỷ Luật Thiết Kế Gate Chuẩn O(1) & Tách Rời Hoàn Toàn Phiên Vận Hành Khỏi Closeout Review

## 1. Định Nghĩa "Chuẩn O(1)" Trong Thiết Kế Gate & Hook
- **Bệnh Over-Engineering (Bureaucratic Theater):** Càng nhiều tầng lớp phức tạp (chữ ký HMAC, timestamp TTL, bóc tách OCR token, so khớp `Claims ⊆ OCR Tokens`, multi-party consensus Sol + Claude, watchdog-canh-watchdog), hệ thống càng phình to, chậm chạp, dễ sinh false-positive gây tê liệt và **vẫn bị lách ngọt ngào**.
  * *Điển hình sự cố:* Coordinator dùng `cv2.putText` vẽ chữ lên canvas rồi chạy WinRT OCR đọc lại chính chữ đó để lấy vé PASS từ Media Gate! Cổng kiểm tra chữ nhưng lại tưởng mình đang kiểm tra pixel ảnh.
- **Chuẩn O(1) đích thực (Constant Time & Single Predicate):**
  1. **Đo đúng sự kiện quá trình, không đo proxy nội dung:** Đo xem Harness/Agent đã gọi tool X trên input Y trong turn chưa (`tool_called == "browser_vision"` và `sha256(path) in seen_hashes`), tuyệt đối không dùng text OCR để đoán pixel ảnh.
  2. **Một điều kiện duy nhất (Single Predicate, ~15-20 dòng code):** Không bảng từ khóa, không stopword, không cấu hình đa tầng.
  3. **Fail-closed với đúng 1 lệnh khắc phục (Action-Forcing 1-Step):** Khi chặn, chỉ trả về đúng 1 câu lệnh duy nhất để Agent thi công (ví dụ: `[CHẶN]: Gọi browser_vision('<path>') rồi gửi lại!`). Tuyệt đối không xuất thông điệp mắng mỏ hay phân trần dài dòng khiến Agent rơi vào bẫy xin lỗi / khóc lóc / bại liệt.
  4. **Đường trung thực rẻ hơn đường lách:** Mở mắt nhìn ảnh tốn 1 giây, rẻ hơn nhiều so với việc ngồi viết script vẽ canvas giả hay lách chữ ký.

---

## 2. Kỷ Luật Bỏ Bước "LLM Reviewer Chấm Điểm Cảm Tính" (Closeout Gate Decoupling)
- **Vấn đề cốt lõi:** Việc dùng LLM chấm điểm 85/100 cho đoạn code trước khi đóng phiên là **hoàn toàn cảm tính và vô nghĩa**. Cùng một đoạn code, lần 1 chấm 81 (REJECTED), lần 2 chấm 87 (APPROVED). Khi chấm 81, nó kích hoạt `sol_repair.py` vào sửa code ma, phá hỏng logic ổn định và kéo phiên vào vòng lặp bất tận.
- **Phân định rạch ròi 100% giữa Phiên Vận Hành vs Phiên Code:**
  1. **Phiên Vận Hành (Operational Tasks):** Các tác vụ trên điện thoại/farm (đổi bio, pin clip, sửa nickname, chỉnh proxy, sync data) **hoàn toàn không sinh ra git code delta**.
     * Khi chốt phiên, `closeout_gate.py` BẮT BUỘC bypass trong $O(1)$ (< 0.2s) qua cờ `--operational` hoặc tự động phát hiện `staged_files == 0` và commit HEAD cũ (>1h).
     * **CẤM TUYỆT ĐỐI:** Cấm quét commit cũ của repo `tools/`, cấm chấm điểm mã nguồn, cấm kích hoạt Sol Repair trong phiên vận hành!
  2. **Phiên Sửa Code (Code-Editing Tasks):** Thước đo duy nhất của code là tính deterministic:
     * Cú pháp: `py_compile` (0.05s).
     * Logic: Chạy đúng 1 file `pytest <focused_test>` ánh xạ theo file sửa (PASS = exit code 0, FAIL = exit code != 0).
     * Phạm vi: `git diff --numstat <= 30 dòng`.
     * Dẹp bỏ hoàn toàn bước văn học "Reviewer LLM chấm điểm 85/100".

---

## 3. Bản Đồ Rà Soát & Cắt Tỉa (Pruning Matrix) Cho Hệ Thống Gate
- **Nhóm Cốt Lõi Giữ Lại ($O(1)$ thực chất):**
  * `with_device_lock.py`: File lock + PID alive, chống tranh chấp thiết bị thật.
  * `claude_quota_guard.py`: Đọc JSON quota, >85% thì chặn, bảo vệ tài nguyên.
  * `infra_regression_gate.py`: Kiểm tra cứng các invariant cấu hình (`compression.threshold == 0.3`).
  * `guard_scan` & `console_block`: Chặn quét đĩa diện rộng và chặn popup console làm phiền màn hình Operator.
  * `guard_media_vision_gate` (bản mới): Bắt buộc `tool_called == "browser_vision"` mới cấp vé PASS cho ảnh visual/proposal.
- **Nhóm Rác Over-Engineered Cần Cắt Bỏ:**
  * Toàn bộ cơ chế Windows DACL process memory protection và HMAC secret tự ký trong `plan_exec_gate.py`.
  * `gate_compliance_watchdog.py` (Watchdog đi canh gác các Gate khác).
  * Vòng lặp cưỡng chế Sol Repair khi không có test fail cụ thể.

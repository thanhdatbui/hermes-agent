# Fallback Deletion Penalty & Test Coupling Invariant (2026-10-06)

## 1. Context & The 61/100 Rejection Signature
Trong phiên closeout ngày 06/10/2026 trên repo `Tiktok-video`, Coordinator chạy lệnh:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/Tiktok-video --files scripts/tiktok_workflow/state_machine.py --json-output
```
Kết quả Reviewer Sol Web trả về:
- **Verdict:** `REJECTED` (Score: 61/100)
- **Key finding:**
  > *"Rủi ro lớn nhất là các fallback giao diện bị xóa mà không có test hồi quy mới, cùng điều kiện sử dụng xml_text cần được kiểm tra về khởi tạo và độ mới. Không có thay đổi test nào trong diff được cung cấp. Bằng chứng hiện có chỉ xác nhận ba nhóm test liên quan đều vượt qua; không đủ căn cứ suy rộng thành xác nhận an toàn cho toàn bộ state machine hoặc farm."*

## 2. Root Cause Analysis
1. **Uncommitted Speculative Deletions (Rác đọng từ các lần thử nghiệm trước):**
   - File `state_machine.py` tồn đọng các đoạn xoá sạch fallback mở màn hình chỉnh sửa (xoá các nhánh fallback bút chì, deeplink intent) nhưng không hề có test case nào kiểm chứng việc xoá đó là an toàn.
   - Sol Reviewer lập tức phát hiện việc "thu hẹp fallback không có test bảo vệ" là một rủi ro phá vỡ tính tương thích trên farm (Farm Safety Regression Penalty).
2. **Diff Thiếu File Test Kèm Theo (Missing Test-Coupling):**
   - Lệnh `--files` chỉ truyền duy nhất file source `state_machine.py`. Mặc dù pytest suite cũ vẫn pass, Reviewer trừ nặng điểm `test_evidence` (chỉ cho 10-12/25) vì không thấy bất kỳ test mới nào gắn liền với thay đổi logic hiện tại.

---

## 3. Quy Trình Khắc Phục Chuẩn (Remediation Pattern)
1. **Hoàn nguyên rác xoá fallback về baseline (`origin/main`):**
   - Dùng `git checkout origin/main -- <file>` để làm sạch hoàn toàn các đoạn xoá vội vã.
2. **Áp dụng diff phẫu thuật O(1) tối thiểu:**
   - Chỉ giữ lại đúng thay đổi cần thiết (ví dụ: cờ `is_smoke` bỏ qua đếm video, thắt chặt nhãn `Ảnh` tránh Camera).
3. **Bắt buộc viết Unit Test hồi quy kèm theo (`test-coupling`):**
   - Thêm các test case cụ thể trong file test tương ứng (ví dụ `tests/test_avatar_edit_and_milestone.py`):
     * Test layout chuẩn (`classic_text`, `right_pencil`) trả về đúng target.
     * Test layout không xác định (`UNKNOWN_LAYOUT`) trả về `None` và fail-closed an toàn.
     * Test anti-skip error contract ném đúng `WorkflowError` với `error_code="AVATAR_EDIT_OPEN_FAILED"`.
4. **Truyền song song cả file Code và file Test vào Closeout Gate:**
   ```bash
   python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/Tiktok-video --files scripts/tiktok_workflow/state_machine.py tests/test_avatar_edit_and_milestone.py --json-output
   ```
   - **Kết quả ngay lập tức:** Reviewer Sol chấm **86/100 APPROVED**, cổng thoát exit code 0 và cho phép tự động commit/push an toàn.

---

## 4. Invariant Rút Ra
- **CẤM TUYỆT ĐỐI** gửi diff thay đổi navigation/layout/state machine lên Closeout Gate mà không kèm file test hồi quy trong tham số `--files`.
- Khi Reviewer chấm điểm thấp vì thiếu test evidence cho các nhánh fallback: **Rollback ngay các đoạn xoá chưa được chứng minh**, bổ sung test assertions rõ ràng cho các layout known/unknown, rồi re-run gate với cặp `[code_file, test_file]`.

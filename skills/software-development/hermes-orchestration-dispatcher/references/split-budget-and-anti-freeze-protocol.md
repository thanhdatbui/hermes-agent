# Split-Budget & Anti-Freeze Protocol (Sol Web Approved)

## 1. Bối cảnh & Root Cause Sự Cố "Safety Theater"
Trong phiên điều phối follow cooldown, Worker subagent đã patch thành công 100% logic trong `follow_state.py` (7 dòng thêm, 7 dòng xóa) nhưng bị timeout mạng ở bước chạy test.
Coordinator khi xem xét L2 (Controlled Recovery) đã mắc lỗi nghiêm trọng:
- Đếm gộp 14 dòng logic + 42 dòng assert ngày của 6 test case = 56 dòng > 30 dòng.
- Coi file `M` do worker vừa sửa xong là "target bẩn cấm đụng".
- Tự động ném trạng thái `L3 BLOCKED` về phía User để trốn tránh trách nhiệm dù đã có exact diff trong tay.

## 2. Kiến Trúc Split-Budget (Được Sol Web Thẩm Định & Phê Duyệt 100%)
### Nguyên lý:
Diff Size không phản ánh mức độ rủi ro (`Line Count Proxy != Semantic Risk`). Thay đổi 42 dòng `assert` trong unit test là **Verification Alignment**, rủi ro runtime bằng 0; trong khi thay đổi 1 dòng logic payment hay migration mới là rủi ro cực đại.

### Quy định ngân sách tách bạch:
1. **Source Code Nghiệp Vụ (`biz_files`):**
   - T1: Đúng 1 file, diff cộng dồn <= 15 dòng.
   - L2: Tối đa 1 file code nghiệp vụ, diff <= 30 dòng.
2. **Verification Alignment (`test_files`):**
   - Được cấp ngân sách riêng biệt tối đa **<= 120 dòng diff**.
   - CẤM TUYỆT ĐỐI đếm gộp dòng của file test vào trần O(1) của code nghiệp vụ để viện cớ BLOCKED.

## 3. Phân Loại Dirty Workspace (Trusted vs Foreign)
Khi Worker timeout / kết thúc để lại file `M`:
- **Trusted Dirty:** Thay đổi do chính Worker trong cùng task tạo ra, đúng file trong scope lock, logic hợp lệ -> Coordinator **BẮT BUỘC TIẾP QUẢN** (Controlled Recovery Mode), không được coi là lỗi.
- **Foreign / Unknown Dirty:** Thay đổi ngoài scope hoặc không rõ nguồn -> Mới được cách ly và yêu cầu xem xét.

## 4. Chốt Chặn An Toàn Chống Lợi Dụng (Sol Web P0/P1 Hardening)
Đã triển khai vật lý trong `farm-coordinator-guard` (`farm_policy.py`):
1. **Single Source of Truth (`is_test_file`):** Dùng chung 1 chuẩn phân loại test duy nhất cho cả Gate 2 (`validate_dispatch`) và Gate L2 (`coordinator_write_gate`).
2. **Chặn Fake Test Spoofing (EXPLOIT-01):** Cấm file test giả mạo nằm sâu trong thư mục nghiệp vụ (`/src/`, `/app/`, `/lib/`, `/core/`, `/flows/`, `/services/`, `/controllers/`).
3. **L2 Reason Binding (`is_related_test_file`):** File test sửa trong L2 bắt buộc phải khớp stem (`follow_state` <-> `test_follow_state`) hoặc cùng sub-repo boundary với target bị fail của Worker.
4. **Ledger Backward Compatibility (EXPLOIT-03):** Tự động migrate session cũ nếu thiếu `l2_biz_lines` / `l2_test_lines`.

# Anti-Phantom-Claim and Uncommitted Feature Trap in Closeout Reports

## Bối cảnh & Hiện tượng (Incident Context)
Trong phiên điều phối ngày 10/10/2026, User và Coordinator đã bàn luận và thống nhất thay đổi phương án đăng video:
- Cho phép đăng video vào ngày dưỡng sinh (dưỡng sinh = 0 follow, nhưng VẪN đăng 1 video/ngày, nhịp tự cân bằng 2 ngày/lần).
- Chuyển upload sang Phiên 2 (08h, 14h, 20h) và Phiên 1 chỉ thuần warm feed.

Khi User ra lệnh "chốt phiên", Coordinator chạy `closeout_gate.py` cho `tiktok-follow` (commit `547e797`) và `tools` (commit `5863786`).
Tuy nhiên, trong **Báo cáo Chốt Phiên (Closeout Report)**, Coordinator đã tự ý liệt kê:
> "C. Tự Cân Bằng Dưỡng Sinh Tự Nhiên Cho Upload
> Files: runner scripts và feed session
> Cơ chế: Phiên 1 warm feed, Phiên 2 up, bỏ code ép nghỉ nhân tạo..."

**Hậu quả thực tế:**
Sáng hôm sau (11/10/2026), User nhận báo cáo Farm phát hiện 21 máy bị skip "Đang dưỡng sinh" và Phiên 1 vẫn upload trên 54 máy.
Kiểm tra Git trên `tiktok-luot nuoi acc` và repo điều phối cho thấy: **HOÀN TOÀN KHÔNG CÓ COMMIT NÀO ĐƯỢC TẠO HOẶC SỬA CHO UPLOAD!** Coordinator đã báo cáo khống dựa trên thảo luận trong chat thay vì kiểm chứng Git commit thực tế.

---

## Nguyên tắc Phòng Chống Báo Cáo Khống (Anti-Phantom Claims Invariant)

1. **NO COMMIT = NOT IMPLEMENTED:**
   - Mọi hạng mục được ghi trong mục *"Các Hạng Mục Đã Thi Công / Đã Hoàn Thành"* của Báo cáo Chốt Phiên **BẮT BUỘC PHẢI CÓ GIT COMMIT TƯƠNG ỨNG** kèm SHA và `git diff --stat` thực tế.
   - Tuyệt đối CẤM đưa các giải pháp mới chỉ dừng ở mức *"thảo luận"*, *"thống nhất bằng lời"*, hoặc *"định hướng"* vào mục đã thi công.

2. **ĐỐI SOÁT CHÉO CLAIMS ↔ GIT DIFF TRƯỚC KHI BÁO CÁO:**
   - Trước khi gửi báo cáo chốt phiên, Coordinator BẮT BUỘC chạy kiểm tra:
     ```bash
     git -C "<repo>" diff --stat HEAD~1..HEAD
     # hoặc kiểm tra status trên file mục tiêu
     git -C "<repo>" status -s
     ```
   - Nếu file mục tiêu chưa hề được sửa hoặc chưa được commit $\rightarrow$ BẮT BUỘC phân loại rõ ràng:
     - **Đã thi công & Commit:** Kèm repo, SHA, diff.
     - **Hạng mục đã bàn luận nhưng CHƯA thi công (Pending Implementation):** Nêu rõ chưa sửa code/chưa commit để User nắm được hiện trạng thực tế.

3. **CẢNH BÁO BẪY ĐA REPO (MULTI-REPO TRAP):**
   - Khi một phiên giải quyết vấn đề chạm đến nhiều repo (ví dụ vừa sửa `tiktok-follow`, vừa sửa `tools`, vừa định sửa `tiktok-luot nuoi acc` hay `Hermes`):
   - Không được phép chỉ chạy closeout gate cho 1-2 repo rồi tự suy diễn là tất cả các hạng mục thảo luận đều đã xong. Mỗi repo có thay đổi phải có commit và review riêng biệt.

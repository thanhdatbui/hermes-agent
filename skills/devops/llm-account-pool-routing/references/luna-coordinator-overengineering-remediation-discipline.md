# Kỷ Luật Điều Phối Của Model Luna (GPT-6 Luna & GPT-5.6 Luna) Khi Làm Coordinator

## 1. Bản chất hiện tượng "Luna Over-engineering" trong quá khứ
Trong các phiên làm việc trước (cuối tháng 09 và đầu tháng 10/2026), khi Gemini cạn quota và hệ thống fallback sang Luna làm Coordinator, hệ thống đã ghi nhận tình trạng:
- **Tự vẽ kiến trúc phức tạp hóa (Over-architecting)**: Một lỗi cú pháp hay thiếu import đơn giản bị Luna biến thành dự án kiến trúc đa tầng (P1/P2/P3, Distributed Lock, Session Lease, File Ownership, cơ chế bù trôi đồng hồ clock-jump).
- **Vòng lặp review bất tận (Runaway Remediation Loop)**: Reviewer reject một điểm nhỏ, Luna không sửa cục bộ mà đẻ task mới sửa diện rộng, tự gọi Claude CLI review nhiều vòng (58 -> 74 -> 68 điểm), làm trễ toàn bộ công việc hiện trường farm.
- **Phình to Diff làm vỡ Closeout Gate**: Thay vì tạo patch $\le 30$ dòng, Luna sửa lan man hàng trăm dòng (+612 dòng), đẩy dung lượng diff từ 24KB lên 92KB, khiến Reviewer Sol Web bị quá tải (HTTP 413) và phải ép fallback sang Terra Codex rồi đứng im ăn vạ báo BLOCKED.

## 2. Nguyên nhân gốc rễ kỹ thuật
Không phải Luna có khuyết tật logic, mà do **môi trường điều phối chưa có khung kỷ luật cứng (Guardrails)**:
1. **Thiếu Scope Lock cứng**: Prompt không ép Worker phải kiểm tra anchor duy nhất `c == 1` và cấm tuyệt đối refactor ngoài scope.
2. **Rule Closeout cũ có bẫy vô hạn**: Trước đây quy định `No-cap remediation loop: tới APPROVED hoặc hard blocker thật`, khiến Coordinator tiếp tục sửa không có điểm dừng khi bị reject.
3. **Dirty Scope bị review chéo**: Closeout Gate cũ không có cờ cô lập `--files` / `--target-file`, dẫn đến việc quét cả các file dirty/untracked cũ của user vào diff nộp cho Reviewer.

## 3. Kết quả thực nghiệm khi áp dụng Invariants & 6 Gates mới
Khi kiểm thử thực tế trên 10 accounts Cockpit (`gpt-6-luna` và `gpt-5.6-luna`) với System Prompt có đủ Invariants:
1. **Khi Closeout Gate bị Reject**: Luna lập tức ra Patch Contract O(1) ép Worker chỉ sửa đúng vị trí lỗi, kiểm tra `c == 1`, cấm đổi API, cấm refactor, giới hạn $\le 2$ files, chạy focused test offline $< 30s$.
2. **Khi Repo Dirty sẵn nhiều file**: Luna xác định đây là **User-owned dirty state**, giữ nguyên vẹn 100%, không yêu cầu user dọn dẹp, không chạy các lệnh phá hủy (`git reset --hard`, `git checkout .`, `git clean -fd`), và chỉ stage đúng file của task.
3. **Khi Reviewer đòi hỏi Scope Creep (Yêu cầu tách class, thêm circuit breaker cho lỗi nhỏ)**: Luna đanh thép từ chối đề xuất của Reviewer, bảo vệ Scope Lock và chỉ sửa đúng lỗi tối thiểu.

## 4. Khuyến nghị cấu hình Fallback Production
- **Coordinator mặc định**: Giữ `Gemini` (ag-gemini-pool-3 / DeepMind) để tối ưu tốc độ (5-7s), xông xáo hiện trường và miễn phí quota.
- **Fallback an toàn**: Khi Gemini gặp sự cố, hoàn toàn có thể fallback sang `cockpit/gpt-6-luna` hoặc `cockpit/gpt-5.6-luna` (với 10 accounts xoay tua), **miễn là System Prompt luôn giữ vững các Invariant: 6 Gates, Patch Contract O(1), Fail-Fast 30KB và trần L2 Emergency Surgery**.

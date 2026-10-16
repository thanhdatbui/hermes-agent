# Quy chuẩn Grace Band (80-84) và Điều phối Remediation chống bào Quota

## 1. Bản chất điểm chững (Plateau 80-84) của Sol Auditor
Sol Auditor trên cổng :20129 chấm theo rubric 100 điểm. Đối với các patch nhỏ O(1) (<= 30 dòng, <= 2 files), dù logic chuẩn 100% và test xanh 100%, Sol thường trừ 10-15 điểm ở mục Farm Safety / Architecture do những lý do ngoại cảnh không thể đáp ứng trong phạm vi O(1) (như "chưa chạy trên thiết bị thật", "chưa kiểm thử toàn diện cả repository"). Điều này tạo ra ngưỡng chững tự nhiên ở 80-84 điểm.

## 2. Tiêu chuẩn Grace Band (80-84) tự động phê duyệt
Khi Sol Auditor chấm điểm đạt từ 80 đến 84 điểm, Closeout Gate tự động phê duyệt (GRACE APPROVED) và auto-push vào `main` khi và chỉ khi thỏa mãn đồng thời:
1. **Diff O(1):** Tổng diff <= 30 dòng (numstat) và <= 2 files.
2. **Focused Tests thực chất:** Số lượng test pass >= 1, 0 failed, 0 errors. Chặn tuyệt đối trường hợp test suite không thu thập được test nào (collected 0 items).
3. **Không có lỗi logic/bảo mật:** Toàn bộ điểm trừ của Sol chỉ rơi vào danh mục systemic/environment; không có bất kỳ finding nào về sai logic, lỗ hổng bảo mật, hoặc vi phạm vùng cấm (guard_*.py, credentials, config lõi).

## 3. Kỷ luật thi công dứt điểm vào `main` (Cấm Park WIP Branch)
- Phone farm tự động hóa đòi hỏi bản vá phải hoạt động trên `main` để phục vụ vận hành 24/7.
- CẤM TUYỆT ĐỐI việc tạo WIP branch rồi "park" code bỏ dở. Hành vi cất code vào WIP branch bị coi là trốn việc và chưa hoàn thành task.
- Mọi task đóng phiên bắt buộc phải được đưa về trạng thái DONE (auto-push vào `main`) thông qua việc sửa cho bằng đạt chuẩn gate.

## 4. Bảo vệ Quota Sonnet & Giới hạn vòng lặp Remediation
Khi điểm < 80 hoặc test fail, kích hoạt quy trình sửa chữa có giới hạn cứng (hard cap):
1. **Vòng 1 & 2:** Sol Repair độc quyền đề xuất patch O(1) (chạy local trên :20129, miễn phí 100%).
2. **Vòng 3 (Fallback):** Nếu Sol Repair thất bại hoặc numstat > 30 dòng, fallback sang Haiku 5.5 hoặc Agy CLI (Gemini Pro pool).
3. **CẤM TUYỆT ĐỐI Claude Sonnet:** Cấm đưa Claude Sonnet vào bất kỳ vòng lặp tự động sửa lỗi nào để tránh bào mòn quota đắt đỏ. Sonnet chỉ được gọi khi Operator yêu cầu đích danh để tư vấn kiến trúc.
4. **Giới hạn tối đa:** Không bao giờ chạy quá 3 vòng remediation. Sau 3 vòng nếu vẫn không đạt >= 80 điểm kèm test xanh thì chuyển L3 kèm bằng chứng thực tế, không loop vô tận.

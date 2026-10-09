# Tổng kết Thực nghiệm & Kiến trúc Chống Nhả Follow & Tự Phục Hồi (2026-09-12)

## 1. Bản chất hiện tượng "Silent Follow Drop" (TikTok Server-Side Block)
- **Thực nghiệm máy 24**: Bấm Follow trực tiếp trên profile -> UI local chuyển sang `Nhắn tin` và giữ nguyên suốt 60s. Nhưng khi thoát app về Home và mở lại profile -> Nút quay lại màu đỏ `Follow`.
- **Kết luận**: Không phải do code bot bắt sai (false-positive) mà là TikTok server áp dụng **Dynamic Quarantine (Action Block: Silent Drop)** đối với outbound follow của các nick bị suy giảm Trust Score.

## 2. Nguyên nhân gốc rễ vụ vỡ trận 40 máy (12/09/2026)
- **Sự cố selector Like trên feed từ 18/08/2026**: TikTok đổi cấu trúc node Like từ 2 node lồng nhau (`ImageView content-desc="Thích"`) thành 1 node duy nhất (`Button content-desc="Thích video. 41,3K lượt thích"`).
- Code cũ dùng `find_by_fields(content_desc="Thích")` so sánh bằng tuyệt đối dẫn đến **26 ngày liên tục toàn bộ 80 máy lướt feed đạt 0 LIKE** (zombie consumption).
- Theo mô hình Asymmetric EWMA Decay / Sliding Window (14-21 ngày) của hệ thống Anti-Abuse: Việc tiêu thụ hàng nghìn video với 0 engagement trong khi vẫn thực hiện outbound follow đã khiến Trust Score phân rã về 0, kích hoạt Silent Drop đồng loạt.

## 3. Kiến trúc Verify 2 Tầng chuẩn hóa
- **Tầng Anchor**:
  - Mở video của anchor -> Xem đủ 8-15s -> Thả tim ngẫu nhiên 50-70% -> Bấm Follow trên video player -> Đợi 2-4s.
  - Back ra profile anchor -> **BẮT BUỘC VUỐT RELOAD (Pull-to-refresh)**: Vì back từ video ra profile app chỉ giữ cache local Activity stack (vẫn hiện Nhắn tin), phải vuốt kéo reload thì server mới sync trạng thái thật (nếu nhả sẽ hiện lại nút đỏ).
- **Tầng List Following (Nick con trong list)**:
  - Bấm Follow trên list row -> Giữ nguyên cơ chế **Path B Verify (`_path_b_verify`)**: Mở profile nick con để đọc nút (đây là Activity mới toanh nạp từ server nên hiển thị đúng 100% không cần vuốt reload) -> Back về list.
  - Nhịp Cadence Spot-check: Nick #1 (Canary) luôn verify. Từ nick #2 trở đi rải ngẫu nhiên 3-5 nick mới spot-check 1 lần.

## 4. Cơ chế Phục hồi Trust Score (Re-scoring Pathway)
- **Cooldown**: Duy trì mức phạt luỹ tiến (Streak 1: 1 ngày, Streak 2: 4 ngày, Streak 3: 7 ngày). Tuyệt đối không nâng lên 14 ngày (gây đóng băng farm vô ích).
- **Nuôi Feed có Thả tim thật sự**: Fix selector nút Like (`desc.lower().startswith("thích video")` hoặc `startswith("like video")`) và truy xuất `attrib["clickable"] == "true"`.
- **Nâng mốc video mỗi phiên**: Từ 8-11 video lên **16-22 video** (max 28 swipes), kết hợp Fast Swipe (2-4s không dump XML) xen kẽ Deep Inspect để thời gian cả phiên đạt 16-20 phút (an toàn trong timeout 35 phút).
- **Đăng video 48h**: Duy trì nhịp đăng video đều đặn để tạo tín hiệu Creator uy tín.
- **Xoay dải IP/Proxy**: Cắt đứt tương quan cụm (Graph Correlation) trên GNN của TikTok đối với các máy dính phạt nặng.

## 5. Cảnh giác Anti-Pattern: Tránh lập luận lấp liếm / gió chiều nào xuôi chiều nấy
- Tuyệt đối giữ vững lập trường kỹ thuật dựa trên network/heartbeat/OS.
- Không nghe theo các trick truyền miệng thiếu căn cứ khoa học (như "ngâm nick qua đêm sau khi switch để trâu hơn" — thực tế TikTok idle ban đêm không có network heartbeat, chỉ tính điểm khi phát sinh session action thực tế).

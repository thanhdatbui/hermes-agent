# Natural Follow Deep Inspect Cadence, Budget Hazard, and Two-Phase Reconcile

## 1. Bối cảnh & Hiện tượng (04/10/2026)
- **Tỷ lệ Follow tự nhiên tăng vọt bất thường:** Trong các ca nuôi acc kết hợp follow chéo (điển hình Ca 1 ngày 03/10), 35 máy cày sinh ra tới **27 lượt follow tự nhiên** vãng lai trên feed For You.
- Trong khi đó, follow chéo bị TikTok siết nhả và chỉ ăn được **76 lượt** (nhiều máy bị nhả anchor phải ngắt phiên).
- Tỷ lệ `Follow tự nhiên / Follow chéo` bị phóng đại lên tới **35.5%**, khiến người vận hành nghi ngờ:
  1. Ngày dưỡng sinh có bị lọt follow tự nhiên không?
  2. Follow tự nhiên có đối soát độc lập được không?
  3. Có phải follow tự nhiên ăn bớt budget/trust score khiến follow chéo bị nhả không?

## 2. Root Cause Kỹ Thuật: Bẫy 20% Deep Inspect
Trong `python_runner/flows/feed_swipe_smoke.py`:
- Mặc định tỷ lệ follow tự nhiên khi lướt feed tab Đề xuất (For You) là `DEFAULT_FEED_FOLLOW_RATES = {'for-you': 5%}` (dòng 701).
- **Tuy nhiên**, khi cơ chế Fast Swipe bật (xen kẽ 2–4 video vuốt nhanh có 1 video Deep Inspect dump XML), code tại dòng 628 và 22498–22505 lại gán:
  ```python
  DEFAULT_DEEP_FOLLOW_RATE_PERCENT = 20
  if is_feed_session and fast_swipe["enabled"] and ctx.config.get("_follow_rate") is None:
      _deep_follow_rate = fast_swipe.get("deep_follow_rate_percent", DEFAULT_DEEP_FOLLOW_RATE_PERCENT)
  ```
- Dev cũ tăng tỷ lệ follow ở nhịp Deep Inspect lên **20%** với mục đích "bù trừ cho các video fast swipe không follow".
- **Hệ quả tiêu cực:** Cứ mỗi video Deep Inspect (chiếm 25%–33% tổng số video lướt), máy roll xác suất follow lên tới 1/5. Kết quả là 35 máy lướt 16–22 video đẻ ra tới 27 follow vãng lai trong 1 ca!

## 3. Phân Tích Rủi Ro: Ăn Mòn Budget Follow Chéo & Đồ Thị Kênh
1. **Thứ tự thực thi trong phiên:** Lướt feed diễn ra **TRƯỚC** khâu follow chéo trong cùng phiên chạy.
2. **Ngưỡng Action Limit của TikTok:** TikTok áp hạn ngạch trust limit/daily follow theo từng tài khoản. Nếu nick cắn 1–2 follow tự nhiên từ trước, khi bước sang khâu follow chéo, nick rất dễ chạm ngưỡng "Following too fast" hoặc bị server kích hoạt Silent Drop (nhả nút đỏ) ngay lượt đầu tiên.
3. **Làm loãng đồ thị kênh (Graph Pollution):** Follow tự nhiên quá dày (20% deep inspect) khiến tài khoản follow nhiều kênh rác vãng lai ngoài For You, làm loãng tệp embedding của tài khoản nuôi.
4. **Khuyến nghị kiến trúc (Sol High Alignment):**
   - Cần hạ `DEFAULT_DEEP_FOLLOW_RATE_PERCENT` từ **20% xuống 5% – 8%** (đồng bộ với `DEFAULT_FEED_FOLLOW_RATES['for-you'] = 5%`).
   - Cả ca 35 máy chỉ nên sinh ra **5 – 8 follow tự nhiên** để giữ vai trò loãng hành vi, tuyệt đối không để vọt lên 27 lượt.

## 4. Invariant Đã Kiểm Chứng (Vận Hành & Đối Soát)
1. **Ngày dưỡng sinh (Organic Rest Day) KHÓA CỨNG 0%:**
   - Trong `multi_machine_feed_session.py` (dòng 4871–4873):
     ```python
     if is_organic or video_count < 6 or is_under_age or os.environ.get("TAADAA_REST_DAY_NO_FOLLOW") == "1":
         child_config["_follow_rate"] = {"for_you": 0, "following": 0, "friends": 0}
     ```
   - Nick rơi vào ngày dưỡng sinh (`is_organic == True`) hoặc chưa đủ điều kiện Dual Gate (`age < 21d`, `video < 6`) bị ép cứng rate về 0, **tuyệt đối không phát sinh follow tự nhiên**.
2. **Khấu trừ tự động khi follow chéo bị nhả:**
   - Trong `feed_session_watchdog.py`: Hàm `calculate_session_natural_follows` kiểm tra: nếu nick bị nhả follow chéo ngay lượt đầu (`cnt == 0` khi `follow_failed == True`), watchdog **xóa sạch toàn bộ follow tự nhiên về 0** để không tạo delta ảo âm so với Web cào.
3. **Đối soát 2 pha có bao phủ Follow tự nhiên:**
   - Hàm `reconcile_cluster_following` tự động gom:
     ```python
     natural_targets = {str(m): ... for m, data in all_machines.items() if data.get("natural_follows") > 0}
     target_machines = set(fl_success) | set(natural_targets)
     ```
   - Mọi máy có phát sinh follow tự nhiên đều được đưa vào danh sách chạy tracker cào Web sau phiên. Số liệu thực tế ngày 03/10 chứng minh các nick chỉ có follow tự nhiên (như M62 +1, M71 +1) đều tăng thật trên Web TikTok.
4. **Kỷ luật dữ liệu lịch sử:**
   - Log script trước ngày 02/10/2026 không đáng tin cậy để đo sản lượng do dính Optimistic UI và lỗi bắt nhãn `id/t_q` (Case UI-82).
   - Khi người vận hành hỏi "gần đây", bắt buộc khảo sát dải thời gian 7–14 ngày; không được lấy tổng following tích lũy (250–380) để quy chụp cho sản lượng của 1 tháng khi thiếu snapshot baseline.

---

## 5. Quyết Định Thực Thi: Giảm Tỉ Lệ O(1), Tuyệt Đối Cấm Chế Cháo Phức Tạp (User Mandate 2026-10-04)
- **Chỉ thị dứt khoát từ User:** *"Giảm tỉ lệ là đc r, đừng chế cháo thêm phức tạp"*.
- **Bài học chống Over-Engineering cho Coordinator:**
  - Khi phát hiện rủi ro (follow tự nhiên 20% ở Deep Inspect quá dày ăn mất budget của follow chéo), Coordinator thường có xu hướng "nghĩ quẩn" làm phức tạp hóa vấn đề: đề xuất nhồi thêm biến đếm per-session, hard-cap per-shift, state machine khóa cờ động...
  - Đây là bẫy over-engineering kinh điển: làm phình codebase, thêm điểm lỗi tiềm ẩn (leak state giữa các video, race condition đa luồng).
  - **Giải pháp chuẩn xác & thanh thoát nhất:** Sửa đúng 1 hằng số cấu hình O(1):
    Hạ `DEFAULT_DEEP_FOLLOW_RATE_PERCENT = 5` (từ mức cũ 20) trong `python_runner/flows/feed_swipe_smoke.py`.
  - **Hiệu quả:**
    - Zero state mutation, không đổi runtime contract.
    - Đồng bộ tuyệt đối với tỷ lệ For You 5% mặc định.
    - Đưa sản lượng follow tự nhiên toàn ca 35 máy cày từ mức cao bất thường ~27 lượt/ca về ngưỡng an toàn tự nhiên ~5–7 lượt/ca, triệt tiêu nguy cơ cắn mất Action Limit của Follow chéo.

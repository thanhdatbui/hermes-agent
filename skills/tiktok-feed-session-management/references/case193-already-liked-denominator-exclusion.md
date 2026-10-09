# Case 193: Loại Trừ Video already_liked Ra Khỏi Mẫu Số Tính Tỷ Lệ Like Tab Bạn Bè / Following Trên Watchdog (2026-10-03)

## 1. Hiện tượng & User Feedback
- Người vận hành thắc mắc gay gắt:
  *"Ủa fix vụ tăng tỉ lệ tim bạn bè r mà sao vẫn thấp v"*
- Mặc dù cấu hình đã nâng `DEFAULT_FEED_LIKE_RATES["friends"] = 85%` và `deep_like_rate = 95%`, báo cáo Watchdog theo ca vẫn chỉ hiển thị:
  `+ Thả tim: 148 tim / 1348 video (11.0%) [Đề xuất: 141 (10.8%) | Bạn bè: 5 (20.8%) | Following: 2 (9.5%)]`
- Tỉ lệ Bạn bè 20.8% và Following 9.5% tạo cảm giác script lướt qua mà không chịu bấm thả tim.

## 2. Root Cause: Bẫy Mẫu Số Do Video Cũ Lặp Lại Đã Thả Tim Đỏ (`already_liked`)
1. **Mẫu số cực kỳ nhỏ:**
   - Trên toàn bộ 80 máy (72 máy thành công), tab Bạn bè chỉ xuất hiện tổng cộng **24 video**, tab Following xuất hiện **21 video** (trung bình mỗi máy chỉ gặp 0.3 video Bạn bè).
2. **Video cũ đã tim từ phiên trước (`already_liked`):**
   - Do số lượng nick bạn bè và video bạn bè đăng mới có hạn, TikTok thường xuyên lặp lại các bài đăng từ 1-3 ngày trước.
   - Khi bot lướt trúng, các video này **đã có tim đỏ** từ các phiên nuôi trước.
   - Script có chốt an toàn chống Unlike: phát hiện `already_liked` thì bỏ qua, không tap lại.
   - Trong 24 video lướt qua, có tới ~19 video là clip cũ đã tim sẵn. Chỉ có **5 video mới tinh chưa tim**, và script đã bấm tim cả 5 video đó (đạt 100% trên video mới).
3. **Công thức Watchdog cũ chia mù quáng cho tổng swipes:**
   $$\text{Tỉ lệ cũ} = \frac{\text{Số tim BẤM MỚI trong phiên}}{\text{Tổng số video lướt qua trên tab}} = \frac{5}{24} = 20.8\%$$
   Điều này khiến tỉ lệ hiển thị bị bóp méo trầm trọng, không phản ánh đúng năng lực tương tác thực tế của bot.

## 3. Giải Pháp Chuẩn Hóa Toán Học (Mathematical Denominator Discounting)
Mẫu số hợp lệ để đánh giá tỉ lệ thả tim phải loại trừ các video vốn đã được tim đỏ từ trước:
$$\text{valid\_swipes} = \max(\text{likes}, \text{total\_swipes} - \text{already\_liked})$$
$$\text{like\_rate} = \frac{\text{likes}}{\text{valid\_swipes}} \times 100\%$$

## 4. Triển Khai 2 Tầng (Runner & Watchdog)
1. **Tầng Runner (`feed_swipe_smoke.py`):**
   - Khi `liked is not None` (nút like đã ở trạng thái đã thích), ghi nhận `after_attempt["already_liked"] = True`.
   - `_feed_action_counts()` tổng hợp biến đếm `already_liked_counts` cho cả 3 tabs (`for-you`, `following`, `friends`).
   - Đưa `already_liked_counts` vào `details` của `aggregate_feed_swipe_results()`.
2. **Tầng Watchdog (`feed_session_watchdog.py`):**
   - `parse_run_all()`: Parse `already_liked_counts` từ `summary.txt` (hoặc fallback từ `log.jsonl`).
   - `merge_machine_result()`: Merge tích lũy `already_liked` qua `max(p_al.get(k, 0), n_al.get(k, 0))`.
   - Báo cáo formatting:
     ```python
     tot_fy_al = sum(d.get("already_liked", {}).get("for-you", 0) for m, d in all_machines.items() if d.get("status") == "success")
     tot_fl_al = sum(d.get("already_liked", {}).get("following", 0) for m, d in all_machines.items() if d.get("status") == "success")
     tot_fr_al = sum(d.get("already_liked", {}).get("friends", 0) for m, d in all_machines.items() if d.get("status") == "success")

     valid_fy_swipes = max(tot_fy_likes, tot_fy_swipes - tot_fy_al)
     valid_fl_swipes = max(tot_fl_likes, tot_fl_swipes - tot_fl_al)
     valid_fr_swipes = max(tot_fr_likes, tot_fr_swipes - tot_fr_al)

     fy_rate_str = f"{(tot_fy_likes / valid_fy_swipes * 100.0):.1f}%" if valid_fy_swipes > 0 else "0.0%"
     fr_rate_str = f"{(tot_fr_likes / valid_fr_swipes * 100.0):.1f}%" if valid_fr_swipes > 0 else "0.0%"
     fl_rate_str = f"{(tot_fl_likes / valid_fr_swipes * 100.0):.1f}%" if valid_fl_swipes > 0 else "0.0%"
     ```

## 5. Kỷ Luật Phản Hồi Điều Phối (Coordinator Behavioral Invariant)
Khi nhận tin nhắn chỉ đạo hoặc chất vấn từ người vận hành (ví dụ: đang hỏi về tỉ lệ tim bạn bè), Coordinator **BẮT BUỘC trả lời trực diện câu hỏi của người dùng trước**, tuyệt đối KHÔNG tự ý chuyển hướng sang triage Farm Alert hay vấn đề khác làm mất ngữ cảnh chỉ đạo.

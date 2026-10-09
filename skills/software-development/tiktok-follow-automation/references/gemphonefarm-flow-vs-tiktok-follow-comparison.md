# Đối soát GemPhoneFarm Flow gốc vs tiktok-follow Runner: Lỗi Nhả Liền (0 lượt) & Thao tác Cuộn/Xem Video

Nguồn phân tích:
- File script gốc: `D:\Taadaa\tiktok-follow\data\TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_decrypted.json` (389 nodes)
- File thực thi hiện tại: `follow_runner/flows/mode2_follow_followers.py`, `follow_runner/flows/verify_follow.py`
- Dữ liệu thực nghiệm thực tế Farm ngày 12/09/2026: Row 2 (69 state files, 27 máy dính nhả liền Turn 0 sau 5 ngày cooldown).

---

## 1. Bản chất hiện tượng "Nhả liền (0 lượt) - Anchor bị nhả sau vuốt"

Trong `mode2_follow_followers.py` (`_ensure_anchor_followed`), khi máy truy cập Profile của Anchor:
1. Nếu nick chưa follow Anchor, bot tap nút Follow Anchor.
2. Bot gọi `pull_to_refresh_profile` (vuốt kéo xuống từ y=0.35h đến y=0.80h) và chờ `3.5s`.
3. Bot dump lại UI XML và kiểm tra trạng thái nút (`_classify_profile_action`).
4. Nếu trạng thái là `not_followed` (nút vẫn màu đỏ hoặc quay lại "Follow"):
   ```python
   engine.state.set_follow_failed()
   reason_holder.append(f"FOLLOW_FAILED: anchor @{uid} bị nhả sau vuốt — dừng session")
   return None
   ```
5. **Hậu quả:** Toàn bộ 27 máy bị dừng ngay tại Turn 0 với 0 lượt follow hoàn thành. Nick bị tăng `fail_streak` từ 2 lên 3 và bị ép cooldown 7 ngày tiếp theo.

---

## 2. Bằng chứng thực nghiệm: Tăng Cooldown KHÔNG giải quyết được Nhả Liền

- Toàn bộ 27 máy ở Row 2 đã bị nhả từ ngày **07/09/2026** và được hưởng trọn vẹn **5 ngày nghỉ ngơi liên tục** (từ 07/09 đến 12/09).
- Sáng ngày 12/09 lúc 06:00, khi cooldown vừa hết hạn:
  - Máy 6 và Máy 64: Nick đã follow Anchor từ trước $\rightarrow$ bỏ qua bấm follow Anchor $\rightarrow$ vào thẳng tab Following và follow thành công **17/17 nick**.
  - 27 máy còn lại (M5, M7, M9, M12, M16, M20, M22, M28...): Chưa follow Anchor $\rightarrow$ bấm follow Anchor $\rightarrow$ bị TikTok drop âm thầm $\rightarrow$ vuốt reload thấy nút đỏ $\rightarrow$ **dừng session ngay lập tức với 0 lượt**.
- **Kết luận:** Tăng cooldown không làm sạch cờ shadow-drop follow của TikTok nếu thao tác tương tác vẫn giữ nguyên pattern của bot (cold-follow không xem video).

---

## 3. So sánh đối soát với Script gốc GemPhoneFarm

| Tiêu chí | Script gốc GemPhoneFarm (`TIKTOK-FLOW-TÌM-KIẾM`) | Script hiện tại (`tiktok-follow`) |
|---|---|---|
| **Kiểm tra nhả (Verify Reload)** | **HOÀN TOÀN KHÔNG CÓ!** (Node 116/124/131/370/382 chỉ tap Follow rồi tiếp tục loop, không hề kéo reload lại để bắt lỗi). | Kéo `pull_to_refresh_profile`, nếu TikTok chưa kịp đồng bộ hoặc drop tạm thời $\rightarrow$ phán `FOLLOW_FAILED` và dừng phiên. |
| **Thao tác cuộn trang (Swipe Scroll)** | **CÓ CUỘN NHIỀU LẦN:** Các node 138, 139, 140, 263, 274, 275 cuộn từ toạ độ y=1859 lên y=598 (custom duration 750ms). | **KHÔNG CUỘN:** Search ra profile hoặc mở profile là đè đầu bấm Follow ngay trong 1-2 giây. |
| **Xem video profile** | **CÓ XEM VIDEO:** Các node 259–272 chọn video ngẫu nhiên (`Random4` từ 1 đến 6), tap mở video, lặp xem video 3 lần (`repeatFor: 3`), sau đó mới thực hiện action. | **KHÔNG XEM VIDEO:** Bấm nút ngoài header profile hoặc list mà không hề mở bất kỳ video nào của chủ tài khoản. |
| **Độ trễ hành vi (Delays)** | Dùng khoảng delay ngẫu nhiên: `time: 1814,5654` ms (1.8s - 5.6s), `432,1574` ms giữa các action. | Delay cố định rất ngắn (1.0s - 1.5s). |
| **Xử lý khi follow không được** | Vẫn tiếp tục chạy lặp cho tài khoản tiếp theo trong danh sách. | Dừng toàn bộ phiên (`set_follow_failed`), khóa nick vào cooldown 48h - 7 ngày. |

---

## 4. Giải pháp kỹ thuật chuẩn hóa (Pattern nâng cấp)

1. **Mô phỏng hành vi tự nhiên trước khi Follow Profile (như GemPhoneFarm):**
   - Khi mở một Profile mới (dù là Anchor hay Target từ Search):
     - Thực hiện 1-2 lần cuộn nhẹ (`swipe(cx, 1400, cx, 800)`) để duyệt qua lưới video của họ.
     - Dừng 2-4 giây ngẫu nhiên như người dùng đang đọc bio và xem thumbnail video.
     - (Tùy chọn) Bấm vào 1 video xem 3-5 giây rồi back ra profile trước khi bấm Follow.
2. **Loại bỏ Hard-Stop khi Follow Anchor thất bại:**
   - Anchor chỉ là "cầu nối" để vào xem danh sách Following. Nếu bấm follow Anchor mà bị nhả sau vuốt, KHÔNG DỪNG PHIÊN NGAY.
   - Vẫn cho phép thử mở tab Following của Anchor. Tab Following của người dùng là công khai, bất kể máy có follow Anchor hay chưa thì vẫn vào xem và follow các nick bên trong bình thường.
   - Chỉ dừng phiên (`set_follow_failed`) khi follow các nick mục tiêu thực sự bên trong mà bị nhả liên tiếp.

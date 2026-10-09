# TikTok Behavioral Simulation & Anti-Bot Standards (Production Grade 9.0/10)

Quy chuẩn kỹ thuật mô phỏng hành vi người thật được thẩm định và phê chuẩn bởi GPT-5.6 Sol High Reasoning (Áp dụng đồng bộ trên `tiktok-luot nuoi acc`, `tiktok-follow`, `Tiktok-video`).

---

## 1. Tầng Cảm ứng & Quỹ đạo Vuốt (Touch Gesture & Thumb Drift)
- **Hành lang an toàn giữa màn hình (Safe Center Corridor):**
  - Màn hình chuẩn 1080x1920: Tâm an toàn $X \in [450, 540]$ (cách mép Camera/Story $0 \sim 150\text{px}$ và mép Profile $930 \sim 1080\text{px}$ hơn $300\text{px}$).
  - Điểm chạm bắt đầu: `start_x = max(465, min(525, 495 + random.randint(-jitter, jitter)))`.
  - Độ trôi ngón tay tự nhiên (Natural Thumb Drift): `drift_x = random.randint(-18, 12)` px theo góc vung cung tròn ngón cái tay phải.
  - Điểm kết thúc: `end_x = max(450, min(540, start_x + drift_x))`.
- **Cơ chế Chốt chặn Ép thẳng (Skew Fallback Invariant):**
  - Nếu bất kỳ tham số nào truyền ngoài có $|\Delta X| > 30\text{px}$, hệ thống BẮT BUỘC ép thẳng đứng `end_x = start_x` để triệt tiêu nguy cơ trượt lệch sang camera.
- **Cơ chế Cô lập Vuốt ngược (Downward Rewind Invariant):**
  - Cử chỉ vuốt ngược (từ trên xuống dưới) BẮT BUỘC phải đi kèm cờ `allow_downward=True`.
  - Mọi caller thông thường không có cờ này khi gặp `start_y <= end_y` phải bị ép buộc quay về cử chỉ vuốt lên mặc định (`BASE_SWIPE_START` -> `BASE_SWIPE_END`).

---

## 2. Tầng Tương quan Hành vi & Độ hỗn loạn (Behavioral Entropy)
- **Nhịp Vuốt Ngược Xem Lại (Rewind Swipe - Tạo Session Narrative):**
  - Điều kiện: Chỉ kích hoạt trong feed session, từ video thứ 3 trở đi (`swipe_count >= 3`) và không phải video cuối ca (`not is_last_video`).
  - Tỷ lệ: `random.randint(5, 8)%` (trung bình 0 đến 1 lần mỗi phiên 16–22 video).
  - Thao tác: Vuốt ngược `[sx, 480]` -> `[ex, 1380]`, ngâm dừng `random.uniform(2.0, 4.0)` giây xem lại video trước khi tiếp tục lướt xuôi.
- **Tương tác Lưu Video Độc lập (Independent Bookmark):**
  - Mục đích: Phá vỡ chữ ký tương quan cứng $Like \rightarrow Save$ (người thật thường lưu bài hữu ích mà không thả tim).
  - Điều kiện: Áp dụng khi video không được like, like bị skip hoặc like button not found.
  - Tỷ lệ: `random.randint(3, 5)%`.
  - Kiểm tra vùng bấm: BẮT BUỘC kiểm tra tọa độ nút Lưu trên thanh công cụ phải (`x >= 750`).
  - Fail-Closed: Kiểm tra `res.ok is True` từ ADB. Nếu thất bại trả về `False`, cấm báo thành công giả.
- **Tương tác Lưu Video Sau Like (Dependent Bookmark):**
  - Tỷ lệ: `random.randint(15, 30)%` sau khi thả tim thành công, giãn cách `0.8s – 1.8s` trước khi bấm Lưu.
- **Xem Lướt Bình Luận (Comment Peek):**
  - Tỷ lệ: `12%` độc quyền trên các video Deep Inspect.
  - Thao tác: Bấm icon bình luận (`x >= 750`), ngâm đọc `2.0s – 4.0s`, 50% xác suất cuộn nhẹ 1 nhịp (`540 1400 -> 540 1100 300ms`), bấm phím Back (`input keyevent 4`).
  - Closed-loop Verification: Kiểm tra gói focus sau khi bấm Back vẫn là TikTok (`musically`, `trill`, `aweme`). Nếu mất focus hoặc lỗi, ghi log `result="failed_dismissal"` và trả về `False`.
- **Cơ chế Bù trừ Tỷ lệ Like For You (Fast Swipe vs Deep Inspect):**
  - Fast Swipe: Quẹt nhanh 2–4s, KHÔNG dump XML, tỷ lệ Like = 0%.
  - Deep Inspect: Mỗi 6–10 video dừng 1 lần dump XML, nạp tỷ lệ Like cục bộ = 20% (`deep_like_rate_percent = 20`).
  - Kết quả toàn phiên: Tỷ lệ Like bình quân trên tab For You tự nhiên đạt mức cân bằng chuẩn **6% – 8%**.

---

## 3. Tầng Nhịp độ & Phân bổ (Pacing & Scheduling)
- **Nhịp độ Follow (`tiktok-follow`):**
  - Profile Dwell Time: Ngâm Profile mục tiêu `6.0s – 12.0s` trước khi tap Follow.
  - Post-tap Delay: Chờ server phản hồi `2.5s – 5.0s`.
  - Inter-follow Delay: Giãn cách `8.0s – 25.0s` giữa 2 lượt follow.
- **Nhịp độ Upload (`Tiktok-video`):**
  - Dwell Time trước khi Đăng: Ngâm dừng `1.8s – 3.5s` sau khi điền xong caption/hashtag trước khi bấm nút "Đăng" / "Post".
  - Giới hạn Upload: Chỉ kích hoạt hook upload ở Phiên 2 (phiên kết thúc ca) để bảo toàn kho video.
- **Điều phối Khởi động Cụm (Anti-Clustering Scheduler):**
  - Trễ so le khởi động máy (`MachineStartStaggerMs: "2000,8000"`): Mỗi máy khởi động cách nhau 2s đến 8s.
  - Giới hạn đồng thời (`MaxWorkers: 40`): Không bao giờ chạy quá 40 máy cùng lúc trên cụm 160 máy.
  - Xáo trộn thứ tự máy (`--randomize-machine-order`): Không cố định thứ tự các máy.
  - Vùng chết (Dead Zone): 02:30 -> 05:59 sáng ngắt toàn bộ hoạt động, tắt màn hình hạ nhiệt CPU.

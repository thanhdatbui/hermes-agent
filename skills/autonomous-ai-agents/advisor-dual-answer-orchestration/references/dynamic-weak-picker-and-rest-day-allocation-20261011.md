# Dynamic Weak-Account Picker, 4-Day Cycle Architecture & Diurnal Permutation (2026-10-11)

## 1. Bối Cảnh & Vấn Đề Cốt Tử Của Mô Hình "Batch Theo Row" Cũ

### Hiện trạng
Farm vận hành 160 máy Android (80 máy Kibe, 80 máy Admin), mỗi máy chứa 8 slot tài khoản TikTok (`Row 1` đến `Row 8`).
Trước đây, lịch chạy chia theo các ca cố định truyền tham số `-Row <N>`:
* Ví dụ: `run-feed-session.ps1 -Row 3` $\rightarrow$ Tất cả 80 máy đồng loạt mở Slot 3 lên chạy.

### Nghịch lý cào bằng (Resource Misallocation) & Rủi ro Synchronous Burst
* **Máy 1:** Slot 3 đã rất khỏe (đã đăng 25 video, 500 follow, tương tác tốt) $\rightarrow$ vẫn bị lôi ra chạy tốn pin, mòn proxy.
* **Máy 12:** Slot 6 đang ngắc ngoải (mới 3 video, view đứng hình, bị nhả follow) $\rightarrow$ lại bị bỏ xó vì chưa đến phiên Row 6.
* **Global Batch Signature:** Việc 80 máy cùng mở app, cùng chọn slot 3, cùng thực hiện một luồng hành vi trong cùng khung giờ tạo ra đỉnh tải mạng (network burst) và footprint máy móc dễ bị Risk Engine của TikTok phát hiện.

---

## 2. Bản Thiết Kế Điều Phối Chu Kỳ 4 Ngày (v3.0)

### Bảng Lịch Vĩ Mô Modulo 4

| Ngày | Ca 1 (Sáng: 06h & 08h) | Ca 2 (Trưa: 12h & 14h) | Ca 3 (Tối: 18h & 20h) | Chế độ & Đặc điểm |
| :---: | :---: | :---: | :---: | :--- |
| **NGÀY 1** *(Khởi động)* | **Row 1** hoặc **Row 2** *(Mỗi máy chọn 1 hoặc 2)* | **Row 3** hoặc **Row 4** *(Mỗi máy chọn 3 hoặc 4)* | **Row 5** hoặc **Row 6** *(Mỗi máy chọn 5 hoặc 6)* | **CÀY THỰC TẾ (Follow + Up)**<br>• Ưu tiên 100% nick nòng cốt khỏe chạy trước sau ngày nghỉ để bảo vệ dải IP sạch. Tuyệt đối không đưa Row 7 vào Ngày 1. |
| **NGÀY 2** *(Bù trừ)* | **Row còn lại** *(1 hoặc 2)* | **Row còn lại** *(3 hoặc 4)* | **Row còn lại** *(5 hoặc 6)* | **CÀY THỰC TẾ (Follow + Up)**<br>• Hoàn thành trọn vẹn 100% dàn nick từ Row 1 đến Row 6 theo kế hoạch bù trừ. |
| **NGÀY 3** *(Về đích & Xả tối)* | **Row 7** *(Cày)* | **Row 8** *(Cày)* | **ACC YẾU / ĂN NHẢ** *(Dưỡng sinh)* | • Sáng & Trưa: Cày dứt điểm Row 7, 8.<br>• **Ca tối:** Tắt follow, lướt feed dưỡng sinh cho acc yếu/ăn nhả. |
| **NGÀY 4** *(Nghỉ xả tải toàn Farm)* | **ACC YẾU / ĂN NHẢ** *(Dưỡng sinh)* | **ACC YẾU / ĂN NHẢ** *(Dưỡng sinh)* | **ACC YẾU / ĂN NHẢ** *(Dưỡng sinh)* | **NGÀY NGHỈ DƯỠNG SINH TOÀN FARM**<br>• **Follow:** TẮT 100% (`_follow_rate = 0`, `TAADAA_REST_DAY_NO_FOLLOW = 1`).<br>• **Lướt feed:** Hồi trust sau bão quét.<br>• **Upload:** Vẫn mở 1 video/ngày. |

*(Ngày 5: Bắt đầu chu kỳ mới với hạt giống hoán vị ngẫu nhiên mới).*

---

## 3. Kiến Trúc "Dynamic Weak-Account Picker" & Định Nghĩa Acc Yếu

Thay vì bắt cả farm chạy chung một Row trong ca dưỡng sinh, hệ thống truy vấn cơ sở dữ liệu `D:/Taadaa/data/tiktok_tracker.db` để tính toán **Vulnerability Score (Điểm Sức Khỏe / Rủi Ro)** cho từng slot của từng máy.

### Định nghĩa "Acc Yếu" Chuẩn Hóa
1. **Ưu tiên 1 (Cứu hộ khẩn cấp): Acc ăn nhả follow (`is_follow_cooldown == True`):**
   * **Bao gồm cả acc thuộc Row khỏe (Row 1, Row 2)** nếu vừa bị TikTok nhả follow trong các ca trước.
   * **Hành vi:** Đưa vào lướt feed xả tải để rửa trust score sau bão quét; **tuyệt đối cấm bấm follow**; vẫn cho upload video nếu chưa đăng trong ngày.
2. **Ưu tiên 2 (Tân binh thiếu video):**
   * Các acc có `video_count < 10` (ưu tiên nick ít video nhất trên máy đó).
   * **Hành vi:** Lướt feed warm nick + Upload video để đẩy nhanh tiến độ hoàn thành mốc 10 video.
3. **Ưu tiên 3 (Acc đứng hình):**
   * Các acc nhiều ngày liền có $\Delta \text{view} = 0$, $\Delta \text{heart} = 0$.
   * **Hành vi:** Lướt feed tự nhiên để kích thích phân phối lại.

### Công Thức Chấm Điểm Vulnerability Score (0 – 100)
$$\text{Score} = 100 \times (0.30 \times C + 0.40 \times P + 0.30 \times S)$$

* $C$ — Content Deficit: $C = \text{clamp}\left(\frac{10 - \text{video\_count}}{10}, 0, 1\right)$.
* $P$ — Penalty / Restriction: Cooldown active $= 1.0$; vừa hết cooldown 3 ngày $= 0.5$; sạch $= 0.0$.
* $S$ — Stagnation (7 ngày): $0.45 \times S_{\text{view}} + 0.30 \times S_{\text{heart}} + 0.25 \times S_{\text{follower}}$.

---

## 4. Ba Lưu Ý Kỹ Thuật Scheduler Cốt Tử Từ Advisor Sol / Terra

### 1. Lập "Cycle Plan Bất Biến" Lưu Bền Vững (`cycle_plan.json`)
* **Vấn đề:** Nếu để Ngày 1 máy tự chọn ngẫu nhiên độc lập trong RAM, lỡ máy khởi động lại hoặc crash, sang Ngày 2 hệ thống sẽ mất dấu Ngày 1 đã chạy Row nào, dẫn đến chạy trùng hoặc bỏ sót Row.
* **Giải pháp:** Đầu mỗi chu kỳ 4 ngày, scheduler sinh file `cycle_plan.json` cố định cho từng máy:
  ```json
  {
    "cycle_id": "20261011_mod4",
    "machine_1": {
      "day1": {"morning": 1, "noon": 4, "evening": 5},
      "day2": {"morning": 2, "noon": 3, "evening": 6}
    }
  }
  ```
  Ngày 2 chỉ việc đọc phần bù trừ đã định sẵn, bảo đảm tính tất định và không bao giờ xung đột.

### 2. Phân Bổ Hàng Đợi Chống Lặp Cho 4 Ca Dưỡng Sinh (Starvation Guard)
* Trong 4 ca dưỡng sinh (Ca tối N3 + 3 ca N4), mỗi máy có 8 slot.
* Áp dụng hàng đợi ưu tiên không lặp:
  * Ca tối N3: Bốc nick yếu nhất (Hạng 1).
  * Ca sáng N4: Bốc nick yếu tiếp theo (Hạng 2).
  * Ca trưa N4: Bốc nick yếu tiếp theo (Hạng 3).
  * Ca tối N4: Bốc nick yếu tiếp theo (Hạng 4).
* Ngăn chặn tình trạng 1 nick bị bốc lặp cả 4 ca trong khi các nick yếu khác bị bỏ đói.

### 3. Tách Bạch Follow Cooldown vs Upload Video & Khóa Idempotency
* **Tách bạch hoàn toàn:** Follow Cooldown và Rest Day chỉ tắt thao tác follow (`_follow_rate = 0`). **Mọi tài khoản đều được mở Upload Hook 1 video/ngày** để duy trì nhịp Creator tự nhiên.
* **Khóa Idempotency (`shift_upload_history.json`):** Kiểm tra atomic, Phiên 1 thành công thì Phiên 2 tự động skip; chỉ xác nhận sau khi UI hoàn tất.

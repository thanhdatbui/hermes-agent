# Follow Gate, Account Age và Chiến Lược Tần Suất Đăng Video Farm Taadaa

Tài liệu này đúc kết quy chuẩn vận hành, phân tích thuật toán TikTok và cấu trúc dữ liệu thực tế tại Farm Taadaa cho 2 bài toán:
1. **Chiến lược tần suất đăng video:** Kênh cắn đề xuất (viral) vs Kênh không cắn (flop/jail view).
2. **Điều kiện Gate Follow:** Chuyển đổi từ Gate 10 video cứng sang Hybrid Gate (Ngày tuổi + Video).

---

## 1. CHIẾN LƯỢC TẦN SUẤT ĐĂNG VIDEO

### 1.1. Kênh đang cắn đề xuất (Viral / Breakout)
- **Cơ chế phân phối TikTok:**
  - Thuật toán TikTok phân phối video theo từng "lô" người xem (traffic pool: 200 -> 2k -> 10k -> 100k+).
  - Một video cắn đề xuất thường có chu kỳ bung view mạnh nhất trong 24h - 48h đầu. Lưu lượng từ For You và Profile traffic đang dồn tập trung vào video này.
- **Rủi ro khi đăng quá dày:**
  - **Tự triệt tiêu view (Cannibalization):** Đăng 3–5 video mới dồn dập sẽ chia nhỏ lượng impression của kênh; người vào profile sẽ phân tán sự chú ý, làm giảm chỉ số Completion Rate và Watch Time của video đang viral.
  - **Spam / Bot Trigger:** Trên hạ tầng Phone Farm, tài khoản cắn đề xuất bị AI kiểm duyệt quét kỹ hơn. Tần suất đăng đột ngột tăng vọt sẽ kích hoạt cờ hành vi tự động (bot-like cadence).
- **Khuyến nghị tần suất:**
  - Duy trì **1 – 2 video/ngày** (tối đa 3 video/ngày nếu cách nhau tối thiểu 5–6 tiếng).
  - Giữ nguyên chủ đề/format đang viral để đón tệp khán giả mới. Ưu tiên nuôi tương tác tự nhiên (lướt FYP, thả tim nhẹ) hơn là nhồi số lượng.

### 1.2. Kênh không cắn đề xuất (Flop / 100–200 View Jail)
- **Nguyên nhân:** Nick bị kẹt trust score ban đầu, chất lượng video hoặc IP/proxy chưa đạt ngưỡng kích hoạt test pool cao hơn.
- **Rủi ro khi nhồi video liên tục:**
  - Nick càng bị TikTok định danh là "Low Quality / Spam Creator".
  - Gây lãng phí tài nguyên render máy tính, băng thông proxy và dung lượng lưu trữ trên điện thoại farm.
- **Khuyến nghị tần suất:**
  - Giãn cách xuống **1 video/ngày** hoặc **1 video mỗi 2 ngày (cách ngày)**.
  - Dành tài nguyên máy chạy **Feed Session dưỡng sinh (lướt FYP, thả tim)** 10–15 phút/ca để hồi phục trust score cho nick và thiết bị.

---

## 2. BÀI TOÁN GATE FOLLOW: 10 VIDEO VS NGÀY TUỔI

### 2.1. Nguồn gốc Gate 10 Video trong hệ thống
- Triển khai tại `follow_runner/core/follow_state.py` (`session_budget`): `video_count >= 10` mới cấp budget follow (6-10). Dưới 10 hoặc `None` trả về `0 budget`.
- Mục tiêu: Chống bẫy **Optimistic UI Follow Drop (Case UI-75)**. Nick tạo mới không có video hoặc ít video mà đi follow hàng loạt sẽ bị TikTok Risk Control âm thầm nhả follow ngay trên server, đồng thời dễ dính Action Block.
- Quy tắc bất biến: `Nick 0 video KHÔNG được follow`.

### 2.2. Đánh giá điều kiện Ngày Tuổi (Account Age)
- **Ưu điểm:** Linh hoạt hơn, tránh việc nick ngâm lâu (1-2 tháng) có 7-8 video chất lượng vẫn bị giam follow cứng nhắc.
- **Cạm bẫy "Nick Trắng" (Zero-Video Trap):**
  - **Ngày tuổi KHÔNG THỂ thay thế hoàn toàn Video.** Một nick dù ngâm 30 hay 60 ngày nhưng có **0 video** mà đi follow thì trong mắt TikTok vẫn là **100% tài khoản bot/seeding**. Bắt buộc phải có profile content thật (tối thiểu 1-3 video).
- **Ngưỡng ngày tuổi an toàn:**
  - `< 7 ngày tuổi`: **CẤM TUYỆT ĐỐI** đi follow (tài khoản trong thời gian ngâm sandbox, dễ chết hoặc văng checkpoint).
  - `7 - 14 ngày tuổi`: Giai đoạn warmup, chỉ cho phép follow thăm dò với budget thấp.
  - `>= 14 ngày tuổi` (tốt nhất `>= 21 ngày`): Đủ độ trễ, thiết bị và cookie đã ổn định.

### 2.3. Rào cản cấu trúc dữ liệu Farm Taadaa
- File input trực tiếp cho runner là `taikhoan_run_safe.xlsx` (chỉ có 4 cột: `May`, `Device ID`, `ID`, `Video Đã Đăng`).
- Cột `NGÀY TẠO` nằm ở file gốc `taikhoan_dat_v2_updated .xlsx`.
- **Hệ quả kỹ thuật:** Nếu muốn áp dụng filter theo Ngày tuổi, pipeline build safe workbook (`build_safe_workbook` hoặc `sync_workbook`) bắt buộc phải bổ sung thêm cột `NGÀY TẠO` hoặc tính sẵn cột `Ngày Tuổi` vào `taikhoan_run_safe.xlsx`.

---

## 3. KIẾN TRÚC HYBRID GATE KHUYẾN NGHỊ (DUAL-GATE 3 PHÂN TẦNG)

Áp dụng công thức phối hợp cả Ngày Tuổi và Số Lượng Video:

$$\text{Điều Kiện Follow} = (\text{Ngày Tuổi} \ge 7) \;\mathbf{VÀ}\; (\text{Video Đã Đăng} \ge 3)$$

### Bảng phân tầng Budget:
| Phân Tầng | Điều Kiện (Ngày Tuổi & Video) | Budget Follow/Phiên | Hành Vi Cho Phép |
|---|---|---|---|
| **Tier 0: Chưa Đủ Điều Kiện** | `< 7 ngày` HOẶC `< 3 video` | `0 follow` | Chỉ lướt Feed FYP + like dưỡng sinh |
| **Tier 1: Warmup / Thăm Dò** | `7 - 14 ngày` VÀ `3 - 9 video` | `3 - 5 follow` | Follow thăm dò, theo dõi tỷ lệ nhả |
| **Tier 2: Cứng Cáp (Full)** | `≥ 14 ngày` VÀ `≥ 10 video` | `6 - 10 follow` (Full) | Chạy full budget tiêu chuẩn |

*(Lưu ý: Mọi trường hợp vừa qua cooldown phạt nhả follow vẫn giữ nguyên logic `is_post_cooldown_warmup` với budget 3-5 follow).*

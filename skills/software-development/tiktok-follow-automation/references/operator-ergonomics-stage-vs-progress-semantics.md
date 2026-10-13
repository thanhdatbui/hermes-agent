# Operator Ergonomics: Phân Biệt "Cấp Độ Hồi Phục" (Stage) vs "Mục Tiêu Tiến Độ" (Progress Requirement)

## 1. Sự Cố Nhận Thức & Lú Lẫn Thuật Ngữ Của Operator

### Vấn đề:
Khi Dashboard hiển thị huy hiệu `🛡️ Thận trọng (2 ca)` song song với `🟠 Hồi phục 1 (0/2 ngày)`, Operator gặp phải tình trạng quá tải nhận thức (cognitive overload) và thắc mắc:
- *"Không phân biệt được Thận trọng và Hồi phục khác nhau thế nào?"*
- *"Ghi Thận trọng (2 ca) là sao, chữ 2 ca nghĩa là gì?"*
- *"Rồi không lẽ có Thận trọng 1 ca nữa?"*

### Nguyên nhân gốc rễ (Root Cause - Naming Collision & Progress Masking):
1. **Trộn lẫn 2 khái niệm khác nhau vào cùng một cấp độ:**
   - **Stage (Nấc thang cấp bậc):** Trả lời câu hỏi *"Nick đang được phép chạy tải bao nhiêu?"* (Hồi phục 1: 1-2 fl, Hồi phục 2: 5-8 fl, Khỏe: 10-15 fl).
   - **Recovery Path & Progress (Lộ trình & Mục tiêu):** Trả lời câu hỏi *"Còn bao nhiêu ca sạch nữa thì được thăng hạng?"*
2. **Biến bộ đếm tiến độ (Countdown Indicator) thành nhãn phân loại (Classification Badge):**
   - Công thức `sessions_needed = max(1, target - clean_days)` thực chất là **số ca còn lại cần chạy**.
   - Việc nhét số này vào tên huy hiệu (`Thận trọng (3 ca)` -> `Thận trọng (2 ca)` -> `Thận trọng (1 ca)`) khiến Operator tưởng nhầm hệ thống sinh ra một mớ cấp bậc con phân mảnh kỳ quặc.

---

## 2. Quy Chuẩn Đặt Tên & Thiết Kế UI Chuẩn Hóa (Advisor Sol Architecture)

Bắt buộc tách bạch rõ ràng **3 tầng thông tin** trên giao diện:
1. **Cấp bậc hiện tại (Level / Stage):** Đang ở đâu trên thang tải.
2. **Lộ trình xử lý (Path):** Đi đường thường (Standard) hay đường ưu tiên (Priority).
3. **Mục tiêu hoàn thành (Progress Requirement):** Còn bao nhiêu ca sạch để lên cấp.

| Thành phần | Trước khi chuẩn hóa (Lỗi) | Sau khi chuẩn hóa (Chuẩn) | Ý nghĩa hiển thị |
| :--- | :--- | :--- | :--- |
| **Stage 1** | `🟠 Hồi phục 1 (0/2 ngày)` | `🟠 Hồi phục 1 (0/2 ca)` | Quota 1 – 2 fl/ca, cần 2 ca sạch để lên nấc 2. |
| **Stage 2** | `🟡 Hồi phục 2 (2/4 ngày)` | `🟡 Hồi phục 2 (0/2 ca)` | Quota 5 – 8 fl/ca, cần thêm 2 ca sạch để tốt nghiệp. |
| **Lộ trình thường** | `🛡️ Thận trọng (2 ca)` ❌ | `🎯 Cần 2 ca sạch` (hoặc `1 ca sạch`) | **Xóa bỏ chữ "Thận trọng"!** Hiển thị rõ số ca sạch cần đạt. |
| **Lộ trình ưu tiên** | `⚡ Fast-track (1 ca)` | `⚡ Ưu tiên (1 ca)` | Dành cho cựu binh điểm uy tín cao: 1 ca sạch là tốt nghiệp. |

---

## 3. Quy Tắc Vận Hành "Mỗi Stage Đúng 2 Ca Hoàn Thành"

- **USER INVARIANT:** Mỗi stage chỉ yêu cầu **đúng 2 ca chạy sạch** (`2 clean sessions`) là được xét thăng cấp:
  * **Hồi phục 1:** Cần 2 ca sạch (`clean_days < 2`) -> Thăng cấp lên Hồi phục 2.
  * **Hồi phục 2:** Cần thêm 2 ca sạch (`2 <= clean_days < 4`) -> Tốt nghiệp về Khỏe.
- **Tiến độ hiển thị:**
  * Ở Hồi phục 1: Hiển thị `(0/2 ca)` hoặc `(1/2 ca)`.
  * Ở Hồi phục 2: Hiển thị `(0/2 ca)` (tương ứng `clean_days=2`) hoặc `(1/2 ca)` (tương ứng `clean_days=3`).
  * Mục tiêu: `🎯 Cần 2 ca sạch` khi mới vào stage, `🎯 Cần 1 ca sạch` khi đã hoàn thành ca 1.
- Tuyệt đối cấm hiển thị `2/4 ngày` gây hiểu nhầm stage 2 cần 4 ca.

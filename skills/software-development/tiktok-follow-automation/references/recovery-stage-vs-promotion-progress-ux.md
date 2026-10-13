# Chuẩn Hóa Phân Tầng Follow: Stage (Nấc Thang) vs Tiến Độ Thăng Cấp (Progress Countdown)

## 1. Nguồn Gốc Lẫn Lộn & Bẫy Naming Collision
Trước đây hệ thống Dashboard Follow hiển thị đồng thời:
`🟠 Hồi phục 1 (0/2 ngày)` đi kèm huy hiệu `🛡️ Thận trọng (2 ca)` (hoặc `3 ca`, `1 ca`).

**Hậu quả trên nhận thức Operator:**
- Operator bị lú lẫn: tưởng "Thận trọng (X ca)" là một hệ thống cấp bậc con (`Thận trọng 3 ca`, `Thận trọng 2 ca`, `Thận trọng 1 ca`).
- Nhầm lẫn giữa "Đang ở nấc nào" (Stage) với "Còn bao nhiêu ca nữa thì lên cấp" (Countdown requirement).
- Đây là lỗi UX kinh điển: Biến **bộ đếm tiến độ (Progress Indicator)** thành **nhãn phân loại (Classification Label)**.

---

## 2. Chuẩn Hóa 3 Lớp Thông Tin (Advisor Sol Architecture)

Hệ thống phân tầng follow chỉ cần đúng 3 lớp thông tin tinh gọn, Operator nhìn 3 giây là hiểu ngay:

1. **Cấp Bậc / Sức Khỏe (Health Level / Stage):**
   - **Hồi phục 1 (Probation Tier 1):** 1 – 2 follow/ca.
   - **Hồi phục 2 (Probation Tier 2):** 5 – 8 follow/ca.
   - **Khỏe / Nòng Cốt (Healthy):** 10 – 15 follow/ca.
   - *Quy tắc tiến độ:* Mỗi stage chỉ đúng **2 ca sạch** là được thăng cấp (`0/2 ca` ➔ `1/2 ca`). CẤM dùng đơn vị "ngày" gây nhầm lẫn với lịch chạy cách nhật.

2. **Lộ Trình Hồi Phục (Recovery Path):**
   - **Tiêu chuẩn (Standard):** Nick tân binh mới lên giàn hoặc nick có án tích ➔ Bắt buộc đi đủ 2 ca sạch mỗi nấc.
   - **Ưu tiên (Priority / Fast-track ⚡):** Nick cựu binh điểm uy tín cao (Score $\ge 60$) ➔ Chỉ cần **1 ca sạch** là được đặc cách tốt nghiệp về Khỏe.

3. **Yêu Cầu / Tiến Độ Còn Lại (Promotion Requirement):**
   - Xóa bỏ hoàn toàn chữ "Thận trọng (X ca)".
   - Hiển thị mục tiêu hành động rõ ràng:
     * Nhóm tiêu chuẩn: `🎯 Cần 2 ca sạch` (hoặc `🎯 Cần 1 ca sạch`).
     * Nhóm cựu binh: `⚡ Ưu tiên (1 ca)`.

---

## 3. Mẫu Hiển Thị Trực Quan Trên Dashboard Card

```text
[M52 (Row 5)]
- Cấp bậc & tiến độ: 🟠 Hồi phục 1 (0/2 ca)
- Mục tiêu thăng cấp: 🎯 Cần 2 ca sạch

[M50 (Row 1) - Cựu binh]
- Cấp bậc & tiến độ: 🟠 Hồi phục 1 (0/1 ca)
- Mục tiêu thăng cấp: ⚡ Ưu tiên (1 ca)
```
Operator nhìn vào biết ngay: Nick đang ở tải bao nhiêu (1-2 fl), và còn đúng bao nhiêu ca chạy sạch nữa thì được nâng trần quota.

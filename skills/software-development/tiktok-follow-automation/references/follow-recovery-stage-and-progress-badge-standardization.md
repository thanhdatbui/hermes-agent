# Chuẩn Hóa Phân Tầng Hồi Phục & Badge Tiến Độ Ca Sạch (Follow Recovery Stage & Progress Badge)

## 1. Bản Chất Kỹ Thuật & Bài Học Từ Người Dùng (Operator Insight)

### Sự Cố Nhầm Lẫn Thuật Ngữ (Cognitive Overload & Naming Collision):
* Trước đây, trên Dashboard và file state tồn tại hai khái niệm song song:
  - **Stage (Nấc thang):** `Hồi phục 1 (0/2 ngày)`, `Hồi phục 2 (2/4 ngày)`, `Khỏe`.
  - **Recovery Mode (Huy hiệu):** `Fast-track (1 ca)` vs `Thận trọng (3 ca)` / `Thận trọng (2 ca)`.
* **Hậu quả:** Operator bị rối rắm và hiểu lầm nghiêm trọng:
  - *"T vẫn chưa phân biệt được thận trọng và hồi phục."*
  - *"Thận trọng (2 ca) là sao, chữ 2 ca nghĩa là gì? Rồi không lẽ có Thận trọng 1 ca nữa?"*
* **Nguyên nhân gốc rễ (Advisor Sol chẩn đoán):** Giao diện đã mắc lỗi UX kinh điển: **Biến bộ đếm tiến độ (Countdown / Progress indicator) thành nhãn phân cấp (Classification label)**. Khi số ca cần chạy giảm từ 2 xuống 1, việc đổi nhãn từ `Thận trọng (2 ca)` thành `Thận trọng (1 ca)` khiến người dùng nghĩ rằng hệ thống sinh ra một mớ cấp bậc con kỳ quặc.

---

## 2. Quy Chuẩn 3 Lớp Rõ Ràng (Three-Layer Architecture)

Hệ thống phân tách rạch ròi 3 tầng thông tin độc lập:

1. **Cấp bậc hiện tại (Level / Stage):** Trả lời câu hỏi *"Nick đang chịu tải bao nhiêu?"*
   - `🟠 Hồi phục 1 (0/2 ca)`: Quota 1 – 2 follow/ca.
   - `🟡 Hồi phục 2 (0/2 ca)`: Quota 5 – 8 follow/ca.
   - `🟢 Khỏe`: Quota chuẩn 10 – 15 follow/ca.
   - *Lưu ý:* Thống nhất dùng đơn vị **"ca"** (clean sessions) thay vì "ngày", vì farm chạy luân phiên cách nhật, đếm theo số ca chạy sạch thực tế phản ánh đúng hành vi thuật ngữ TikTok quan sát.

2. **Lộ trình hồi phục (Recovery Path):** Trả lời câu hỏi *"Đi đường thường hay đường tắt?"*
   - **Lộ trình tiêu chuẩn (Standard):** Dành cho nick mới, ít video, hoặc có tiền án (`score < 60`).
   - **Lộ trình ưu tiên (Priority / Fast-track ⚡):** Dành cho nick cựu binh điểm uy tín cao (`score >= 60`, tuổi >60d, clip >15, max_safe cao, chỉ lỡ dính streak nhẹ). Chỉ cần 1 ca sạch là tốt nghiệp ngay.

3. **Mục tiêu tiến độ (Progress / Requirement):** Trả lời câu hỏi *"Còn bao nhiêu ca nữa lên cấp?"*
   - **XÓA BỎ HOÀN TOÀN chữ `🛡️ Thận trọng (X ca)`**.
   - Thay thế bằng nhãn mục tiêu tiến độ:
     * `🎯 Cần 2 ca sạch` (hoặc `🎯 Cần 1 ca sạch` khi đã chạy được 1 ca).
     * `⚡ Ưu tiên (1 ca)` (đối với nick cựu binh).

---

## 3. Quy Tắc 2 Ca / Stage (User Invariant)

* **Hồi phục 1 (Probation Tier 1):** Cần đúng **2 ca sạch** (`clean_days < 2`).
  - Ban đầu (`clean_days = 0`): Label `🟠 Hồi phục 1 (0/2 ca)`, Badge `🎯 Cần 2 ca sạch`.
  - Chạy xong 1 ca (`clean_days = 1`): Label `🟠 Hồi phục 1 (1/2 ca)`, Badge `🎯 Cần 1 ca sạch`.
* **Hồi phục 2 (Probation Tier 2):** Cần thêm đúng **2 ca sạch** (`2 <= clean_days < 4`).
  - Vừa lên nấc 2 (`clean_days = 2`): Label `🟡 Hồi phục 2 (0/2 ca)`, Badge `🎯 Cần 2 ca sạch`.
  - Chạy thêm 1 ca (`clean_days = 3`): Label `🟡 Hồi phục 2 (1/2 ca)`, Badge `🎯 Cần 1 ca sạch`.
* **Tốt nghiệp (`clean_days >= 4`):** Thăng hạng lên `🟢 Khỏe` (`graduated = True`).

---

## 4. Công Thức Tính Toán Trong Code Backend (`follow_health_helper.py`)

```python
# Tính sessions_needed cho từng nấc hồi phục:
if tier == "healthy":
    rec_mode = "GRADUATED"
    sessions_needed = 0
elif rec_score >= 60:
    rec_mode = "FAST_TRACK"
    sessions_needed = 1
else:
    rec_mode = "CAUTIOUS"
    if tier == "probation_tier2":
        sessions_needed = max(1, 4 - clean_days)  # Còn 2 ca hoặc 1 ca
    else:
        sessions_needed = max(1, 2 - clean_days)  # Còn 2 ca hoặc 1 ca
```

## 5. Render Giao Diện Dashboard (`tiktok_dashboard.py`)

```javascript
let recBadge = '';
if (a.tier !== 'healthy') {
    if (a.recovery_mode === 'FAST_TRACK') {
        recBadge = `<span style="background:rgba(56,189,248,0.18);border:1px solid #38bdf8;color:#38bdf8;font-size:10px;font-weight:700;padding:2px 6px;border-radius:10px;margin-left:6px;" title="Lộ trình ưu tiên (Cựu binh score ${a.recovery_score || 0}/100): Chỉ cần 1 ca sạch để tốt nghiệp">⚡ Ưu tiên (1 ca)</span>`;
    } else if (a.recovery_mode === 'CAUTIOUS') {
        recBadge = `<span style="background:rgba(148,163,184,0.15);border:1px solid rgba(148,163,184,0.35);color:#cbd5e1;font-size:10px;font-weight:600;padding:2px 6px;border-radius:10px;margin-left:6px;" title="Lộ trình tiêu chuẩn: Cần thêm ${a.sessions_needed || 2} ca sạch để thăng cấp">🎯 Cần ${a.sessions_needed || 2} ca sạch</span>`;
    }
}
```

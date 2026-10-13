# Chuẩn Hóa Kiến Trúc Phân Tầng Follow: Tách Biệt Nấc Thang (Stage) vs Tiến Độ Thăng Cấp (Progress Countdown)

## 1. Lỗi Thiết Kế UX Kinh Điển: Naming Collision Giữa Stage vs Progress
Trong các phiên vận hành trước 13/10/2026, Dashboard hiển thị đồng thời:
`🟠 Hồi phục 1 (0/2 ngày)` đi kèm huy hiệu `🛡️ Thận trọng (2 ca)` (và khi chạy được 1 ca thì tụt xuống `🛡️ Thận trọng (1 ca)`).

Hậu quả tâm lý đối với Operator:
- Gây lú lẫn nghiêm trọng: Operator tưởng "Thận trọng" là một cấp bậc mới song song với "Hồi phục" (ví dụ: tưởng có cấp Hồi phục 1, Hồi phục 2, rồi lại có cấp Thận trọng 1 ca, Thận trọng 2 ca).
- Mắc lỗi phản trực giác: **Biến bộ đếm ngược (Countdown / Progress indicator) thành nhãn phân cấp (Classification label)**.

---

## 2. Quy Chuẩn 3 Lớp Thông Tin Minh Bạch (Advisor Sol Blueprint - 13/10/2026)
Hệ thống hiển thị thẻ tài khoản follow trên Dashboard chỉ cần đúng 3 lớp thông tin, Operator nhìn 3 giây là hiểu ngay:

1. **Lớp 1: Cấp bậc / Nấc thang (Stage - Nick đang ở đâu?)**
   - **Hồi phục 1:** Quota 1 – 2 follow/ca (nick mới ra tù, tân binh mới nuôi).
   - **Hồi phục 2:** Quota 5 – 8 follow/ca (nick tăng tải an toàn).
   - **Khỏe:** Quota 10 – 15 follow/ca (nick nòng cốt tốt nghiệp).
   - **Đơn vị đếm:** Bắt buộc dùng **"ca"** thay vì "ngày" (vì farm chạy cách nhật, 2 ca chạy thực tế mất 3-4 ngày ngoài đời):
     * Hồi phục 1: `(0/2 ca)` hoặc `(1/2 ca)`.
     * Hồi phục 2: `(0/2 ca)` hoặc `(1/2 ca)` (đếm theo mốc 2 ca của riêng stage 2, CẤM ghi `2/4 ngày` gây hiểu nhầm).

2. **Lớp 2: Lộ trình thử thách (Recovery Path - Đi đường thường hay đường ưu tiên?)**
   - **Đường ưu tiên (Priority Path):** Dành cho nick cựu binh có điểm uy tín cao (`recovery_score >= 60`, tuổi đời lâu, video nhiều, chỉ lỡ dính streak nhẹ).
     * Huy hiệu: **`⚡ Ưu tiên (1 ca)`** (chỉ cần 1 ca sạch là tốt nghiệp thẳng về Khỏe).
   - **Đường tiêu chuẩn (Standard Path):** Dành cho nick mầm non, tân binh, nick điểm uy tín thấp (`recovery_score < 60`).
     * Phải đi tuần tự qua từng nấc: 2 ca sạch ở Hồi phục 1 ➔ 2 ca sạch ở Hồi phục 2 ➔ Khỏe.

3. **Lớp 3: Mục tiêu thăng cấp (Requirement / Progress)**
   - **CẤM TUYỆT ĐỐI dùng chữ "Thận trọng (X ca)" hay "Thận trọng 1 ca / 2 ca"**.
   - Hiển thị rõ ràng mục tiêu hành động:
     * **`🎯 Cần 2 ca sạch`** (khi mới vào nấc).
     * **`🎯 Cần 1 ca sạch`** (khi đã vượt qua 1 ca đầu an toàn).
   - Tooltip/Title: `Lộ trình tiêu chuẩn: Cần thêm X ca sạch để thăng cấp`.

---

## 3. Telemetry & Observability Bắt Buộc Trong Backend (`follow_health_helper.py`)
Để tránh lỗi thiếu metrics khi Closeout Reviewer chấm điểm:
Hàm `get_follow_health_data()` bắt buộc trả về trong `telemetry`:
```python
"telemetry": {
    "execution_ms": duration_ms,
    "total_tracked": summary["total_tracked"],
    "state_files_found": len(accounts),
    "recovery_cautious_count": sum(1 for a in accounts if a.get("recovery_mode") == "CAUTIOUS"),
    "recovery_fast_track_count": sum(1 for a in accounts if a.get("recovery_mode") == "FAST_TRACK"),
}
```

---

## 4. Test Suite Bắt Buộc Gated Trong Closeout (`tests/test_tiktok_dashboard.py`)
Mọi thay đổi liên quan đến recovery flow bắt buộc phải có test phủ:
- Chuyển nấc `probation_tier1` vs `probation_tier2` theo số ca `(0/2 ca)`.
- Giá trị `sessions_needed == 2` cho từng stage.
- Telemetry `recovery_cautious_count` được populate.
- Render HTML chứa đúng `🎯 Cần` và `⚡ Ưu tiên`.

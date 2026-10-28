# Khế Ước Phân Định Ca vs Phiên & Cơ Chế Tự Leo Tháp Quota Follow (2026-10-28)

## 1. Phân Định Rõ Ràng: Ca (Shift) vs Phiên (Session)
- **4 Ca lớn trong ngày**:
  - Ca 1 (Sáng): 06:00 – 12:00
  - Ca 2 (Chiều): 12:00 – 18:00
  - Ca 3 (Tối): 18:00 – 24:00
  - Ca 4 (Đêm): 00:00 – 06:00
- **Mỗi Ca chia làm 2 Phiên** (Session):
  - Ví dụ Ca Chiều (Ca 2):
    - Phiên 1: 12:00 – 14:00 (thực tế chạy ~12:24)
    - Phiên 2: 14:00 – 18:00 (thực tế chạy ~14:20)
- **Giãn cách an toàn giữa 2 Phiên**: Cách nhau $\ge 90 - 120$ phút để TikTok reset cửa sổ giám sát thao tác dồn (Burst Action Window).

## 2. Hai Tầng Rate Limit của TikTok & Kỷ Luật Không Bịa Đặt Vạch Đỏ
- **Tầng 1: Session Burst Limit (Trần Phiên)**:
  - Khống chế từ 10–15 lượt cho mỗi lần mở app (tùy nick bóp trần do từng bị nhả). Bấm dồn quá nhanh trong 5–10 phút sẽ bị TikTok kích hoạt Silent Drop tức thì (Pull-to-refresh bắt nhả tại chỗ).
- **Tầng 2: Daily Action Limit (Trần Ngày)**:
  - Trong cấu hình gốc (`config.py` dòng 52): `budget_per_day: 40`, ngưỡng kịch khung an toàn là **50 lượt/ngày** (theo kinh nghiệm farm).
  - CẤM TUYỆT ĐỐI Coordinator tự suy luận hay bịa ra các con số "vạch đỏ 30" không có trong code gốc hoặc đòi ép trần ngày xuống 14–15 làm sụt giảm 50% sản lượng follow chéo của farm.

## 3. Cơ Chế Tự Động "Leo Tháp" Quota (`follow_state.py`)
- Dòng 272–280 trong `follow_state.py`:
  - Khi một tài khoản Veteran/Khỏe hoàn thành ca sạch (`last_session_clean == True`), hệ thống tự động tăng `active_ceiling = min(40, proven_safe_ceiling + 2)`.
  - Quota tự leo theo từng bậc thang: $14 \rightarrow 16 \rightarrow 18 \dots \rightarrow 40$.
- Giữ nguyên cơ chế trần theo Phiên + Giãn cách giữa các phiên là phương án tối ưu nhất: vừa bảo vệ nick khỏi bị nhả tức thời, vừa để dàn nick khỏe tự leo tháp tối đa hóa hiệu suất farm.

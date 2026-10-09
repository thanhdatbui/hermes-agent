# S7 Rolling Cleanup: Prioritizing GPM Live Accounts

## Background
Khi các máy S7 trong Taadaa Farm đạt ngưỡng trần tài khoản (ví dụ 10 accounts/máy) cần dọn cuốn chiếu (rolling cleanup) để giải phóng chỗ cho lượt reg tiếp theo, việc chọn tài khoản để gỡ khỏi máy cần tuân thủ thứ tự ưu tiên nhằm bảo toàn an toàn tài khoản và hiệu suất vận hành.

## Candidate Selection & Priority Rules
Trong `preflight_s7_rolling_cleanup.py` (`evaluate_s7_accounts`):

1. **Điều kiện đủ điều kiện (Eligible candidate):**
   - Tài khoản đã lên GPM (`has_gpm = info.get("has_gpm_live", False) or info.get("has_oauth", False)`), **HOẶC**
   - Tài khoản thỏa mãn điều kiện tuổi an toàn: Có 2FA (`gate1 = has_2fa`) VÀ Tuổi >= 30 ngày (`gate3 = age_days >= 30`).

2. **Thứ tự ưu tiên gỡ (Sort priority):**
   - **Ưu tiên 1 (Priority 0):** Các tài khoản đã có GPM Live / OAuth thành công. Lý do: Tài khoản đã được đồng bộ và hoạt động ổn định trên môi trường PC/GPM, việc gỡ khỏi S7 giải phóng slot trên điện thoại mà không làm gián đoạn khai thác.
   - **Ưu tiên 2 (Priority 1):** Các tài khoản chưa lên GPM nhưng đã đủ 2FA và đủ 30 ngày tuổi.
   - Giữa các tài khoản cùng mức ưu tiên: Sắp xếp theo ngày tạo (`created_date`) từ cũ nhất đến mới nhất:
     ```python
     candidates.sort(key=lambda x: (x.get("priority", 1), x["created_date"]))
     ```

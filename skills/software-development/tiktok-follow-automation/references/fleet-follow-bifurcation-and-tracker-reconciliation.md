# Fleet Follow Bifurcation & Tracker DB Reconciliation Protocol

## 1. Nguyên Tắc Đối Soát Kép Khi Audit Follow Fleet (Dual-Source Invariant)
- **CẤM KẾT LUẬN THIÊN KIẾN TỪ MỘT NGUỒN:** TUYỆT ĐỐI KHÔNG chỉ đọc các file `runs/state/follow_state_*.json` rồi suy diễn toàn farm bị chết/nhả follow.
  - Các file `follow_state_*.json` lưu trữ trạng thái streak và cooldown lịch sử; các nick inactive hoặc kẹt streak vẫn nằm đó qua nhiều tuần.
- **BẮT BUỘC ĐỐI SOÁT VỚI `tiktok_tracker.db`:**
  - Bảng `daily_account_actions` & `session_action_stats` là Source of Truth về throughput follow thực tế mỗi ngày.
  - Query kiểm tra nick thực sự active trong 7 ngày gần nhất:
    ```sql
    SELECT username, may, sum(internal_follows), count(distinct target_date)
    FROM daily_account_actions
    WHERE target_date >= date('now', '-7 days') AND internal_follows > 0
    GROUP BY username, may;
    ```

## 2. Quy Luật Phân Cực Fleet (Fleet Bifurcation)
Khảo sát toàn diện 411 state files và tracker DB cho thấy farm phân cực rõ rệt thành 2 nhóm:
1. **Nhóm Khỏe / Trụ cột (~25% - 30% farm, 60 - 70 nick):**
   - Tập trung tại Row 1, 2, 3 của các máy; account age > 60-90 ngày, video count >= 15 - 25 video.
   - Sở hữu Inbound Trust vững; chạy đều đặn mỗi ngày (100 - 300+ follows/ngày toàn farm), tỷ lệ sống sót cao, streak = 0.
2. **Nhóm Yếu Bị Kẹt Vòng Lặp Phạt Cooldown (~180 - 200 slot):**
   - Tập trung tại Row 4 - 8 và nhóm < 10 video (chưa đạt chuẩn Dual Gate).
   - Tỷ lệ ra tù bị dính nhả liền (relapse immediate): 85% - 93%.
   - Tỷ lệ ra tù follow được vài cái (1 - 3 cái warm-up) rồi dính lại: 7% - 13%.
   - Nguyên nhân: Thiếu Inbound Trust tự nhiên từ video và tương tác inbound; server TikTok gán cờ tài khoản spam, cooldown đơn thuần không xóa được cờ này.

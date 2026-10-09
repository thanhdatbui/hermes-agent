# Fleet Post-Cooldown Relapse & Row/Video Audit (07/10/2026)

## 1. Bối cảnh & Quy mô Đối soát
- **Dữ liệu nguồn:** Toàn bộ 411 state file (`runs/state/follow_state_*.json`) thuộc 80 máy Phone Farm (`D:/Taadaa/tiktok-follow`).
- **Mục tiêu:** Đánh giá thực nghiệm tỷ lệ sống sót của tài khoản TikTok sau khi mãn hạn cooldown (ra tù), phân tích tương quan giữa số lượng video, vị trí slot (Row) và khả năng hồi phục Inbound Trust.

---

## 2. Tổng quan Tỷ lệ Sống sót Sau Ra Tù

| Trạng thái | Số lượng (411 nick) | Tỷ lệ toàn farm | Tỷ lệ trên nhóm ra tù (215 nick) |
| :--- | :---: | :---: | :---: |
| **Chưa từng dính phạt (Streak 0)** | 22 nick | 5.4% | - |
| **Mới dính phạt lần đầu (Streak 1)** | 174 nick | 42.3% | - |
| **Tổng số nick ĐÃ TỪNG MÃN HẠN RA TÙ (Streak ≥ 2)** | 215 nick | 52.3% | 100.0% |
| ↳ **Cứ ra tù là dính nhả liền liên tục (0 follow / đứt ngay)** | **184 - 200 nick** | **44.8% - 48.7%** | **85.6% - 93.0%** |
| ↳ **Ra tù follow được vài cái (1 - 5 cái) rồi dính lại** | **15 - 29 nick** | **3.6% - 7.1%** | **7.0% - 13.5%** |
| ↳ **Hồi phục hoàn toàn (Streak về 0, follow ổn định)** | **2 nick** | **0.5%** | **0.9%** |

*Ghi chú đặc biệt:* Toàn bộ farm 411 nick chỉ ghi nhận **đúng 2 nick** (Máy 1 Row 1 và Máy 52 Row 1) phục hồi sạch streak về 0 sau khi từng dính cooldown. Cả 2 nick này đều có **trên 22 video và tuổi đời > 4 tháng**.

---

## 3. Thống kê Chi tiết theo Row (Slot tài khoản trên máy)

| Row (Slot) | Tổng nick | Avg Video | Chưa fail | Streak 1 | Đã ra tù (Streak ≥ 2) | Nhả liền liên tục | Follow được vài cái | Tỷ lệ nhả liền sau ra tù |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Row 1** | 80 | **23.8** | 12 | 38 | 30 | 28 | 2 | **93.3%** |
| **Row 2** | 78 | **12.5** | 4 | 20 | 54 | 38 | 16 | **70.4%** |
| **Row 3** | 73 | **10.6** | 4 | 21 | 48 | 44 | 4 | **91.7%** |
| **Row 4** | 77 | **8.9** | 0 | 19 | 58 | 53 | 5 | **91.4%** |
| **Row 5** | 37 | **6.3** | 1 | 25 | 11 | 11 | 0 | **100.0%** |
| **Row 6** | 39 | **6.1** | 0 | 27 | 12 | 12 | 0 | **100.0%** |
| **Row 7** | 19 | **6.9** | 0 | 17 | 2 | 2 | 0 | **100.0%** |
| **Row 8** | 7 | **6.1** | 0 | 7 | 0 | 0 | 0 | *(Chưa mãn hạn cữ 1)* |

### Nhận xét theo Row:
1. **Row 1 (Kênh nòng cốt lâu đời):** Sở hữu lượng video cao nhất (trung bình 23.8 video), tỷ lệ nick chưa từng dính phạt cao nhất (15%). Nhưng một khi đã bị TikTok gắn cờ theo dõi, khi mãn hạn cooldown vẫn có **93.3%** khả năng bị nhả liền.
2. **Row 2 (Kênh trung hạn):** Tỷ lệ "nhích" được vài follow (1-5 follow) sau ra tù cao nhất farm (**29.6%**). Nhóm này thường nuốt trọn được cữ warm-up 3-5 follow ở phiên đầu tiên trước khi bị nhả lại ở các phiên sau.
3. **Row 5 - 7 (Kênh mới bổ sung):** Video mỏng (trung bình chỉ 6.1 - 6.9 video). Khi đã dính vào tù, **100% tài khoản** khi ra tù đều bị cắn nhả lại ngay lập tức (Streak leo thẳng lên 2, 3, 4).

---

## 4. Thống kê Chi tiết theo Số Lượng Video

| Nhóm Video | Tổng nick | Chưa dính fail | Mới dính cữ 1 | Đã từng ra tù | Nhả liền liên tục | Follow được vài cái | Tỷ lệ nhả liền sau ra tù |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dưới 10 video** *(Chưa đạt Dual Gate)* | 179 | 2 | 102 | 75 | **71 nick** | 4 nick | **94.7%** |
| **10 – 19 video** *(Đạt chuẩn tối thiểu)* | 159 | 5 | 40 | 114 | **94 nick** | 20 nick | **82.5%** |
| **≥ 20 video** *(Dày dặn Inbound Trust)* | 62 | 10 | 29 | 23 | **21 nick** | 2 nick | **91.3%** |
| **Chưa scan video** | 11 | 5 | 3 | 3 | 2 nick | 1 nick | **66.7%** |

### Kết luận Kỹ thuật & Hành động Vận hành:
1. **Số lượng video có tạo khác biệt không?**
   - Đạt 10-19 video giúp tăng tỷ lệ follow được vài cái sau ra tù từ **5.3% lên 17.5%**.
   - Tuy nhiên, số lượng video **KHÔNG THỂ XÓA CỜ SPAM** một khi TikTok đã đưa tài khoản vào danh sách đen follow. Tỷ lệ bị nhả lại ở tất cả các nhóm vẫn ở mức áp đảo (>82%).
2. **Nguyên tắc bất biến về Trust Recovery:**
   - **Nghỉ follow đơn thuần + lướt feed KHÔNG làm hồi phục Trust Follow.**
   - Nick bị phạt tái phạm nhiều lần (Streak ≥ 4) bắt buộc phải tuân thủ Cooldown 15 ngày, đồng thời cần tiếp tục đăng thêm video và tích lũy view/tương tác tự nhiên trước khi kích hoạt lại follow.

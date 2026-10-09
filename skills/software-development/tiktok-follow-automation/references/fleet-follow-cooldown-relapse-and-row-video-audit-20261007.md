# Fleet Follow Cooldown Relapse, Row & Video Count Audit (07/10/2026)

## 1. Kết Quả Khảo Sát Toàn Bộ Farm (411 State Files / 80 Máy)

Đã đối soát thực tế toàn bộ `runs/state/follow_state_*.json` trên 80 máy:
- **Tổng số nick trong hệ thống:** `411 nick`
- **Nick chưa từng dính phạt (Streak = 0):** `22 nick` (5.4%)
- **Nick mới bị dính phạt lần đầu (Streak = 1 - đang/vừa xong cữ phạt đầu):** `174 nick` (42.3%)
- **Tổng số nick đã từng ra tù (Streak >= 2 hoặc đã qua >= 1 vòng cooldown):** `215 nick` (52.3%)

---

## 2. Tỉ Lệ Hành Vi Khi Ra Tù (Trên 215 Nick Đã Từng Mãn Hạn)

| Hành vi sau khi ra tù | Số lượng | Tỉ lệ trên nick ra tù | Tỉ lệ trên toàn farm |
| :--- | :---: | :---: | :---: |
| **1. Cứ ra tù là dính nhả liền liên tục** *(0 follow / fail ngay / Streak leo 2->6)* | **184 - 200 nick** | **~85.6% - 93.0%** | **~44.8% - 48.7%** |
| **2. Ra tù follow được vài cái (1 - 5 cái) rồi bị lại** *(Ăn warm-up 3-5 cái rồi phiên sau bị lại)* | **15 - 29 nick** | **~7.0% - 13.5%** | **~3.6% - 7.1%** |
| **3. Ra tù follow lại bình thường / hồi phục sạch streak** | **2 nick** | **~0.9%** | **~0.5%** |

---

## 3. Phân Tích Chi Tiết Theo Row (Slot Vị Trí Trên Máy)

| Row (Slot) | Tổng nick | Avg Video | Chưa fail | Streak 1 | Đã ra tù (Streak ≥ 2) | Nhả liền | Được vài cái | Tỉ lệ nhả liền sau ra tù |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Row 1** | 80 | **23.8 vid** | 12 | 38 | 30 | 28 | 2 | **93.3%** |
| **Row 2** | 78 | **12.5 vid** | 4 | 20 | 54 | 38 | 16 | **70.4%** |
| **Row 3** | 73 | **10.6 vid** | 4 | 21 | 48 | 44 | 4 | **91.7%** |
| **Row 4** | 77 | **8.9 vid** | 0 | 19 | 58 | 53 | 5 | **91.4%** |
| **Row 5** | 37 | **6.3 vid** | 1 | 25 | 11 | 11 | 0 | **100%** |
| **Row 6** | 39 | **6.1 vid** | 0 | 27 | 12 | 12 | 0 | **100%** |
| **Row 7** | 19 | **6.9 vid** | 0 | 17 | 2 | 2 | 0 | **100%** |
| **Row 8** | 7 | **6.1 vid** | 0 | 7 | 0 | 0 | 0 | *(Chưa ra tù)* |

- **Row 1:** Nick lâu đời nhất, lượng video trung bình cao nhất (23.8 video), nhiều nick chưa từng dính phạt nhất (12/80 nick ~ 15%). Nhưng khi đã dính jail thì ra tù vẫn bị cắn lại 93.3%.
- **Row 2:** Tỷ lệ sống sót được vài lượt warm-up sau ra tù cao nhất (29.6%).
- **Row 5, 6, 7:** Dàn nick mới bổ sung, video mỏng (~6 video) -> 100% dính nhả liền liên tục khi ra tù.

---

## 4. Phân Tích Chi Tiết Theo Số Lượng Video

| Nhóm Video | Tổng nick | Chưa dính fail | Mới dính cữ 1 | Đã từng ra tù | Nhả liền sau ra tù | Ăn được vài cái | Tỉ lệ nhả liền sau ra tù |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **< 10 video** *(Chưa đạt Dual Gate)* | 179 | 2 | 102 | 75 | **71 nick** | 4 nick | **94.7%** |
| **10 – 19 video** *(Đạt chuẩn cơ bản)* | 159 | 5 | 40 | 114 | **94 nick** | 20 nick | **82.5%** |
| **≥ 20 video** *(Dày video)* | 62 | 10 | 29 | 23 | **21 nick** | 2 nick | **91.3%** |

---

## 5. Kết Luận & Quy Tắc Vận Hành Đúc Rút

1. **Độc lập giữa Feed Trust và Follow Trust:**
   - Nghỉ follow đơn thuần + chỉ lướt feed **KHÔNG** tự động hồi phục Follow Trust một khi tài khoản đã bị TikTok đưa vào diện theo dõi/gắn cờ spam follow.
   - 2 nick duy nhất hồi phục hoàn toàn (Máy 1 Row 1 và Máy 52 Row 1) đều có tuổi đời > 4 tháng và trên 22-28 video.
2. **Kỷ luật Same-Day Warmup (Case UI-99):**
   - Với các nick ra tù ăn được 3-5 lượt warm-up ở phiên đầu (chiếm 7-13.5%), **BẮT BUỘC giữ nguyên cờ warm-up trong suốt các phiên còn lại của ngày hôm đó**, cấm reset fail_streak sớm khiến các phiên sau nhảy vọt full budget gây cắn phạt tức thì.

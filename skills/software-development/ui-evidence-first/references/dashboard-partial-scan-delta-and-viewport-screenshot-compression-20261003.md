# Bẫy Quét Dở Dang Gây Báo Đỏ Ảo Trên Dashboard & Kỷ Luật Nén Ảnh MEDIA Viewport (03/10/2026)

## 1. BẪY QUÉT DỞ DANG GÂY BÁO ĐỎ ẢO TRÊN DASHBOARD (PARTIAL SCAN FALSE NEGATIVE DELTA)

### Hiện tượng & Phản ánh của User:
- User mở Dashboard (ví dụ Modal Biểu Đồ Tăng Trưởng Toàn Farm tại `kibe:1905`) thấy chỉ số giảm nghiêm trọng, các thẻ KPI và bảng biến động báo số âm đỏ rực:
  * FOLLOWER: `-1,082` (đỏ lòm)
  * TIM: `-2,810` (đỏ lòm)
  * ĐÃ FOLLOW: `-1,504` (đỏ lòm)
  * Số nick hiển thị: `1,129` (giảm 123 nick so với `1,252` nick ngày hôm trước).
- User bức xúc: *"Sao quét ms nhất thiếu nick r đi báo đỏ lòm v"*.

### Nguyên nhân cốt lõi:
1. **Lệch pha thời điểm quét (Partial Scan in Progress):**
   - Dàn farm lớn (160 máy, 1.252 nick) thường quét theo từng cụm hoặc từng máy rải rác (Cụm Kibe quét lúc 03:46, Cụm Admin quét lúc 04:07).
   - Tại thời điểm 04:11, một số máy chưa kịp quét hoặc file Excel vừa đồng bộ trễ, trong DB chỉ mới có 1.129 nick có snapshot của ngày hôm nay.
2. **Thuật toán lấy Tổng trừ Tổng (Naive Sum Aggregation):**
   - Modal gom tất cả snapshot trong ngày: `SUM(follower_today)`.
   - Sau đó tính Delta ngày bằng phép trừ thô: `Delta = SUM(hôm nay) - SUM(hôm qua)`.
   - Kết quả: Lấy tổng của 1.129 nick hôm nay trừ cho tổng của cả 1.252 nick hôm qua! 123 nick chưa quét bị biến mất khỏi phép cộng dồn, làm mất luôn follower/tim của chính 123 nick đó, tạo ra số âm ảo khổng lồ.
3. **Ngưỡng chặn cố định bị lọt lưới (`threshold * 0.5`):**
   - Code cũ có chốt chặn: `if history[-1]["total_users"] < (history[-2]["total_users"] * 0.5)`.
   - Ngưỡng 50% chỉ kích hoạt khi quét dưới 626 nick. Khi quét được 1.129 nick (~90%), chốt chặn không kích hoạt, làm lọt số liệu dở dang ra ngoài.

### Quy chuẩn khắc phục (Standard Fix Pattern):
1. **Đối soát động với dàn nick hoạt động (`target_total = max(live_total, prev_total)`):**
   - Không dùng ngưỡng tỷ lệ cố định (`* 0.5`).
   - Kiểm tra nếu `history[-1]["total_users"] < target_total`, lập tức kích hoạt cơ chế kế thừa (carry-over):
     * Lấy `farm_data = get_farm_data(db_path)` (bảng chính luôn duy trì snapshot hợp lệ gần nhất trong 2 ngày của toàn bộ 1.252 nick).
     * Ghi đè số liệu ngày hôm nay bằng `summary` hợp lệ: `total_users = target_total`, `follower = s["total_followers"]`, `following = s["total_following"]`, `heart = s["total_hearts"]`.
2. **Kỷ luật dữ liệu:** Khi phát hiện thiếu nick theo máy/cụm, Coordinator chủ động chạy lệnh quét bổ sung theo danh sách username/máy thiếu (`python tiktok_account_tracker.py --usernames ...`), không để sót nick đến ca sau.

---

## 2. KỶ LUẬT NÉN ẢNH MEDIA VIEWPORT & CHỐNG DECOMPRESSION BOMB

### Bối cảnh kỹ thuật:
- Trên các web dashboard có bảng danh sách dữ liệu lớn (như bảng 1.252 dòng của farm TikTok), lệnh chụp toàn màn hình (`browser_vision` / `full_page=True`) tạo ra file PNG có chiều cao vượt quá 65.500 pixels và dung lượng 9–10 MB.
- Hậu quả nghiêm trọng:
  1. Telegram Bot API timeout khi upload `sendPhoto`, gây cảnh báo `⚠️ Couldn't deliver the file attachment...` hoặc tự chuyển sang tệp đính kèm Document.
  2. Thư viện xử lý ảnh (Pillow / PIL) ném cảnh báo `DecompressionBombWarning` hoặc lỗi `OSError: Maximum supported image dimension is 65500 pixels`.

### Quy tắc xử lý ảnh UI trước khi gửi qua `MEDIA:`:
1. **Crop đúng Viewport cần nghiệm thu:**
   - Với modal popup hoặc khu vực KPI đầu trang: Cắt ảnh từ `y = 0` đến `min(height, 1400)` pixels. Không để ảnh kéo dài toàn bộ 1.252 dòng bảng.
2. **Convert sang JPEG nén (Quality 85):**
   - Chuyển ảnh sang RGB và lưu định dạng JPEG với `quality=85, optimize=True`.
   - Đảm bảo dung lượng file luôn nằm trong ngưỡng an toàn: **`< 1 - 2 MB`** (thực tế ~150 - 300 KB).
3. **Tuyệt đối tuân thủ Telegram UX:** User xem ảnh ngay lập tức trên app Telegram mobile/desktop, hiển thị sắc nét, không bị giật lag và không bị văng lỗi timeout gateway.

# Quy Chuẩn Audit Lịch Chạy Parity, Ngưỡng Quota & Hiện Trạng Phục Hồi Cooldown Follow

## 1. Cạm Bẫy Phân Tích Múi Giờ UTC vs Ngày Chẵn/Lẻ (Parity Lane)
- **Bối cảnh vận hành:**
  * Farm chạy chia theo ngày chẵn/lẻ giờ Việt Nam (`Asia/Ho_Chi_Minh`, GMT+7).
  * Ngày lẻ (01, 03, 05, 07): Chạy các Row lẻ (Row 1, 3, 5, 7). Ca sáng chạy từ 06:00 - 08:30 sáng VN.
  * Ngày chẵn (02, 04, 06, 08): Chạy các Row chẵn (Row 2, 4, 6, 8). Ca sáng chạy từ 06:00 - 08:30 sáng VN.
- **Cạm bẫy đối soát Timestamp:**
  * File state JSON lưu timestamp chuẩn ISO UTC (`+00:00`), ví dụ `2026-10-02T23:23:35+00:00`.
  * Nếu parse trực tiếp chuỗi ngày (`ts[:10]`), ca sáng 06:23 ngày 03/10 (giờ VN) sẽ bị đọc nhầm thành ngày 02/10 (ngày chẵn), dẫn đến kết luận sai lệch nghiêm trọng ("Row 1 chạy vào ngày chẵn").
- **Quy tắc bắt buộc:**
  * Khi audit bất kỳ file state hoặc log follow nào, BẮT BUỘC convert toàn bộ timestamp sang `ZoneInfo("Asia/Ho_Chi_Minh")` trước khi group theo ngày:
    ```python
    from datetime import datetime
    from zoneinfo import ZoneInfo
    HCMC = ZoneInfo("Asia/Ho_Chi_Minh")
    dt_vn = datetime.fromisoformat(iso_str).astimezone(HCMC)
    day_vn = dt_vn.strftime("%Y-%m-%d")
    ```

---

## 2. Di Chứng Từ Lỗi Verify Lừa (False-Positive Verify) & Blacklist Server
- **Nguyên nhân lịch sử (Trước 02/10):**
  * Hàm `verify_follow.py` từng nhận diện nhầm nhãn đếm header (`id/sdn`, `id/shq`, `id/t1i`... số lượng following của chính profile) là tín hiệu follow thành công.
  * Khi TikTok server âm thầm từ chối (silent-drop), script tưởng thành công và tiếp tục ép nick follow liên tục 10-20 acc khác trong cùng phiên.
  * Hậu quả: TikTok đưa hàng loạt UID vào danh sách đen "Spam Bot nặng" ở cấp độ tài khoản (Account-level Action Block).
- **Thực trạng sau khi vá verify (Từ 02/10 trở đi):**
  * 344/411 nick bị phát hiện dính cờ nhả ngay lượt bấm đầu tiên.
  * **Tỉ lệ phục hồi sau khi hết cooldown (3-5 ngày):**
    + **~93.3%:** Bị nhả ngay lượt bấm đầu tiên (0 follow), streak tiếp tục tăng lên 2, 3, 4, 5.
    + **~6.7%:** Bấm được 1-5 lượt ở cữ warm-up phiên đầu rồi bị nhả lại ở phiên kế tiếp.
    + **0%:** Chưa có nick nào từng dính phạt đạt trạng thái phục hồi bền vững dài hạn.
  * **21 nick duy nhất cày follow đều mỗi ngày:** Là nhóm nick nguyên bản chưa từng bị dính phạt từ trước đến nay (tuổi đời > 215 ngày, video > 20, có tương tác ngược tự nhiên từ followers).

---

## 3. Quy Tắc Đối Soát Dữ Liệu Chống Báo Cáo Khống
1. **Tuyệt đối không lấy tổng lũy kế nhiều ngày gộp lại:** Phải bóc tách chính xác từng ngày theo đúng múi giờ GMT+7.
2. **Đối soát chéo với DB Scrape Snapshot:** So sánh số lượt follow trong state JSON với chỉ số `following` thật sự cào từ profile TikTok trên máy (`snapshots` table trong `tiktok_tracker.db`).
3. **Phân biệt rạch ròi 2 nhóm:**
   - Nhóm chưa từng dính phạt (khỏe mạnh thực tế).
   - Nhóm ra tù đang trong diện theo dõi/relapse (không được vội vàng kết luận là đã khỏi bệnh).

---

## 4. Lịch Sử Phục Hồi Dài Hạn (Historical Recovery từ Tháng 08/2026)
- **Đối soát ngược nick đang chạy vs lịch sử tháng 8-9:**
  * 100% các nick đang đi follow mượt mà trong tháng 10 (như Máy 01, 02, 09, 14, 17, 18, 28, 39, 50, 52...) là nick nguyên bản **CHƯA TỪNG dính fail trong lịch sử** (Following thật trên profile đạt 200 - 330, video 24-29, tuổi >215 ngày).
  * 100% các nick từng bị ghi nhận dính án nhả trong tháng 9 (37 nick) sang tháng 10 đều **0 follow**, tiếp tục kẹt trong cooldown hoặc bị nhả lại ngay phát đầu.
- **Điều kiện để nick từng bị nhả hồi phục thực tế:**
  * Qua dữ liệu lịch sử từ khi khởi chạy farm (tháng 8/2026), các ca hồi phục thành công (như Máy 12 R1, Máy 14 R1, Máy 17 R1) đều có **quãng nghỉ (rest gap) rất dài từ 10 đến 36 ngày**.
  * Cooldown ngắn hạn 3 - 5 ngày là KHÔNG ĐỦ để TikTok server xóa UID khỏi blacklist đối với các nick đã bị phạt sâu.
- **Cơ chế tái phát cùng ngày (Same-Day Quota Spike Bug):**
  * Lỗi logic cũ trong `mark(STATUS_FOLLOWED)` xóa `fail_streak = 0` ngay lượt bấm đầu tiên khiến phiên 2 cùng ngày nhảy vọt lên Full Budget (10-20 lượt), trực tiếp kích hoạt bộ lọc trừng phạt của TikTok ngay trong ngày ra tù.
  * Bắt buộc duy trì Case UI-99: Khóa quota 3-5 lượt suốt cả ngày ra tù, chỉ xem xét reset streak sang ngày hôm sau.

---

## 5. Phân Tích Thực Nghiệm: Ngưỡng Quota Follow Trong Ngày & Đề Xuất 2 Tầng Quota
Qua đối soát 54 lượt chạy thực tế của toàn farm trong tháng 10 sau khi vá verify:
- **1 – 6 follow / ngày:** Rủi ro nhả cao (>66% - 81%) nếu rơi vào acc đang bị phạt/chưa sạch án.
- **7 – 10 follow / ngày (VÙNG AN TOÀN NHẤT):** Đạt tỷ lệ an toàn **~88.9%** (chỉ 1/9 lượt chạy bị nhả). Đây là ngưỡng tối ưu cho các acc thông thường.
- **11 – 15 follow / ngày (NGƯỠNG KÍCH HOẠT QUÉT SPAM):** Tỷ lệ nhả vọt lên **25%** (gãy hàng loạt ở lượt thứ 12 – 13).
- **>= 16 follow / ngày:** An toàn 100% nhưng **chỉ áp dụng riêng cho Nick Trâu Bò VIP** (>215 ngày, >25 video, có tương tác ngược tốt).

### Đề xuất cấu hình 2 tầng Quota (Tiered Quota):
- **Tầng 1 (Tier-1 VIP):** 12 – 16 follow/ngày (chia 2 phiên, 6 – 8 follow/phiên) cho nhóm acc >180d, >20v, `streak == 0`.
- **Tầng 2 (Tier-2 Tiêu chuẩn & Acc hồi phục):** 6 – 8 follow/ngày (chia 2 phiên, 3 – 4 follow/phiên), trần cứng không quá 10 follow/ngày.

---

## 6. Loại Bỏ Hoàn Toàn Tài Liệu Cũ `uiautomator.md`
- Hệ thống đã bãi bỏ hoàn toàn framework và tài liệu `uiautomator.md` (toàn farm chạy ATX-Agent / XML UI dump).
- Tuyệt đối CẤM trích dẫn, tham chiếu hay đòi hỏi cập nhật file `uiautomator.md`. Mọi case fix đều quy chuẩn về `references/case-ui-*.md` dưới skill này.

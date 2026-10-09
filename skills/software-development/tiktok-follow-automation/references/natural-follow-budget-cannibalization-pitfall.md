# Cạm Bẫy Follow Tự Nhiên Lướt Feed & Ăn Mòn Daily Follow Budget (Cannibalization Pitfall)

## 1. Bản chất vấn đề
- Khi lướt feed (`feed_swipe_smoke.py`), hệ thống có cơ chế `DEFAULT_FEED_FOLLOW_RATES` (5% trên tab For You) và `DEFAULT_DEEP_FOLLOW_RATE_PERCENT = 5` nhằm giả lập hành vi người dùng thật bấm follow tự nhiên trên video đề xuất.
- Tuy nhiên, trong thực tế vận hành Farm:
  + Tỉ lệ máy đủ điều kiện đi follow rất ít: đa số máy đang ở chế độ **Dưỡng sinh** (~33% nghỉ), bị **Cooldown** (sau chuỗi nhả), hoặc chưa đủ điều kiện (tuổi < 21d, video < 6).
  + TikTok áp trần **Daily Action Quota** cực kỳ nghiêm ngặt trên tài khoản nuôi (chỉ vài lượt follow an toàn mỗi ngày trước khi bị server silent-drop hoặc checkpoint).
  + Khi số lượng nick được phép follow đã ít, việc để bot tự ý bấm "Follow tự nhiên" trên For You sẽ **ăn thẳng vào daily follow budget của nick**, làm cạn kiệt quota dành cho **Follow chéo nội bộ (Anchor / Bù)**.

## 2. Bằng chứng thực tế (Case Study Ca 1 Sáng)
- **Log Watchdog & Đối soát:**
  + 80 máy Kibe chỉ có **8 máy** đủ điều kiện follow chéo thành công.
  + Bot thực hiện **17 lượt follow tự nhiên** khi lướt feed $\rightarrow$ **11 lượt bị TikTok NHẢ NGAY LẬP TỨC (drop 65%)**, chỉ sót lại 6 lượt.
  + Các nick bị nhả điển hình:
    * M75: 0 chéo, 1 tự nhiên $\rightarrow$ Web tăng +0 (nhả 100%).
    * M4: 1 chéo, 1 tự nhiên $\rightarrow$ Web tăng +1 (nhả 1).
    * M26: 5 chéo, 1 tự nhiên $\rightarrow$ Web tăng +5 (nhả 1).
  + Tỉ lệ follow tự nhiên (14 lượt chênh lệch) chiếm tới 25% tổng lượng follow (so với 56 chéo), gây lãng phí hành động và làm rác trust profile.

## 3. Nguyên tắc vận hành & Khắc phục
1. **Ưu tiên bảo toàn Quota cho Follow Chéo:**
   - Follow chéo nội bộ (Module 2 Anchor & Module 1 Bù) là mục tiêu cốt lõi để đẩy follower cho kênh chính và tăng tương tác dàn acc.
   - Khi lướt Feed nuôi acc, mục tiêu chính là **giữ trust sạch**: tập trung xem video (dwell time), thả tim phân phối hợp lý (10–15%), đọc comment, scroll rewind; **KHÔNG** nên bấm follow dạo bừa bãi.
2. **Cấu hình chuẩn hóa:**
   - Nên tắt hẳn hoặc đưa `follow_rate` trên Feed về `0` (`FEED_TYPE_FOR_YOU: 0`) cho các tài khoản đang trong diện nuôi/chéo.
   - Nếu muốn duy trì organic loãng chuỗi: chỉ áp dụng cho nick có độ trust cao vượt trội (> 60 ngày, > 30 video, không có lịch sử nhả), với tỉ lệ cực thấp (< 0.5%) và trần cứng tối đa 1 lượt / tuần.
3. **Phân tích số liệu đối soát:**
   - Khi thấy chênh lệch giữa Web Following và Bot Follow chéo, luôn kiểm tra số lượt Follow tự nhiên đã log trong Feed session và tỉ lệ drop của chúng trước khi kết luận nick bị hack hay script chạy lén.

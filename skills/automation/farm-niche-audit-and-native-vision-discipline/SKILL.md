---
name: farm-niche-audit-and-native-vision-discipline
description: "Kỷ luật đối soát ngách bằng script kiểm toán 1.272 nick farm (audit_niches_farm.py), cấm nguồn tin tức và cấm giả lập soi mắt bằng browser_vision."
---
# Farm Niche Audit & Native Vision Discipline

Sử dụng quy chuẩn này khi tài khoản TikTok farm cần đổi nguồn video, kiểm toán hiệu suất ngách (niche breakout/flop), hoặc khi kiểm chứng hình ảnh gửi Telegram.

## 1. Kỷ Luật Đối Soát Niche Bằng Script Thật (Anti-Fake Audit Reporting)
- **Cấm đoán mò / Bịa đặt số liệu:** Khi Operator yêu cầu *"tự chọn ngách hot dựa trên dữ liệu cắn đề xuất của farm"*:
  - **CẤM TUYỆT ĐỐI** đếm số dòng Excel hoặc chọn đại một kênh có sẵn trong `sources.qualified30.json` rồi tâng bốc làm "top view" để báo cáo láo.
  - **BẮT BUỘC** chạy script kiểm toán dữ liệu snapshot toàn farm:
    ```bash
    python D:/Taadaa/tools/audit_niches_farm.py
    ```
- **Bảng Chuẩn Hiệu Suất Niche Farm (Cập nhật 1.272 nick):**
  - 👑 **Top 1 Tương Tác:** **`Câu chuyện` (Storytelling)** — 50 nick, 31.046 tim, 39.4 tim/clip, 13 nick breakout. Đây là lựa chọn số 1 khi xoay nguồn cho nick flop.
  - 🚀 **Top Hiệu Suất / Clip:** **`Giao thông` (Camera hành trình)** — 6 nick, 5.497 tim, 45.4 tim/clip, 0% flop.
  - 🔥 **Bền vững & Follower:** **`Gym / Fitness`** — 41 nick, 8.433 tim, 1.283 follower, 19.7 tim/clip.
  - ❌ **Bẫy Flop Nặng (Tránh Xa):** **`Ẩm thực`** (69 nick, chỉ 4.1 tim/clip, tỷ lệ flop 20.3% — TikTok bóp reach mạnh video cận chảo thiếu mặt người).

## 2. Kỷ Luật Loại Bỏ Nguồn Tin Tức / Phóng Sự (News Contamination Rejection)
- **Phát hiện ô nhiễm tin tức:** Khi video gốc mang tính chất thời sự, bản tin, phỏng vấn nhân vật tin tức truyền hình:
  - **CẤM TUYỆT ĐỐI** crop mặt nhân vật tin tức làm avatar hay cố gượng chuẩn hóa kênh.
  - Bắt buộc kích hoạt ngay quy trình **Wipe & Swap Nguồn Triệt Để**:
    ```bash
    python D:/Taadaa/Tiktok-video/scripts/swap_single_folder_pipeline.py \
      --machine <M> --tik <T> \
      --folder-raw <F_raw> --folder-render <F_rend> \
      --channel "<URL_SHORTS>" \
      --uploader "<Uploader>" \
      --niche-slug "cauchuyen" \
      --niche-label "Câu chuyện" \
      --hashtag-pool "<hashtags>" \
      --min-videos 40 \
      --start-seq <posted_count + 1> \
      --clean-old
    ```

## 3. Native Multimodal Vision vs Browser Vision Anti-Hack
- **Kiến trúc Native Vision:** Khi model chính (Gemini) hỗ trợ Multimodal Native (`supports_vision: True`), ảnh người dùng gửi vào chat được nhúng base64 trực tiếp vào turn prompt.
- **Cấm làm màu bằng browser:**
  - CẤM mở file ảnh local bằng `browser_navigate(file:///...)` rồi chụp qua `browser_vision` để giả vờ soi mắt.
  - CẤM mô tả hay bịa đặt (hallucinate) nội dung ảnh khi LLM chưa thực sự nhận diện được pixel thật.
  - Kiểm chứng text/UI: Dùng WinRT OCR thật (`run_winrt_ocr.py`) hoặc Native Vision trực tiếp.

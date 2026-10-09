# Hashtag Safety Composition, State.db Niche Parity & Farm-Wide Parity Suite

## 1. Bối cảnh & Hiện tượng lỗi (2026-09-27)
- **Triệu chứng**: Các kênh TikTok trên farm đăng video có nội dung một đằng nhưng gắn hashtag một nẻo:
  - Video tin tức xã hội "Tin 3 Phút" (`@chungan981` M33 Slot 5) bị gắn toàn bộ hashtag âm nhạc (`#nhacvietnam #singing #amnhac #nhac`).
  - Video gái selfie tập yoga (`@hiencao179` M49 Slot 1) bị gắn toàn bộ hashtag game (`#game #choigame #gamevietnam #gamingvietnam`).
- **Nguyên nhân gốc rễ**:
  1. **Lệch mapping từ DB nguồn (`state.db`)**: Script cào/tạo folder ban đầu gán cột `niche` bằng cách duyệt tuần tự theo số thứ tự dòng của `niches_pool.txt` (Folder 49 = dòng 49 "Game", Folder 33 = dòng 33 "Gym") mà không đối soát với tên kênh YouTube/TikTok thực tế được cào về (`uploader` / `source_channel`).
  2. **167 folder bị kẹt nhãn `pending`**: Khiến script sync sinh ra hashtag rác `#pending #pendingvietnam #pendingmoingay` trên hàng loạt tài khoản.
  3. **Lỗ hổng thuật toán sinh hashtag cũ**: `hashtag_selector.py` ưu tiên lấy từ khóa và bốc toàn bộ tag từ `Hashtag Pool`. Khi Pool bị sai toàn bộ, 100% 3-5 hashtag gắn vào caption đều là tag sai, làm video bị loạn tín hiệu đề xuất và phản cảm.

---

## 2. Invariant Lớp Khiên Bảo Vệ Hashtag (`hashtag_selector.py`)
Mọi video đăng tải trên toàn farm bắt buộc tuân thủ 4 điều kiện bất biến (đã encode cứng vào `scripts/tiktok_workflow/hashtag_selector.py`):
1. **Tổng số hashtag**: Luôn nằm trong khoảng $3 \le N \le 5$, biến thiên tự nhiên theo trọng số: 3 tag (15%), 4 tag (55%), 5 tag (30%). Bất kỳ `count_range` lạ hoặc lỗi type đều được clamp an toàn về `[3, 5]`.
2. **Pool Hashtag Viral Quốc Dân (`COMMON_VIRAL_HASHTAGS`)**:
   `#fyp`, `#xuhuong`, `#videohay`, `#viral`, `#trending`, `#tiktokvietnam`, `#moingay`, `#hay`.
   Mỗi bài đăng bắt buộc có **2 đến 4 hashtag** thuộc pool này để bảo hiểm ngữ cảnh và kéo reach.
3. **Tối đa DUY NHẤT 1 Hashtag Niche**:
   Chỉ cho phép tối đa 1 tag ngách (nếu có trong pool/keyword). Nếu folder nguồn có bị lệch niche, video chỉ lệch đúng 1 tag, 3-4 tag còn lại cùng âm thanh/hình ảnh video sẽ giữ vững đề xuất.
4. **Hiệu năng & Telemetry**:
   - Dùng `seen_niche = set()` O(1) để deduplicate thay vì comprehension.
   - Ghi telemetry có cấu trúc:
     `logger.info(f"[HASHTAG_TELEMETRY] total={len(selected)} niche_count={len(selected) - common_count} common_count={common_count} candidates={len(niche_candidates)} tags={' '.join(selected)}")`

---

## 3. Quy Trình Chuẩn Hóa Data State.db & All Tik (Tik1..Tik8)
1. **Khôi phục 167 folder pending**:
   - Đối chiếu sang `D:\CodexRuntime\tiktok-video-downloader\state-real-1-tiktok-final.db` để lấy niche và source_channel chuẩn (phủ 166/167 folder).
   - Folder 563 (vải sợi / black thread) gán `thoitrang`.
2. **Mapper tự động theo Uploader**:
   - Quét cột `uploader` và `source_channel` trong `state.db` bảng `videos` để reclassify các kênh lớn (Xuân Hinh $\rightarrow$ haihuoc, Mê Xe $\rightarrow$ oto, nhaTO $\rightarrow$ noithat, Tin 3 phút $\rightarrow$ cauchuyen, Yoga Phương Thùy $\rightarrow$ yoga).
3. **Đồng bộ Excel an toàn**:
   - Chạy `python C:/Users/Kibe/AppData/Local/hermes/scripts/sync_all_tik_keywords.py` (atomic write + backup `.bak`).
   - Đảm bảo 100% 640 tài khoản trên cả 8 file Tik có `Keyword Video` và `Hashtag Pool` hợp lệ, 0 ô trống, 0 pending.

---

## 4. Test Suite Chứng Minh (End-to-End Parity)
- Module unit tests: `python -m pytest tests/test_hashtag_selector.py -v` (7 tests covering count clamping, malformed pool, telemetry, deduplication).
- Farm E2E parity test: `python -m pytest tests/test_farm_hashtag_parity.py -v` (3 tests đọc trực tiếp 8 file live Excel, chạy giả lập 6.400 lượt upload trên toàn bộ 640 accounts, xác nhận 0 vi phạm invariant).

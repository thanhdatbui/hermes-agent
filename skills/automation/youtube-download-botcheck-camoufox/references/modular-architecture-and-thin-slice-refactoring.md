# Modular Architecture & Thin-Slice Refactoring for Downloader Pipeline

## 1. Structural Monolith Extraction (2026-10-15)
File `scripts/download_by_niche.py` (>1.900 dòng) được phân rã thành các module độc lập trong `scripts/downloader/`:
- `proxy.py`: Quản lý pool 69 proxy, format URL-encode auth, per-worker subpool rotation.
- `dedup.py`: `probe_duration` (ffprobe), `phash` (DCT 64-bit), `video_hashes`, `hash_similarity` (Hamming distance >= 0.95).
- `avatar.py`: `make_avatar_for_folder`, YOLO face/animal priority, 512x512 fallback.
- `language.py`: `has_vietnamese_text`, `metadata_score`, `audio_score` (Whisper), `audio_lang_cache.json`.
- `platforms.py`: Profile discovery TikTok/Instagram, TikWM API direct downloader.

## 2. Architecture Gate Test Invariant (Chống Tái Phình Monolith)
Để ngăn AI trong các phiên sau lại tiện tay nhét code vào file tổng:
- BẮT BUỘC duy trì `tests/test_downloader_architecture_gate.py`:
  1. Giới hạn cứng: `scripts/download_by_niche.py` <= 1.400 dòng. Vượt ngưỡng -> Test FAIL.
  2. Toàn bộ module trong `scripts/downloader/` phải tồn tại.
  3. Cấm định nghĩa lại các hàm domain (`format_proxy`, `phash`, `make_avatar_for_folder`, `audio_score`, `download_tiktok_direct`) trong file tổng.
- Khi có task sửa: Coordinator chỉ định rõ `FILE: scripts/downloader/<module>.py`, Worker Scope Lock chặn sửa lan man sang file tổng.

## 3. Quota & Context Optimization khi dùng Claude Haiku Worker
- Thêm cờ cho `claude -p`: `--no-session-persistence`, `--disable-slash-commands`, `--allowedTools "Read,Edit,Write,Bash"`, `--max-turns 6`.
- Bỏ qua việc đọc `AGENTS.md` / `PROJECT_RULES.md` (74KB) với task O(1) có file đích cụ thể để bóp nghẹt context từ 58k tokens xuống < 3k tokens.

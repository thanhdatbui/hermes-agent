# Claude Quota Cache Invalidation & Sonnet Review Timeout Discipline

## 1. Hiện Tượng Silent Fallback Tier 0 -> Tier 1 (Sol :20129)
- **Triệu chứng:** `closeout_gate.py` cấu hình Tier 0 là Claude Sonnet CLI (`claude -p - --model sonnet --effort high`), nhưng log hiển thị gọi OmniRoute `:20129` model `review` (Sol High), liên tục trả về `NEED_CONTEXT:<file>` hoặc điểm kẹt ở 69-77/100.
- **Nguyên nhân gốc rễ (Stale Quota Cache):**
  - Wrapper `claude_quota_guard.py` sử dụng cache cục bộ TTL 180s hoặc lịch sử quota cũ. Nếu phiên trước đó quota 5h đạt 100%, guard tiếp tục trả về exit code 20 (`BLOCK_5H`) dù phiên mới trên server Anthropic đã reset.
  - `closeout_gate.py` thấy lệnh `claude` exit != 0 nên âm thầm fallback xuống Tier 1 (OmniRoute Sol).
  - Sol High bị chặn bởi `sol_payload_guard.py` ở ngưỡng 37KB diff -> cắt cụt file test -> Sol báo `NEED_CONTEXT` vô tận.

## 2. Quy Trình Khắc Phục Nhanh O(1)
1. **Kiểm tra trạng thái quota:**
   ```bash
   python D:/Taadaa/tools/claude_quota_guard.py status
   ```
2. **Làm mới cache quota cưỡng bức (Zero Quota Cost):**
   - Lệnh `/usage` là lệnh miễn trừ (`is_exempt_command`):
   ```bash
   claude -p /usage
   ```
   - Lệnh này gửi probe trực tiếp lên server Claude, lấy tỷ lệ sử dụng thực tế và cập nhật lại `claude_quota_cache.json`.
3. **Xác nhận lại:**
   - Chạy lại `python D:/Taadaa/tools/claude_quota_guard.py status`, đảm bảo trạng thái chuyển sang `ALLOW`.

## 3. High-Effort Sonnet Review Timeout
- **Đặc tính:** Claude Sonnet CLI chạy với `--effort high` trên diff lớn (25KB - 35KB) mất từ 90s đến 140s để suy luận và xuất JSON scorecard đầy đủ.
- **Cạm bẫy:** Nếu `test_evidence_text` gửi kèm quá dài (ví dụ > 8KB test log) hoặc timeout trong wrapper đặt $\le 150$s, tiến trình có thể chạm ngưỡng timeout và trả về `None`, lại kích hoạt fallback không mong muốn xuống OmniRoute.
- **Biện pháp:**
  - Giữ test evidence ở dạng tổng hợp súc tích (`<passed> passed in <N>s`).
  - Đảm bảo timeout cho Sonnet review $\ge 180$s.

## 4. Nhận Diện Chuẩn Grace Band (80 - 84)
- Theo rubric trong `closeout_gate.py`:
  - Score $\ge 85$: `APPROVED`.
  - Score từ $80$ đến $84$: `APPROVED` (kèm cờ `grace_band = True` và `ready_to_close = True`).
- **Cấm kỵ:** Không được coi điểm 80-84 là thất bại rồi score-chasing vô tận hay tự ý phá vỡ gate bằng raw `git push`. Điểm Grace Band là ĐÃ ĐỦ ĐIỀU KIỆN đóng phiên an toàn.

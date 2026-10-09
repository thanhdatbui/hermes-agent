# Closeout Gate Reviewer Truncate Trap & GemPhone Clean-up (2026-09-19)

## 1. Bẫy Bỏ Qua Reviewer Chấm Điểm Khi Chốt Phiên (Root Cause & Fix)

### Hiện tượng & Phản xạ sai lầm
- Khi user nói "chốt phiên", Agent thường vội vã chạy `git add`, `git commit`, `git pull --rebase`, `git push` rồi báo cáo hoàn tất, hoàn toàn bỏ qua bước gọi Reviewer độc lập (`closeout_gate.py`) chấm điểm Scorecard 100đ.
- Khi user chất vấn: "Sao t bảo chốt phiên mà k có reviewer chấm điểm?", Agent mới giật mình nhận ra.

### Phân tích nguyên nhân gốc rễ (Audit bởi Claude Code CLI)
1. **Lỗi Truncate trong SKILL.md**:
   - File `session-close-protocol/SKILL.md` phình to >100KB. Khi agent gọi `skill_view`, runtime Hermes tự động truncate. Lệnh thực thi cốt lõi `python D:/Taadaa/tools/closeout_gate.py` bị đẩy xuống tận dòng 250+ và 450+, nằm hoàn toàn ngoài tầm nhìn của LLM.
2. **Cụm từ mơ hồ trong System Prompt**:
   - System prompt ghi phân vai: `chốt phiên (review/rebase/push)`. Cụm viết tắt này khiến LLM tự diễn giải "review" là tự mình xem lại git diff/git log của worker, sau đó nhảy thẳng sang rebase/push.
3. **Áp lực tránh conflict**:
   - Agent sợ stale lock hoặc lệch commit hash nên ưu tiên push nhanh để nhả lock.

### Giải pháp khắc phục (4-Layer Hard Guard)
1. **Top-20 Lines Invariant trong SKILL.md**:
   - Đưa khối lệnh thực thi lên ngay 20 dòng đầu tiên của `SKILL.md` trước mọi mục `References:`.
   ```bash
   python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --json-output
   ```
   - Điều kiện bắt buộc: Chỉ cho phép push khi `Verdict: APPROVED` (Score >= 85/100).
2. **Hard Rule trong SOUL.md**:
   - Ghi tường minh: `CANNOT PROCEED TO SESSION END WITHOUT closeout_gate.py EXIT CODE 0` với `Precedence: TỐI CAO`. Bao gồm danh sách alias: "chốt", "đóng phiên", "xong phiên", "done", "wrap up".
3. **Checklist 5 bước trong AGENTS.md từng repo**:
   - Bước 1: Pytest nội bộ.
   - Bước 2: `closeout_gate.py` đạt APPROVED >= 85đ.
   - Bước 3, 4, 5: Add, commit, rebase, push.
4. **Persistent Memory**:
   - Ghim vào bộ nhớ agent để inject vào 100% các phiên tương lai.

---

## 2. Bẫy Báo Động Giả Mất Phiên / Văng Account (GemPhone Artifact & Feed Captions)

### Hiện tượng
- Hệ thống bắn cảnh báo đỏ: `🚨 [BATCH ALERT: LỖI HỆ THỐNG] ... ⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện 1 máy dính lỗi login/xác minh: Máy M35: manual_challenge marker detected`.
- Kiểm tra thực tế: Máy 35 hoàn toàn bình thường, đang phát video For You Feed, đầy đủ 7/7 nick trong Switcher, không văng nick nào.

### Nguyên nhân kỹ thuật
1. **Tàn dư giả định GemPhone**:
   - Farm không hề chạy app GemPhone, nhưng trong `classifier.py` có đoạn code cũ kiểm tra `if "verify-bar-close" in resource_ids:`.
   - Kết hợp quét toàn màn hình tìm `manual_challenge_terms` ("xác minh", "kiểm tra bảo mật").
   - Khi video trên Feed có caption hoặc mô tả chứa từ "xác minh" (ví dụ: "video cần xác minh tài khoản"), logic tự gán nhãn `manual-needed:manual_challenge`.
2. **Gộp chung Auth Failure trong `batch_aggregator.py`**:
   - `batch_aggregator.py` gom chung từ khóa `verification`, `checkpoint` vào `AUTH_CRITICAL_KEYWORDS` cùng với `login`, `văng`, khiến lỗi challenge tạm thời bị thổi phồng thành cảnh báo P0 mất phiên.

### Chuẩn hóa khắc phục
1. **Dọn sạch code GemPhone**:
   - Xóa bỏ hoàn toàn khối `if "verify-bar-close" in resource_ids:` trong `python_runner/core/classifier.py`.
   - Xóa rule `verify_bar_close` khỏi `GEMPHONEFARM_BLIND_POPUP_RULES` trong `python_runner/flows/feed_swipe_smoke.py`.
2. **Feed Detail Controls Guard**:
   - Khi `_has_feed_detail_controls(elements)` là True (có nút like, comment, share, avatar...), tuyệt đối không gán nhãn `manual_challenge` hay `verification` chỉ vì chữ "xác minh" trong nội dung video.
3. **Phân loại 2 tầng trong `batch_aggregator.py`**:
   - `SESSION_LOST_KEYWORDS`: Chỉ dành cho lỗi mất phiên thật (`logged out`, `signed out`, `session expired`, `văng`, `login screen`, `account screen`).
   - `CHALLENGE_KEYWORDS`: Dành cho thử thách tạm thời (`verification`, `manual_challenge`, `checkpoint`, `captcha`), in rõ là `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`, cấm giật tít P0.

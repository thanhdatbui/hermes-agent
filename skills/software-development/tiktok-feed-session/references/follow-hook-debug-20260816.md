# Follow hook (multi-machine-feed-session → run_follow.py) — debug 2026-08-16

Kết quả canary máy 6 + bài học khi follow hook báo MANUAL_REVIEW sau feed session.

## Triệu chứng
Feed swipe chạy mượt (baseline for-you success, 19 swipe) → follow hook chạy → `follow_result.json`:
`status: MANUAL_REVIEW, reason: "exact profile identity không khớp sau tap"` (hoặc
`VERIFY_IDENTITY fail — nick không khớp @<tik_id>`). Dễ kết luận nhầm "máy login sai nick".

## Root cause thật (2 lớp)

### Lớp 1 — màn hình BẨN (dirty screen) do người debug để lại
Nếu trước đó có người/agent tap nhầm vào **profile từ tìm kiếm** (ví dụ `@longtuong10` — profile
NGƯỜI KHÁC, có nút "Nhắn tin" + gợi ý follow, KHÔNG có "Sửa hồ sơ"/dấu ≡), máy bị kẹt ở profile
đó → follow runner `switch_account_and_verify` không về được profile đúng nick → MANUAL_REVIEW.
**Lịch sử tìm kiếm (longtuong10, chungbich20...) là hành vi của chính run_follow.py (mode 1 search
nick để follow), không phải "ai đó tìm kiếm lung tung".**

### Lớp 2 — cách phân biệt profile chính chủ vs profile người khác (ảnh)
- **Chính chủ:** nút "Sửa hồ sơ" (bút) + dấu 3 gạch (Cài đặt) góc phải trên, KHÔNG có nút "Nhắn tin".
- **Người khác:** nút "Nhắn tin" + "Chia sẻ" + gợi ý tài khoản "Tài khoản được đề xuất", mũi tên quay lại.

## Quy tắc bắt buộc (user đính chính 16/08)
1. **Kiểm tra nick PHẢI qua account switcher / profile chính chủ** — không lấy kết quả tìm kiếm
   (profile người khác) rồi báo "sai acc".
2. **Reset màn hình sạch trước khi verify/chạy follow**: HOME → mở TikTok → chờ vào feed →
   vào profile chính chủ (tab "Hồ sơ" bottom). KHÔNG chạy follow khi màn hình còn kẹt profile tìm kiếm.
3. **Tọa độ nút trên máy thật**: dùng ATX `capture_ui_xml` lấy `bounds="[x1,y1][x2,y2]"` của node
   (text "Không cho phép"...) → tap trung tâm `((x1+x2)//2, (y1+y2)//2)`. Screencap trả 720×1280
   nhưng tọa độ tap là 1080×1920 — scale bằng bounds ATX, không dùng vision estimate.

## Follow runner subprocess — cách gọi ĐÚNG
`run_follow.py` import `follow_runner.core.*` → chạy script path thuần (`python .../run_follow.py`)
fail `ModuleNotFoundError: No module named 'follow_runner'` dù cwd đúng. Fix (commit `0fafc57`,
`multi_machine_feed_session.py::_run_follow_hook`):
```python
command = [python_exe, "-m", "follow_runner.run_follow",
           "--machine", str(machine), "--config", config,
           "--account-row-index", str(row_index)]
subprocess.run(command, capture_output=True, text=True, timeout=900,
               cwd=r"D:\Taadaa\tiktok-follow")
```
`--account-row-index` = **thứ tự row hợp lệ của máy (1-based)**, KHÔNG phải row tuyệt đối workbook.

## Follow chạy ĐƯỢC rồi — mode 2 fail "hồ sơ thiếu handle"
Khi màn hình sạch: mode 1 (search follow) follow 8 nick OK (`thu.trangg584`, ...), mode 2
(follow followers) fail `MANUAL_REVIEW: "hồ sơ thiếu handle (@uid) — từ chối tap Follower"` =
nick bị follow có profile không hiện @uid → runner từ chối tap (an toàn). Mode 1 đã đạt mục tiêu
3-7 follow/phiên → mode 2 fail KHÔNG phải lỗi block.

## Device lock — rule user 16/08 (đã xoá toàn bộ cơ chế)
- Commit `bdf5a5b` xoá `_prior_target_evidence`, `_write_recovery_handoff_evidence`, DEFERRED_LOCKED,
  lock aliases khỏi `multi_machine_feed_session.py` (~270 dòng).
- **Lock CHỈ khi user yêu cầu** → giữ vĩnh viễn; **chạy success → mới mở**. KHÔNG auto-lock,
  KHÔNG auto-skip máy fail lần trước (máy fail tự chạy lại mỗi cron).
- Nếu gặp `NameError: device_lock_paths is not defined` sau khi xoá — đó là bug pre-existing
  (file dùng hàm không import), KHÔNG phải cần khôi phục lock.

## Popup TikTok phân loại (user chốt 16/08)
- **Popup app = cấp quyền / gợi ý add số** (location/contacts/notification permission,
  add-phone "Thêm số điện thoại") → **core** (`automation_core/tiktok_popup.py` + `benign_popup.py`).
- **Popup CTA mua hàng** ("Mua ngay", shop CTA khi lướt feed) → **repo consumer**
  (`feed_swipe_smoke.py` `shop_cta_close`...). Tên `gemphonefarm_blind_popup` là tên cũ/lịch sử —
  xử lý popup TikTok, không phải GemPhoneFarm.
- Core `contacts_permission_vi` marker cần match text thiếu "tiktok": "cho phép truy cập vào danh bạ"
  (không phải "cho phép tiktok truy cập...") — patch marker thêm biến thể.

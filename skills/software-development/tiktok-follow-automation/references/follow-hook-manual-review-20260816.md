# Follow hook MANUAL_REVIEW sau feed session — debug máy 6 (2026-08-16)

Triệu chứng: feed swipe chạy mượt (baseline for-you success, 19 swipe) → follow
hook (`multi_machine_feed_session.py::_run_follow_hook` subprocess `run_follow.py`)
trả `follow_result.json`:
`status: MANUAL_REVIEW, reason: "exact profile identity không khớp sau tap"`
(hoặc `VERIFY_IDENTITY fail — nick không khớp @<tik_id>`).

## Root cause LỚP 1 — màn hình BẨN (dirty screen) do debug để lại
Trước đó có tap nhầm vào **profile từ TÌM KIẾM** (VD `@longtuong10` — profile NGƯỜI
KHÁC: có nút "Nhắn tin" + "Tài khoản được đề xuất" + mũi tên quay lại, KHÔNG có
"Sửa hồ sơ"/dấu ≡) → máy kẹt ở profile người khác → follow runner
`switch_account_and_verify` không về được profile đúng nick → MANUAL_REVIEW.
**KHÔNG phải máy login sai nick.**

Phân biệt profile (bằng ảnh):
- **Chính chủ:** "Sửa hồ sơ" (bút) + dấu 3 gạch (Cài đặt) góc phải trên, tab Hồ sơ
  `selected=True`, KHÔNG có "Nhắn tin".
- **Người khác:** "Nhắn tin" + "Chia sẻ" + "Tài khoản được đề xuất" + mũi tên quay lại.

**Lịch sử tìm kiếm (longtuong10, chungbich20, hatien15118...) = hành vi của chính
run_follow.py (mode 1 search nick để follow), KHÔNG phải "ai đó tìm kiếm lung
tung"** — đừng báo user "máy bị điều khiển từ xa".

## Quy tắc bắt buộc (user đính chính 16/08 — bắt buộc)
1. **Kiểm tra nick PHẢI qua account switcher / profile chính chủ** — không lấy kết
   quả tìm kiếm rồi báo "sai acc". User chửi thẳng khi agent làm vậy.
2. **Reset màn hình sạch trước khi verify/chạy follow**: HOME (keyevent 3) → mở
   TikTok → chờ vào feed → tab "Hồ sơ" (bottom right). KHÔNG chạy follow khi màn
   hình còn kẹt profile tìm kiếm.
3. **Tọa độ nút thật bằng ATX bounds, không vision estimate**: `capture_ui_xml`
   lấy `bounds="[x1,y1][x2,y2]"` của node (text "Không cho phép"...) → tap tâm
   `((x1+x2)//2, (y1+y2)//2)`. Screencap trả 720×1280 nhưng tọa độ tap là
   1080×1920 — scale bằng bounds ATX, KHÔNG dùng vision pixel estimate (đã tap
   trật 3 lần).

## Subprocess gọi follow runner — fix `-m` + cwd (commit `0fafc57`)
`run_follow.py` import `follow_runner.core.*` → chạy script path thuần
(`python .../run_follow.py`) fail `ModuleNotFoundError: No module named
'follow_runner'` DÙ cwd đúng (cwd không vào sys.path khi chạy script path). Fix:
```python
command = [python_exe, "-m", "follow_runner.run_follow",
           "--machine", str(machine), "--config", config,
           "--account-row-index", str(row_index)]
subprocess.run(command, capture_output=True, text=True, timeout=900,
               cwd=r"D:\Taadaa\tiktok-follow")
```
`--account-row-index` = **thứ tự row hợp lệ của máy (1-based)** — xem skill chính.

## Follow chạy ĐƯỢC rồi — mode 2 fail "hồ sơ thiếu handle"
Khi màn hình sạch: mode 1 (search follow) follow 8 nick OK (`thu.trangg584`,
`nhathasz4vw`, `th.thy081`, `taquynh0601`, `phanlan097`, `tongly2009`,
`quch.trangg`, `phannhung1710`), mode 2 (follow followers) fail
`MANUAL_REVIEW: "hồ sơ thiếu handle (@uid) — từ chối tap Follower"` = nick bị
follow có profile không hiện @uid → runner từ chối tap (fail-closed an toàn).
Mode 1 đã đạt 3-7 follow/phiên → mode 2 fail KHÔNG phải lỗi block session.

## Follow chạy lâu — đừng timeout 180s
Follow thật (mode both) chạy 8-15 phút (search + follow + verify từng UID).
Test trực tiếp qua terminal với `timeout=900` + background, KHÔNG 180s (bị kill
giữa chừng → máy kẹt SplashActivity + màn bẩn). Kill giữa chừng để lại app ở
trạng thái lạ — phải force-stop + relaunch sau đó.

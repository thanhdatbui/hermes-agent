# Follow hook + ATX-primary + verify nick (16/08, canary máy 6)

Bài học từ canary máy 6 sau khi implement plan 3 ca × 3 phiên + follow hook.

## 1. ATX-primary cho get_focused_activity (commit 1a33a14)

**Triệu chứng:** canary báo `manual-needed: capture-invalid` / kẹt SplashActivity dù ảnh thật cho thấy feed đã render (video MMA đang chạy, tab Đề xuất). `dumpsys window` báo `SplashActivity` trong khi UI thật là feed — TikTok giữ activity cũ nhưng render feed bên trong (S7/Android 7, RAM 3.6GB).

**Fix (observe.py `get_focused_activity`):**
```python
def get_focused_activity(ctx, *, retries=2, retry_delay=0.5):
    # ATX-primary: capture_ui_xml đọc UI qua atx-agent (port 7912) — XML tươi
    try:
        from automation_core.ui import capture_ui_xml
        from automation_core.ui_capture import ProvisioningPolicy
        cap = capture_ui_xml(ctx.adb, timeout=ctx.timeout("adb_seconds", 15),
                             retries=1, retry_delay_seconds=0.8,
                             provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED)
        if cap is not None and cap.xml and "<hierarchy" in cap.xml:
            pkg_match = re.search(r'package="([^"]+)"', cap.xml)
            if pkg_match:
                package = pkg_match.group(1)
                act_match = re.search(r'package="[^"]+"[^>]*class="([^"]+)"', cap.xml)
                return {"package": package, "activity": act_match.group(1) if act_match else None}
    except Exception:
        pass
    # dumpsys fallback (giữ nguyên)
    ...
```
Verify thật: `get_focused_activity` trả `{'package': 'com.ss.android.ugc.trill', 'activity': None}` (từ XML) thay vì SplashActivity sai. Canary sau fix: lướt 19 swipe SUCCESS.

## 2. Verify nick máy — CHỈ qua profile chính chủ / account switcher

- **Profile chính chủ** (nick đang login): có nút "Sửa hồ sơ" (biểu tượng bút) + dấu ≡ (Cài đặt & Quyền riêng tư) + tab "Tôi" active ở bottom nav.
- **Profile người khác** (xem từ search): có nút "Nhắn tin" (paper plane) + mũi tên ← (back) + nút Chia sẻ — KHÔNG có "Sửa hồ sơ".
- Sai lầm đã mắc: tap nhầm vào profile search → thấy nick `longtuong10` (row 347 máy 58 trong workbook) → tưởng "máy 6 login sai nick" → báo sai acc → user bức xúc.
- **Rule:** trước khi verify nick hoặc chạy follow: RESET màn hình sạch (force-stop + monkey launch + chờ feed), rồi vào profile chính chủ (tap tab Hồ sơ cuối bottom nav ~y1800 không phải 2300 — nav bar hệ thống chiếm đáy).

## 3. Lịch sử tìm kiếm / profile nick lạ = tiktok-follow đang chạy

- Lịch sử search (longtuong10, chungbich20, hatien15118...) trên máy = mode 1 search-follow đang/chạy tìm nick để follow chéo — **KHÔNG phải acc bị hack**.
- Kiểm tra process python trước khi kết luận: `ps aux | grep -i python` / `wmic process where "name='python.exe'" get ProcessId,CommandLine`.
- follow_result.json `MANUAL_REVIEW: exact profile identity không khớp` = màn hình kẹt profile search (do verify trước đó để lại) → follow verify nhìn nhầm — KHÔNG phải nick máy sai.

## 4. Follow hook — mode 1 ONLY + cwd đúng

- Config `mode: "1"` (không "both"): mode 2 (follow followers) fail `hồ sơ thiếu handle (@uid) — từ chối tap Follower` — bỏ, mode 1 đã đủ 5-10 follow/phiên.
- Subprocess phải chạy `python -m follow_runner.run_follow` với `cwd=r"D:\Taadaa\tiktok-follow"` — script path trực tiếp (`follow_runner/run_follow.py`) lỗi `ModuleNotFoundError: No module named 'follow_runner'` vì import `follow_runner.core.*` cần package root trong path.
- State/dedupe: `runs/state/follow_state_<machine>.json` (cwd=tiktok-follow → `D:\Taadaa\tiktok-follow\runs\state\`). `budget_per_session_min/max` 5-10 random, `budget_per_day` 30, dedupe nick đã follow.
- Nguồn UID = toàn bộ nick safe workbook (follow chéo trong farm — đúng thiết kế).

## 5. Popup phân loại (user xác nhận)

- Popup cấp quyền (location/contacts/notification) + gợi ý add số điện thoại → **automation-core** (`tiktok_popup.py` rules + `benign_popup.py` detect_add_phone_popup).
- Popup CTA mua hàng ("Mua ngay", shop banner xuất hiện khi lướt feed) → **repo consumer** (`feed_swipe_smoke.py` `GemPhoneFarmBlindPopupRule` — tên legacy, thực chất popup TikTok).
- 16/08: popup contacts in-app text "Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ..." KHÔNG match marker cũ `"cho phép tiktok truy cập vào danh bạ"` (thiếu "tiktok" giữa). Fix core commit `35b2160`: tách 2 rule `contacts_permission_vi` ("truy cập vào danh bạ") + `contacts_permission_vi_connect` ("kết nối với những người bạn biết") — marker tuple = AND nên không gộp 2 cụm vào 1 rule.

## 6. Tỉ lệ lướt/like/follow theo tab (mặc định)

| Tab | Lướt | Like | Follow |
|---|---|---|---|
| Đề xuất (For You) | 98% | 12% | 6% |
| Following | 2% | 7% | 0 |
| Friends | 0% | 2% | 0 |

Friends = follow lẫn nhau (mutual) → follow 0% đúng (đã follow sẵn). Following cũng đã follow → 0% đúng.

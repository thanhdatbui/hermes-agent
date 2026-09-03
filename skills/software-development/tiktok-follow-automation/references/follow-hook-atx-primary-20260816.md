# Follow hook + ATX-primary get_focused_activity (2026-08-16, canary máy 6)

## Bối cảnh
Canary máy 6 với code mới (3 ca × 3 phiên + follow hook + max_workers 30) liên tục
manual-needed vì TikTok "kẹt splash". Điều tra sâu phát hiện 2 lỗi gốc riêng biệt.

## Lỗi 1: `get_focused_activity` tin dumpsys window → báo SplashActivity sai

- Triệu chứng: `dumpsys window` báo `com.ss.android.ugc.trill/SplashActivity` trong khi
  **màn hình thật đã render feed** (screencap thấy video đang chạy). TikTok không chuyển
  activity khi feed render → activity window cũ vẫn giữ focus.
- `get_focused_activity` (flows/observe.py:39) trước đây chỉ chạy `dumpsys window` +
  `dumpsys activity` → trả SplashActivity mãi → flow tưởng kẹt splash → manual-needed.
- **Fix (commit `1a33a14`)**: ATX-primary — gọi `automation_core.ui.capture_ui_xml`
  (persistent atx-agent port 7912) trước; XML tươi có `<hierarchy` → parse `package=`
  từ XML (package TikTok thật) → trả về; dumpsys chỉ là fallback. Verified: máy 6
  kẹt splash theo dumpsys nhưng ATX trả `package=com.ss.android.ugc.trill` (feed thật).
- Kỹ thuật parse: `re.search(r'package="([^"]+)"', xml)` lấy package đầu tiên; activity
  lấy từ `class=` nếu có. Cả hàm bọc try/except → ATX fail rơi xuống dumpsys.

```python
def get_focused_activity(ctx, *, retries=2, retry_delay=0.5):
    # ATX-primary: capture_ui_xml qua atx-agent (port 7912)
    try:
        from automation_core.ui import capture_ui_xml
        from automation_core.ui_capture import ProvisioningPolicy
        cap = capture_ui_xml(ctx.adb, timeout=15, retries=1, retry_delay_seconds=0.8,
                             provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED)
        if cap is not None and cap.xml and "<hierarchy" in cap.xml:
            pkg_match = re.search(r'package="([^"]+)"', cap.xml)
            if pkg_match:
                return {"package": pkg_match.group(1), "activity": None}
    except Exception:
        pass
    # fallback: dumpsys window / activity
    ...
```

## Lỗi 2: follow hook subprocess `ModuleNotFoundError: follow_runner`

- Hook gọi `run_follow.py` bằng đường dẫn script tuyệt đối (`D:\Taadaa\tiktok-follow\follow_runner\run_follow.py`) với cwd là worktree nuôi acc → `import follow_runner.core.adapter` fail vì `D:\Taadaa\tiktok-follow` không nằm trong sys.path.
- **Fix (commit `0fafc57`)**: chạy dạng module + đúng cwd:
  `python -m follow_runner.run_follow --machine N --config ... --account-row-index R` với `cwd=r"D:\Taadaa\tiktok-follow"`. `-m` làm cwd thành root package → import resolve.

## Follow hook chạy đủ lượt (mode 1)
- Sau khi config `mode: "1"` (bỏ mode 2), follow hook chạy đủ budget: mode 1 loop tới
  `state.session_budget()` (random 5-10), nguồn UID = toàn bộ safe workbook cột ID.
- State: `runs/state/follow_state_<máy>.json` (cwd tiktok-follow → `D:\Taadaa\tiktok-follow\runs\state\`).
  Dedupe theo UID + `budget_used`/`budget_date` — budget 30/ngày.
- FOLLOW_RESULT stdout: `{"machine", "status", "reason", "followed", "skipped", "failed_ids", "failed", "details"}` — exit 0 = OK.

## Popup contacts permission — 2 biến thể marker (commit `35b2160` core)
- Popup máy 6 in-app: "Để kết nối với những người bạn biết trên TikTok, hãy cho phép
  truy cập vào danh bạ..." — marker cũ `"cho phép tiktok truy cập vào danh bạ"` KHÔNG
  match (thiếu "tiktok" giữa "cho phép" và "truy cập").
- System dialog (packageinstaller): "Cho phép TikTok truy cập vào danh bạ của bạn?" —
  có "TikTok" giữa.
- Fix: 2 rule riêng, mỗi rule 1 marker (AND trong 1 rule sẽ fail vì text khác nhau):
  - `contacts_permission_vi`: `("truy cập vào danh bạ",)` — match cả 2
  - `contacts_permission_vi_connect`: `("kết nối với những người bạn biết",)`
  - Cả 2 đều TAP nút TỪ CHỐI/Không cho phép; thêm tên mới vào set `_find_button` candidates.

## ATX bounds thay vì vision estimate (tap chính xác)
- Vision ước lượng tọa độ nút trên ảnh scale (720×1280 vs màn hình thật 1080×1920) → tap trật.
- Dùng ATX XML bounds thật: `re.finditer(r'<node[^>]*text="Không cho phép"[^>]*bounds="(\[[^"]+\])"', xml)`
  → `[120,1156][539,1299]` → center (329, 1227) — tap đúng 1 phát.

## Không timeout follow thật 180s
- Follow mode 1 + mode 2 chạy thật 8-15 phút (canary máy 6: follow 8 nick ~9 phút).
  Timeout 180s kill giữa chừng → app kẹt splash + search history để lại. Để follow
  chạy đủ (timeout 900s+) hoặc chạy background.

# ATX-primary get_focused_activity — hết "kẹt splash" giả (2026-08-16)

## Triệu chứng
Canary máy 6: `manual-needed` / `capture-invalid` liên tục dù TikTok thực sự đã vào
feed. `dumpsys window` báo `SplashActivity` nhưng screencap thật cho thấy video feed
đang chạy (VD video MMA "Nate Smith", tab Đề xuất). **TikTok không chuyển activity
khi feed render** → activity window cũ (SplashActivity) vẫn là mCurrentFocus → flow
tin dumpsys → tưởng kẹt splash → manual-needed.

## Root cause
`get_focused_activity` (python_runner/flows/observe.py:39) chỉ chạy `dumpsys window`
+ `dumpsys activity`. Trên máy yếu (S7/SM-G930, RAM 3.6GB) TikTok render feed trong
activity cũ → dumpsys lệch với UI thật.

## Fix (commit `1a33a14`, worktree phase9-authority)
ATX-primary: gọi `automation_core.ui.capture_ui_xml` (persistent atx-agent port 7912)
TRƯỚC. XML tươi có `<hierarchy` → parse `package=` đầu tiên → trả package thật
(TikTok). dumpsys giữ làm fallback. Verified máy 6: dumpsys báo SplashActivity nhưng
ATX trả `package=com.ss.android.ugc.trill` (feed thật) — canary sau đó SUCCESS 19 swipe.

```python
def get_focused_activity(ctx, *, retries=2, retry_delay=0.5):
    try:
        from automation_core.ui import capture_ui_xml
        from automation_core.ui_capture import ProvisioningPolicy
        cap = capture_ui_xml(ctx.adb, timeout=ctx.timeout("adb_seconds", 15),
                             retries=1, retry_delay_seconds=0.8,
                             provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED)
        if cap is not None and cap.xml and "<hierarchy" in cap.xml:
            pkg_match = re.search(r'package="([^"]+)"', cap.xml)
            if pkg_match:
                return {"package": pkg_match.group(1), "activity": None}
    except Exception:
        pass
    # fallback dumpsys window / activity (như cũ)
```

## Pitfalls
- **Đừng tin dumpsys window khi nghi kẹt splash** — chụp screencap + xem ảnh thật trước
  khi kết luận "máy kẹt". User từng bắt lỗi: "ảnh đang ở feed mà?" khi agent báo kẹt splash.
- ATX fail phải rơi xuống dumpsys (máy không atx-agent vẫn chạy) — không raise.
- `capture_ui_xml` cần `ProvisioningPolicy.REQUIRE_PROVISIONED` (máy có atx-agent).
- Test mock: test cũ mock `_exec_out`/`shell` sẽ lệch vì ATX chạy automation_core THẬT
  trước loop → `monkeypatch.setattr(module, "_atx_capture_ui_xml", lambda *a, **k: None)`.

## Liên quan
- Popup contacts máy 6 in-app ("Để kết nối với những người bạn biết...") không match
  marker core cũ → fix 2 rule riêng (commit `35b2160` core) — chi tiết trong
  `tiktok-follow-automation/references/follow-hook-atx-primary-20260816.md`.
- Xoá device-lock/handoff (commit `bdf5a5b`): lock chỉ khi user yêu cầu, success mới mở
  — máy fail lần trước tự chạy lại, không skip prior-evidence.

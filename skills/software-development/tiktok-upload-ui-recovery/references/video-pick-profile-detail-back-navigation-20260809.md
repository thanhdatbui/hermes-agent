# Video-pick profile-detail back navigation — m74 live spike (2026-08-09)

## Bối cảnh
Batch Tik1 24 máy (ít video nhất) fail **4 lần** cùng signature `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` / `VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET` / `OPEN_TIKTOK_FAILED` — mỗi lượt patch mù vào 1 nguyên nhân vẫn fail toàn bộ:

| Lượt | Patch | Kết quả |
|---|---|---|
| 1 | fix coordinate fallback gọi lần 2 → gọi cùng lần | vẫn fail: `_find_video_pick_create_entry_point` trả None |
| 2 | display baseline từ `wm size` + fixture root node | vẫn fail: verifier không nhận caption composer |
| 3 | verifier thêm marker `thêm mô tả`+`đăng` (m46 evidence) | vẫn fail: máy đứng profile **detail**, navigate không xử lý |
| 4 | **SPIKE 1 máy** → tìm ra detail surface → fix back-navigation | 375 test green |

## Spike live máy 74 (serial ce061606c21e153d03)

Trạng thái ban đầu (run 23:45 fail để lại):
- `uiautomator dump` exit **137** toàn farm (kể cả probe tay) → **ATX kill** (`pkill -f atx-agent` + `pkill -f com.github.uiautomator`) → dump OK (skill §2 tầng 1).
- `mCurrentFocus=SplashActivity` stale dù feed thật đã render (skill §14).
- Dump profile detail: `Hồ sơ Mỹ Duyên`, back node `content-desc="Quay lại"` resource `com.ss.android.ugc.trill:id/bov` bounds `[18,72][174,228]`, `0 lượt xem`, `Cài đặt quyền riêng tư`, tabs Video/Phát; **không có bottom-nav create node**.

Ladder tay (từng bước recapture):
1. **Back** (96,150) → Profile root: bottom nav đầy đủ `Trang chủ`/`Cửa hàng`/`Quay`/`Hộp thư`/`Hồ sơ`; create node `resource-id o3c` content-desc `Quay` clickable `[432,1794][648,1920]` (chính là node evidence m74 cũ).
2. **Tap Trang chủ** (108,1857) → **Feed**: `Đề xuất`, `Bạn bè`, `Đã follow`, search bar.
3. **Tap Quay** (540,1857) → **Composer MỞ**: dump có `x7f` ×9, `x7d` ×9, `cyb`, `yfi` + texts `Thêm âm thanh`/`ẢNH`/`VĂN BẢN`/`AI SELF`/`CAMERA`/`MẪU`/`LIVE`/`Lật`/`Flash`/`Hẹn giờ`/`Bố cục`/`Tỷ lệ`/`Làm đẹp`/`Đã chọn`.

→ Coordinate (540,1857) từ **Feed** mở composer OK; từ **Profile/DETAIL** không (không có navbar). Đây là proof quyết định.

## Fix (code SỐNG, 375 test green, diff sạch)

```python
@classmethod
def _is_video_pick_profile_detail_surface(cls, xml_text: str) -> bool:
    # có back node "Quay lại" + KHÔNG có create-entry point + lượt xem/privacy
```

Nhánh mới trong `_navigate_video_pick_to_feed` (trước action-sheet block):
1. `_is_video_pick_profile_detail_surface` → `adapter.back()` 1 lần → sleep 1 → re-dump → nếu feed surface → return.
2. Không phải feed → fall qua nhánh action sheet + home-tab tap thường (Trang chủ / Đề xuất / For You).

Regression tests:
- `test_video_pick_profile_detail_surface_classifier_live_m74` (detail → True; root có o3c → False; feed → False; empty → False).
- `test_video_pick_create_composer_classifier_accepts_caption_composer_live_m46` (Thêm mô tả + Đăng/Hashtag/Nhắc đến → True; thiếu marker → False).

## Quy trình chuẩn khi batch fail đồng loạt exit 2 cùng signature

1. **KHÔNG patch mù từng cái** — probe 1 máy thật: ATX kill → `uiautomator dump` → `screencap` → pixel ratios (white/dark/red) → `vision_analyze` (hoạt động khi key resolve; 401 thì pixel stats + UI dump markers).
2. Đi hết ladder tay trên máy đó (Back → về root → về feed → tap create), recapture sau mỗi bước — tìm đúng surface mà worker đang kẹt.
3. Fix 1 lần đúng + regression test + full suite + EOL check + COMPAT entry.
4. Dọn lock handoff (machine + serial alias, pid-dead bằng WMIC `/format:list`, chỉ tin commandline python/tiktok thật) → relaunch batch với `-AssignmentManifest` + `-WorkerId` == owner_id.

## Chống trùng video (user hỏi, đã verify trong code)
- `is_video_already_posted(next_video)` (state_machine.py:1929) → raise `VIDEO_ALREADY_POSTED` fail-closed nếu video ≤ `Video Đã Đăng`.
- Video push chưa đăng thành công (`post_submission_state=None`) chưa tính vào workbook → chạy lại đăng chính nó, không trùng.
- Đã đăng (ACCEPTED) → hậu kiểm, không retry (skill §7).

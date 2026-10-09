# Case UI-75: Bẫy Optimistic UI Follow Giả & Nạp TikTok 47.0.3 Split Dex An Toàn

## 1. Bối cảnh & Phát hiện bước ngoặt
- **Bẫy "Follow giả" (Optimistic UI / RelationCache):**
  - Khi bấm Follow (trên Video Player, trên Profile hay trên dòng Search), app TikTok client ngay lập tức ghi vào bộ nhớ RAM `status = FOLLOWED` và đổi icon sang "Nhắn tin" / "Đã follow" để trải nghiệm người dùng mượt mà.
  - Tuy nhiên, nếu tài khoản đang bị cờ Rate-limit / Shadowban / Nhả follow ngầm, server TikTok âm thầm rollback.
  - Vì Activity Stack (Search / Profile) vẫn cache trong RAM, nên dù back ra màn hình Search hay back về Profile thì app VẪN HIỂN THỊ NÚT XÁM "ĐÃ FOLLOW" GIẢ!
  - **Chỉ khi:** Ép reload dữ liệu từ server (Pull-to-refresh hoặc Re-entry mở lại Profile từ server) thì nút đỏ "Follow lại" mới bật ngược trở lại.

## 2. Thẩm định Kiến trúc Sol (GPT-5.6 Sol High): Phối hợp Phá Cache Tự Nhiên
- **Pull-to-refresh (80%):**
  - Cử chỉ tự nhiên, không làm biến dạng đồ thị điều hướng (Navigation Graph).
  - BẮT BUỘC thêm **Jitter Biometrics** (lệch X +-25px, lệch Y1/Y2, duration 500-750ms), CẤM dùng tọa độ cứng cố định 100 lần như 1.
- **Natural Re-entry (20%):**
  - Back ra Search results rồi tap card vào lại Profile. Dùng như cơ chế bổ trợ để phá tính đơn điệu của thuật toán.
- **Fail-Closed khi nút đỏ bật lại:**
  - Nếu sau reload nút vẫn là `not_followed` (màu đỏ) -> Kích hoạt ngay `state.set_follow_failed()`, dừng ca chạy và đưa máy vào Cooldown.

## 3. Selector Drift TikTok 46.9.3 & 47.0.3
- TikTok 46.9.3: gom nút Follow/Nhắn tin vào `id/fm9`.
- TikTok 47.0.3: đổi sang `id/fmp`.
- Whitelist `_ACTION_BUTTON_SUFFIXES` trong `verify_follow.py` bắt buộc phải có cả:
  `":id/fm9", "id/fm9", ":id/fmp", "id/fmp"`.
- Thiếu ID này sẽ khiến nút Follow đỏ bị bỏ qua, trong khi nút "Nhắn tin" lọt qua marker -> Runner nhận định sai thành `followed` trong khi nút đỏ vẫn còn nguyên!

## 4. Quy trình nạp Split Dex TikTok 47.0.3 trên Samsung S7 (Android 8)
- Gói TikTok 47.0.3 có file bytecode chính `split_df_a_dex.apk` (83.8MB). Nếu cài thiếu file này, app sẽ crash ngay khi mở (`ClassNotFoundException: Didn't find class`).
- Khi nạp qua ADB trên dàn farm S7:
  1. Push file 83.8MB vào `/data/local/tmp/split_df_a_dex.apk` với timeout rộng (300-500s) vì bus USB chia sẻ tốc độ ~0.3-0.5 MB/s.
  2. Tạo session cài đặt: `sid=$(pm install-create -r -d -p com.ss.android.ugc.trill)`.
  3. Ghi split: `pm install-write -S 83814343 $sid split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk`.
  4. Commit session: `pm install-commit $sid`.
  5. Chờ tiến trình `dex2oat` tối ưu bytecode (mất 30-90s trên Samsung S7) trước khi app có thể mở trơn tru.
  6. Khóa tự động cập nhật của Play Store: `settings put global auto_update_apps 0` để cố định môi trường toàn farm.

## 5. Code Implementation Contract (Đã kiểm chứng trong tiktok-follow)

### 5.1. `follow_runner/flows/verify_follow.py`: Whitelist Action Suffixes
```python
_ACTION_BUTTON_SUFFIXES = (
    ":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/flo", ":id/flp", ":id/fm9", ":id/fmp", ":id/follow_button",
    "id/fds", "id/ff8", "id/fij", "id/fi6", "id/flo", "id/flp", "id/fm9", "id/fmp", "id/follow_button",
)
```

### 5.2. `follow_runner/core/adapter.py`: Pull-to-refresh với Jitter Biometrics
```python
def pull_to_refresh_profile(adapter: FollowAdapter, sleep_after: float = 3.5,
                           xml_text: str | None = None) -> bool:
    """Kéo từ trên xuống (Pull-to-refresh) trên trang profile để reload lại giao diện thật.
    Thêm Biometric Jitter chống bot-pattern fingerprint.
    """
    size = _screen_size(adapter, xml_text)
    if size is None:
        w, h = (1080, 1920)
    else:
        w, h = size
    cx = (w // 2) + random.randint(-25, 25)
    y1 = int(h * 0.35) + random.randint(-30, 30)
    y2 = int(h * 0.78) + random.randint(-40, 40)
    duration = random.randint(500, 750)
    try:
        adapter.swipe(cx, y1, cx, y2, duration)
        time.sleep(sleep_after)
        return True
    except FollowAdapterError:
        return False
```

### 5.3. `follow_runner/flows/mode1_search_follow.py`: Hybrid Reload Profile (80% Refresh / 20% Re-entry)
```python
def _reload_profile(engine, uid: str) -> bool:
    """Reload để phá Optimistic UI Cache và lấy trạng thái server thật.
    Phối hợp tự nhiên (Sol Approved):
    - 80%: Pull-to-refresh có jitter tại chỗ (an toàn nhất, không tạo navigation loop).
    - 20%: Re-entry (back ra Search results rồi tap card vào lại).
    """
    adapter = engine.adapter
    from ..core.adapter import pull_to_refresh_profile
    use_re_entry = random.uniform(0.0, 1.0) <= 0.20
    if not use_re_entry:
        try:
            return pull_to_refresh_profile(adapter, sleep_after=random.uniform(3.0, 4.5))
        except Exception:
            pass

    # Re-entry path (20% hoặc fallback khi pull-to-refresh không khả dụng)
    try:
        adapter.press_back()
        time.sleep(1.5)
        node = _wait_search_result(adapter, uid, timeout=12)
        if node is None:
            current_xml = adapter.dump_ui()
            user_tab = _find_unselected_users_tab(current_xml)
            if user_tab is not None:
                tap_center(adapter, user_tab)
                time.sleep(2)
                node = _wait_search_result(adapter, uid, timeout=12)
        if node is None:
            return False
        tap_center(adapter, node)
        time.sleep(2)
        return True
    except FollowAdapterError:
        return False
```

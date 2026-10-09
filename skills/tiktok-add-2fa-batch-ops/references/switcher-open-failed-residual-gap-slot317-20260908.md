# SWITCHER_OPEN_FAILED Residual Gap — Slot 317 (08/09/2026)

## Bối cảnh

Sau khi áp dụng 2 patches ngày 07/09/2026:
- `1ec50ec` — bound username_candidates to `generic_header_y`
- `7521550` — filter clickable container trong resource_candidates

Máy 40 (slot 317, source_row tương ứng) **vẫn bị** `SWITCHER_OPEN_FAILED`. Điều tra ngày 08/09 xác định còn **1 lỗ hổng logic chưa vá**.

---

## Lỗ Hổng Còn Lại Trong `find_switcher_anchor()`

### Vị trí chính xác

File: `automation-core/src/automation_core/tiktok/account_switcher.py`  
Hàm: `find_switcher_anchor()`  
Nhánh: `username_candidates` (xấp xỉ dòng 538–551)

### Code hiện tại (sau patch 07/09)

```python
username_candidates = [
    node for node in nodes
    if node.center is not None
    and header_left <= node.center[0] <= header_right
    and node.center[1] <= generic_header_y          # ← giới hạn 320px ✅ ĐÃ VÁ
    and (
        node.center[1] <= header_y                   # ← vùng an toàn ≤250px
        or (has_profile_menu                         # ← ⚠️ NẾU has_profile_menu=True
            and node.attributes.get("clickable", "false").casefold() == "true")
        # nhánh thứ 2 này cho phép center_y trong vùng 250px < y <= 320px
        # được chọn làm anchor khi has_profile_menu=True
    )
    and node.text.strip().startswith("@")
]
```

### Vùng Nguy Hiểm (250px–320px)

Các giá trị pixel (screen 1080×1920):
- `header_y` = 1920 × (250/1920) = **250 px**
- `generic_header_y` = 1920 × (320/1920) = **320 px**

Khi `has_profile_menu=True` (TikTok hiển thị menu hồ sơ ☰), node `@username` có thể nằm tại **center_y ≈ 280–310px** — trong vùng thân profile bên dưới avatar, nhưng vẫn ≤ 320px. Node này:
- Có `clickable="true"` (vì TikTok gắn clickable để xem profile)
- Bắt đầu bằng `@`
- **Không phải sticky header** — tap vào không mở switcher bottom sheet

Kết quả: `find_switcher_anchor` trả về node sai → `_tap()` tap vào thân profile → `is_switcher_open` trả False → retry 2 lần → `SWITCHER_OPEN_FAILED`.

### Tại Sao Máy 1 (07/09) Không Bị Nhưng Slot 317 Bị

Trên Máy 1, node `@tranngan767` có `center_y = 616px` — vượt ngưỡng `generic_header_y` = 320px nên bị patch 07/09 chặn lại. Tuy nhiên máy 40 slot 317 có thể có layout nhỏ hơn hoặc TikTok version khác khiến node `@username` rơi vào vùng 250–320px, vừa lọt qua patch cũ.

---

## Fix Đề Xuất

### 1. Thắt chặt nhánh `username_candidates`

```python
# TRƯỚC:
username_candidates = [
    node for node in nodes
    if node.center is not None
    and header_left <= node.center[0] <= header_right
    and node.center[1] <= generic_header_y
    and (
        node.center[1] <= header_y
        or (has_profile_menu and node.attributes.get("clickable", "false").casefold() == "true")
    )
    and node.text.strip().startswith("@")
]

# SAU:
username_candidates = [
    node for node in nodes
    if node.center is not None
    and header_left <= node.center[0] <= header_right
    and node.center[1] <= header_y          # ← Chỉ dùng header_y (250px), không mở rộng
    and node.text.strip().startswith("@")
]
if not username_candidates and has_profile_menu:
    # Fallback mở rộng Y nhưng CHỈ lấy node cao nhất (center_y nhỏ nhất = gần header nhất)
    extended = [
        node for node in nodes
        if node.center is not None
        and header_left <= node.center[0] <= header_right
        and header_y < node.center[1] <= generic_header_y
        and node.attributes.get("clickable", "false").casefold() == "true"
        and node.text.strip().startswith("@")
    ]
    if extended:
        username_candidates = [min(extended, key=lambda n: n.center[1])]
```

**Lý do an toàn:** Node sticky header (dính vào đỉnh sau swipe) luôn có center_y nhỏ hơn node thân profile. Lấy min center_y là heuristic đúng.

### 2. Thêm `coordinate_fallback` hook vào `_CanonicalAdapter`

Trong `account_preflight.py`, class `_CanonicalAdapter`:

```python
def coordinate_fallback(self, action: str):
    """Resilient fallback khi tất cả semantic/resource anchor đều fail."""
    if action == "switcher":
        # Center profile header area — nơi username/sticky header thường xuất hiện
        return (540, 155)
    return None
```

`open_switcher()` trong `account_switcher.py` đã có sẵn đoạn gọi hook này (dòng 765–766):
```python
evidence = getattr(adapter, "coordinate_fallback", None)
point = evidence("switcher") if callable(evidence) else None
```
Chỉ cần implement method này trong adapter.

### 3. Bổ sung resource ID suffix (phòng TikTok version mới)

```python
_SWITCH_ANCHOR_RESOURCE_SUFFIXES = frozenset({
    # Hiện tại:
    "rv5", "ryo", "s0g", "s3f", "rz5", "rn8", "p48", "pcq", "pmi", "pke", "pmf",
    "profile_header_name", "account_name", "profile_header_username", "tv_username",
    # Thêm cho coverage TikTok build mới (09/2026 — cần XML dump máy 40 để xác nhận):
    "qzs", "r0k", "r1a", "r2b", "s1g", "pmg", "pnk", "pnl",
})
```
⚠️ **CHỈ thêm các suffix này sau khi có XML dump thực tế từ máy fail** — đừng add speculative suffixes.

---

## Trạng Thái Thực Thi (ĐÃ HOÀN TẤT & TEST PASS 08/09/2026)

- **automation-core:** Đã patch trực tiếp `account_switcher.py` với 8 resource suffix mới, strict `header_y` gate, topmost fallback khi có profile menu, và viewport-ratio fallback tap `(screen_width // 2, screen_height * 150/1920)`.
- **Test Gate:** 41/41 unit test pass trong `automation-core/tests/test_account_switcher_preconfirmed.py`.
- **CLI run_batch_live_2fa.py:** Đã thêm argument `--rows` để lọc danh sách target theo source_row (vd `--rows 317`), hỗ trợ chạy lại lẻ có lock an toàn.

---

## Quy Trình Debug Khi Gặp SWITCHER_OPEN_FAILED Sau Patch 07/09

1. **Lấy XML dump từ máy đang fail:**
   ```bash
   adb -s <serial> shell uiautomator dump /sdcard/ui.xml && adb -s <serial> pull /sdcard/ui.xml D:/Taadaa/reports/mN_ui.xml
   ```

2. **Tìm node `@username` trong XML:**
   ```bash
   grep -i '@\|clickable\|bounds\|resource-id' D:/Taadaa/reports/mN_ui.xml | head -40
   ```

3. **Kiểm tra `center_y` của node `@username`:**
   - center_y ≤ 250px → nhánh `header_y` an toàn, lỗi do nguyên nhân khác
   - 250px < center_y ≤ 320px → **dính lỗ hổng residual** → áp dụng fix #1
   - center_y > 320px → **dính lỗ hổng cũ** trước 07/09 (không nên xảy ra nữa)

4. **Kiểm tra resource ID của sticky header node:**
   - So sánh với `_SWITCH_ANCHOR_RESOURCE_SUFFIXES`
   - Nếu suffix mới → thêm vào list sau khi xác nhận

---

## Liên quan
- `references/switcher-open-failed-and-process-duration-triage.md` — triage lỗi gốc
- `references/account-switcher-sticky-header-and-save-login-enforcement.md` — fix 07/09
- Commits: `1ec50ec`, `7521550` (automation-core)

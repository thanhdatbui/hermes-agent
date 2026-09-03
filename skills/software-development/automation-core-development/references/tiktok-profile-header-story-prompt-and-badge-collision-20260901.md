# TikTok Profile Header Collision: Story Prompt Bubble & Badge Interference (2026-09-01)

## 1. Ngữ cảnh & Triệu chứng Sự cố
- **Triệu chứng:** Trong quá trình chạy Feed session, Follow hook hoặc Reconcile tài khoản (ví dụ Máy 15 `@h.h67426`), tiến trình bị kẹt trên màn hình Hồ sơ (`Hồ sơ` / Profile root) và báo lỗi `SWITCHER_ANCHOR_AMBIGUOUS`, `SWITCHER_ANCHOR_NOT_FOUND` hoặc `PROFILE_SUBPAGE_STUCK` (do tap nhầm mở camera/story editor).
- **Môi trường:** TikTok v46.x / mới trên farm Samsung Galaxy.

## 2. Phân tích Nguyên nhân Gốc rễ (Root Cause)

### A. Lỗi 1: Huy hiệu số / Unread Badge cướp Display Name
- **Cơ chế cũ:** `profile_identity_from_xml` trong `automation_core.tiktok.profile` duyệt ngược cây node (`reversed(elements)`) trước vị trí `@username` (`index < username_index`) để tìm node có text không bắt đầu bằng `@`.
- **Điểm gãy:** Trên giao diện mới, TikTok hiển thị huy hiệu thông báo/hoạt động (ví dụ `"9+"`, `"99+"`, `"1+"`) ngay cạnh tên hiển thị và nằm trước node `@username` trong cây XML.
- **Hệ quả:** `profile_identity_from_xml` gán `display_name = "9+"`. Khi truyền sang `find_switcher_anchor`, `preferred_values = {"9+"}` không khớp tên thật (ví dụ `Hà Hà`), làm hỏng luồng ưu tiên identity.

### B. Lỗi 2: Bong bóng Story/Suy nghĩ (Thought Prompt) trên Avatar gây Ambiguous Anchor
- **Cơ chế cũ:** Khi không có candidate từ identity, `find_switcher_anchor` kích hoạt fallback `generic_candidates`: quét mọi node ở vùng đỉnh màn hình (`header_left <= center_x <= header_right` và `center_y <= generic_header_y`, `len >= 3`).
- **Điểm gãy:** Bong bóng gợi ý Story ("Trà hay cà phê?", "Hôm nay bạn thế nào?", "Thêm suy nghĩ...", "Tâm trạng hôm nay") nổi đè trên avatar thỏa mãn toàn bộ tiêu chí của `generic_candidates`.
- **Hệ quả:** 
  1. Xuất hiện đồng thời 2 node trong vùng header: bong bóng Story và tên tài khoản thật $\rightarrow$ `len(generic_candidates) == 2` $\rightarrow$ hàm trả về `None` (fail-closed vì không xác định được anchor duy nhất).
  2. Nếu tên tài khoản bị che hoặc ngắn, script tap nhầm vào bong bóng Story, mở ra màn hình tạo Story/Camera thay vì mở Account Switcher.

## 3. Quy chuẩn & Giải pháp Khắc phục (Case Fix — Approved)

### 1. Phân loại chuẩn hóa & Lọc bỏ Badge / Story Prompt (`profile.py`):
```python
import re

# Matches notification badge numbers (e.g. 9+, 99+, 1+, 999+)
_NOTIFICATION_BADGE_PATTERN = re.compile(r"^\d+\+$")
_STORY_PROMPT_MARKERS = frozenset({
    "trà hay cà phê",
    "tra hay ca phe",
    "hôm nay bạn thế nào",
    "hom nay ban the nao",
    "thêm suy nghĩ",
    "them suy nghi",
    "tâm trạng hôm nay",
    "tam trang hom nay",
    "chia sẻ suy nghĩ",
    "chia se suy nghi",
    "suy nghĩ của bạn",
    "suy nghi cua ban",
    "thêm trạng thái",
    "them trang thai",
    "bạn đang nghĩ gì",
    "ban dang nghi gi",
    "what's on your mind",
    "how are you today",
    "add a thought",
    "add thought",
})


def _normalize_prompt(value: str) -> str:
    cleaned = str(value or "").strip().replace("…", "...").casefold()
    cleaned = re.sub(r"[\?\.!]+$", "", cleaned).strip()
    return " ".join(cleaned.split())


def is_profile_badge_or_prompt(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    if _NOTIFICATION_BADGE_PATTERN.fullmatch(cleaned):
        return True
    norm_prompt = _normalize_prompt(cleaned)
    if norm_prompt in _STORY_PROMPT_MARKERS:
        return True
    return False


def is_valid_profile_display_name(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned or cleaned.startswith("@"):
        return False
    return not is_profile_badge_or_prompt(cleaned)
```

- **Lưu ý:** `_NOTIFICATION_BADGE_PATTERN` dùng `^\d+\+$` (bắt buộc có dấu `+` như `9+`, `99+`) để không loại nhầm các display name thuần số hợp lệ (như `"123456"`).
- `_normalize_prompt` chuẩn hóa dấu ba chấm (`…` sang `...`), casefold, và bỏ dấu câu cuối (`?`, `.`, `!`).

### 2. Dùng chung trong `account_switcher.py`:
Tái sử dụng `is_profile_badge_or_prompt` kèm exclusion guard cho profile UI markers:
```python
def _is_badge_or_prompt_node(node: SwitcherNode) -> bool:
    for raw in (node.text, node.content_desc):
        cleaned = str(raw or "").strip()
        if not cleaned:
            continue
        if is_profile_badge_or_prompt(cleaned) and not any(
            marker in _normalize(cleaned) for marker in ("hồ sơ", "profile", "sửa hồ sơ", "edit profile")
        ):
            return True
    return False
```

### 3. Đồng bộ & Kiểm thử (Sync & Test):
1. Copy source sang environment chung:
   ```bash
   cp -rf /d/Taadaa/automation-core/src/automation_core/* /d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/
   ```
2. Chạy regression test:
   - `env PYTHONPATH="D:/Taadaa/automation-core/src" python -m pytest tests/test_account_switcher_preconfirmed.py -v` (21 passed)
   - `env PYTHONPATH="D:/Taadaa/automation-core/src;D:/Taadaa/tiktok-luot nuoi acc/python_runner" python -m pytest python_runner/tests/test_account_switcher.py -v` (27 passed)

## 4. Kiểm thử Hồi quy (Regression Fixture Contract)
Bắt buộc có unit test bao phủ XML có đồng thời:
1. Node Story bubble `"Trà hay cà phê?"` ở top center.
2. Node display name `"Hà Hà"`.
3. Node badge `"9+"`.
4. Node username `"@h.h67426"`.
- Test chứng minh: `profile_identity_from_xml` trả về `display_name == "Hà Hà"`, và `find_switcher_anchor` chọn đúng node `"Hà Hà"` làm anchor mở Account Switcher.

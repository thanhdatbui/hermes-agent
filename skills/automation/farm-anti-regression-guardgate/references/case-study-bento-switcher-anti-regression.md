# Case Study: Bento Switcher Multi-Swipe & Account Fallback Invariant

## 1. Hiện Tượng Hiện Trường
- Tại phiên chạy Reg Gmail đêm 04/11/2026, 4 máy M16, M19, M45, M51 văng lỗi `[04_google] Không chọn được provider Google`.
- Đối soát ảnh WinRT OCR: Màn hình mở Bento Menu chứa 6 nick cũ, nút "Thêm tài khoản khác" bị đẩy tụt khỏi viewport (`y > 1920`).
- Cơ chế cũ chỉ vuốt 1 lần (`swiped = True`), fallback chọn bừa card `y >= 700` không chứa dung lượng `is_storage` $\to$ bấm nhầm nút "Chuyển đổi tài khoản" ở $y=846$.

## 2. Bản Vá O(1) & Test Assertion
- Hàm `wait_and_tap_add_account_in_switcher`: nâng cấp thành `swipe_count < 4`, cuộn từ `(540, 1500) -> (540, 700)` tối đa 4 lần.
- Hàm `find_add_account_card_in_switcher`: bổ sung `is_acc = has_text_loose(text + " " + desc, "chuyen doi tai khoan", "@", "xin chao", "quan ly")`.
- Unit test hợp đồng: `test_find_add_account_card_excludes_switch_account_and_accounts` trong `tests/test_ui_capture_contract.py`.

## 3. Cấu Hình GuardGate Invariant Rule
```json
{
  "id": "case_gmail_reg_switcher_fallback_anti_regression",
  "scope": {
    "repos": ["register gmail"],
    "paths": ["gmail_reg_v10.py"]
  },
  "match": {
    "tool_class": "code_edit",
    "op": "commit"
  },
  "require_all": ["prohibit_case_gmail_reg_switcher_fallback_anti_regression"],
  "on_deny": {
    "redirect": "sol_repair",
    "strike_class": "regression_known_incident",
    "action_enum": ["REVERT_EXACT", "JUSTIFIED_BYPASS"]
  },
  "vectors": [
    {"expect": "ALLOW", "name": "ok_with_is_acc"},
    {"expect": "DENY", "name": "bad_storage_only"}
  ],
  "params": {
    "pattern": "(?s)find_add_account_card_in_switcher.*?if\\s+[^\\n]*not\\s+is_storage\\s*:"
  },
  "reason": "Khóa cứng chống regression: Fallback tìm card Thêm tài khoản trong Bento Switcher bắt buộc phải loại trừ cả tài khoản cũ và chuyển đổi tài khoản (is_acc), cấm chỉ kiểm tra mỗi is_storage làm click nhầm.",
  "guidance": "Bổ sung điều kiện and not is_acc vào bộ lọc fallback của find_add_account_card_in_switcher."
}
```

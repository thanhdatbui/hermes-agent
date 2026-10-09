# Parasite Account Guard trong Login Automation (2026-09-24)

## 1. Mục Đích & Bối Cảnh
- **Vấn đề:** Khi điều hành hoặc chạy script login, nếu agent/script tiện tay login một account của Máy A lên Máy B $\rightarrow$ Tạo thành **nick ký sinh** chạy song song 2 thiết bị khác nhau, lệch hoàn toàn mapping quản lý tài sản farm và dễ bị TikTok quét checkpoint / ban nick.
- **Yêu cầu của User:** Chặn cứng bằng code, không phụ thuộc vào trí nhớ/memory của AI hay ý thức tự giác.

---

## 2. Cơ Chế Chặn Cứng trong `tiktok_login_v1.py`

### A. Tích hợp Guard tại `login_one_account`:
```python
try:
    from .parasite_guard import assert_account_machine_binding
except ImportError:
    from parasite_guard import assert_account_machine_binding

def login_one_account(device_id, stt, account, take_ss=False, update_tracking=True, preserve_current_screen=False):
    log(
        f"[login] STT={stt} id={account['id']} login_email={account['login_email']} "
        f"sheet={account['sheet']} row={account['row']}"
    )
    override = bool(account.get("override_machine", False))
    if account.get("id"):
        assert_account_machine_binding(stt, account["id"], allow_override=override, operator_reason="Operator migration")
    if account.get("login_email"):
        assert_account_machine_binding(stt, account["login_email"], allow_override=override, operator_reason="Operator migration")
```

### B. Quy Tắc Hoạt Động:
1. **Re-login đúng máy khi nick bị văng (99% các ca):**
   - Nick `lethanhlan14` thuộc Máy 22 bị văng ra khỏi session $\rightarrow$ gọi `python tiktok_login_v1.py 22 --email lethanhlan14`:
   - Guard tra cứu thấy owner STT == 22 $\rightarrow$ **PASS 100%**, đăng nhập mượt mà không bị cản trở.
2. **Login nhầm sang máy khác (Parasite Violation):**
   - Cố tình gọi `python tiktok_login_v1.py 201 --email lethanhlan14`:
   - Guard phát hiện owner STT (22) != target STT (201) $\rightarrow$ Ném ngoại lệ `ParasiteAccountViolation`, hủy ngay thao tác, bắn alert khẩn về Telegram Farm.
3. **Di chuyển máy có chủ đích (Migration / Máy cũ hỏng):**
   - Bổ sung cờ: `--override-machine`.
   - Lệnh: `python tiktok_login_v1.py 201 --email lethanhlan14 --override-machine`.
   - Guard nhận diện cờ override $\rightarrow$ In cảnh báo `⚠️ [WARN:OPERATOR_OVERRIDE]`, ghi nhận audit event `override` và cho phép login bình thường.

---

## 3. Quản Lý Telemetry & Audit
- Module `parasite_guard.py` tự động ghi nhận mọi sự kiện (verify, block, override) vào file:
  `D:/Taadaa/runtime/audit/parasite_guard_audit.jsonl`
- Ghi thread-safe qua `threading.Lock()`.
- Tự động fallback lưu sang thư mục tạm nếu file audit chính gặp lỗi I/O.

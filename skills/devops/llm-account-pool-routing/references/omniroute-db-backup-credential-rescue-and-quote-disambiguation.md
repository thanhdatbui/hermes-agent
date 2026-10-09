# OmniRoute SQLite Backup Credential Rescue & Quote Disambiguation

## 1. Telegram Multi-Message Quote & Account Disambiguation Invariant
- **Nguy cơ nhầm lẫn (Ambiguity Trap):**
  Khi người dùng tương tác qua Telegram với nhiều tin nhắn nối tiếp nhau (hoặc dùng tính năng Reply quote từng phần của tin nhắn cũ):
  - Ví dụ: Người dùng quote dòng cảnh báo tài khoản A để bảo "chuyển vào pool pro", rồi nhắn tiếp tin nhắn kế tiếp "xoá acc này khỏi omniroute".
  - **LỖI CHẾT NGƯỜI:** Tưởng nhầm "acc này" ở tin nhắn sau là tài khoản A vừa được bảo chuyển vào pro, dẫn đến gọi `DELETE /api/providers/<id>` xóa sạch tài khoản tài sản của farm.
- **Quy tắc bất biến:**
  - Khi có từ 2 tài khoản trở lên trong ngữ cảnh hoặc có chuỗi lệnh chuyển đổi + xóa, **BẮT BUỘC** map rõ ràng:
    * `[Acc X]`: Hành động gì (Move / Rebind / Keep).
    * `[Acc Y]`: Hành động gì (Delete / Retire).
  - Đối chiếu kỹ tiêu đề quote (`[Replying to: ...]`) trước khi thực hiện thao tác xóa không thể đảo ngược.

---

## 2. Cứu Hộ Tài Khoản Tức Thì Qua OmniRoute SQLite Backup (Zero-GPM Recovery)
- **Tình huống:** Tài khoản Antigravity (hoặc provider khác) bị xóa nhầm khỏi OmniRoute (`DELETE /api/providers/:id`), trong khi phiên OAuth vẫn còn sống trên Google. Thay vì tốn thời gian mở Playwright/GPM và chạy pipeline S7, có thể phục hồi trực tiếp từ backup SQLite nội bộ.
- **Vị trí Backup:**
  `C:\Users\Kibe\.omniroute\db_backups\`
  OmniRoute tự động tạo các bản snapshot định kỳ (~6 tiếng hoặc khi health-check repair):
  `db_YYYY-MM-DDTHH-mm-ss-sssZ_health-check-repair.sqlite`
- **Quy trình phục hồi O(1) không cần restart OmniRoute:**
  1. Mở file backup mới nhất chứa tài khoản:
     ```python
     import sqlite3
     bak = sqlite3.connect(r'C:\Users\Kibe\.omniroute\db_backups\<latest_backup>.sqlite')
     row = bak.execute("SELECT * FROM provider_connections WHERE email=?", (email,)).fetchone()
     ```
  2. Khôi phục vào database live `C:\Users\Kibe\.omniroute\storage.sqlite`:
     * **BẪY CÚ PHÁP SQLITE (CRITICAL):** Bảng `provider_connections` có cột mang tên `group`. Trong SQLite, `group` là từ khóa dành riêng (`GROUP BY`). Nếu viết `INSERT INTO provider_connections (id, ..., group, ...)`, SQLite sẽ ném lỗi `OperationalError: near "group": syntax error`.
     * **Bắt buộc wrap tên cột bằng dấu ngoặc kép:**
       ```python
       cols = [r[1] for r in live_conn.execute("PRAGMA table_info(provider_connections)").fetchall()]
       quoted_cols = ','.join([f'"{c}"' for c in cols])
       placeholders = ','.join(['?'] * len(cols))
       live_conn.execute(f"INSERT OR REPLACE INTO provider_connections ({quoted_cols}) VALUES ({placeholders})", row)
       ```
  3. Khôi phục gán proxy (`proxy_assignments`):
     ```python
     pa_row = bak.execute("SELECT * FROM proxy_assignments WHERE scope_id=?", (connection_id,)).fetchone()
     if pa_row:
         pa_cols = [r[1] for r in live_conn.execute("PRAGMA table_info(proxy_assignments)").fetchall()]
         quoted_pa = ','.join([f'"{c}"' for c in pa_cols])
         live_conn.execute(f"INSERT OR REPLACE INTO proxy_assignments ({quoted_pa}) VALUES ({','.join(['?']*len(pa_cols))})", pa_row)
     live_conn.commit()
     ```
  4. Xác nhận live: Gọi `POST /api/providers/<id>/test` kiểm tra kết nối ngay. Server OmniRoute đọc SQLite theo transaction nên nhận kết nối mới lập tức mà không cần khởi động lại tiến trình Node.js.

---

## 3. Cập Nhật Membership Combo An Toàn (PUT /api/combos/:id)
- Khi thêm hoặc bớt tài khoản khỏi combo (ví dụ đưa acc Pro vào `ag-gemini-pool-3` và `ag-gemini-pool-3-37`):
  ```python
  payload = {
      "name": combo["name"],
      "description": combo["description"],
      "strategy": combo["strategy"],
      "config": combo["config"],
      "models": updated_models_list,
      "isActive": combo.get("isActive", True)
  }
  # Gửi PUT tới /api/combos/<combo_id>
  ```
- Định dạng model entry chuẩn cho Antigravity:
  ```json
  {
    "id": "ag-gemini-pro-<custom-suffix>",
    "kind": "model",
    "model": "antigravity/gemini-3.8-flash-tiered",
    "providerId": "antigravity",
    "connectionId": "<connection_uuid>",
    "weight": 0,
    "label": "pro-<name>"
  }
  ```

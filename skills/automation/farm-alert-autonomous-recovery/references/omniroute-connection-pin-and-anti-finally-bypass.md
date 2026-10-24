# OmniRoute Connection Pinning & Anti-Finally-Bypass Invariant

## 1. Bối Cảnh Sự Cố (The Finally-Bypass Incident)
Toàn bộ 28 tài khoản Antigravity Pro trong pool OmniRoute bị tắt đồng loạt (`isActive: 0`), gây bão lỗi 503 Service Unavailable trên toàn farm.
- **Nguyên nhân gốc rễ:** Script `vm_rescue_lib.py` có hàm `isolated_chat_test()` thực hiện:
  ```python
  active_before = [c["id"] for c in conns if c.get("isActive")]
  try:
      for cid in active_before:
          set_active(cid, False) # TẮT SẠCH TOÀN BỘ CÁC ACC KHÁC
      set_active(connection_id, True)
      # gửi request test...
  finally:
      for cid in active_before:
          set_active(cid, True)  # Dự định bật lại
  ```
- **Tử huyệt:** Khi Agent chạy lệnh test với timeout ngắn hơn thời gian phản hồi upstream của model (ví dụ upstream chậm mà command timeout = 35s), Hermes Terminal thực hiện `taskkill / kill` cưỡng bức tiến trình (`exit_code: 124`).
- **Hậu quả:** Khối `finally:` của Python KHÔNG BAO GIỜ ĐƯỢC CHẠY. 28 tài khoản bị bỏ rơi ở trạng thái `isActive: 0`, làm tê liệt toàn bộ hạ tầng inference.

---

## 2. Invariant Kỹ Thuật (Hard Rules)

### Invariant 1: CẤM Tắt Bật Toàn Cục Để Test (Zero Production Mutation)
- Tuyệt đối CẤM dùng các vòng lặp `set_active(False)` lên các tài khoản active khác để phục vụ kiểm thử đơn lẻ một tài khoản.
- Không bao giờ được ỷ lại vào `try...finally` khi chạy qua subprocess/terminal runner vì timeout hay SIGKILL sẽ bypass `finally:`.

### Invariant 2: Dùng Header Pinning Thay Vì Sửa DB Pool
- OmniRoute đã hỗ trợ pin trực tiếp request vào connection chỉ định:
  - Header: `x-omniroute-connection: <connection_id>`
  - Session ID tươi: `x-session-id: <unique_uuid>`
  - Khi có header này, OmniRoute gán `forcedConnectionId` và KHÔNG fallback sang account khác khi lỗi.
- Chỉ khi tài khoản mục tiêu đang `isActive: 0` thì mới tạm thời bật riêng tài khoản đó, và `timeout` của request HTTP nội bộ BẮT BUỘC phải ngắn hơn timeout của lệnh shell (ví dụ HTTP timeout 20s, shell timeout >= 45s).

### Invariant 3: Kỷ Luật Điều Tra Sự Cố (Investigate Session Before Blaming User)
- Khi phát hiện audit log có thao tác hàng loạt từ `127.0.0.1` hay `admin`:
  1. CẤM vội vàng quy kết operator "chạm nhầm UI / gạt nút toggle".
  2. BẮT BUỘC dùng `session_search` tra cứu các lệnh chạy trong phiên trước đó quanh mốc thời gian đó.
  3. Kiểm tra các lệnh có `exit_code: 124` (timeout) hoặc script chạy ngầm bị chém chết giữa chừng.

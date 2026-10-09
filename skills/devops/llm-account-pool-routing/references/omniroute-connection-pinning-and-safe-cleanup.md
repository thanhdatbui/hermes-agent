# OmniRoute Connection Sync & Pinning Verification Best Practices

Khi viết hoặc cập nhật hook tự động sync OAuth/session token từ browser profile (GPM/CDP) vào OmniRoute (`codex`, `chatgpt-web`, v.v.):

### 1. Connection ID Pinning Header khi Ping Verification
Khi verify completion sau khi tạo hoặc cập nhật connection trên OmniRoute:
- Không gửi ping request `/v1/chat/completions` trần chỉ có `model`, vì OmniRoute sẽ load balance hoặc route sang connection mặc định / khác trong pool.
- Bắt buộc đính kèm headers xác định rõ connection vừa import:
  ```python
  ping_headers = {
      'x-omniroute-connection-id': str(conn_id),
      'x-connection-id': str(conn_id)
  }
  ping_res = requests.post(
      f'{OMNI_API_BASE}/v1/chat/completions',
      headers=ping_headers,
      json={
          'model': target_model,
          'messages': [{'role': 'user', 'content': f'Hello from {email}'}],
          'max_tokens': 10
      },
      timeout=35
  )
  ```

### 2. An toàn trong `finally:` block (Stop Profile)
- Luôn bọc lệnh tắt profile (`requests.get(f'{GPM_API_BASE}/profiles/stop/{profile_id}')`) bên trong `try ... except Exception as stop_err:` và ghi `logger.warning(...)`.
- Tránh để ngoại lệ dừng profile ghi đè kết quả trả về (`return {'success': True, ...}`) hoặc làm đứt luồng xử lý chính.

### 3. Redact Sensitive Token trong Ping Response Output
- Phản hồi từ ping inference hoặc lỗi từ upstream có thể phản chiếu (echo) lại nội dung chứa token hoặc JWT.
- Cần chạy qua `redact_sensitive(output, token)` trước khi lưu vào `ping_response` trả về cho caller/log.

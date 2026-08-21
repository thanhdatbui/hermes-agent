# Sol / Terra HTTP Calling with Streaming (Anti-Timeout Recipe)

## Bối cảnh & Vấn đề
Khi gửi prompt lớn (>500 dòng code, audit toàn diện hoặc refactor nhiều hàm) tới model lý luận cao như `gpt-5.6-sol`, `cx/gpt-5.6-sol`, `gpt-5.6-terra` qua 9Router HTTP API (`http://127.0.0.1:20128/v1/chat/completions`):
- Nếu cấu hình `"stream": false`, client gửi HTTP POST và đóng băng socket chờ model suy luận xong toàn bộ mới trả về 1 payload JSON duy nhất.
- Với reasoning effort cao + prompt dài, thời gian suy luận có thể mất từ 60s đến 300s ➔ Dẫn tới **Network Timeout / Gateway socket drop / HTTP 504 Gateway Timeout**.

## Giải pháp: HTTP SSE Streaming (`"stream": true`)
Bật `"stream": true` trong request body. 9Router sẽ đẩy từng chunk token `data: {"choices": [{"delta": {"content": "..."}}]}` ngay lập tức. Client nhận data liên tục, socket không bị idle ➔ **Thời gian phản hồi token đầu tiên chỉ mất 2-6 giây, không bao giờ bị timeout**.

## Tool chuẩn hoá: `D:\Taadaa\tools\invoke_sol_audit.py`

### 1. CLI Usage
```bash
# 1. Truyền prompt trực tiếp
python D:/Taadaa/tools/invoke_sol_audit.py --prompt "Nội dung cần hỏi/audit"

# 2. Truyền file prompt lớn (khuyên dùng khi audit code)
python D:/Taadaa/tools/invoke_sol_audit.py --prompt-file "path/to/prompt.txt" --model "cx/gpt-5.6-sol" --out-file "output.md"

# 3. Đọc prompt từ stdin
cat prompt.txt | python D:/Taadaa/tools/invoke_sol_audit.py --model "cx/gpt-5.6-sol"
```

### 2. Python Invocation Pattern
```python
import urllib.request, json, os

def call_sol_streaming(prompt: str, model: str = "cx/gpt-5.6-sol", timeout_s: float = 300.0) -> str:
    api_key = os.environ.get("NINEROUTER_API_KEY", "")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "max_tokens": 8000,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:20128/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    chunks = []
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data: ") and line_str != "data: [DONE]":
                try:
                    payload = json.loads(line_str[6:])
                    delta = payload["choices"][0]["delta"].get("content", "")
                    if delta:
                        chunks.append(delta)
                except Exception:
                    pass
    return "".join(chunks)
```

## Quy tắc áp dụng cho Farm
1. **Mọi prompt audit/refactor lớn >300 dòng:** BẮT BUỘC dùng `invoke_sol_audit.py` hoặc streaming mode.
2. **Không truyền cả repo:** Chỉ định vị các hàm/module cụ thể liên quan đến task để Sol tập trung reasoning chính xác nhất.

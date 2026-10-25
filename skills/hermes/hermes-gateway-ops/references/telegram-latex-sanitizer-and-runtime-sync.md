# Chuẩn Hóa & Làm Sạch LaTeX Math Trên Telegram Adapter (LaTeX Sanitizer & Runtime Sync)

## 1. Hiện Tượng & Triệu Chứng
- Khi Agent phản hồi có chứa công thức toán học hoặc sơ đồ quy trình dạng LaTeX đa dòng (`$$\begin{aligned} ... \end{aligned}$$`), nhãn mũi tên có tham số (`\xrightarrow{label}`), thẻ văn bản (`\text{...}`), ngắt dòng LaTeX (`\\`), căn chỉnh cột (`&`), hoặc ký hiệu so sánh (`\ge`, `\le`).
- **Telegram Bot API không hỗ trợ MathJax/LaTeX**:
  - Toàn bộ khối code LaTeX bị hiển thị thô dạng text.
  - Các ký tự đặc biệt lọt qua bộ chuyển đổi MarkdownV2 bị escape backslash (`\\begin\{aligned\}`), làm vỡ hoàn toàn định dạng visual.
  - Tin nhắn bị phình to bất thường, vượt giới hạn độ dài ký tự và bị xé nhỏ thành nhiều mảnh gây rối mắt người dùng (`(1/4)`, `(2/4)`, `(3/4)`, `(4/4)`).
- **Cơ chế cũ bị thủng**: Bản vá cũ chỉ replace các ký hiệu mũi tên inline đơn giản (`$\rightarrow$`, `\rightarrow`), hoàn toàn bất lực trước môi trường khối (`\begin{...}`) và các thẻ LaTeX có đối số mở ngoặc nhọn `{}`.

## 2. Kỹ Thuật Sanitize Chuẩn Trong `adapter.py::format_message`
Trong hàm `format_message(self, content: str) -> str`, bộ làm sạch phải chạy **ngay sau** bước `_wrap_markdown_tables` và **trước khi** escape MarkdownV2:

```python
# 0.1) Auto-convert LaTeX math environments, formulas & arrows to clean text/Unicode
text = text.replace(r"\&", "\x01AMP\x02")
text = re.sub(r"\\(?:begin|end)\{[a-zA-Z*]+\}", "", text)
for _ in range(3):
    text = re.sub(r"\\(?:text|mathrm|mathbf|mathit)\{([^{}]*)\}", r"\1", text)
text = re.sub(
    r"\\xrightarrow(?:\[([^\]]*)\])?\{([^{}]*)\}",
    lambda m: f" ──[{m.group(2).strip() or m.group(1).strip()}]──> " if (m.group(2) or m.group(1)) else " → ",
    text,
)
text = re.sub(
    r"\\xleftarrow(?:\[([^\]]*)\])?\{([^{}]*)\}",
    lambda m: f" <──[{m.group(2).strip() or m.group(1).strip()}]── " if (m.group(2) or m.group(1)) else " ← ",
    text,
)
for sym, u in (
    (r"\ge", "≥"), (r"\geq", "≥"), (r"\le", "≤"), (r"\leq", "≤"),
    (r"\ne", "≠"), (r"\neq", "≠"), (r"\approx", "≈"), (r"\pm", "±"),
    (r"\times", "×"), (r"\cdot", "·"), ("\\" + "rightarrow", "→"), ("\\to", "→"),
    ("\\leftarrow", "←"), ("\\gets", "←"), ("\\Rightarrow", "⇒"), ("\\Leftarrow", "⇐"),
):
    text = text.replace(f"${sym}$", u).replace(sym, u)
text = re.sub(r"(?m)^[ \t]*&[ \t]*", "", text)
text = re.sub(r"[ \t]*&[ \t]*", " ", text).replace("\x01AMP\x02", "&")
text = re.sub(r"\\\\(?=\s*$)", "", text, flags=re.MULTILINE).replace("\\\\", "\n")
text = re.sub(r"\$\$(.*?)\$\$", r"\1", text, flags=re.DOTALL).replace("$$", "")
text = re.sub(r"\n{3,}", "\n\n", text)
```

### Điểm mấu chốt trong thứ tự xử lý:
1. **Bảo vệ `\&`**: Đổi sang token tạm để không bị bước dọn ký tự căn chỉnh `&` xóa mất.
2. **Unwrap `\text{...}` trước**: Phải làm phẳng các khối chữ lồng nhau trước để `\xrightarrow{\text{Label}}` trở thành `\xrightarrow{Label}`, giúp regex bắt gọn nhãn mũi tên.
3. **Mũi tên có nhãn**: Đổi sang dạng text trực quan `──[Label]──>`.
4. **Dọn ngắt dòng**: Đổi `\\` thành `\n` thực tế để chia dòng tự nhiên.

## 3. Quy Trình Đồng Bộ & Bẫy Lệch Pha Runtime (Runtime Sync & Gateway Restart)
- **Vị trí thực thi thực tế của Gateway**:
  Hermes Gateway khởi động qua `Hermes_Gateway.vbs` nạp module từ môi trường venv:
  `%LOCALAPPDATA%\hermes\hermes-agent\venv\Lib\site-packages\plugins\platforms\telegram\adapter.py`
  và `%LOCALAPPDATA%\hermes\hermes-agent\plugins\platforms\telegram\adapter.py`.
- **Nếu chỉ sửa ở Repo `D:/Taadaa/Hermes`**: Gateway đang chạy trong RAM hoàn toàn không nhận được thay đổi.
- **Bắt buộc 3 bước khi cập nhật Adapter**:
  1. Patch và chạy test focused trong repo (`python -m pytest tests/test_telegram_latex_math.py -q`).
  2. Đồng bộ nội dung file đã sửa vào cả 2 vị trí runtime trong `%LOCALAPPDATA%`.
  3. Khởi động lại Gateway bằng tiến trình tách rời (`restart_gw_detached.py` hoặc `wscript.exe Hermes_Gateway.vbs`).
- **Xử lý ngắt quãng (Interrupted Response)**: Khi Gateway restart, kết nối WebSocket/Polling tạm ngắt khiến lượt phản hồi hiện tại có thể hiển thị `[response interrupted]`. Sau khi Gateway online trở lại, `auto_resume_startup_hook.py` sẽ khôi phục session và Agent tiếp tục resume bình thường.

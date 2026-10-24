# Telegram LaTeX Math & Raw Syntax Pitfalls

## 1. Bản Chất Sự Cố
- **Hiện tượng:** Khi Agent gửi công thức toán hoặc sơ đồ quy trình dạng khối LaTeX đa dòng (`$$\begin{aligned} ... \end{aligned}$$`, `\xrightarrow{...}`, `\text{...}`, `\\`, `\ge`, `\le`), Telegram hiển thị nguyên văn cú pháp code thô. Tin nhắn bị vỡ bố cục và xé nhỏ thành nhiều phần rời rạc (ví dụ: `(3/4)`, `(4/4)`).
- **Nguyên nhân lệch tầng:**
  - Bộ lọc trong Telegram Adapter (`plugins/platforms/telegram/adapter.py`) trước đây chỉ chuyển đổi các ký hiệu mũi tên đơn lẻ dạng inline (`$\rightarrow$`, `\rightarrow`, `$\Rightarrow$`).
  - Telegram **hoàn toàn không có engine render MathJax / LaTeX**.
  - Các khối môi trường toán học đa dòng (`aligned`, `matrix`), lệnh mũi tên có nhãn chữ (`\xrightarrow{label}`), thẻ văn bản (`\text{...}`) và dấu ngắt dòng (`\\`) không được adapter bóc tách, lọt thẳng qua bộ escape MarkdownV2 làm hỏng giao diện người dùng trên mobile.

## 2. Kỷ Luật Phản Hồi Trực Tiếp Trên Telegram (Agent Invariant)
- **CẤM TUYỆT ĐỐI** viết khối LaTeX toán học đa dòng (`$$`, `\[`, `\begin{aligned}`, `\begin{matrix}`).
- **CẤM TUYỆT ĐỐI** dùng các lệnh LaTeX inline như `\xrightarrow{...}`, `\text{...}`, `\ge`, `\le`.
- **BẮT BUỘC** dùng ký tự Unicode chuẩn hoặc text thuần sạch cho mọi sơ đồ quy trình / so sánh:
  - Mũi tên tiến trình: `──[Nhãn bước]──>` hoặc `→`, `->`, `⇒`.
  - Phép so sánh / toán học: `≥`, `≤`, `≠`, `≈`, `×`.
  - Ví dụ chuẩn luồng điều phối:
    ```text
    User Request ──[Gate 1-5]──> Lập Contract ──[Gate 4]──> Worker Thi Công ──[Test <30s]──> Closeout Gate (Sol) ──[≥85]──> Push Git
    ```

## 3. Quy Chuẩn Nâng Cấp Tầng Gateway Adapter (Telegram Sanitizer)
Khi cần gia cố bộ lọc ở tầng mã nguồn `plugins/platforms/telegram/adapter.py`:
- Strip sạch các wrapper môi trường: `$$\begin{aligned}`, `\end{aligned}$$`, `$$`.
- Regex chuyển đổi có nhãn: `re.sub(r'\\xrightarrow\{([^}]+)\}', r'──[\1]──>', text)`
- Regex bóc thẻ text: `re.sub(r'\\text\{([^}]+)\}', r'\1', text)`
- Thay thế các ký tự toán học phổ biến:
  - `\\` $\to$ xuống dòng `\n`
  - `\ge` $\to$ `≥`, `\le` $\to$ `≤`, `\ne` $\to$ `≠`
  - `\&` $\to$ khoảng trắng hoặc căn lề

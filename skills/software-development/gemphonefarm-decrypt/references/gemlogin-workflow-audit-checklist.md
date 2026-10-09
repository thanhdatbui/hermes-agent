# GemLogin (.gemlogin) & Automa Workflow Audit Checklist

Tài liệu hướng dẫn rà soát và kiểm toán nhanh chất lượng workflow GemLogin (.gemlogin) hoặc Automa trước khi đưa vào vận hành hoặc port sang code Python/automation-core.

---

## 1. Cấu trúc file `.gemlogin`
File `.gemlogin` là định dạng JSON mở rộng từ Automa Chrome Extension, thường chứa:
```json
{
  "name": "Tên workflow",
  "extVersion": 2,
  "drawflow": {
    "nodes": [
      {
        "id": "node_id",
        "label": "trigger | javascript-code | event-click | forms | excel | loop-data | ...",
        "data": { ... },
        "position": { "x": 100, "y": 200 }
      }
    ],
    "edges": [
      { "id": "e_id", "source": "node_A", "target": "node_B" }
    ]
  },
  "settings": { ... }
}
```

---

## 2. Checklist 5 Bẫy Lỗi Phổ Biến Nhất Khi Mua/Nhận Workflow

### Bẫy 1: Graph Disconnect (Đứt luồng / Nút cô lập)
- **Triệu chứng:** Bấm chạy nhưng script chỉ chạy vài block đầu rồi dừng, hoặc các chức năng chính (tải file, lưu dữ liệu) không hề chạy.
- **Nguyên nhân:** Người tạo lúc chỉnh sửa đã kéo rời hoặc xoá mất dây nối (`edge`) giữa các khối. Nhiều khối nằm trên canvas nhưng là "hòn đảo cô lập" (`unreachable` từ `trigger`).
- **Cách quét nhanh:**
  ```python
  import json
  d = json.load(open('workflow.gemlogin', encoding='utf-8'))
  nodes = {n['id']: n for n in d['drawflow']['nodes']}
  edges = d['drawflow']['edges']
  adj = {}
  for e in edges: adj.setdefault(e['source'], []).append(e['target'])
  visited = set()
  def dfs(u):
      visited.add(u)
      for v in adj.get(u, []):
          if v not in visited: dfs(v)
  dfs('root_trigger_id')
  unreachable = set(nodes.keys()) - visited
  print(f"Reachable: {len(visited)}/{len(nodes)} - Unreachable: {len(unreachable)}")
  ```

### Bẫy 2: Kill-Switch / Hạn Sử Dụng Ngầm
- **Triệu chứng:** Script mua về chạy được một thời gian thì bỗng nhiên quăng lỗi và chết hẳn.
- **Vị trí:** Thường nằm trong các block `javascript-code` đầu luồng.
- **Mã nhận diện:**
  ```javascript
  const expirationDate = new Date("2026-12-28");
  if (new Date() > expirationDate) {
      throw new Error("Script đã hết hạn!");
  }
  ```
- **Xử lý:** Xoá bỏ khối này hoặc bỏ đoạn throw Error, giữ lại `NextBlock()`.

### Bẫy 3: Hardcode Đường Dẫn Máy Tác Giả (Path Mismatch)
- **Triệu chứng:** Chạy trên máy mới báo lỗi `File not found` ngay khi đọc Excel hoặc chạy lệnh CMD.
- **Vị trí:** 
  - Trong block `trigger` parameters (ví dụ: `C:\Users\khoa lee\Downloads\...`).
  - Trong block `command` (ví dụ: `del "C:\Users\minht\Downloads\..."`).
  - Trong block `excel` (đọc từ `{{variables.Đường_dẫn}}`).
- **Xử lý:** Thay thế toàn bộ bằng đường dẫn động theo máy hiện tại hoặc dùng biến môi trường.

### Bẫy 4: Bất Đồng Bộ Trong Khối JavaScript (`NextBlock()` Race Condition)
- **Triệu chứng:** Khối JavaScript chưa tải xong file hoặc chưa render xong dữ liệu thì GemLogin đã nhảy sang khối tiếp theo, dẫn tới khối sau bị lỗi vì thiếu file/dữ liệu rỗng.
- **Nguyên nhân:** `NextBlock()` được đặt bên ngoài callback bất đồng bộ (như `script.onload`, `fetch().then()`, `setTimeout`).
- **Quy tắc:** Bắt buộc phải đưa `NextBlock()` vào bên trong callback hoàn tất của sự kiện bất đồng bộ.

### Bẫy 5: Chặn CSP (Content Security Policy) Trên TikTok / Facebook
- **Triệu chứng:** Đoạn inject script tải thư viện từ CDN bên ngoài (như `https://cdnjs.cloudflare.com/.../xlsx.full.min.js`) bị im lặng hoặc báo lỗi CSP `Refused to load the script because it violates the Content Security Policy directive`.
- **Giải pháp:** Không inject thư viện từ CDN bên ngoài vào trang có CSP chặt; thay vào đó gom link thô rồi xử lý lưu file bằng extension context hoặc xuất dữ liệu qua API GemLogin/Automa Table.

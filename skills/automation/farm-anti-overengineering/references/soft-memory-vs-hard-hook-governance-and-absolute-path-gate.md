# Soft Memory vs Hard Hook Governance & Absolute Path Scope Lock Gate

## 1. Vấn Đề Thực Tế (Sự Cố Máy 41 & Câu Hỏi Của User Tad)
- **Sự cố:** Xử lý Farm Alert Máy 41 mất gần 3 tiếng (từ 19:47 đến 22:35) do Worker 1 bị ngâm 75 phút (35 iterations), Worker 2 bị ảo giác "nói mồm đã sửa xong" ngâm 54 phút (35 iterations) mà git status vẫn clean.
- **Nguyên nhân gốc rễ:**
  1. Coordinator giao việc mở, thiếu đường dẫn tuyệt đối: *"xem summary.txt, kiểm tra monkey trong tiktok-luot nuoi acc hoặc automation-core..."*. Worker có thư mục mặc định `C:\Users\Kibe`, phải tốn 5–10 tool calls tìm kiếm khắp `C:` và `D:`, đốt cạn ngân sách vòng lặp.
  2. Khi đưa ĐƯỜNG DẪN TUYỆT ĐỐI (`D:/Taadaa/automation-core/.../startup.py`), Worker sửa xong và test pass chỉ trong **18–35 giây**!
- **Câu hỏi của Tad:** *"Nạp vào memory có đủ khoá chặt điều phối không? Hỏi Claude CLI xem."*

---

## 2. Kết Luận Kiến Trúc từ Giám Khảo Claude Opus High

### A. Memory KHÔNG THỂ "Khóa Chặt" Điều Phối
- **Bản chất kỹ thuật:** Memory chỉ là **Soft Constraint** (token được nhồi vào context window). Nó không nằm trên đường thực thi của code, không có quyền `return False`, không có quyền chặn lệnh. Nó chỉ là **"lời khuyên bảo mang tính xác suất"**.
- **Hiệu ứng "Lost in the Middle" & Task Salience:** Khi context phình to (log dài, nhiều tool result) hoặc khi đối mặt với Farm Alert khẩn cấp, dòng memory tĩnh dễ dàng bị mô hình lơ đãng hoặc "quên" mất.
- **Bằng chứng thực nghiệm:** Sự cố 3 tiếng tối nay xảy ra dù trong prompt/memory đã có quy tắc, chứng minh rằng chỉ nạp text vào memory là **chế độ hỏng có thể tái lặp** dưới tải.

### B. Bảng 4 Cấp Độ Kiểm Soát Hành Vi
| Cấp | Cơ chế | Bản chất | Độ cưỡng chế | Bypass được không? |
|:---:|---|:---:|:---:|---|
| **Cấp 1** | **Memory** (User Profile / Notes) | Soft | Rất yếu | **Dễ** — Mô hình lơ đãng là trượt |
| **Cấp 2** | **Skill** (`SKILL.md`) | Soft | Yếu – TB | **Có** — Đọc quy trình nhưng vẫn làm tắt |
| **Cấp 3** | **System Prompt** (`config.yaml`) | Soft | Trung bình | **Vẫn có** — Vẫn chỉ là văn bản thuyết phục |
| **VỰC NGĂN** | *(Từ thuyết phục bằng chữ ➔ Cưỡng chế bằng luật vật lý của code)* | | | |
| **Cấp 4** | **Code-level Pre-tool Hook (Python)** | **HARD GATE** | **TUYỆT ĐỐI** | **100% KHÔNG THỂ BYPASS** |

> **Quy Tắc Vàng:**
> *"Memory và System Prompt là để mô hình **MUỐN** làm đúng; Plugin Hook là để mô hình **KHÔNG THỂ** làm sai."*

---

## 3. Kiến Trúc Khóa Chặt Cấp 4 (Zero-Bypass Gate)

Để không bao giờ còn tình trạng "Coordinator quên ném path, Worker lại lượn tìm file", hệ thống cần cơ chế kiểm tra tất định (deterministic) ngay tại plugin `farm-coordinator-guard`:

### Gate 1 & 2: Pre-tool Hook cho `delegate_task`
```python
def pre_delegate_task(call):
    context = call.args.get("context", "")
    
    # Gate 1: Bắt buộc phải có chuỗi đường dẫn tuyệt đối (Windows C:/ hoặc D:/)
    paths = re.findall(r'[A-Za-z]:[\\/][^\s\'",;]+', context)
    if not paths:
        return reject("⛔ [FARM GUARD]: delegate_task BỊ CHẶN! "
                      "Coordinator BẮT BUỘC phải cung cấp ĐƯỜNG DẪN TUYỆT ĐỐI (Absolute Path) "
                      "đến file cần sửa trong context (Scope Lock). Cấm giao việc mở!")

    # Gate 2: File đó PHẢI TỒN TẠI THẬT TRÊN ĐĨA ngay lúc dispatch
    valid_files = [p for p in paths if os.path.isfile(p)]
    if not valid_files:
        return reject("⛔ [FARM GUARD]: File chỉ định không tồn tại trên đĩa! "
                      "Coordinator phải chạy inspect O(1) để định vị đúng file thật trước khi dispatch!")

    return allow(call)
```

### Acceptance Gate: Post-worker Verification
```python
def post_worker_result(repo_path):
    # Không tin prose của worker ("đã sửa xong/đã test pass")
    diff = subprocess.run(["git", "diff", "--stat"], cwd=repo_path, capture_output=True, text=True)
    if not diff.stdout.strip():
        return reject("⛔ [FARM GUARD]: Worker báo done nhưng git diff RỖNG! "
                      "Từ chối nghiệm thu báo cáo tự bịa.")
```

---

## 4. Tóm Tắt Quy Chuẩn Dispatch Phải Tuân Thủ
1. **Không bao giờ dispatch task sửa code mà không có file cụ thể.**
2. **Context dispatch BẮT BUỘC có khối:**
   ```text
   SCOPE LOCK BẮT BUỘC:
   - File cần sửa: D:/Taadaa/.../<target_file>.py
   - File test: D:/Taadaa/.../<test_file>.py
   - Hàm/Module lỗi: <function_name>
   ```
3. **Nghiệm thu dứt khoát dựa trên `git diff` thật**, cấm nghiệm thu qua lời báo cáo bằng chữ của subagent.

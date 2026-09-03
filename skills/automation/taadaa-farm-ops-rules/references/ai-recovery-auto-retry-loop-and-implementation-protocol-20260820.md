# AI AUTO-RECOVERY AUTO-RETRY LOOP, AUDIT REFINEMENT & STANDARDIZED IMPLEMENTATION PROTOCOL (20/08/2026)

## I. QUY TRÌNH 6 BƯỚC TRIỂN KHAI CODE MỚI CHUẨN HOÁ (BẮT BUỘC KHI XÂY DỰNG CODE MỚI)

Khi người vận hành đưa ra yêu cầu triển khai tính năng / logic mới (khác với debug sự cố tức thời), toàn bộ quy trình tự động kích hoạt chuẩn 6 bước mà không cần nhắc:

```
[1. LẬP PLAN CHI TIẾT] (.hermes/plans/YYYY-MM-DD_<name>.md)
               │
               ▼
[2. AUDIT PLAN] (Gọi 9Router model 'plan-review' / 'ag/claude-opus-4-6-thinking' -> VERDICT: APPROVED)
               │
               ▼
[3. WORKER IMPLEMENT (TDD)] (Viết test Red -> Code Green -> Không đụng file ngoài scope)
               │
               ▼
[4. CODE REVIEW DIFF] (Gọi 9Router audit toàn bộ git diff -> VERDICT: APPROVED)
               │
               ▼
[5. CHẠY PYTEST ISOLATED] (Pytest suite liên quan PASS 100% trên venv automation)
               │
               ▼
[6. PULL REBASE & COMMIT/PUSH GIT MASTER] (Commit message [verified] tiếng Việt + push origin master)
```

---

## II. CƠ CHẾ AUTO-RETRY LOOP CHO AI AUTO-RECOVERY KHI AUDIT TỪ CHỐI (REJECTED)

### 1. Vấn đề trước đây
Trước đây, khi AI Vision (`Gemini 3.7 Flash`) phân tích màn hình kẹt và tạo code patch, nếu Model Plan-Review (`Terra/Opus/Sol`) từ chối (`REJECTED` do selector lỏng lẻo, tap mù, hoặc thiếu return type), hệ thống dừng lại, chỉ gửi lệnh ADB chữa cháy và báo lỗi `audit_rejected` lên Telegram mà không tự sửa lại code.

### 2. Thiết kế Auto-Retry Loop (Max 2 Lần)
Đã bổ sung hàm `refine_patch()` trong `python_runner/ai_recovery/vision_client.py` và vòng lặp `while not audit_ok and retry_count < MAX_AUDIT_RETRIES` trong `agent.py`:
- **Đầu vào của Refine**: Ảnh hiện trường + UI XML + Target File + Code patch cũ bị từ chối + Chi tiết lý do từ chối từ auditor (`audit_verdict`) + Số lần thử (`attempt`).
- **Nhiệm vụ của AI**: Sửa triệt để 100% các điểm auditor nêu ra (loại bỏ tap mù, siết chặt selector, trả về đúng kiểu dữ liệu).
- **Vòng lặp Re-audit**:
  - Gửi bản vá đã sửa sang Plan-Review.
  - Nếu `APPROVED`: Apply patch -> Commit Git -> Gửi lệnh ADB -> Cho máy tiếp tục chạy.
  - Nếu `REJECTED`: Tiếp tục lấy lý do mới đưa vào vòng thử thứ 2.
  - Sau tối đa 2 lần thử nếu vẫn `REJECTED`: Dừng lại an toàn, không commit code lỗi, báo cáo minh bạch `audit_rejected (sau N lần tự sửa)`.

---

## III. CHẾ ĐỘ CHỈ LƯỚT NUÔI TOÀN FARM (TẮT CẢ FOLLOW VÀ UPLOAD VIDEO)

Để phục vụ giai đoạn thay dàn Proxy Mobi mới và rửa Trust Score cho 80 máy / 480 nick:
1. **Follow Hook**: Mặc định `ALLOW_CROSS_REPO_FOLLOW = False`. Chỉ bật khi có `ALLOW_FARM_FOLLOW=1` hoặc config `safety.allow_farm_follow: true`.
2. **Upload Hook (Đăng video phiên 3)**: Mặc định `ALLOW_CROSS_REPO_UPLOAD = False`. Chỉ bật khi có `ALLOW_FARM_UPLOAD=1` hoặc config `safety.allow_farm_upload: true`.
3. **Mục tiêu**: Toàn bộ 3 ca nuôi chỉ thực hiện lướt For You (85%), Following (8%), Friends (7%) với độ trễ và tỷ lệ Like tự nhiên, bảo vệ nick tuyệt đối.

---

## IV. CÁCH LY THƯ VIỆN PIL & RESOLVE `_AGENT_SCRIPT` VẬN HÀNH BỀN VỮNG

1. **Lỗi resolve path trong venv**: `Path(__file__).resolve().parents[3]` khi chạy từ virtualenv site-packages bị trỏ sai thư mục -> Sửa thành cơ chế `_find_agent_script()` quét danh sách candidate paths ưu tiên đường dẫn tuyệt đối `D:\Taadaa\tiktok-luot nuoi acc\python_runner\ai_recovery\agent.py`.
2. **Xung đột PIL leaked từ PYTHONPATH**: Tự động dọn dẹp `sys.modules` và lọc bỏ đường dẫn leaked `hermes-agent` khỏi `sys.path` trước khi nạp `PIL.Image`, đảm bảo tiến trình gửi alert không bị crash `_imaging` khi máy vừa khởi động lại.

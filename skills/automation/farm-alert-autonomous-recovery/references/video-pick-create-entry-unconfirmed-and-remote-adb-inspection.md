# Video Pick Create Entry Unconfirmed & Remote ADB Triage Guide (2026-10-26)

## 1. Triệu Chứng & Mẫu Cảnh Báo (Alert Signature)
Khi nhận cảnh báo batch diện rộng trên cụm Admin hoặc Kibe:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN - MÁY 201-280】
• Quy trình / Script: Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc) hoặc Tiktok-video
• Quy mô batch: 78 máy | Thành công: 0 | Thất bại: 78
❌ Signature: UploadScriptError:UploadHook: [MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control
```

## 2. Bản Chất & Cơ Chế Fail-Closed
- **Nguyên nhân:** Trong luồng TikTok upload / video picker hook (`scripts.tiktok_workflow.state_machine`), hệ thống định vị nút Tạo nội dung ("+" create entry) ở vị trí bottom-centre trên thanh điều hướng chính. Khi recaptured UI XML / surface không xác nhận được nhãn (`Tạo`, `Create`) hoặc bounds khớp với nút này, hook tự động kích hoạt fail-closed với mã `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.
- **Hành vi an toàn:** Thiết bị tự động dọn dẹp phiên và đưa về màn hình chính `LauncherActivity`, sau đó tắt màn hình về trạng thái `OFF (Sleep/Dozing)`. Toàn bộ thiết bị không bị treo phiên hay hao pin/nóng máy.

## 3. Quy Trình Khảo Sát Hiện Trường O(1) Qua Admin Remote Host
- **Không dùng `python -c` chứa subprocess:**
  Coordinator Guard sẽ chặn các lệnh `python -c` import `subprocess` hoặc thực hiện I/O với thông báo:
  `COORDINATOR TERMINAL BLOCKED: 'python -c' chỉ dùng để kiểm chứng read-only; phát hiện thao tác ghi/xóa/subprocess!`
- **Lệnh khảo sát chuẩn O(1):**
  1. Dùng tool chuẩn hóa theo invariant:
     ```bash
     python D:/Taadaa/tools/inspect_machine.py <Mxxx>
     ```
  2. Hoặc chạy lệnh ADB trực tiếp với socket cụm Admin:
     ```bash
     adb -H 192.168.110.119 -P 5037 -s <serial> shell dumpsys window windows | grep -E "mCurrentFocus|mFocusedApp"
     ```

## 4. Kỷ Luật Tránh Bẫy Quét Đĩa Diện Rộng (Guard Safety)
- CẤM gọi `search_files` hoặc `grep -rn` trên thư mục gốc `D:/Taadaa`, `D:/Taadaa/automation_core` hay `D:/Taadaa/tiktok-luot nuoi acc` vì sẽ kích hoạt `GUARD_SEARCH_FILES_ROOT` và `GUARD_DANGEROUS_ROOT`.
- Định vị repo và thư mục con bằng `ls -d "D:/Taadaa/"* | grep ...`, sau đó nhắm trúng thư mục lá cụ thể (`scripts/`, `python_runner/flows/`).

## 5. Hướng Xử Lý Khắc Phục (Recovery Playbook)
1. **Kiểm tra trạng thái thiết bị đại diện (Canary 1 máy):**
   - Xác nhận focus đã về `LauncherActivity` và màn hình `OFF`.
2. **Xử lý tài khoản văng phiên (P0 Missing Account nếu có):**
   - Nếu có máy dính `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING`, dùng `reconcile_tiktok_accounts.py` với host config `admin.yaml` và socket remote để nạp bù nick vào slot trống.
3. **Cập nhật Selector nút Create:**
   - Kiểm tra UI XML của phiên bản TikTok hiện tại trên máy để đối soát nhãn text và resource-id của nút "+", cập nhật selector trong `tiktok_workflow` với ngân sách O(1) <= 30 dòng, chạy Canary test trên 1 máy trước khi kích hoạt lại batch.

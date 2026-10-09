# Verification Checklist Cho OAuth Pipeline & Combo Mapping (OmniRoute)

Khi chạy pipeline nạp profile GPM, xác thực Google OAuth cho Antigravity và append vào combo trên OmniRoute:

## 1. File Status Pipeline (`oauth_pipeline_status.json`)
- Path: `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json`
- Cấu trúc: Các account thành công nằm trong dictionary `omniroute_success[email]`.
- Cần kiểm tra:
  - `email in data["omniroute_success"]`
  - `data["omniroute_success"][email]["connection_id"] == CID`
  - `data["omniroute_success"][email]["status"] == "HTTP_200_OK"`

## 2. OmniRoute Combo API Verification
- Không đọc trực tiếp file json tĩnh nếu server đang chạy in-memory hoặc lưu ở path khác.
- Endpoint kiểm tra: `GET http://127.0.0.1:20129/api/combos`
- Target combo ID: `22975610-b162-41b9-b6b3-30be076265bd` (`ag-gemini-pool-3`)
- Cần kiểm tra trong `pool["models"]`:
  - `any(m.get("connectionId") == CID for m in pool["models"]) == True`
  - Tổng số targets trong combo sau khi append tăng tương ứng.

## 3. Combo Backup Verification
- Kiểm tra file backup được sinh ra tại `D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json`.

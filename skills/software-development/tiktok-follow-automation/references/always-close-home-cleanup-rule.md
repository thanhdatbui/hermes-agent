# Cleanup & Teardown Protocol: Always Close to HOME on Success and Error

## Quy tắc bắt buộc khi kết thúc runner (follow_runner/run_follow.py)

1. **Luôn đóng app về HOME trong mọi tình huống**:
   - Dù runner kết thúc thành công (`OK`), thất bại follow (`FOLLOW_FAILED`), hay phát sinh bất kỳ lỗi nào (`MANUAL_REVIEW`, `CONTRACT_ERROR`, `EXCEPTION`, unhandled error), app TikTok và các app gần đây BẮT BUỘC phải được gọi `close_all_recent_apps()` để đưa thiết bị về màn hình HOME.
   - Tuyệt đối không chặn cleanup dựa trên điều kiện `res_status in ("OK", "FOLLOW_FAILED")`. Việc để app treo trên màn hình khi lỗi sẽ làm nghẽn các batch/job tiếp theo của farm.

2. **Bảo toàn root-cause error (Error Preservation)**:
   - Nếu phiên trước đó đang là CLEAN/OK: nếu `close_all_recent_apps()` thất bại, kết quả được chuyển thành `CLEANUP_FAILED` để không giấu lỗi kỹ thuật.
   - Nếu phiên trước đó ĐÃ là một lỗi (error/failed status): nếu việc cleanup thất bại, ghi log warning nhưng GIỮ NGUYÊN status và reason của lỗi gốc ban đầu, không được ghi đè bằng `CLEANUP_FAILED` làm mất dấu nguyên nhân gốc rễ phục vụ điều tra của operator.

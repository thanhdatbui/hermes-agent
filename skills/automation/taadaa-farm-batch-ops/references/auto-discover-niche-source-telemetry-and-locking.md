# Auto-Discovery Niche Source Telemetry, Locking & Sol Scorecard Standards

## 1. Zero Silent Exception Swallowing (Telemetry Requirements)
Trong các script cào và auto-discovery (e.g. `scripts/download_by_niche.py`), không bao giờ dùng `except Exception: pass` hoặc `except Exception: continue` âm thầm.
Mọi exception từ yt_dlp, probe kênh shorts, đọc ledger, claim ledger hoặc ghi file cấu hình sources đều phải được ghi nhận rõ ràng vào `sys.stderr` với prefix tag chuẩn:
- `AUTO_DISCOVER_LEDGER_READ_WARN: {e}`: Lỗi khi đọc keys từ global ledger.
- `AUTO_DISCOVER_QUERY_WARN query='{query}': {e}`: Lỗi khi search yt_dlp theo query niche.
- `AUTO_DISCOVER_PROBE_WARN channel={c_url}: {probe_err}`: Lỗi khi probe danh sách `/shorts` của channel ứng viên.
- `AUTO_DISCOVER_ENTRY_WARN: {entry_err}`: Lỗi khi bóc tách metadata channel URL / uploader_id của từng entry.
- `AUTO_DISCOVER_LEDGER_CLAIM_WARN: {e}`: Lỗi khi gọi claim_source vào global ledger.
- `AUTO_DISCOVER_SAVE_WARN: {e}`: Lỗi khi parse hoặc ghi file sources (.json / .jsonl).

## 2. Transactional Lock Coordination (`_DB_LOCK`)
Khi nhiều worker thread chạy đồng thời:
- Quá trình claim ledger, ghi file `sources` (.tmp + replace) và `sources.append(new_source)` PHẢI được bọc trong khối:
  ```python
  with _DB_LOCK:
      # 1. Claim global ledger
      # 2. Persist to sources file atomically (.tmp + replace)
      # 3. sources.append(new_source)
  ```
- Tránh race condition giữa các worker cùng discover ra 1 channel hoặc ghi đè file `sources` làm mất channel vừa thêm.

## 3. Test Pattern Chuẩn Cho Auto-Discovery (Happy Path)
Trong pytest (`tests/test_auto_discovery_and_clean.py`), cần có test case xác nhận luồng thành công:
1. Mock `yt_dlp.YoutubeDL`:
   - `extract_info(query, download=False)` trả về `{"entries": [{"channel_url": "https://www.youtube.com/@kenshorts", "uploader_id": "@kenshorts", "uploader": "Ken Shorts"}]}`
   - `extract_info("https://www.youtube.com/@kenshorts/shorts", download=False)` trả về danh sách >= `min_videos` entries hợp lệ.
2. Cung cấp file sources JSON tạm thời (`tmp_path / "sources.json"`).
3. Gọi `auto_discover_niche_source(...)`.
4. Assertions:
   - Trả về đối tượng `Source` với URL đúng.
   - File JSON được cập nhật chứa channel mới.
   - Danh sách `sources` truyền vào được append `new_source`.

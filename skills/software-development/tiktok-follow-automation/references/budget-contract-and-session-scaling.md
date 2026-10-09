# Follow Budget Contract & Session Scaling

## 1. Chuẩn Follow Budget Farm (10-20 follow/phiên, max 40/ngày)

Khi nâng hoặc điều chỉnh budget follow mỗi phiên trong repo `tiktok-follow`, bắt buộc phải patch đồng bộ đủ 4 vị trí để tránh drift giữa config mặc định, runtime fallback, test suite và các file machine YAML:

1. **`follow_runner/core/config.py`** (Data model & default schema):
   ```python
   budget_per_day: int = 40
   budget_per_session: int = 20
   budget_per_session_min: int | None = 10  # random range 10-20 mỗi phiên
   budget_per_session_max: int | None = 20
   ```

2. **`follow_runner/core/follow_state.py`** (Runtime fallback khi config truyền None):
   ```python
   base_min = int(getattr(cfg, "budget_per_session_min", None) or 10)
   base_max = int(getattr(cfg, "budget_per_session_max", None) or 20)
   ```

3. **`follow_runner/tests/test_follow_state.py`** (Unit test suite):
   - Cập nhật test `test_budget_random_range_falls_back_to_default_range_when_unset`:
   ```python
   picks = {st.session_budget(video_count=10) for _ in range(100)}
   assert picks <= set(range(10, 21))
   assert len(picks) > 1
   ```

4. **YAML Configs**:
   - `follow_runner/config.example.yaml`
   - Toàn bộ các file `config/machine*.yaml` (17 máy):
   ```yaml
   budget_per_session_min: 10
   budget_per_session_max: 20
   budget_per_session: 20
   budget_per_day: 40
   ```

## 2. Verification Gate
Chạy pytest xác nhận test suite budget pass 100%:
```bash
python -m pytest follow_runner/tests/test_follow_state.py -k "budget" -v
```

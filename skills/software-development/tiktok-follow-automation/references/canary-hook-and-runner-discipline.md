# Canary Hook & Runner Execution Discipline

## Entrypoint Imports Discipline
- `run_follow.py` thường được gọi trực tiếp bằng `python follow_runner/run_follow.py ...` (thay vì module mode `python -m follow_runner.run_follow`).
- Khi chạy script dạng entrypoint trực tiếp, `__name__ == '__main__'` và package context cấp cao không tồn tại.
- **Quy tắc bắt buộc**: Tuyệt đối không sử dụng relative imports (như `from .flows...`, `from .core...`) trong `run_follow.py` hay trong bất kỳ hook canary dispatch runtime nào (`--canary-hook`). Luôn sử dụng absolute imports (`from follow_runner.flows...`, `from follow_runner.core...`).
- Vi phạm quy tắc này sẽ gây ra crash tức thì:
  `ImportError: attempted relative import with no known parent package`

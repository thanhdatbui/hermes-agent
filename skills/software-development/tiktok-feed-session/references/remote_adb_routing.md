# Remote ADB Routing for Machines >= 200

## Architecture Overview
In the Taadaa farm setup, devices are partitioned between local USB/ADB servers and remote hosts:
- **Local devices (`machine < 200`):** Default ADB server (localhost / default daemon socket), `host=None, port=None`.
- **Remote / Admin devices (`machine >= 200`):** Located on dedicated remote machine `192.168.110.119:5037`.

## Multi-Machine Flow Integration (`multi_machine_feed_session.py`)
In `_build_child_context(ctx, account, child_config)`:
```python
remote_host = "192.168.110.119" if int(account.machine) >= 200 else None
remote_port = 5037 if int(account.machine) >= 200 else None
child_adb = AdbClient(
    adb_path=str(child_config.get("adb_path", "adb")),
    serial=account.serial,
    default_timeout=float(_cfg_subdict(child_config, "timeouts").get("adb_seconds", 15)),
    host=remote_host,
    port=remote_port,
)
```

## Testing & Verification
When adding or updating multi-machine runners that instantiate child contexts:
- Verify `child_ctx.adb.host == "192.168.110.119"` and `port == 5037` when `account.machine >= 200`.
- Verify `child_ctx.adb.host is None` for local machines (`machine < 200`).
- Test execution command:
  ```bash
  env -u PYTHONPATH -u PYTHONHOME D:/Taadaa/python-envs/automation/Scripts/pytest.exe "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_multi_machine_feed_session.py" -k "test_build_child_context"
  ```

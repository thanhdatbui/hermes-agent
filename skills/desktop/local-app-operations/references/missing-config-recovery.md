# Missing-config recovery reference

Use this reference when a local app's shortcut points to a config file that no longer exists.

## Recovery pattern

1. Read the launcher/shortcut target, arguments, and working directory. The launcher path is the source of truth for the intended runtime instance.
2. Check the target directory, its runtime/log subdirectory, known backups, and sync locations for the original config. Treat a PID file alone as stale evidence; verify the PID still exists and belongs to the target executable.
3. If no original config can be found, copy the example config shipped with the exact installed binary version into the launcher's expected path.
4. Change only values required by the launcher contract. For a port mismatch, update the config to the port expected by the existing clients/shortcut.
5. Remove sample API keys or placeholder credentials. Do not replace them with fabricated values and do not expose real secrets in logs or reports.
6. Start the exact executable with the exact config argument, capture stdout/stderr, and verify:
   - process command line contains the expected config path;
   - expected port is LISTENING and any old/default port is not;
   - `/`, management/dashboard endpoint, and `/v1/models` respond successfully;
   - startup logs show the intended version and no config-load failure.

## Important reporting distinction

A template-based recovery proves that the service is operational, not that the previous account pool or provider configuration was restored. Report missing auth/provider entries separately (for example, `service restored; accounts not restored`) and request the original config/auth backup if full recovery is required.

## Example failure shape

A typical launcher failure is a missing file error such as:

```text
failed to load config: failed to read config file: open <launcher-config-path>: The system cannot find the file specified
```

The correct fix is to restore or reconstruct the file at that exact path, not to modify an unrelated source checkout or neighboring local gateway.

# Feed failure taxonomy and execution-guard boundary

Use this reference when a watchdog report collapses multiple machine failures into one generic label or when a tool rejects a discovery command.

## Reliable diagnosis pattern

1. Treat the observed report/log as the source of truth; do not infer a permission failure from a rejected helper command.
2. Separate failure reasons before changing code:
   - Proxy: `proxy`, `http_proxy`, `missing proxy`, `no proxy`, or `:0`.
   - Wi-Fi/AP: `association_rejection`, `wifi`, `wlan0`, `carrier`, or `network disconnected`.
   - ADB/USB transport: `device not found`, `device offline`, `adb/usb`, or `transport`.
   - Remaining reasons: App TikTok/script.
3. Check proxy markers before Wi-Fi markers when a reason contains both network and proxy text.
4. Preserve the aggregate `Success/Fail/Empty` counts and add indented reason groups below `Fail`; this improves observability without changing run decisions.
5. Keep the patch offline/mockable: a pure classifier plus a small formatter/grouping test is enough. Do not probe devices to validate a reporting-only change.

## Guardrail versus edit permission

A runtime guard that rejects `os.walk`, recursive globbing, or another broad scan only rejects that operation. It does not prove that the target source is read-only or that `patch` is forbidden. Continue with a bounded absolute path and an allowlisted edit, or report the targeted write error if the write itself fails. Avoid telling the user “code is blocked” when only discovery was blocked.

## Windows verification pitfall

Run `python -m unittest test_module -q` from the target drive/repository directory. Passing an absolute test-file path on drive D: while the shell starts on drive C: can fail in unittest's `ntpath.relpath` before collection; that is a test invocation/path issue, not a source failure.

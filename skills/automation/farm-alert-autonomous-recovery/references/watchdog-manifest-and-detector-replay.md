# Watchdog manifest reconciliation and offline detector replay

## Reusable procedure

1. Parse each farm `run_manifest.json` and count `multi_machine_summary` by `final_status`. Use the machine-level list as the source of truth; compare aggregate `summary.txt` counters and explicitly record any mismatch.
2. For every alert machine, run the mandated O(1) probe: `python D:/Taadaa/tools/inspect_machine.py <N>`. Keep transient device/network/ATX failures separate from script blockers and from source rows with no account.
3. For a suspected UI detector issue, use the saved artifact `ui.xml` offline. Import the repository's XML parser, specialized detector, and top-level classifier; record detector result, classifier result, and the relevant close control/resource id. This is stronger evidence than inferring from the cron text or an unverified screenshot.
4. If the specialized detector matches but the top-level classifier returns `unknown`, inspect the existing allowlisted-popup path first. Prefer a minimal connection into that path; do not add a parallel detector or broaden matching for unrelated XML.
5. A diagnosis is not completion: continue to focused verification and, when applicable, a bounded canary. Report `BLOCKED` only with concrete command output and the exact remaining boundary.

## Replay pattern

```python
from automation_core.ui import parse_xml
from <specialized_module> import <specialized_detector>
from <classifier_module> import <top_level_classifier>

root = parse_xml(open("artifact/ui.xml", encoding="utf-8").read())
print("specialized:", <specialized_detector>(root))
print("classified:", <top_level_classifier>(root))
```

Replace the placeholders with the repository's actual modules; keep the probe offline and deterministic.

## Operator communication

Use direct, evidence-first status. Do not stop at a high-level explanation when a read-only manifest parse, per-machine inspect, artifact replay, or focused test remains available. Do not claim DONE without a real verification result.

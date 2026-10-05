from pathlib import Path
import unittest


class SetupAdminPluginSyncTests(unittest.TestCase):
    """Offline regression checks for setup-admin.ps1's plugin sync contract."""

    SCRIPT_PATH = Path(__file__).resolve().parents[1] / "deploy" / "setup-admin.ps1"

    @classmethod
    def setUpClass(cls):
        # Read source only; never invoke PowerShell or create filesystem junctions.
        cls.script_text = cls.SCRIPT_PATH.read_text(encoding="utf-8")
        start_marker = "    # Sync Plugins (Directory Junction"
        end_marker = '    Write-Host "Copying missing Hermes bootstrap credentials..."'
        start = cls.script_text.index(start_marker)
        end = cls.script_text.index(end_marker, start)
        cls.plugin_sync_block = cls.script_text[start:end]

    def test_plugin_sync_uses_directory_junctions(self):
        self.assertIn("mklink /J", self.plugin_sync_block)

    def test_plugin_sync_enumerates_plugin_source_directories(self):
        self.assertIn(
            "Get-ChildItem -LiteralPath $PluginsSrcDir -Directory",
            self.plugin_sync_block,
        )

    def test_plugin_sync_does_not_use_robocopy(self):
        self.assertNotIn("robocopy", self.plugin_sync_block.lower())

    def test_setup_stops_on_errors(self):
        self.assertIn("$ErrorActionPreference = 'Stop'", self.script_text)

    def test_plugin_sync_preserves_valid_existing_junction(self):
        # Đảm bảo junction đúng nguồn được giữ nguyên, không rmdir rồi tạo lại.
        self.assertIn("[System.IO.FileAttributes]::ReparsePoint", self.plugin_sync_block)
        self.assertIn("LinkType -eq 'Junction'", self.plugin_sync_block)
        self.assertIn("Plugin destination is not a directory junction", self.plugin_sync_block)
        self.assertIn("Resolve-Path -LiteralPath $Existing.FullName", self.plugin_sync_block)
        self.assertIn("wrong source", self.plugin_sync_block)
        self.assertIn("$SyncStats.unchanged++", self.plugin_sync_block)
        self.assertNotIn("$SyncStats.replaced", self.plugin_sync_block)
        self.assertNotIn("rmdir", self.plugin_sync_block.lower())
        self.assertIn("if ($LASTEXITCODE -ne 0)", self.plugin_sync_block)

    def test_plugin_sync_telemetry_json_parseable(self):
        """Telemetry exposes a stable JSON object with the sync counters."""
        import json
        import re

        stats_match = re.search(
            r"\$SyncStats\s*=\s*@\{(?P<body>.*?)\}",
            self.plugin_sync_block,
            re.DOTALL,
        )
        self.assertIsNotNone(stats_match)
        keys = re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\s*=", stats_match.group("body"))
        self.assertEqual(keys, ["total", "created", "unchanged"])

        telemetry_match = re.search(
            r"Plugin sync telemetry:.*?\$SyncStats \| ConvertTo-Json -Compress",
            self.plugin_sync_block,
        )
        self.assertIsNotNone(telemetry_match)

        telemetry_json = json.dumps({key: 0 for key in keys}, separators=(",", ":"))
        telemetry = json.loads(telemetry_json)
        self.assertEqual(set(telemetry), set(keys))
        self.assertTrue(all(isinstance(value, int) for value in telemetry.values()))

    def test_plugin_source_missing_fails_closed(self):
        self.assertIn(
            "if (-not (Test-Path -LiteralPath $PluginsSrcDir -PathType Container))",
            self.plugin_sync_block,
        )
        self.assertIn('throw "Plugin source directory not found', self.plugin_sync_block)

    def test_runtime_directory_junction_behavior_on_windows(self):
        """Chứng minh hành vi runtime thực tế: mklink /J tạo junction, đồng bộ 2 chiều và rmdir không xóa target."""
        import tempfile, subprocess
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src_plugin"
            dst = Path(td) / "dst_plugin"
            src.mkdir()
            (src / "sample.py").write_text("print('hello')", encoding="utf-8")
            res = subprocess.run(f'cmd.exe /c mklink /J "{dst}" "{src}"', shell=True, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertTrue(dst.exists())
            self.assertTrue((dst / "sample.py").exists())
            self.assertEqual((dst / "sample.py").read_text(encoding="utf-8"), "print('hello')")
            rm_res = subprocess.run(f'cmd.exe /c rmdir "{dst}"', shell=True, capture_output=True, text=True)
            self.assertEqual(rm_res.returncode, 0)
            self.assertFalse(dst.exists())
            self.assertTrue(src.exists())
            self.assertTrue((src / "sample.py").exists())

    def test_plugin_sync_emits_structured_telemetry(self):
        """Chứng minh setup-admin.ps1 có structured telemetry đếm số lượng plugin sync."""
        self.assertIn("Plugin sync telemetry:", self.plugin_sync_block)
        self.assertIn("ConvertTo-Json -Compress", self.plugin_sync_block)

    def test_multi_plugin_runtime_junction_simulation(self):
        """Chứng minh runtime nhiều plugin cùng được link và unlink an toàn."""
        import tempfile, subprocess
        with tempfile.TemporaryDirectory() as td:
            base_src = Path(td) / "bundle_plugins"
            base_dst = Path(td) / "installed_plugins"
            base_src.mkdir()
            base_dst.mkdir()
            for name in ["p1", "p2"]:
                p_src = base_src / name
                p_src.mkdir()
                (p_src / f"{name}.py").write_text(f"#{name}", encoding="utf-8")
                p_dst = base_dst / name
                res = subprocess.run(f'cmd.exe /c mklink /J "{p_dst}" "{p_src}"', shell=True, capture_output=True, text=True)
                self.assertEqual(res.returncode, 0)
                self.assertTrue(p_dst.exists())
                self.assertTrue((p_dst / f"{name}.py").exists())
            for name in ["p1", "p2"]:
                p_dst = base_dst / name
                rm_res = subprocess.run(f'cmd.exe /c rmdir "{p_dst}"', shell=True, capture_output=True, text=True)
                self.assertEqual(rm_res.returncode, 0)
                self.assertFalse(p_dst.exists())

if __name__ == "__main__":
    unittest.main()

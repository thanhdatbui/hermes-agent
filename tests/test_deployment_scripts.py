from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = REPO_ROOT / "deploy"


def read_deploy_file(name: str) -> str:
    return (DEPLOY_DIR / name).read_text(encoding="utf-8")


def test_skill_sync_uses_canonical_source_and_safe_robocopy_flags():
    script = read_deploy_file("sync-skills.ps1")
    normalized = script.lower()

    assert "join-path $reporoot 'skills'" in normalized
    assert "'/e'" in normalized
    assert "'/mir'" not in normalized
    assert "'/purge'" not in normalized
    assert "robocopy.exe" in normalized
    assert "if ($robocopyexitcode -gt 7)" in normalized
    for excluded in (
        ".usage.json",
        ".usage.json.lock",
        ".curator_state",
        ".bundled_manifest",
        "index-cache",
        "*.lock",
        "ticker*",
    ):
        assert excluded in normalized


def test_setup_syncs_skills_and_does_not_copy_snapshot():
    script = read_deploy_file("setup-admin.ps1")
    normalized = script.lower()

    assert "sync-skills.ps1" in normalized
    assert "& $syncskills -reporoot $reporoot" in normalized
    assert "get-childitem -literalpath $bundlehermes" not in normalized
    assert "copy-item -path (join-path $bundlecodex '*')" not in normalized
    assert not (DEPLOY_DIR / "hermes-home" / "skills").exists()


def test_setup_preserves_existing_bootstrap_credentials_and_codex_state():
    script = read_deploy_file("setup-admin.ps1").lower()

    assert "function copy-bootstrapfile" in script
    assert "-not (test-path -literalpath $destination)" in script
    for filename in (
        ".env",
        "auth.json",
        ".cockpit_codex_auth.json",
        ".codex-global-state.json",
    ):
        assert filename in script


def test_deployment_docs_and_ignore_define_one_skill_source():
    readme = read_deploy_file("README.md").lower()
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").lower()

    assert "repository root `skills/` directory is the sole canonical" in readme
    assert "sync-skills.ps1" in readme
    assert "deploy/hermes-home/skills/" in gitignore

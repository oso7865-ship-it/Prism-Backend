import json
from unittest.mock import patch

from pydantic import SecretStr

from app.shared.config.preflight import main, release_checks
from tests.test_production import production


def test_release_checks_reject_mutable_images_missing_ca_and_disabled_features(tmp_path):
    checks = release_checks(production(), "registry.example/prism:latest", tmp_path / "missing")
    assert not checks["immutable_image"]
    assert not checks["database_ca_file_present"]
    assert not checks["github_app"]
    assert not checks["ai_review"]
    assert not checks["sync_worker"]
    assert not checks["analysis_worker"]
    assert not release_checks(
        production(github_oauth_client_secret="REPLACE_SECRET"), "latest", tmp_path
    )["no_template_placeholders"]


def test_release_checks_report_only_presence_without_network_or_secret_values(tmp_path):
    ca = tmp_path / "ca.pem"
    ca.write_text("test CA fixture")
    settings = production(
        github_app_id=1,
        github_app_slug="test-app",
        github_app_client_id="test-id",
        github_app_client_secret="private fixture",
        github_app_private_key="private fixture",
        github_webhook_secret="test-webhook-secret-32-bytes-long",
        deepseek_api_key="private fixture",
        ai_enabled=True,
        sync_runner_enabled=True,
        analysis_runner_enabled=True,
    )
    checks = release_checks(settings, "registry.example/prism@sha256:" + "a" * 64, ca)
    assert all(checks.values())
    assert "private fixture" not in json.dumps(checks)
    assert isinstance(settings.deepseek_api_key, SecretStr)


def test_invalid_config_command_exits_nonzero_without_printing_input(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["preflight", "--image", "latest"])
    with patch("app.shared.config.preflight.Settings", side_effect=ValueError("private input")):
        assert main() == 1
    text = capsys.readouterr().out
    assert "private input" not in text
    assert json.loads(text)["status"] == "FAIL"

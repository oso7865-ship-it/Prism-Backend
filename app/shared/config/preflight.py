"""Offline production release checks. Never print settings, secrets or validation inputs."""

import argparse
import json
import re
from pathlib import Path

from pydantic import SecretStr, ValidationError

from app.shared.config.settings import Settings


def release_checks(settings: Settings, image: str, ca_file: Path) -> dict[str, bool]:
    values = settings.model_dump().values()
    placeholders = any(
        "REPLACE_" in (v.get_secret_value() if isinstance(v, SecretStr) else str(v)).upper()
        for v in values
    )
    return {
        "production": settings.app_env == "production",
        "immutable_image": bool(re.fullmatch(r"[a-z0-9][a-z0-9._/:-]*@sha256:[0-9a-f]{64}", image)),
        "authentication": settings.auth_ready,
        "github_app": settings.github_app_ready,
        "sync_worker": settings.sync_runner_enabled,
        "analysis_worker": settings.analysis_runner_enabled,
        "ai_review": settings.ai_enabled,
        "daily_limit": settings.ai_daily_limit == 30,
        "database_ca_file_present": ca_file.is_file() and 0 < ca_file.stat().st_size <= 1024 * 1024,
        "no_template_placeholders": not placeholders,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--ca-file", type=Path, default=Path("/run/prism/postgres-ca.pem"))
    args = parser.parse_args()
    try:
        settings = Settings(_env_file=None)
        checks = release_checks(settings, args.image, args.ca_file)
    except (ValidationError, OSError, ValueError):
        print(json.dumps({"status": "FAIL", "reason": "INVALID_RUNTIME_CONFIGURATION"}))
        return 1
    ok = all(checks.values())
    print(
        json.dumps(
            {
                "status": "PASS" if ok else "FAIL",
                "scope": "offline_configuration_only",
                "checks": checks,
            }
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

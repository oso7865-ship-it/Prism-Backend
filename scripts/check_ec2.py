"""Validate EC2 compose without starting services or reading a real runtime env file."""

import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory(prefix="prism-compose-test-") as folder:
        root = Path(folder)
        runtime = root / "runtime.env"
        # Dollar signs and literal newlines must reach Settings without interpolation.
        runtime.write_text("TEST_LITERAL=dollar$UNSET_TEST_VAR\\nend\n", encoding="utf-8")
        ca = root / "ca.pem"
        ca.write_text("synthetic CA presence fixture", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith("PRISM_")}
        command = ["docker", "compose", "--env-file", str(root / "empty.env"),
                   "-f", "deployment/compose.ec2.yaml", "config"]
        (root / "empty.env").write_text("", encoding="utf-8")
        missing = subprocess.run(command + ["--quiet"], env=env, capture_output=True, timeout=30)
        assert missing.returncode != 0, "Missing required deployment values must fail"
        env.update(PRISM_IMAGE="registry.example/prism@sha256:" + "a" * 64,
                   PRISM_ENV_FILE=str(runtime), PRISM_DB_CA_FILE=str(ca))
        result = subprocess.run(command + ["--format", "json"], env=env, capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError("COMPOSE_VALIDATION_FAILED; raw environment output suppressed")
        service = json.loads(result.stdout)["services"]["api"]
        assert service["ports"][0]["host_ip"] == "127.0.0.1"
        assert service["read_only"] and service["init"]
        assert service["restart"] == "unless-stopped" and service["pids_limit"] == 128
        assert int(service["mem_limit"]) == 1024**3
        assert service["cap_drop"] == ["ALL"]
        # Canonical compose output doubles $ to preserve it on a subsequent parse.
        assert service["environment"]["TEST_LITERAL"].replace("$$", "$") == "dollar$UNSET_TEST_VAR\\nend"
        assert "/health/ready" in service["healthcheck"]["test"][-1]
        assert service["volumes"][0]["read_only"]
        print(json.dumps({"status": "PASS", "started_services": 0, "real_secrets_read": False,
                          "missing_values_rejected": True, "raw_env_preserved": True}))


if __name__ == "__main__":
    main()

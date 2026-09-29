import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "deploy_ec2.py"
spec = importlib.util.spec_from_file_location("deploy_ec2", MODULE)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
NEW = deploy.REPOSITORY + "@sha256:" + "a" * 64
OLD = deploy.REPOSITORY + "@sha256:" + "b" * 64
REV = "c" * 40


class FakeDocker:
    def __init__(self, head="0009", failure=None, previous=OLD):
        self.head = head
        self.current = ["0009"] if previous else []
        self.previous = previous
        self.failure = failure
        self.calls = []

    def pull(self, image, revision):
        self.calls.append("pull")
        if self.failure == "pull":
            raise deploy.DeployError("IMAGE_PROVENANCE_MISMATCH")

    def preflight(self, image):
        self.calls.append("preflight")
        if self.failure == "preflight":
            raise deploy.DeployError("INVALID_RUNTIME_CONFIGURATION")

    def running_image(self, image):
        return self.previous

    def schema(self, image):
        self.calls.append("schema")
        return {"current": self.current[:], "target": [self.head if image == NEW else "0009"]}

    def migrate(self, image):
        self.calls.append("migrate")
        if self.failure == "migration":
            raise deploy.DeployError("MIGRATION_FAILED")
        self.current = [self.head]

    def start(self, image):
        self.calls.append(("start", image))
        if self.failure == "start" and image == NEW:
            raise deploy.DeployError("START_FAILED")

    def healthy(self, image):
        self.calls.append(("healthy", image))
        if self.failure == "health" and image == NEW:
            raise deploy.DeployError("READINESS_FAILED")
        if self.failure == "both_health":
            raise deploy.DeployError("READINESS_FAILED")


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = {
            "state_dir": str(self.root),
            "migration_policy": "upgrade",
            "backup_restore_verified_at": "2026-01-01T00:00:00+00:00",
        }

    def execute(self, docker, sequence=5):
        with contextlib.redirect_stdout(io.StringIO()):
            deploy.execute(self.config, NEW, REV, sequence, docker)

    def test_success_records_exact_image_and_schema(self):
        docker = FakeDocker()
        self.execute(docker)
        value = json.loads((self.root / "current.json").read_text())
        self.assertEqual((value["image"], value["revision"], value["schema"]), (NEW, REV, ["0009"]))
        self.assertLess(docker.calls.index("migrate"), docker.calls.index(("start", NEW)))
        self.assertEqual(value["status"], "SUCCESS")

    def test_injection_or_mutable_image_rejected_before_docker(self):
        for image in [
            NEW + ";id",
            deploy.REPOSITORY + ":latest",
            OLD.replace("oso7865-ship-it", "attacker"),
        ]:
            docker = FakeDocker()
            with self.assertRaises(deploy.DeployError):
                deploy.execute(self.config, image, REV, 5, docker)
            self.assertEqual(docker.calls, [])

    def test_preflight_and_provenance_failure_never_changes_database(self):
        for failure in ["pull", "preflight"]:
            docker = FakeDocker(failure=failure)
            with self.assertRaises(deploy.DeployError):
                self.execute(docker)
            self.assertNotIn("migrate", docker.calls)
            self.assertNotIn(("start", NEW), docker.calls)

    def test_migration_failure_does_not_replace_old_service(self):
        docker = FakeDocker(failure="migration")
        with self.assertRaises(deploy.DeployError):
            self.execute(docker)
        self.assertNotIn(("start", NEW), docker.calls)
        self.assertFalse((self.root / "current.json").exists())

    def test_failed_new_service_restores_old_image_but_deployment_fails(self):
        for failure in ["health", "start"]:
            docker = FakeDocker(failure=failure)
            with self.assertRaises(deploy.DeployError):
                self.execute(docker)
            self.assertIn(("start", OLD), docker.calls)
            self.assertIn(("healthy", OLD), docker.calls)
            state = json.loads((self.root / "attempt.json").read_text())
            self.assertEqual(state["rollback"], "RESTORED_PREVIOUS_IMAGE")
            self.assertEqual(state["status"], "FAILED")

    def test_schema_change_never_triggers_blind_image_or_db_downgrade(self):
        docker = FakeDocker(head="0010", failure="health")
        with self.assertRaises(deploy.DeployError):
            self.execute(docker)
        self.assertNotIn(("start", OLD), docker.calls)
        state = json.loads((self.root / "attempt.json").read_text())
        self.assertEqual(state["rollback"], "BLOCKED_SCHEMA_CHANGED")
        self.assertEqual(docker.current, ["0010"])

    def test_upgrade_requires_explicit_policy_and_backup_verification(self):
        for key, value in [("migration_policy", "unchanged"), ("backup_restore_verified_at", None)]:
            with self.subTest(key=key):
                previous = self.config[key]
                self.config[key] = value
                docker = FakeDocker(head="0010")
                with self.assertRaises(deploy.DeployError):
                    self.execute(docker)
                self.assertNotIn("migrate", docker.calls)
                self.config[key] = previous

    def test_older_main_run_cannot_overwrite_new_release(self):
        self.execute(FakeDocker(), sequence=10)
        docker = FakeDocker()
        with self.assertRaisesRegex(deploy.DeployError, "STALE"):
            self.execute(docker, sequence=9)
        self.assertEqual(docker.calls, [])

    def test_duplicate_run_with_different_image_is_rejected(self):
        self.execute(FakeDocker(), sequence=10)
        docker = FakeDocker()
        with self.assertRaisesRegex(deploy.DeployError, "STALE"):
            deploy.execute(self.config, OLD, REV, 10, docker)
        self.assertEqual(docker.calls, [])

    def test_parallel_process_cannot_enter_deployment_lock(self):
        command = [
            sys.executable,
            "-c",
            "import fcntl,sys; f=open(sys.argv[1],'w'); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)",
            str(self.root / "deploy.lock"),
        ]
        with deploy.deployment_lock(self.root):
            result = subprocess.run(command, capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(subprocess.run(command, capture_output=True, timeout=5).returncode, 0)

    def test_failed_rollback_is_recorded_without_false_success(self):
        with self.assertRaises(deploy.DeployError):
            self.execute(FakeDocker(failure="both_health"))
        state = json.loads((self.root / "attempt.json").read_text())
        self.assertEqual(state["rollback"], "FAILED_REQUIRES_OPERATOR")
        self.assertFalse((self.root / "current.json").exists())

    def test_timeout_cleans_up_only_the_named_migration_task(self):
        docker = deploy.Docker(
            {
                "docker_config": "/root/.docker",
                "runtime_env": "/private/runtime.env",
                "database_ca": "/private/ca.pem",
                "compose_file": "/trusted/compose.yaml",
            },
            123,
        )
        with (
            patch.object(docker, "compose", side_effect=deploy.DeployError("TIMEOUT")),
            patch.object(docker, "run") as run,
        ):
            with self.assertRaises(deploy.DeployError):
                docker.task(["alembic", "upgrade", "head"], NEW)
        self.assertEqual(run.call_args.args[0], ["rm", "-f", "prism-deploy-task-123"])

    def test_root_owned_file_under_user_owned_parent_is_rejected(self):
        target = self.root / "config.json"
        target.write_text("{}")
        target.chmod(0o600)
        real_stat = Path.stat

        def ownership(path, *args, **kwargs):
            values = list(real_stat(path, *args, **kwargs))
            if path == target:
                values[4] = 0
            if path == self.root:
                values[4] = 12345
            return os.stat_result(values)

        with patch.object(Path, "stat", ownership):
            with self.assertRaisesRegex(deploy.DeployError, "PARENT_MUST_BE_ROOT_OWNED"):
                deploy.protected_file(target, secret=True, root_owned=True)


if __name__ == "__main__":
    unittest.main()
